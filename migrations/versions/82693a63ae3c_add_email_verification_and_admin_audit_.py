"""initial schema (users, applications, scores, engagement)

Revision ID: 82693a63ae3c
Revises: 
Create Date: 2026-02-08 14:54:37.850011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82693a63ae3c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=False)

    op.create_table(
        "class_fee",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(length=20), nullable=False),
        sa.Column("amount_bdt", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_name"),
    )

    op.create_table(
        "application",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("class_fee_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("payment_reference", sa.String(length=120), nullable=True),
        sa.Column("payment_proof_filename", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("spin_discount_pct", sa.Integer(), nullable=False),
        sa.Column("games_discount_pct", sa.Integer(), nullable=False),
        sa.Column("bonus_discount_pct", sa.Integer(), nullable=False),
        sa.Column("bonus_week_key", sa.String(length=12), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["class_fee_id"], ["class_fee.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("sender_name", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_message_application_id"), "chat_message", ["application_id"], unique=False)

    op.create_table(
        "game_score",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("game_key", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("earned_discount_pct", sa.Integer(), nullable=False),
        sa.Column("is_flagged", sa.Boolean(), nullable=False),
        sa.Column("flag_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_game_score_application_id"), "game_score", ["application_id"], unique=False)

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

    op.create_table(
        "announcement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

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
    op.drop_index(op.f("ix_user_game_stat_user_id"), table_name="user_game_stat")
    op.drop_table("user_game_stat")

    op.drop_index(op.f("ix_user_activity_day_user_id"), table_name="user_activity_day")
    op.drop_table("user_activity_day")

    op.drop_index(op.f("ix_badge_award_user_id"), table_name="badge_award")
    op.drop_table("badge_award")

    op.drop_table("announcement")

    op.drop_index(op.f("ix_admin_audit_log_admin_user_id"), table_name="admin_audit_log")
    op.drop_table("admin_audit_log")

    op.drop_index(op.f("ix_game_score_application_id"), table_name="game_score")
    op.drop_table("game_score")

    op.drop_index(op.f("ix_chat_message_application_id"), table_name="chat_message")
    op.drop_table("chat_message")

    op.drop_table("application")
    op.drop_table("class_fee")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
