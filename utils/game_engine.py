"""
utils/game_engine.py
====================
NutriTrack Family Mode — Game Engine Utilities

All functions are pure computation helpers that query the database and return
plain Python dicts/lists.  They do NOT import Flask's `current_app` so they
can be exercised in unit tests without an app context, but they DO require an
active SQLAlchemy session (i.e. call them from within a request context or a
test that has pushed an app context and set up the DB).

Public API
----------
calculate_daily_score(user_id, target_date) -> dict
calculate_weekly_score(user_id, week_start_date) -> dict
get_user_streak(user_id) -> int
check_and_award_badges(user_id) -> list[str]
"""

from __future__ import annotations

import logging
from datetime import date, time, timedelta
from typing import Optional

from sqlalchemy import func, text

from models import db
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.water_log import WaterLog
from models.daily_note import DailyNote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Badge catalogue
# ---------------------------------------------------------------------------

BADGE_CATALOG: dict[str, dict] = {
    "7_day_streak": {
        "name": "7-Day Streak",
        "description": "Logged food on 7 consecutive calendar days.",
        "icon_emoji": "🔥",
        "icon_class": "nt-icon-flame",
    },
    "perfect_week": {
        "name": "Perfect Week",
        "description": "Hit all four macro targets every single day for a full ISO week.",
        "icon_emoji": "⭐",
        "icon_class": "nt-icon-star",
    },
    "protein_king": {
        "name": "Protein King",
        "description": "Met your protein target (>= 90 %) for 5 days in the last 30.",
        "icon_emoji": "💪",
        "icon_class": "nt-icon-muscle",
    },
    "hydration_hero": {
        "name": "Hydration Hero",
        "description": "Hit your daily water goal for 7 consecutive days.",
        "icon_emoji": "💧",
        "icon_class": "nt-icon-droplet",
    },
    "early_bird": {
        "name": "Early Bird",
        "description": "Logged a Breakfast entry before 09:00 on 5 consecutive days.",
        "icon_emoji": "🌅",
        "icon_class": "nt-icon-sunrise",
    },
    "consistent_30": {
        "name": "Consistent",
        "description": "Logged at least one food entry on every calendar day for 30 days in a row.",
        "icon_emoji": "📅",
        "icon_class": "nt-icon-calendar",
    },
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _in_range(actual: float, target: float) -> bool:
    """Return True when actual is within 90–110 % of target."""
    if target <= 0:
        return False
    ratio = actual / target
    return 0.9 <= ratio <= 1.10


def _get_effective_target(user_id: int, target_date: date) -> Optional[DailyTarget]:
    """Return the DailyTarget row with the latest effective_from <= target_date."""
    return (
        DailyTarget.query
        .filter(
            DailyTarget.user_id == user_id,
            DailyTarget.effective_from <= target_date,
        )
        .order_by(DailyTarget.effective_from.desc())
        .first()
    )


def _daily_macro_totals(user_id: int, d: date) -> Optional[dict]:
    """
    Return aggregated macro totals for a user on a given date, or None if
    no entries exist.
    """
    row = (
        db.session.query(
            func.sum(FoodEntry.protein).label("protein"),
            func.sum(FoodEntry.fat).label("fat"),
            func.sum(FoodEntry.carbs).label("carbs"),
            func.sum(FoodEntry.calories).label("calories"),
            func.count(FoodEntry.id).label("entry_count"),
        )
        .filter(FoodEntry.user_id == user_id, FoodEntry.entry_date == d)
        .one()
    )
    if not row.entry_count:
        return None
    return {
        "protein": row.protein or 0.0,
        "fat": row.fat or 0.0,
        "carbs": row.carbs or 0.0,
        "calories": row.calories or 0.0,
        "entry_count": row.entry_count,
    }


def _daily_water_total(user_id: int, d: date) -> float:
    """Return total water logged (ml) for a user on a given date."""
    total = (
        db.session.query(func.sum(WaterLog.amount_ml))
        .filter(WaterLog.user_id == user_id, WaterLog.log_date == d)
        .scalar()
    )
    return total or 0.0


def _has_nonempty_note(user_id: int, d: date) -> bool:
    """Return True when a non-empty DailyNote exists for user on date."""
    note = (
        DailyNote.query
        .filter(DailyNote.user_id == user_id, DailyNote.note_date == d)
        .first()
    )
    return bool(note and note.content and note.content.strip())


def _has_early_breakfast(user_id: int, d: date) -> bool:
    """Return True when at least one Breakfast entry exists before 09:00."""
    cutoff = time(9, 0)
    entry = (
        FoodEntry.query
        .filter(
            FoodEntry.user_id == user_id,
            FoodEntry.entry_date == d,
            FoodEntry.meal_type == "Breakfast",
            FoodEntry.entry_time < cutoff,
        )
        .first()
    )
    return entry is not None


def _is_postgresql() -> bool:
    """Detect whether the active engine is PostgreSQL."""
    url = str(db.engine.url)
    return url.startswith("postgresql")


def _upsert_badge(user_id: int, badge_key: str) -> bool:
    """
    Insert a (user_id, badge_key) row into user_badge if it does not exist.
    Returns True if the row was newly inserted (badge just earned).

    The table is created by the badge seed / migration; we use raw SQL so we
    can target both SQLite and PostgreSQL with the appropriate ON CONFLICT
    clause without depending on a specific ORM model import.
    """
    if _is_postgresql():
        sql = text(
            """
            INSERT INTO user_badge (user_id, badge_key, awarded_at)
            VALUES (:uid, :bk, NOW())
            ON CONFLICT (user_id, badge_key) DO NOTHING
            """
        )
    else:
        sql = text(
            """
            INSERT OR IGNORE INTO user_badge (user_id, badge_key, awarded_at)
            VALUES (:uid, :bk, datetime('now'))
            """
        )

    result = db.session.execute(sql, {"uid": user_id, "bk": badge_key})
    db.session.commit()
    # rowcount == 1 means the row was inserted (new badge)
    return result.rowcount == 1


def _ensure_user_badge_table() -> None:
    """
    Create the user_badge table if it does not exist yet.
    Called lazily before badge operations so the engine is required.
    """
    if _is_postgresql():
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS user_badge (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                badge_key VARCHAR(64) NOT NULL,
                awarded_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, badge_key)
            )
            """
        )
    else:
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS user_badge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_key TEXT NOT NULL,
                awarded_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, badge_key)
            )
            """
        )
    db.session.execute(sql)
    db.session.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_daily_score(user_id: int, target_date: date) -> dict:
    """
    Compute the game score for a user on a specific date.

    Returns
    -------
    {
        "base": int,          # 0–100 (4 × 25 macro checks)
        "bonus": int,         # 0–13  (water +5, note +3, early_bird +5)
        "total": int,         # min(base + bonus, 115)
        "breakdown": {
            "protein_pts": int,   # 25 or 0
            "fat_pts": int,
            "carbs_pts": int,
            "calories_pts": int,
            "water_bonus": int,
            "note_bonus": int,
            "early_bird_bonus": int,
        }
    }
    """
    empty = {
        "base": 0,
        "bonus": 0,
        "total": 0,
        "breakdown": {
            "protein_pts": 0,
            "fat_pts": 0,
            "carbs_pts": 0,
            "calories_pts": 0,
            "water_bonus": 0,
            "note_bonus": 0,
            "early_bird_bonus": 0,
        },
    }

    target = _get_effective_target(user_id, target_date)
    if target is None:
        return empty

    totals = _daily_macro_totals(user_id, target_date)
    if totals is None:
        return empty

    # --- Base score (4 macro checks × 25 pts each) ---
    protein_pts = 25 if _in_range(totals["protein"], target.protein) else 0
    fat_pts = 25 if _in_range(totals["fat"], target.fat) else 0
    carbs_pts = 25 if _in_range(totals["carbs"], target.carbs) else 0
    calories_pts = 25 if _in_range(totals["calories"], target.calories) else 0
    base = protein_pts + fat_pts + carbs_pts + calories_pts

    # --- Bonus points ---
    water_bonus = 0
    if target.water_goal_ml is not None and target.water_goal_ml > 0:
        water_total = _daily_water_total(user_id, target_date)
        if water_total >= target.water_goal_ml:
            water_bonus = 5

    note_bonus = 3 if _has_nonempty_note(user_id, target_date) else 0

    early_bird_bonus = 5 if _has_early_breakfast(user_id, target_date) else 0

    bonus = water_bonus + note_bonus + early_bird_bonus
    total = min(base + bonus, 115)

    return {
        "base": base,
        "bonus": bonus,
        "total": total,
        "breakdown": {
            "protein_pts": protein_pts,
            "fat_pts": fat_pts,
            "carbs_pts": carbs_pts,
            "calories_pts": calories_pts,
            "water_bonus": water_bonus,
            "note_bonus": note_bonus,
            "early_bird_bonus": early_bird_bonus,
        },
    }


