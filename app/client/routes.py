from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path

from flask import Blueprint, flash, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..engagement import (
    badge_rules_after_game,
    compute_streak_days,
    maybe_award_discount_badges,
    maybe_award_weekly_bonus,
    record_activity_day,
    should_flag_score,
    update_user_game_stat,
    weekly_challenge_for_application,
)
from ..models import Announcement, Application, BadgeAward, ChatMessage, ClassFee, GameScore, UserGameStat

bp = Blueprint("client", __name__, url_prefix="/client")


def _require_client():
    if current_user.is_admin:
        flash("Admins must use the admin dashboard.", "error")
        return redirect(url_for("admin.dashboard"))
    return None


@bp.get("/dashboard")
@login_required
def dashboard():
    r = _require_client()
    if r:
        return r

    announcement = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).first()
    streak_days = compute_streak_days(current_user.id)
    recent_badges = (
        BadgeAward.query.filter_by(user_id=current_user.id)
        .order_by(BadgeAward.created_at.desc())
        .limit(5)
        .all()
    )

    class_fees = ClassFee.query.order_by(ClassFee.class_name.asc()).all()
    apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).all()
    return render_template(
        "client/dashboard.html",
        class_fees=class_fees,
        apps=apps,
        announcement=announcement,
        streak_days=streak_days,
        recent_badges=recent_badges,
    )


@bp.post("/apply")
@login_required
def apply():
    r = _require_client()
    if r:
        return r

    class_fee_id = int(request.form.get("class_fee_id"))
    class_fee = db.session.get(ClassFee, class_fee_id)
    if not class_fee:
        flash("Invalid class selection.", "error")
        return redirect(url_for("client.dashboard"))

    existing = Application.query.filter_by(user_id=current_user.id, class_fee_id=class_fee_id).first()
    if existing:
        flash("You already applied for this class.", "info")
        return redirect(url_for("client.application", app_id=existing.id))

    app_row = Application(user_id=current_user.id, class_fee_id=class_fee_id)
    db.session.add(app_row)
    db.session.commit()

    flash("Application created. Add payment to unlock spin & games.", "success")
    return redirect(url_for("client.application", app_id=app_row.id))


