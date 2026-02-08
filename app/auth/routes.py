from __future__ import annotations

import secrets
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..extensions import db
from ..mail_utils import send_email
from ..models import User
from ..tokens import generate_token, verify_token
from .forms import ForgotPasswordForm, LoginForm, ResetPasswordForm, SignupForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.get("/login")
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect())

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if not user or not user.check_password(form.password.data):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", form=form)

        login_user(user)
        return redirect(_post_login_redirect())

    return render_template("auth/login.html", form=form)


@bp.get("/signup")
@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect())

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("That email is already registered. Please sign in.", "error")
            return render_template("auth/signup.html", form=form)

        user = User(email=email, name=form.name.data.strip(), is_admin=False)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("client.dashboard"))

    return render_template("auth/signup.html", form=form)


@bp.post("/logout")
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("main.index"))






@bp.get("/forgot")
@bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect())

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        # Do not reveal if the email exists.
        if user:
            token = generate_token("reset_password", email)
            link = url_for("auth.reset_password", token=token, _external=True)
            send_email(
                to=email,
                subject="Reset your password",
                text=f"Reset your password using this link (valid for 60 minutes):\n\n{link}\n",
                html=f"<p>Reset your password using this link (valid for 60 minutes):</p><p><a href=\"{link}\">{link}</a></p>",
            )

        flash("If that email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@bp.get("/reset/<token>")
@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if current_user.is_authenticated:
        return redirect(_post_login_redirect())

    data = verify_token("reset_password", token, max_age_seconds=60 * 60)
    if not data:
        flash("Reset link is invalid or expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    email = data["email"].lower().strip()
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Account not found.", "error")
        return redirect(url_for("auth.signup"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Password updated. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)


def _post_login_redirect():
    if current_user.is_authenticated and current_user.is_admin:
        return url_for("admin.dashboard")
    return url_for("client.dashboard")


