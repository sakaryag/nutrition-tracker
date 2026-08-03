"""
seed_data/badges_seed.py
========================
NutriTrack Family Mode — Badge Definitions & Seeder

BADGE_DEFINITIONS is the canonical list of all badges in the system.
seed_badges() upserts them into the `badge` table (separate from user_badge,
which tracks per-user awards).

The `badge` table schema (created here if absent):
    id          INTEGER / SERIAL  PK
    slug        TEXT / VARCHAR(64) UNIQUE NOT NULL
    name        TEXT / VARCHAR(128) NOT NULL
    description TEXT NOT NULL
    icon_emoji  TEXT / VARCHAR(8)  NOT NULL
    icon_class  TEXT / VARCHAR(64) NOT NULL

Idempotent: safe to call on every deploy / app startup.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from models import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Badge definitions — single source of truth
# ---------------------------------------------------------------------------

BADGE_DEFINITIONS: list[dict] = [
    {
        "slug": "7_day_streak",
        "name": "7-Day Streak",
        "description": "Logged food on 7 consecutive calendar days.",
        "icon_emoji": "🔥",
        "icon_class": "nt-icon-flame",
    },
    {
        "slug": "perfect_week",
        "name": "Perfect Week",
        "description": (
            "Hit all four macro targets (protein, fat, carbs, calories) "
            "every single day for a full ISO calendar week."
        ),
        "icon_emoji": "⭐",
        "icon_class": "nt-icon-star",
    },
    {
        "slug": "protein_king",
        "name": "Protein King",
        "description": (
            "Met your protein target (>= 90 % of goal) on at least 5 days "
            "in the last 30 days."
        ),
        "icon_emoji": "💪",
        "icon_class": "nt-icon-muscle",
    },
    {
        "slug": "hydration_hero",
        "name": "Hydration Hero",
        "description": (
            "Hit your daily water goal for 7 consecutive days. "
            "Requires a water goal to be set in your targets."
        ),
        "icon_emoji": "💧",
        "icon_class": "nt-icon-droplet",
    },
    {
        "slug": "early_bird",
        "name": "Early Bird",
        "description": (
            "Logged a Breakfast entry before 09:00 on 5 consecutive calendar days."
        ),
        "icon_emoji": "🌅",
        "icon_class": "nt-icon-sunrise",
    },
    {
        "slug": "consistent_30",
        "name": "Consistent",
        "description": (
            "Logged at least one food entry on every calendar day "
            "for 30 consecutive days in a row."
        ),
        "icon_emoji": "📅",
        "icon_class": "nt-icon-calendar",
    },
]


# ---------------------------------------------------------------------------
# Table bootstrap helpers
# ---------------------------------------------------------------------------

def _is_postgresql() -> bool:
    return str(db.engine.url).startswith("postgresql")


def _create_badge_table_if_absent() -> None:
    """Create the `badge` catalogue table if it does not exist."""
    if _is_postgresql():
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS badge (
                id          SERIAL PRIMARY KEY,
                slug        VARCHAR(64)  NOT NULL UNIQUE,
                name        VARCHAR(128) NOT NULL,
                description TEXT         NOT NULL,
                icon_emoji  VARCHAR(8)   NOT NULL DEFAULT '',
                icon_class  VARCHAR(64)  NOT NULL DEFAULT ''
            )
            """
        )
    else:
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS badge (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                slug        TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                description TEXT NOT NULL,
                icon_emoji  TEXT NOT NULL DEFAULT '',
                icon_class  TEXT NOT NULL DEFAULT ''
            )
            """
        )
    db.session.execute(sql)
    db.session.commit()


def _create_user_badge_table_if_absent() -> None:
    """Create the `user_badge` join table if it does not exist."""
    if _is_postgresql():
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS user_badge (
                id         SERIAL PRIMARY KEY,
                user_id    INTEGER      NOT NULL,
                badge_key  VARCHAR(64)  NOT NULL,
                awarded_at TIMESTAMP    NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, badge_key)
            )
            """
        )
    else:
        sql = text(
            """
            CREATE TABLE IF NOT EXISTS user_badge (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                badge_key  TEXT    NOT NULL,
                awarded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, badge_key)
            )
            """
        )
    db.session.execute(sql)
    db.session.commit()


# ---------------------------------------------------------------------------
# Public seeder
# ---------------------------------------------------------------------------

def seed_badges() -> None:
    """
    Upsert all badge definitions from BADGE_DEFINITIONS into the `badge` table.

    Idempotent: existing rows are updated to match the current definition so
    that description / icon changes propagate on the next deploy.

    Must be called inside a Flask application context with an active DB session.
    """
    _create_badge_table_if_absent()
    _create_user_badge_table_if_absent()

    if _is_postgresql():
        upsert_sql = text(
            """
            INSERT INTO badge (slug, name, description, icon_emoji, icon_class)
            VALUES (:slug, :name, :description, :icon_emoji, :icon_class)
            ON CONFLICT (slug) DO UPDATE SET
                name        = EXCLUDED.name,
                description = EXCLUDED.description,
                icon_emoji  = EXCLUDED.icon_emoji,
                icon_class  = EXCLUDED.icon_class
            """
        )
    else:
        upsert_sql = text(
            """
            INSERT INTO badge (slug, name, description, icon_emoji, icon_class)
            VALUES (:slug, :name, :description, :icon_emoji, :icon_class)
            ON CONFLICT (slug) DO UPDATE SET
                name        = excluded.name,
                description = excluded.description,
                icon_emoji  = excluded.icon_emoji,
                icon_class  = excluded.icon_class
            """
        )

    inserted = 0
    updated = 0

    for badge in BADGE_DEFINITIONS:
        # Check existence first to distinguish insert vs update for logging
        exists = db.session.execute(
            text("SELECT 1 FROM badge WHERE slug = :slug"),
            {"slug": badge["slug"]},
        ).fetchone()

        db.session.execute(upsert_sql, badge)

        if exists:
            updated += 1
        else:
            inserted += 1

    db.session.commit()
    logger.info(
        "seed_badges: %d inserted, %d updated (total %d badges).",
        inserted,
        updated,
        len(BADGE_DEFINITIONS),
    )


# ---------------------------------------------------------------------------
# CLI entry point (flask seed-badges)
# ---------------------------------------------------------------------------

def register_cli(app) -> None:
    """Register `flask seed-badges` CLI command on the given Flask app."""
    import click
    from flask.cli import with_appcontext

    @app.cli.command("seed-badges")
    @with_appcontext
    def seed_badges_command():
        """Upsert badge definitions into the database."""
        seed_badges()
        click.echo("Badge seeding complete.")