@bp.get("/application/<int:app_id>")
@login_required
def application(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    scores = GameScore.query.filter_by(application_id=app_row.id).order_by(GameScore.created_at.desc()).all()
    streak_days = compute_streak_days(current_user.id)
    recent_badges = (
        BadgeAward.query.filter_by(user_id=current_user.id)
        .order_by(BadgeAward.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "client/application.html",
        app=app_row,
        scores=scores,
        streak_days=streak_days,
        recent_badges=recent_badges,
    )


@bp.post("/application/<int:app_id>/payment")
@login_required
def payment(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()

    if app_row.payment_method is not None:
        flash("Payment already submitted for this application. Discounts are locked.", "info")
        return redirect(url_for("client.application", app_id=app_id))

    method = (request.form.get("method") or "").strip().lower()
    if method not in {"bkash", "bank"}:
        flash("Choose a valid payment method.", "error")
        return redirect(url_for("client.application", app_id=app_id))

    reference = (request.form.get("reference") or "").strip()
    if not reference:
        flash("Enter a transaction/reference id.", "error")
        return redirect(url_for("client.application", app_id=app_id))

    proof = request.files.get("proof")
    filename = None
    if proof and proof.filename:
        safe = secure_filename(proof.filename)
        filename = f"app_{app_id}_{int(datetime.utcnow().timestamp())}_{safe}"
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
        proof.save(str(upload_folder / filename))

    app_row.payment_method = method
    app_row.payment_reference = reference
    app_row.payment_proof_filename = filename
    app_row.paid_at = datetime.utcnow()

    record_activity_day(current_user.id)
    db.session.commit()

    # Badge: payment submitted
    from ..engagement import award_badge_once

    if award_badge_once(current_user.id, "payment_submitted", title="Payment Submitted", icon="💳"):
        flash("Badge unlocked: 💳 Payment Submitted", "success")

    flash("Payment submitted. You can now spin and play games.", "success")
    return redirect(url_for("client.application", app_id=app_id))


@bp.get("/uploads/<path:filename>")
@login_required
def uploads(filename: str):
    # Only allow client to fetch their own proof files by checking ownership via DB.
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(user_id=current_user.id, payment_proof_filename=filename).first_or_404()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], app_row.payment_proof_filename, as_attachment=False)


@bp.get("/application/<int:app_id>/spin")
@login_required
def spin_page(app_id: int):
    """Render the animated spin wheel page."""
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if app_row.discounts_locked:
        flash("Payment already submitted. Discounts are locked.", "error")
        return redirect(url_for("client.application", app_id=app_id))

    return render_template("client/spin.html", app=app_row)


@bp.post("/application/<int:app_id>/spin/result")
@login_required
def spin_result(app_id: int):
    """Return the spin result as JSON (without saving yet) for the animation."""
    r = _require_client()
    if r:
        return jsonify({"error": "admin"}), 403

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if app_row.discounts_locked or app_row.spin_discount_pct > 0:
        return jsonify({"discount": app_row.spin_discount_pct, "locked": True})

    # Weighted prizes, max 30
    prizes = [0, 5, 10, 12, 15, 18, 20, 25, 30]
    weights = [10, 18, 18, 14, 14, 10, 8, 6, 2]
    win = random.choices(prizes, weights=weights, k=1)[0]

    # Store in session temporarily so spin_submit can save it
    from flask import session
    session[f"spin_result_{app_id}"] = win

    return jsonify({"discount": win, "locked": False})


@bp.post("/application/<int:app_id>/spin/submit")
@login_required
def spin_submit(app_id: int):
    """Save the spin result after animation completes."""
    r = _require_client()
    if r:
        return jsonify({"error": "admin"}), 403

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if app_row.discounts_locked or app_row.spin_discount_pct > 0:
        return jsonify({"ok": False})

    from flask import session
    win = session.pop(f"spin_result_{app_id}", 0)
    app_row.spin_discount_pct = int(win)

    record_activity_day(current_user.id)

    from ..engagement import award_badge_once

    if win and int(win) >= 30:
        if award_badge_once(current_user.id, "spin_30", title="30% Spin Winner", icon="🎰"):
            flash("Badge unlocked: 🎰 30% Spin Winner", "success")

    db.session.commit()

    return jsonify({"ok": True, "discount": win})


@bp.post("/application/<int:app_id>/spin")
@login_required
def spin(app_id: int):
    """Legacy POST fallback (redirects to spin page)."""
    return redirect(url_for("client.spin_page", app_id=app_id))


@bp.get("/application/<int:app_id>/games")
@login_required
def games(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if app_row.discounts_locked:
        flash("Payment already submitted. Discounts are locked.", "error")
        return redirect(url_for("client.application", app_id=app_id))

    streak_days = compute_streak_days(current_user.id)
    weekly = weekly_challenge_for_application(app_row)
    plays_this_app = GameScore.query.filter_by(application_id=app_row.id).count()

    # Show a small "top" list of personal bests (top 5 by best_score)
    personal_bests = (
        UserGameStat.query.filter_by(user_id=current_user.id)
        .order_by(UserGameStat.best_score.desc().nullslast())
        .limit(5)
        .all()
    )

    return render_template(
        "client/games.html",
        app=app_row,
        streak_days=streak_days,
        weekly_challenge=weekly,
        plays_this_app=plays_this_app,
        personal_bests=personal_bests,
    )


@bp.post("/application/<int:app_id>/games/submit")
@login_required
def submit_game(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if app_row.discounts_locked:
        flash("Payment already submitted. Discounts are locked.", "error")
        return redirect(url_for("client.application", app_id=app_id))

    game_key = (request.form.get("game_key") or "").strip()
    score = int(request.form.get("score") or 0)

    # Fair play checks
    flagged, reason = should_flag_score(app_row, game_key, score)

    earned = _compute_game_discount(game_key, score)

    if flagged:
        earned = 0

    # Apply earned discount with cap
    before = app_row.total_discount_pct
    app_row.games_discount_pct = min(70, (app_row.games_discount_pct or 0) + earned)

    update_user_game_stat(current_user.id, game_key.lower(), score)
    record_activity_day(current_user.id)

    score_row = GameScore(
        application_id=app_row.id,
        game_key=game_key,
        score=score,
        earned_discount_pct=earned,
        is_flagged=bool(flagged),
        flag_reason=reason,
    )
    db.session.add(score_row)

    # Make pending inserts visible to subsequent queries.
    db.session.flush()

    # Weekly challenge bonus
    if maybe_award_weekly_bonus(app_row):
        flash("Weekly Challenge complete! Bonus +1% added.", "success")

    # Badges
    from ..engagement import award_badge_once

    unlocked_any = False
    for key, icon, title in badge_rules_after_game(current_user.id):
        if award_badge_once(current_user.id, key, title=title, icon=icon):
            flash(f"Badge unlocked: {icon} {title}", "success")
            unlocked_any = True

    for key, icon, title in maybe_award_discount_badges(current_user.id, app_row):
        if award_badge_once(current_user.id, key, title=title, icon=icon):
            flash(f"Badge unlocked: {icon} {title}", "success")
            unlocked_any = True

    db.session.commit()

    after = app_row.total_discount_pct
    if flagged:
        flash("Score submitted for review (fair play check). Discount not applied.", "info")
    elif earned > 0:
        flash(f"You earned +{earned}% discount from {game_key}. Total discount: {after}%.", "success")
    else:
        flash(f"Score submitted for {game_key}. Total discount: {after}%.", "info")

    if after == before and earned > 0:
        flash("Discount cap reached (70%).", "info")

    return redirect(url_for("client.games", app_id=app_id))


@bp.get("/leaderboard")
@login_required
def leaderboard():
    r = _require_client()
    if r:
        return r

    class_fees = ClassFee.query.order_by(ClassFee.class_name.asc()).all()
    class_fee_id = request.args.get("class_fee_id")
    selected_fee = None
    query = Application.query
    if class_fee_id:
        try:
            fee_id_int = int(class_fee_id)
            selected_fee = db.session.get(ClassFee, fee_id_int)
            if selected_fee:
                query = query.filter(Application.class_fee_id == fee_id_int)
        except ValueError:
            selected_fee = None

    apps = query.order_by(
        (Application.spin_discount_pct + Application.games_discount_pct + Application.bonus_discount_pct).desc(),
        Application.created_at.asc(),
    ).limit(10).all()

    leaderboard_rows = []
    for a in apps:
        # Privacy-safe label
        leaderboard_rows.append(
            {
                "label": f"Student #A{a.id:04d}",
                "class_name": a.class_fee.class_name,
                "discount": a.total_discount_pct,
            }
        )

    return render_template(
        "client/leaderboard.html",
        class_fees=class_fees,
        selected_fee=selected_fee,
        rows=leaderboard_rows,
    )


def _compute_game_discount(game_key: str, score: int) -> int:
    # Keep this intentionally simple & deterministic.
    game_key = game_key.lower()

    rules = {
        "click_rush": [(50, 1), (100, 2), (160, 3), (220, 4), (280, 5)],
        "reaction": [(900, 1), (700, 2), (550, 3), (450, 4), (350, 5)],  # lower is better (ms)
        "memory": [(3, 1), (5, 2), (7, 3), (9, 4), (11, 5)],
        "quiz": [(3, 1), (5, 2), (7, 3), (9, 4), (10, 5)],
        "lucky_number": [(30, 1), (45, 2), (60, 3), (75, 4), (90, 5)],
        "keymaster": [(20, 1), (35, 2), (50, 3), (65, 4), (80, 5)],
        "math_sprint": [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
        "coin_flip": [(4, 1), (6, 2), (7, 3), (8, 4), (9, 5)],
        "slider": [(60, 1), (70, 2), (80, 3), (90, 4), (97, 5)],
        "word_scramble": [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
        "timing_tap": [(3, 1), (5, 2), (6, 3), (8, 4), (9, 5)],
        "color_match": [(3, 1), (4, 2), (5, 3), (6, 4), (7, 5)],
        "pattern_memory": [(10, 1), (20, 2), (30, 3), (40, 4), (50, 5)],
        "catch_falling": [(10, 1), (20, 2), (30, 3), (40, 4), (50, 5)],
        "number_guess": [(30, 1), (40, 2), (50, 3), (60, 4), (70, 5)],
        # New games
        "emoji_roulette": [(10, 1), (20, 2), (30, 3), (50, 4), (70, 5)],
        "truth_or_dare": [(20, 1), (35, 2), (50, 3), (60, 4), (75, 5)],
        "would_you_rather": [(10, 1), (20, 2), (30, 3), (40, 4), (50, 5)],
        "pickup_line": [(15, 1), (30, 2), (45, 3), (55, 4), (70, 5)],
        "dad_joke": [(15, 1), (25, 2), (40, 3), (55, 4), (70, 5)],
        "hot_take": [(20, 1), (35, 2), (50, 3), (65, 4), (80, 5)],
        "drunk_walk": [(50, 1), (100, 2), (200, 3), (400, 4), (600, 5)],
        "speed_typer": [(20, 1), (40, 2), (60, 3), (80, 4), (100, 5)],
        "flirty_dice": [(12, 1), (24, 2), (36, 3), (48, 4), (60, 5)],
        "meme_caption": [(15, 1), (30, 2), (45, 3), (55, 4), (70, 5)],
        # Adults Only games
        "roast_master": [(10, 1), (25, 2), (45, 3), (65, 4), (80, 5)],
        "nsfw_trivia": [(15, 1), (30, 2), (45, 3), (60, 4), (75, 5)],
        "awkward_confess": [(15, 1), (30, 2), (50, 3), (65, 4), (80, 5)],
        "dirty_mind": [(20, 1), (35, 2), (50, 3), (60, 4), (75, 5)],
        "booty_shake": [(20, 1), (40, 2), (60, 3), (75, 4), (90, 5)],
        "savage_comeback": [(20, 1), (40, 2), (55, 3), (70, 4), (85, 5)],
        "never_have_i": [(20, 1), (35, 2), (50, 3), (65, 4), (80, 5)],
        "cursed_compliment": [(20, 1), (40, 2), (55, 3), (70, 4), (90, 5)],
        # High-Graphics 18+ Canvas Games
        "strip_pong": [(20, 1), (40, 2), (60, 3), (80, 4), (100, 5)],
        "naughty_snake": [(10, 1), (30, 2), (50, 3), (80, 4), (120, 5)],
        "kiss_catcher": [(30, 1), (60, 2), (100, 3), (150, 4), (200, 5)],
        "spank_mole": [(20, 1), (40, 2), (60, 3), (80, 4), (120, 5)],
        "body_shots": [(20, 1), (50, 2), (80, 3), (120, 4), (180, 5)],
        "twerk_runner": [(15, 1), (30, 2), (50, 3), (80, 4), (120, 5)],
        "strip_poker": [(20, 1), (40, 2), (50, 3), (70, 4), (90, 5)],
        "naughty_blocks": [(100, 1), (250, 2), (500, 3), (800, 4), (1200, 5)],
    }


@bp.get("/profile")
@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    r = _require_client()
    if r:
        return r

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if len(name) < 2:
            flash("Name must be at least 2 characters.", "error")
            return redirect(url_for("client.profile"))
        if len(name) > 120:
            flash("Name is too long.", "error")
            return redirect(url_for("client.profile"))

        current_user.name = name
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("client.profile"))

    apps = Application.query.filter_by(user_id=current_user.id).order_by(Application.created_at.desc()).all()
    badges = BadgeAward.query.filter_by(user_id=current_user.id).order_by(BadgeAward.created_at.desc()).all()
    streak_days = compute_streak_days(current_user.id)
    return render_template(
        "client/profile.html",
        apps=apps,
        badges=badges,
        streak_days=streak_days,
    )

    tiers = rules.get(game_key)
    if not tiers:
        return 0

    if game_key == "reaction":
        # score is ms; award more discount for smaller values
        earned = 0
        for max_ms, pct in tiers:
            if score <= max_ms:
                earned = pct
        return int(earned)

    earned = 0
    for min_score, pct in tiers:
        if score >= min_score:
            earned = pct
    return int(earned)


@bp.get("/application/<int:app_id>/chat")
@login_required
def chat(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    messages = ChatMessage.query.filter_by(application_id=app_row.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template("client/chat.html", app=app_row, messages=messages)


@bp.post("/application/<int:app_id>/chat")
@login_required
def chat_send(app_id: int):
    r = _require_client()
    if r:
        return r

    app_row = Application.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    text = (request.form.get("message") or "").strip()
    if not text:
        return redirect(url_for("client.chat", app_id=app_id))

    msg = ChatMessage(
        application_id=app_row.id,
        sender_role="client",
        sender_name=current_user.name,
        message=text,
    )
    db.session.add(msg)
    db.session.commit()
    return redirect(url_for("client.chat", app_id=app_id))
