from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .extensions import db
from .models import Application, BadgeAward, GameScore, UserActivityDay, UserGameStat


@dataclass(frozen=True)
class WeeklyChallenge:
    key: str
    title: str
    target: int
    progress: int
    reward_pct: int
    complete: bool
    week_key: str
    awarded: bool


def week_key_for(d: date | None = None) -> str:
    d = d or date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def record_activity_day(user_id: int, *, day: date | None = None) -> None:
    day = day or date.today()
    existing = UserActivityDay.query.filter_by(user_id=user_id, day=day).first()
    if existing:
        return
    row = UserActivityDay()
    row.user_id = user_id
    row.day = day
    db.session.add(row)


def compute_streak_days(user_id: int, *, today: date | None = None) -> int:
    today = today or date.today()

    # Pull the last ~40 days of activity and compute consecutive streak.
    window_start = today - timedelta(days=40)
    days = (
        UserActivityDay.query.filter(
            UserActivityDay.user_id == user_id,
            UserActivityDay.day >= window_start,
            UserActivityDay.day <= today,
        )
        .order_by(UserActivityDay.day.desc())
        .all()
    )
    day_set = {row.day for row in days}

    streak = 0
    cursor = today
    while cursor in day_set:
        streak += 1
        cursor = cursor - timedelta(days=1)

    return streak


def award_badge_once(user_id: int, badge_key: str, *, title: str, icon: str) -> bool:
    existing = BadgeAward.query.filter_by(user_id=user_id, badge_key=badge_key).first()
    if existing:
        return False
    row = BadgeAward()
    row.user_id = user_id
    row.badge_key = badge_key
    row.title = title
    row.icon = icon
    db.session.add(row)
    return True


def update_user_game_stat(user_id: int, game_key: str, score: int) -> None:
    row = UserGameStat.query.filter_by(user_id=user_id, game_key=game_key).first()
    now = datetime.utcnow()
    if not row:
        row = UserGameStat()
        row.user_id = user_id
        row.game_key = game_key
        row.plays_count = 0
        db.session.add(row)

    row.plays_count = int(row.plays_count or 0) + 1
    if row.best_score is None or score > int(row.best_score):
        row.best_score = score
        row.best_at = now
    row.updated_at = now


def weekly_challenge_for_application(app_row: Application) -> WeeklyChallenge:
    # Rotate between a few simple challenges based on the ISO week.
    today = date.today()
    wk = week_key_for(today)

    iso_year, iso_week, _ = today.isocalendar()
    rotation = iso_week % 2

    start = today - timedelta(days=today.weekday())  # Monday
    start_dt = datetime.combine(start, datetime.min.time())

    if rotation == 0:
        key = "play_5_games"
        title = "Weekly Challenge: Play 5 games"
        target = 5
        progress = (
            GameScore.query.filter(
                GameScore.application_id == app_row.id,
                GameScore.created_at >= start_dt,
                GameScore.is_flagged.is_(False),
            ).count()
        )
        reward = 1
    else:
        key = "play_3_unique"
        title = "Weekly Challenge: Play 3 different games"
        target = 3
        game_keys = (
            db.session.query(GameScore.game_key)
            .filter(GameScore.application_id == app_row.id, GameScore.created_at >= start_dt)
            .filter(GameScore.is_flagged.is_(False))
            .distinct()
            .all()
        )
        progress = len([k for (k,) in game_keys])
        reward = 1

    complete = progress >= target
    awarded = (app_row.bonus_week_key == wk) and (int(app_row.bonus_discount_pct or 0) > 0)
    return WeeklyChallenge(
        key=key,
        title=title,
        target=target,
        progress=progress,
        reward_pct=reward,
        complete=complete,
        week_key=wk,
        awarded=awarded,
    )


def maybe_award_weekly_bonus(app_row: Application) -> bool:
    ch = weekly_challenge_for_application(app_row)
    if not ch.complete:
        return False
    if ch.awarded:
        return False

    # Apply once per week per application.
    app_row.bonus_discount_pct = min(70, int(app_row.bonus_discount_pct or 0) + ch.reward_pct)
    app_row.bonus_week_key = ch.week_key
    return True


def should_flag_score(app_row: Application, game_key: str, score: int) -> tuple[bool, str | None]:
    # Very simple sanity checks to reduce obvious abuse.
    if score < 0:
        return True, "negative_score"
    if score > 100000:
        return True, "score_too_large"

    # Rapid submissions: more than 20 submissions in last 2 minutes for this application.
    since = datetime.utcnow() - timedelta(seconds=120)
    recent_count = GameScore.query.filter(
        GameScore.application_id == app_row.id,
        GameScore.created_at >= since,
    ).count()
    if recent_count >= 20:
        return True, "rapid_submissions"

    return False, None


def badge_rules_after_game(user_id: int) -> list[tuple[str, str, str]]:
    # Return list of (key, icon, title) badges that should be awarded now.
    total_plays = UserGameStat.query.filter_by(user_id=user_id).with_entities(db.func.sum(UserGameStat.plays_count)).scalar() or 0
    badges: list[tuple[str, str, str]] = []

    if total_plays >= 1:
        badges.append(("first_game", "🎮", "First Game"))
    if total_plays >= 5:
        badges.append(("games_5", "⭐", "5 Games Played"))
    if total_plays >= 10:
        badges.append(("games_10", "🔥", "10 Games Legend"))
    if total_plays >= 25:
        badges.append(("games_25", "👑", "Game Master"))

    return badges


def maybe_award_discount_badges(user_id: int, app_row: Application) -> list[tuple[str, str, str]]:
    badges: list[tuple[str, str, str]] = []
    if app_row.total_discount_pct >= 50:
        badges.append(("discount_50", "💎", "Reached 50% Discount"))
    if app_row.spin_discount_pct >= 30:
        badges.append(("spin_30", "🎰", "30% Spin Winner"))
    return badges
