from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AdminAuditLog, Announcement, Application, ChatMessage, ClassFee, GameScore, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin():
    if not current_user.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("client.dashboard"))
    return None


def _audit(
    action: str,
    *,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: str | None = None,
) -> None:
    try:
        db.session.add(
            AdminAuditLog(
                admin_user_id=current_user.id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=(request.headers.get("User-Agent") or "")[:255],
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()


@bp.get("/dashboard")
@login_required
def dashboard():
    r = _require_admin()
    if r:
        return r

    fees = ClassFee.query.order_by(ClassFee.class_name.asc()).all()
    apps = Application.query.order_by(Application.created_at.desc()).limit(50).all()
    return render_template("admin/dashboard.html", fees=fees, apps=apps)


@bp.get("/analytics")
@login_required
def analytics():
    r = _require_admin()
    if r:
        return r

    total_users = User.query.count()
    total_apps = Application.query.count()
    pending = Application.query.filter_by(status="pending").count()
    accepted = Application.query.filter_by(status="accepted").count()
    rejected = Application.query.filter_by(status="rejected").count()
    paid = Application.query.filter(Application.payment_method.isnot(None)).count()

    # Lightweight audit record for page access.
    _audit("view_analytics")

    return render_template(
        "admin/analytics.html",
        total_users=total_users,
        total_apps=total_apps,
        pending=pending,
        accepted=accepted,
        rejected=rejected,
        paid=paid,
    )


@bp.get("/audit")
@login_required
def audit_log():
    r = _require_admin()
    if r:
        return r

    logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(200).all()
    _audit("view_audit_log")
    return render_template("admin/audit.html", logs=logs)


@bp.get("/announcements")
@login_required
def announcements():
    r = _require_admin()
    if r:
        return r

    rows = Announcement.query.order_by(Announcement.created_at.desc()).limit(50).all()
    _audit("view_announcements")
    return render_template("admin/announcements.html", rows=rows)


@bp.post("/announcements")
@login_required
def announcements_create():
    r = _require_admin()
    if r:
        return r

    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    make_active = (request.form.get("is_active") == "1")

    if len(title) < 3 or len(body) < 3:
        flash("Title and body are required.", "error")
        return redirect(url_for("admin.announcements"))

    if make_active:
        Announcement.query.update({Announcement.is_active: False})

    row = Announcement(title=title[:120], body=body, is_active=make_active)
    db.session.add(row)
    db.session.commit()
    _audit("create_announcement", target_type="Announcement", target_id=row.id, detail=row.title)
    flash("Announcement saved.", "success")
    return redirect(url_for("admin.announcements"))


@bp.post("/announcements/<int:announcement_id>/toggle")
@login_required
def announcements_toggle(announcement_id: int):
    r = _require_admin()
    if r:
        return r

    row = db.session.get(Announcement, announcement_id)
    if not row:
        flash("Announcement not found.", "error")
        return redirect(url_for("admin.announcements"))

    new_state = not bool(row.is_active)
    if new_state:
        Announcement.query.update({Announcement.is_active: False})
    row.is_active = new_state
    db.session.commit()
    _audit(
        "toggle_announcement",
        target_type="Announcement",
        target_id=row.id,
        detail=f"is_active={row.is_active}",
    )
    flash("Announcement updated.", "success")
    return redirect(url_for("admin.announcements"))


@bp.get("/fair-play")
@login_required
def fair_play():
    r = _require_admin()
    if r:
        return r

    flagged = (
        GameScore.query.filter_by(is_flagged=True)
        .order_by(GameScore.created_at.desc())
        .limit(200)
        .all()
    )
    _audit("view_fair_play")
    return render_template("admin/fair_play.html", scores=flagged)


@bp.post("/fees/<int:fee_id>")
@login_required
def update_fee(fee_id: int):
    r = _require_admin()
    if r:
        return r

    fee = db.session.get(ClassFee, fee_id)
    if not fee:
        flash("Fee row not found.", "error")
        return redirect(url_for("admin.dashboard"))

    amount = int(request.form.get("amount_bdt") or 0)
    if amount <= 0:
        flash("Amount must be positive.", "error")
        return redirect(url_for("admin.dashboard"))

    old_amount = fee.amount_bdt
    fee.amount_bdt = amount
    fee.updated_at = datetime.utcnow()
    db.session.commit()

    _audit(
        "update_fee",
        target_type="ClassFee",
        target_id=fee.id,
        detail=f"{fee.class_name}: {old_amount} -> {amount}",
    )
    flash("Fee updated.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/applications/<int:app_id>/status")
@login_required
def set_application_status(app_id: int):
    r = _require_admin()
    if r:
        return r

    app_row = db.session.get(Application, app_id)
    if not app_row:
        flash("Application not found.", "error")
        return redirect(url_for("admin.dashboard"))

    status = (request.form.get("status") or "").strip().lower()
    if status not in {"pending", "accepted", "rejected"}:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.dashboard"))

    old_status = app_row.status
    app_row.status = status
    db.session.commit()
    _audit(
        "set_application_status",
        target_type="Application",
        target_id=app_row.id,
        detail=f"{old_status} -> {status}",
    )
    flash("Application status updated.", "success")
    return redirect(url_for("admin.application", app_id=app_id))


@bp.get("/applications/<int:app_id>")
@login_required
def application(app_id: int):
    r = _require_admin()
    if r:
        return r

    app_row = db.session.get(Application, app_id)
    if not app_row:
        flash("Application not found.", "error")
        return redirect(url_for("admin.dashboard"))

    user = db.session.get(User, app_row.user_id)
    messages = ChatMessage.query.filter_by(application_id=app_row.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template("admin/application.html", app=app_row, user=user, messages=messages)


@bp.post("/applications/<int:app_id>/chat")
@login_required
def chat_send(app_id: int):
    r = _require_admin()
    if r:
        return r

    app_row = db.session.get(Application, app_id)
    if not app_row:
        flash("Application not found.", "error")
        return redirect(url_for("admin.dashboard"))

    text = (request.form.get("message") or "").strip()
    if not text:
        return redirect(url_for("admin.application", app_id=app_id))

    msg = ChatMessage(
        application_id=app_row.id,
        sender_role="admin",
        sender_name="I am Molay Man",
        message=text,
    )
    db.session.add(msg)
    db.session.commit()
    _audit(
        "admin_chat_send",
        target_type="Application",
        target_id=app_row.id,
        detail=(text[:500] if text else None),
    )
    return redirect(url_for("admin.application", app_id=app_id))