def calculate_weekly_score(user_id: int, week_start_date: date) -> dict:
    """
    Sum daily scores for Monday–Sunday of the ISO week containing week_start_date.
    Future days within the week contribute 0.

    Parameters
    ----------
    user_id : int
    week_start_date : date
        Must be a Monday (the function normalises to Monday regardless).

    Returns
    -------
    {
        "total": int,
        "perfect_days": int,   # days where base == 100
        "days": [
            {"date": "YYYY-MM-DD", "score": int, "base": int, "bonus": int},
            ...
        ]
    }
    """
    # Normalise to Monday of the given week
    monday = week_start_date - timedelta(days=week_start_date.weekday())
    today = date.today()

    days_data = []
    total = 0
    perfect_days = 0

    for offset in range(7):
        day = monday + timedelta(days=offset)
        if day > today:
            score_dict = {"base": 0, "bonus": 0, "total": 0}
        else:
            score_dict = calculate_daily_score(user_id, day)

        day_entry = {
            "date": day.isoformat(),
            "score": score_dict["total"],
            "base": score_dict["base"],
            "bonus": score_dict["bonus"],
        }
        days_data.append(day_entry)
        total += score_dict["total"]
        if score_dict["base"] == 100:
            perfect_days += 1

    return {
        "total": total,
        "perfect_days": perfect_days,
        "days": days_data,
    }


