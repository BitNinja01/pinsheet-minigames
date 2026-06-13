from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

log = logging.getLogger("pinsheet")

plugin_info = {
    "name": "pinsheet-minigames",
    "version": "0.3.1",
    "description": "Group golf minigames — Par Bingo and more",
    "author": "PinSheet",
}

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS plugin_minigames_games (
        id            INTEGER PRIMARY KEY,
        game_type     TEXT NOT NULL,
        name          TEXT NOT NULL,
        buy_in        INTEGER NOT NULL DEFAULT 0,
        status        TEXT NOT NULL DEFAULT 'lobby',
        host_user_id  INTEGER NOT NULL,
        winner_user_id INTEGER,
        created_at    TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plugin_minigames_players (
        id       INTEGER PRIMARY KEY,
        game_id  INTEGER NOT NULL REFERENCES plugin_minigames_games(id),
        user_id  INTEGER NOT NULL REFERENCES users(id),
        joined_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(game_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plugin_minigames_rounds (
        id          INTEGER PRIMARY KEY,
        game_id     INTEGER NOT NULL REFERENCES plugin_minigames_games(id),
        user_id     INTEGER NOT NULL REFERENCES users(id),
        round_date  TEXT NOT NULL,
        round_index INTEGER NOT NULL DEFAULT 0,
        assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(game_id, user_id, round_date, round_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plugin_minigames_states (
        id         INTEGER PRIMARY KEY,
        game_id    INTEGER NOT NULL REFERENCES plugin_minigames_games(id),
        user_id    INTEGER NOT NULL REFERENCES users(id),
        state_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(game_id, user_id)
    )
    """,
]


def register(app):
    from .blueprint import bp

    _parent = Path(__file__).parent
    _static_dir = _parent / "static"

    db_path = app.config["DB_PATH"]
    db = sqlite3.connect(str(db_path))
    for ddl in _TABLES:
        db.execute(ddl)
    # Migration: add scoring mode columns if missing
    cols = {r[1] for r in db.execute("PRAGMA table_info(plugin_minigames_games)").fetchall()}
    if "par_scoring" not in cols:
        db.execute("ALTER TABLE plugin_minigames_games ADD COLUMN par_scoring TEXT")
    if "birdie_scoring" not in cols:
        db.execute("ALTER TABLE plugin_minigames_games ADD COLUMN birdie_scoring TEXT")
    db.commit()
    db.close()

    app.register_blueprint(bp, url_prefix="/minigames")

    pname = plugin_info["name"]
    head_tag = f'<link rel="stylesheet" href="/plugins/{pname}/static/minigames.css">'
    app._plugin_blocks["head"] = (
        (app._plugin_blocks.get("head", "") + "\n" + head_tag).strip()
    )

    app._plugin_nav.append({
        "label": "Minigames",
        "url": "/minigames",
        "page_id": "minigames",
    })

    log.info("minigames: registered v%s", plugin_info["version"])


def unregister(app):
    pname = plugin_info["name"]
    head_tag = f'<link rel="stylesheet" href="/plugins/{pname}/static/minigames.css">'
    current_head = app._plugin_blocks.get("head", "")
    app._plugin_blocks["head"] = current_head.replace(head_tag, "").strip()
    app._plugin_nav[:] = [n for n in app._plugin_nav if n.get("page_id") != "minigames"]
