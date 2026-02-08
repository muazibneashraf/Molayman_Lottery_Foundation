"""repair schema + add engagement tables/columns

Revision ID: 9a2f1b6d8c01
Revises: 82693a63ae3c
Create Date: 2026-02-08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "9a2f1b6d8c01"
down_revision = "82693a63ae3c"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    insp = inspect(bind)
    return set(insp.get_table_names())


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    insp = inspect(bind)
    return {c["name"] for c in insp.get_columns(table)}


def upgrade():
    tables = _table_names()

    # Add missing columns to existing tables (common if DB was created via create_all).
    if "user" in tables:
        cols = _column_names("user")
        if "email_verified_at" not in cols:
            with op.batch_alter_table("user") as batch_op:
                batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))

    if "application" in tables:
        cols = _column_names("application")
        with op.batch_alter_table("application") as batch_op:
            if "bonus_discount_pct" not in cols:
                batch_op.add_column(sa.Column("bonus_discount_pct", sa.Integer(), nullable=False, server_default="0"))
            if "bonus_week_key" not in cols:
                batch_op.add_column(sa.Column("bonus_week_key", sa.String(length=12), nullable=True))

    if "game_score" in tables:
        cols = _column_names("game_score")
        with op.batch_alter_table("game_score") as batch_op:
            if "is_flagged" not in cols:
                batch_op.add_column(sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.text("0")))
            if "flag_reason" not in cols:
                batch_op.add_column(sa.Column("flag_reason", sa.Text(), nullable=True))

    # Create missing tables (safe for fresh DB; guarded for existing DB).
    if "admin_audit_log" not in tables:
        op.create_table(
            "admin_audit_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("admin_user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("target_type", sa.String(length=40), nullable=True),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["admin_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_admin_audit_log_admin_user_id"), "admin_audit_log", ["admin_user_id"], unique=False)

    if "announcement" not in tables:
        op.create_table(
            "announcement",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "badge_award" not in tables:
        op.create_table(
            "badge_award",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("badge_key", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("icon", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "badge_key", name="uq_badge_user_key"),
        )
        op.create_index(op.f("ix_badge_award_user_id"), "badge_award", ["user_id"], unique=False)

    if "user_activity_day" not in tables:
        op.create_table(
            "user_activity_day",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("day", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "day", name="uq_activity_user_day"),
        )
        op.create_index(op.f("ix_user_activity_day_user_id"), "user_activity_day", ["user_id"], unique=False)

    if "user_game_stat" not in tables:
        op.create_table(
            "user_game_stat",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("game_key", sa.String(length=50), nullable=False),
            sa.Column("plays_count", sa.Integer(), nullable=False),
            sa.Column("best_score", sa.Integer(), nullable=True),
            sa.Column("best_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "game_key", name="uq_game_stat_user_key"),
        )
        op.create_index(op.f("ix_user_game_stat_user_id"), "user_game_stat", ["user_id"], unique=False)


def downgrade():
    # Best-effort rollback: drop the new tables and columns if present.
    tables = _table_names()

    if "user_game_stat" in tables:
        op.drop_index(op.f("ix_user_game_stat_user_id"), table_name="user_game_stat")
        op.drop_table("user_game_stat")

    if "user_activity_day" in tables:
        op.drop_index(op.f("ix_user_activity_day_user_id"), table_name="user_activity_day")
        op.drop_table("user_activity_day")

    if "badge_award" in tables:
        op.drop_index(op.f("ix_badge_award_user_id"), table_name="badge_award")
        op.drop_table("badge_award")

    if "announcement" in tables:
        op.drop_table("announcement")

    if "admin_audit_log" in tables:
        op.drop_index(op.f("ix_admin_audit_log_admin_user_id"), table_name="admin_audit_log")
        op.drop_table("admin_audit_log")

    if "game_score" in tables:
        cols = _column_names("game_score")
        with op.batch_alter_table("game_score") as batch_op:
            if "flag_reason" in cols:
                batch_op.drop_column("flag_reason")
            if "is_flagged" in cols:
                batch_op.drop_column("is_flagged")

    if "application" in tables:
        cols = _column_names("application")
        with op.batch_alter_table("application") as batch_op:
            if "bonus_week_key" in cols:
                batch_op.drop_column("bonus_week_key")
            if "bonus_discount_pct" in cols:
                batch_op.drop_column("bonus_discount_pct")

    if "user" in tables:
        cols = _column_names("user")
        if "email_verified_at" in cols:
            with op.batch_alter_table("user") as batch_op:
                batch_op.drop_column("email_verified_at")