def get_user_streak(user_id: int) -> int:
    """
    Return the number of consecutive calendar days ending today on which the
    user has at least one food entry (score >= 1, i.e. any logging).

    Walks backward from today until a day with no entries is found.
    """
    streak = 0
    day = date.today()

    while True:
        count = (
            db.session.query(func.count(FoodEntry.id))
            .filter(FoodEntry.user_id == user_id, FoodEntry.entry_date == day)
            .scalar()
        )
        if not count:
            break
        streak += 1
        day -= timedelta(days=1)

    return streak


def check_and_award_badges(user_id: int) -> list[str]:
    """
    Evaluate all badge conditions for user_id and INSERT any newly earned
    badges into the user_badge table.

    Returns
    -------
    list[str]
        Badge keys that were *newly* awarded in this call (previously earned
        badges are silently skipped by the INSERT OR IGNORE / ON CONFLICT).
    """
    _ensure_user_badge_table()

    today = date.today()
    newly_earned: list[str] = []

    # Collect data we reuse across multiple badge checks (last 30 days)
    lookback_30 = today - timedelta(days=29)  # inclusive

    # --- Pre-fetch food entry dates in last 30 days ---
    entry_rows = (
        db.session.query(FoodEntry.entry_date, FoodEntry.meal_type, FoodEntry.entry_time)
        .filter(
            FoodEntry.user_id == user_id,
            FoodEntry.entry_date >= lookback_30,
            FoodEntry.entry_date <= today,
        )
        .all()
    )

    # Set of dates with any food entry
    logged_dates: set[date] = {r.entry_date for r in entry_rows}

    # --- Helper: consecutive days from today backwards in a set ---
    def _consecutive_back(date_set: set[date], from_date: date) -> int:
        count = 0
        d = from_date
        while d in date_set:
            count += 1
            d -= timedelta(days=1)
        return count

    # ================================================================
    # Badge 1: 7_day_streak
    # ================================================================
    streak = get_user_streak(user_id)
    if streak >= 7:
        if _upsert_badge(user_id, "7_day_streak"):
            newly_earned.append("7_day_streak")

    # ================================================================
    # Badge 2: perfect_week
    # Check last 14 days to capture a just-completed ISO week.
    # A "perfect week" means base == 100 on all 7 days of one ISO week.
    # ================================================================
    lookback_14 = today - timedelta(days=13)
    # Determine unique ISO weeks in the window
    iso_weeks: dict[tuple, list[date]] = {}
    for offset in range(14):
        d = lookback_14 + timedelta(days=offset)
        if d > today:
            break
        iso_key = d.isocalendar()[:2]  # (year, week)
        iso_weeks.setdefault(iso_key, []).append(d)

    for week_days in iso_weeks.values():
        if len(week_days) < 7:
            # Incomplete week in window — only evaluate full weeks
            continue
        all_perfect = all(
            calculate_daily_score(user_id, d)["base"] == 100
            for d in week_days
        )
        if all_perfect:
            if _upsert_badge(user_id, "perfect_week"):
                newly_earned.append("perfect_week")
            break  # one award is enough

    # ================================================================
    # Badge 3: protein_king
    # 5 days in the last 30 where protein intake >= 90 % of protein target.
    # (No upper bound — rewards high-protein days.)
    # ================================================================
    protein_hit_days = 0
    for offset in range(30):
        d = lookback_30 + timedelta(days=offset)
        if d > today:
            break
        target = _get_effective_target(user_id, d)
        if target is None:
            continue
        totals = _daily_macro_totals(user_id, d)
        if totals is None:
            continue
        if target.protein > 0 and totals["protein"] / target.protein >= 0.9:
            protein_hit_days += 1

    if protein_hit_days >= 5:
        if _upsert_badge(user_id, "protein_king"):
            newly_earned.append("protein_king")

    # ================================================================
    # Badge 4: hydration_hero
    # 7 consecutive days where water goal was met; skip if no goal set.
    # Evaluated over last 14 days.
    # ================================================================
    # Check if user has any water goal set (use today's effective target)
    current_target = _get_effective_target(user_id, today)
    if current_target and current_target.water_goal_ml:
        water_goal = current_target.water_goal_ml
        hydration_streak = 0
        for offset in range(14):
            d = today - timedelta(days=offset)
            t = _get_effective_target(user_id, d)
            goal = (t.water_goal_ml if t and t.water_goal_ml else water_goal)
            water_total = _daily_water_total(user_id, d)
            if water_total >= goal:
                hydration_streak += 1
            else:
                break  # streak broken

        if hydration_streak >= 7:
            if _upsert_badge(user_id, "hydration_hero"):
                newly_earned.append("hydration_hero")

    # ================================================================
    # Badge 5: early_bird
    # Breakfast entry before 09:00 on 5 consecutive days (last 30).
    # ================================================================
    # Build a set of dates with an early breakfast in the last 30 days
    cutoff = time(9, 0)
    early_breakfast_dates: set[date] = {
        r.entry_date
        for r in entry_rows
        if r.meal_type == "Breakfast" and r.entry_time is not None and r.entry_time < cutoff
    }

    # Find the longest consecutive streak from today backwards
    early_bird_streak = 0
    d = today
    while d in early_breakfast_dates:
        early_bird_streak += 1
        d -= timedelta(days=1)

    if early_bird_streak >= 5:
        if _upsert_badge(user_id, "early_bird"):
            newly_earned.append("early_bird")

    # ================================================================
    # Badge 6: consistent_30
    # At least one food entry on every calendar day for 30 consecutive days.
    # ================================================================
    # We need to go further back than 30 days because the streak may extend
    # beyond our 30-day pre-fetch window if all 30 days are covered.
    consistent_streak = _consecutive_back(logged_dates, today)
    if consistent_streak < 30:
        # Try to extend by fetching older dates (the pre-fetch only covers 30)
        if consistent_streak == 30:
            pass  # Already at 30 — but this branch won't fire
        else:
            # If all 30 days in our window are covered, look further back
            if len(logged_dates) == 30:
                # Build a full streak counter going back from 30 days ago
                extended = 30
                check_day = lookback_30 - timedelta(days=1)
                while True:
                    cnt = (
                        db.session.query(func.count(FoodEntry.id))
                        .filter(
                            FoodEntry.user_id == user_id,
                            FoodEntry.entry_date == check_day,
                        )
                        .scalar()
                    )
                    if not cnt:
                        break
                    extended += 1
                    check_day -= timedelta(days=1)
                consistent_streak = extended

    if consistent_streak >= 30:
        if _upsert_badge(user_id, "consistent_30"):
            newly_earned.append("consistent_30")

    return newly_earned
