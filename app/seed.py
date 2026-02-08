from __future__ import annotations

from datetime import datetime

from .extensions import db
from .models import ClassFee, User


ADMIN_EMAIL = "iamsolayman@gg.com"
ADMIN_PASSWORD = "sexymolayman"
ADMIN_NAME = "I am Molay Man"


def ensure_seed_data() -> None:
    _ensure_admin_user()
    _ensure_default_class_fees()


def _ensure_admin_user() -> None:
    admin = User.query.filter_by(email=ADMIN_EMAIL).first()
    if admin:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
        return

    admin = User(email=ADMIN_EMAIL, name=ADMIN_NAME, is_admin=True, created_at=datetime.utcnow())
    admin.set_password(ADMIN_PASSWORD)
    db.session.add(admin)
    db.session.commit()


def _ensure_default_class_fees() -> None:
    defaults = {
        "Class 6": 10000,
        "Class 7": 11000,
        "Class 8": 12000,
        "Class 9": 13000,
        "Class 10": 14000,
        "Class 11": 15000,
        "Class 12": 16000,
    }

    for class_name, amount in defaults.items():
        row = ClassFee.query.filter_by(class_name=class_name).first()
        if not row:
            db.session.add(ClassFee(class_name=class_name, amount_bdt=amount))

    db.session.commit()
