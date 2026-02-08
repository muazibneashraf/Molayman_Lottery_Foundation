from __future__ import annotations

from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    applications = db.relationship("Application", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class ClassFee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "Class 6"
    amount_bdt = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    class_fee_id = db.Column(db.Integer, db.ForeignKey("class_fee.id"), nullable=False)

    status = db.Column(db.String(20), default="pending", nullable=False)  # pending/accepted/rejected

    payment_method = db.Column(db.String(20), nullable=True)  # bkash/bank
    payment_reference = db.Column(db.String(120), nullable=True)
    payment_proof_filename = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    spin_discount_pct = db.Column(db.Integer, default=0, nullable=False)  # 0..30
    games_discount_pct = db.Column(db.Integer, default=0, nullable=False)  # 0..70
    bonus_discount_pct = db.Column(db.Integer, default=0, nullable=False)  # weekly challenge bonus
    bonus_week_key = db.Column(db.String(12), nullable=True)  # e.g. "2026-W06"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="applications")
    class_fee = db.relationship("ClassFee")

    @property
    def total_discount_pct(self) -> int:
        return min(
            70,
            int(self.spin_discount_pct or 0)
            + int(self.games_discount_pct or 0)
            + int(self.bonus_discount_pct or 0),
        )

    @property
    def fee_amount(self) -> int:
        return int(self.class_fee.amount_bdt)

    @property
    def discounted_amount(self) -> int:
        return int(round(self.fee_amount * (1 - (self.total_discount_pct / 100.0))))

    @property
    def can_spin(self) -> bool:
        # New rule: clients spin/play first, then pay the final amount.
        # Once payment is submitted, discounts are locked.
        return self.payment_method is None

    @property
    def discounts_locked(self) -> bool:
        return self.payment_method is not None


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=False, index=True)

    sender_role = db.Column(db.String(20), nullable=False)  # client/admin
    sender_name = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    application = db.relationship("Application")


class GameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=False, index=True)
    game_key = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    earned_discount_pct = db.Column(db.Integer, nullable=False, default=0)
    is_flagged = db.Column(db.Boolean, nullable=False, default=False)
    flag_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    application = db.relationship("Application")


class AdminAuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(40), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    admin = db.relationship("User")


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class BadgeAward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    badge_key = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(16), nullable=False, default="🏅")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "badge_key", name="uq_badge_user_key"),)


class UserActivityDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    day = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "day", name="uq_activity_user_day"),)


class UserGameStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    game_key = db.Column(db.String(50), nullable=False)
    plays_count = db.Column(db.Integer, nullable=False, default=0)
    best_score = db.Column(db.Integer, nullable=True)
    best_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "game_key", name="uq_game_stat_user_key"),)
