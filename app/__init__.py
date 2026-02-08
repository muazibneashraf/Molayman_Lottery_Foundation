from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import stamp as migrate_stamp
from flask_migrate import upgrade as migrate_upgrade
from sqlalchemy import inspect
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db, login_manager, csrf, mail, migrate
from .seed import ensure_seed_data


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)

    @app.template_filter("bdt")
    def _bdt(value) -> str:
        try:
            amount = int(value or 0)
        except (TypeError, ValueError):
            return "0 BDT"
        return f"{amount:,} BDT"

    # Respect X-Forwarded-* headers (Render/Vercel/reverse proxies)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    default_db_path = Path(app.instance_path) / "app.db"
    default_db_uri = f"sqlite:///{default_db_path.as_posix()}"

    raw_db_uri = os.getenv("DATABASE_URL")
    db_uri = (raw_db_uri or "").strip()
    # Render dashboard sometimes leads people to paste labeled values like:
    # "Internal Database URL: postgresql://...". Extract the URL if needed.
    if db_uri and (" " in db_uri or "\n" in db_uri):
        match = re.search(r"(postgres(?:ql)?://\S+|sqlite:////?\S+)", db_uri)
        if match:
            db_uri = match.group(1)
    db_uri = db_uri.strip().strip('"').strip("'")
    if not db_uri:
        db_uri = default_db_uri

    # Render/Heroku style URLs use postgres:// which SQLAlchemy doesn't accept.
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)

    # If DATABASE_URL is malformed (common copy/paste issue on Render), do not crash.
    # Fall back to local SQLite and log a hint.
    try:
        make_url(db_uri)
    except ArgumentError as e:
        hint = (raw_db_uri or "").strip().replace("\n", " ")
        hint = (hint[:120] + "...") if len(hint) > 120 else hint
        app.logger.error(
            "Invalid DATABASE_URL; falling back to SQLite. Provide a full URL like "
            "postgresql://USER:PASSWORD@HOST:PORT/DBNAME . Got: %r (%s)",
            hint,
            e,
        )
        db_uri = default_db_uri

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", "uploads"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        # Email (Flask-Mail)
        MAIL_SERVER=os.getenv("MAIL_SERVER", ""),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USE_TLS=(os.getenv("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}),
        MAIL_USE_SSL=(os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes"}),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", ""),

    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    from .main.routes import bp as main_bp
    from .auth.routes import bp as auth_bp
    from .client.routes import bp as client_bp
    from .admin.routes import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        auto_migrate_env = os.getenv("AUTO_MIGRATE")
        if auto_migrate_env is None:
            # Default: auto-migrate only for local SQLite.
            auto_migrate = db_uri.startswith("sqlite")
        else:
            auto_migrate = auto_migrate_env.lower() in {"1", "true", "yes"}

        if auto_migrate:
            try:
                insp = inspect(db.engine)
                tables = set(insp.get_table_names())

                # If DB was created via db.create_all (no alembic_version) but tables exist,
                # stamp it to the base revision so we can run the "repair" migration.
                if "alembic_version" not in tables and {"user", "application", "class_fee"} & tables:
                    migrate_stamp(revision="82693a63ae3c")

                migrate_upgrade()
            except Exception as e:
                app.logger.warning("Auto-migrate failed (continuing): %s", e)
        else:
            # For local/dev convenience when migrations are disabled.
            if os.getenv("AUTO_CREATE_DB", "true").lower() in {"1", "true", "yes"}:
                db.create_all()

        try:
            ensure_seed_data()
        except SQLAlchemyError as e:
            # This can happen if the DB schema hasn't been migrated yet.
            app.logger.warning("Skipping seed (database not ready yet): %s", e)

    return app
