# PinSheet Minigames — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A PinSheet Server plugin for asynchronous group golf games, starting with Par Bingo.

**Architecture:** Flask Blueprint with templates extending base.html, game engine registry pattern for extensibility, SQLite tables for persistence.

**Tech Stack:** Python 3, Flask, SQLite, Jinja2, CSS custom properties

---

### Task 1: Plugin Scaffold + DB Schema

**Files:**
- Create: `plugins/pinsheet-minigames/__init__.py`

This is the plugin entry point. It defines `plugin_info`, creates DB tables in `register()`, registers the Blueprint, adds the sidebar nav link, and injects the CSS block.

```python
from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

from .blueprint import bp

log = logging.getLogger("pinsheet")

plugin_info = {
    "name": "pinsheet-minigames",
    "version": "0.1.0",
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
    _parent = Path(__file__).parent
    _static_dir = _parent / "static"

    db_path = app.config["DB_PATH"]
    db = sqlite3.connect(str(db_path))
    for ddl in _TABLES:
        db.execute(ddl)
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
```

- [ ] **Step 1: Create `__init__.py`** with the content above
- [ ] **Step 2: Verify the file parses**

Run: `python -m py_compile plugins/pinsheet-minigames/__init__.py`
Expected: no errors (note: will fail on `blueprint` import until Task 3, but the file itself should be syntactically valid)

- [ ] **Step 3: Commit**

```bash
git add plugins/pinsheet-minigames/__init__.py
git commit -m "feat(minigames): plugin scaffold with DB schema and nav"
```

---

### Task 2: Engine Framework

**Files:**
- Create: `plugins/pinsheet-minigames/engine.py`

The game engine registry and Par Bingo implementation. Contains the abstract base, the registry, and `ParBingoEngine`.

```python
from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path
from typing import Any

log = logging.getLogger("pinsheet")

_engines: dict[str, type["GameEngine"]] = {}


def register_engine(engine_cls: type["GameEngine"]) -> type["GameEngine"]:
    _engines[engine_cls.type_id] = engine_cls
    return engine_cls


def get_engine(game_type: str) -> "GameEngine | None":
    cls = _engines.get(game_type)
    return cls() if cls else None


def get_available_types() -> list[dict]:
    return [
        {
            "type_id": cls.type_id,
            "name": cls.display_name,
            "description": cls.description,
            "min_players": cls.min_players,
            "max_players": cls.max_players,
            "duration": cls.duration,
            "complexity": cls.complexity,
        }
        for cls in _engines.values()
    ]


class GameEngine:
    type_id: str = ""
    display_name: str = ""
    description: str = ""
    min_players: int = 1
    max_players: int = 99
    duration: str = "Multi-round"
    complexity: str = "Simple"

    def create_state(self, game: dict) -> dict:
        raise NotImplementedError

    def process_round(self, game: dict, player_state: dict, round_data: dict, db_path: Path) -> dict:
        raise NotImplementedError

    def check_victory(self, game: dict, player_state: dict) -> bool:
        raise NotImplementedError

    def prize_breakdown(self, game: dict, player_states: list[dict]) -> dict:
        raise NotImplementedError


def _compute_course_handicap(handicap_index: float, slope: int, rating: float, par: int) -> int:
    return round(handicap_index * (slope / 113) + (rating - par))


def _strokes_received(course_handicap: int, hole_index: int) -> int:
    if course_handicap <= 0:
        return 0
    full = course_handicap // 18
    extra = course_handicap % 18
    return full + (1 if hole_index <= extra else 0)


@register_engine
class ParBingoEngine(GameEngine):
    type_id = "par_bingo"
    display_name = "Par Bingo"
    description = "Cross off pars and birdies on your 18-hole card. First to fill it wins the pot."
    min_players = 2
    max_players = 8
    duration = "Multi-round"
    complexity = "Simple"

    def create_state(self, game: dict) -> dict:
        holes = {}
        for i in range(1, 19):
            holes[str(i)] = {"par": False, "birdie": False}
        return {"holes": holes}

    def process_round(self, game: dict, player_state: dict, round_data: dict, db_path: Path) -> dict:
        holes = dict(player_state.get("holes", {}))
        course_name = round_data.get("course", "")
        tees_name = round_data.get("tees", "")
        hi_str = round_data.get("computed_handicap", "")
        try:
            handicap_index = float(hi_str) if hi_str else 0.0
        except ValueError:
            handicap_index = 0.0

        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT data FROM courses WHERE name = ?", (course_name,)).fetchone()
        db.close()

        if not row:
            log.warning("par_bingo: course %r not found", course_name)
            return player_state

        course_data = json.loads(row["data"])
        course_par = int(course_data.get("par", 72))
        tee_data = course_data.get("tees", {}).get(tees_name, {})
        slope = int(tee_data.get("slope", 113))
        rating = float(tee_data.get("rating", 72.0))
        course_holes = course_data.get("holes", {})

        course_handicap = _compute_course_handicap(handicap_index, slope, rating, course_par)

        round_holes = round_data.get("holes", {})
        for hole_num_str, hole_info in round_holes.items():
            if hole_num_str not in holes:
                continue
            try:
                gross = int(hole_info.get("gross", 0))
            except (ValueError, TypeError):
                continue

            hole_def = course_holes.get(hole_num_str, {})
            hole_par = int(hole_def.get("par", 4))
            hole_idx = int(hole_def.get("hole_index", 9))

            strokes = _strokes_received(course_handicap, hole_idx)
            net = gross - strokes

            if net <= hole_par:
                holes[hole_num_str]["par"] = True
            if net < hole_par:
                holes[hole_num_str]["birdie"] = True

        return {"holes": holes}

    def check_victory(self, game: dict, player_state: dict) -> bool:
        holes = player_state.get("holes", {})
        for h_data in holes.values():
            if not h_data.get("par") or not h_data.get("birdie"):
                return False
        return True

    def prize_breakdown(self, game: dict, player_states: list[dict]) -> dict:
        buy_in = game.get("buy_in", 0)
        n = len(player_states)
        pot = buy_in * n

        winner_state = None
        winner_id = None
        for ps in player_states:
            if self.check_victory(game, ps["state"]):
                winner_state = ps["state"]
                winner_id = ps["user_id"]
                break

        if winner_id is None:
            return {}

        winner_birdies = sum(
            1 for h in winner_state.get("holes", {}).values() if h.get("birdie")
        )
        result = {}
        for ps in player_states:
            uid = ps["user_id"]
            if uid == winner_id:
                result[uid] = pot + (winner_birdies * (n - 1))
            else:
                result[uid] = -buy_in - winner_birdies

        return result
```

- [ ] **Step 1: Create `engine.py`** with the content above
- [ ] **Step 2: Verify the file parses**

Run: `python -m py_compile plugins/pinsheet-minigames/engine.py`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add plugins/pinsheet-minigames/engine.py
git commit -m "feat(minigames): game engine registry and ParBingoEngine"
```

---

### Task 3: Blueprint + Routes

**Files:**
- Create: `plugins/pinsheet-minigames/blueprint.py`

```python
from __future__ import annotations

import json
import sqlite3
import logging
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, g, jsonify
from flask_login import login_required, current_user

from .engine import get_engine, get_available_types

log = logging.getLogger("pinsheet")
bp = Blueprint("minigames", __name__)


def _db_path(app) -> Path:
    return app.config["DB_PATH"]


def _get_games_for_user(user_id: int, db_path: Path, status: str | None = None) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    if status:
        rows = db.execute(
            """SELECT g.*, COUNT(DISTINCT p.id) as player_count
               FROM plugin_minigames_games g
               LEFT JOIN plugin_minigames_players p ON p.game_id = g.id
               WHERE g.status = ?
               GROUP BY g.id
               ORDER BY g.created_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT g.*, COUNT(DISTINCT p.id) as player_count
               FROM plugin_minigames_games g
               LEFT JOIN plugin_minigames_players p ON p.game_id = g.id
               WHERE g.host_user_id = ? OR g.id IN (SELECT game_id FROM plugin_minigames_players WHERE user_id = ?)
               GROUP BY g.id
               ORDER BY g.created_at DESC""",
            (user_id, user_id),
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _is_player(game_id: int, user_id: int, db_path: Path) -> bool:
    db = sqlite3.connect(str(db_path))
    row = db.execute(
        "SELECT 1 FROM plugin_minigames_players WHERE game_id = ? AND user_id = ?",
        (game_id, user_id),
    ).fetchone()
    db.close()
    return row is not None


def _get_player_states(game_id: int, db_path: Path) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT s.*, p.user_id, u.display_name
           FROM plugin_minigames_states s
           JOIN plugin_minigames_players p ON p.game_id = s.game_id AND p.user_id = s.user_id
           JOIN users u ON u.id = p.user_id
           WHERE s.game_id = ?
           ORDER BY (
               SELECT COUNT(*)
               FROM json_each(s.state_json, '$.holes')
               WHERE json_extract(value, '$.par') = 1 AND json_extract(value, '$.birdie') = 1
           ) DESC""",
        (game_id,),
    ).fetchall()
    db.close()
    results = []
    for r in rows:
        state = json.loads(r["state_json"])
        holes_data = state.get("holes", {})
        pars = sum(1 for h in holes_data.values() if h.get("par"))
        birdies = sum(1 for h in holes_data.values() if h.get("birdie"))
        results.append({
            "user_id": r["user_id"],
            "display_name": r["display_name"],
            "state": state,
            "pars": pars,
            "birdies": birdies,
            "total": pars + birdies,
        })
    return results


def _get_unassigned_rounds(user_id: int, game_id: int, db_path: Path) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT r.* FROM rounds r
           WHERE r.user_id = ?
           AND NOT EXISTS (
               SELECT 1 FROM plugin_minigames_rounds mr
               WHERE mr.game_id = ? AND mr.user_id = r.user_id
               AND mr.round_date = r.date AND mr.round_index = r.round_index
           )
           ORDER BY r.date DESC, r.round_index DESC""",
        (user_id, game_id),
    ).fetchall()
    db.close()
    return [
        {
            "date": r["date"],
            "round_index": r["round_index"],
            "course": r["course_name"],
            "total_gross": r["total_gross"],
            "label": f'{r["date"]} — {r["course_name"]} ({r["total_gross"]})',
        }
        for r in rows
    ]


@bp.route("/")
@login_required
def dashboard():
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path(bp.app)

    active = _get_games_for_user(uid, dbp, "active")
    lobby = _get_games_for_user(uid, dbp, "lobby")
    completed = _get_games_for_user(uid, dbp, "complete")
    game_types = get_available_types()

    return render_template(
        "minigames_dashboard.html",
        active_games=active,
        lobby_games=lobby,
        completed_games=completed,
        game_types=game_types,
        current_page="minigames",
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_game():
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path(bp.app)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        game_type = request.form.get("game_type", "").strip()
        buy_in_str = request.form.get("buy_in", "0").strip()
        try:
            buy_in = int(buy_in_str) if buy_in_str else 0
        except ValueError:
            buy_in = 0

        if not name or not game_type:
            game_types = get_available_types()
            return render_template(
                "minigames_new.html",
                game_types=game_types,
                error="Name and game type are required.",
                current_page="minigames",
            )

        engine = get_engine(game_type)
        if engine is None:
            game_types = get_available_types()
            return render_template(
                "minigames_new.html",
                game_types=game_types,
                error=f"Unknown game type '{game_type}'.",
                current_page="minigames",
            )

        db = sqlite3.connect(str(dbp))
        cur = db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id) VALUES (?, ?, ?, ?)",
            (game_type, name, buy_in, uid),
        )
        game_id = cur.lastrowid
        db.execute(
            "INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)",
            (game_id, uid),
        )
        initial_state = engine.create_state({"buy_in": buy_in})
        db.execute(
            "INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
            (game_id, uid, json.dumps(initial_state)),
        )
        db.commit()
        db.close()

        return redirect(url_for("minigames.game_detail", id=game_id))

    game_types = get_available_types()
    return render_template(
        "minigames_new.html",
        game_types=game_types,
        current_page="minigames",
    )


@bp.route("/<int:id>")
@login_required
def game_detail(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path(bp.app)

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row
    row = db.execute(
        "SELECT * FROM plugin_minigames_games WHERE id = ?",
        (id,),
    ).fetchone()
    db.close()

    if not row:
        return "Game not found", 404

    game = dict(row)
    engine = get_engine(game["game_type"])
    is_member = _is_player(id, uid, dbp)
    player_states = _get_player_states(id, dbp) if is_member else []

    my_state = None
    my_pars = 0
    my_birdies = 0
    if is_member:
        for ps in player_states:
            if ps["user_id"] == uid:
                my_state = ps["state"]
                my_pars = ps["pars"]
                my_birdies = ps["birdies"]
                break

    # Fetch course hole pars for the bingo card display (use first player's/round's course)
    hole_pars = [4] * 18
    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row
    round_row = db.execute(
        """SELECT r.* FROM plugin_minigames_rounds mr
           JOIN rounds r ON r.date = mr.round_date AND r.round_index = mr.round_index AND r.user_id = mr.user_id
           WHERE mr.game_id = ? LIMIT 1""",
        (id,),
    ).fetchone()
    db.close()
    if round_row:
        course_name = round_row["course_name"]
        db = sqlite3.connect(str(dbp))
        db.row_factory = sqlite3.Row
        course_row = db.execute(
            "SELECT data FROM courses WHERE name = ?",
            (course_name,),
        ).fetchone()
        db.close()
        if course_row:
            course_data = json.loads(course_row["data"])
            ch = course_data.get("holes", {})
            hole_pars = [int(ch.get(str(i), {}).get("par", 4)) for i in range(1, 19)]

    unassigned_rounds = _get_unassigned_rounds(uid, id, dbp) if is_member else []

    return render_template(
        "minigames_detail.html",
        game=game,
        engine=engine,
        is_member=is_member,
        my_state=my_state,
        my_pars=my_pars,
        my_birdies=my_birdies,
        player_states=player_states,
        hole_pars=hole_pars,
        unassigned_rounds=unassigned_rounds,
        current_page="minigames",
    )


@bp.route("/<int:id>/join", methods=["POST"])
@login_required
def join_game(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path(bp.app)

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row
    game_row = db.execute(
        "SELECT * FROM plugin_minigames_games WHERE id = ?",
        (id,),
    ).fetchone()
    if not game_row:
        db.close()
        return "Game not found", 404
    game = dict(game_row)

    if game["status"] not in ("lobby", "active"):
        db.close()
        return "Game is closed", 400

    existing = db.execute(
        "SELECT 1 FROM plugin_minigames_players WHERE game_id = ? AND user_id = ?",
        (id, uid),
    ).fetchone()
    if existing:
        db.close()
        return redirect(url_for("minigames.game_detail", id=id))

    db.execute(
        "INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)",
        (id, uid),
    )
    engine = get_engine(game["game_type"])
    initial_state = engine.create_state(game)
    db.execute(
        "INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
        (id, uid, json.dumps(initial_state)),
    )

    if game["status"] == "lobby":
        db.execute(
            "UPDATE plugin_minigames_games SET status = 'active' WHERE id = ?",
            (id,),
        )

    db.commit()
    db.close()
    return redirect(url_for("minigames.game_detail", id=id))


@bp.route("/<int:id>/log-round", methods=["POST"])
@login_required
def log_round(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path(bp.app)

    round_date = request.form.get("round_date", "")
    round_index_str = request.form.get("round_index", "0")
    try:
        round_index = int(round_index_str)
    except ValueError:
        round_index = 0

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row

    game_row = db.execute(
        "SELECT * FROM plugin_minigames_games WHERE id = ?",
        (id,),
    ).fetchone()
    if not game_row:
        db.close()
        return "Game not found", 404
    game = dict(game_row)

    round_row = db.execute(
        "SELECT * FROM rounds WHERE user_id = ? AND date = ? AND round_index = ?",
        (uid, round_date, round_index),
    ).fetchone()
    if not round_row:
        db.close()
        return "Round not found", 404

    round_data = {
        "course": round_row["course_name"],
        "tees": round_row["tee_name"],
        "holes": json.loads(round_row["holes"] or "{}"),
        "total_gross": round_row["total_gross"],
        "computed_handicap": round_row["computed_handicap"],
    }

    existing = db.execute(
        "SELECT 1 FROM plugin_minigames_rounds WHERE game_id = ? AND user_id = ? AND round_date = ? AND round_index = ?",
        (id, uid, round_date, round_index),
    ).fetchone()
    if existing:
        db.close()
        return redirect(url_for("minigames.game_detail", id=id))

    db.execute(
        "INSERT INTO plugin_minigames_rounds (game_id, user_id, round_date, round_index) VALUES (?, ?, ?, ?)",
        (id, uid, round_date, round_index),
    )

    state_row = db.execute(
        "SELECT * FROM plugin_minigames_states WHERE game_id = ? AND user_id = ?",
        (id, uid),
    ).fetchone()

    engine = get_engine(game["game_type"])
    if engine and state_row:
        current_state = json.loads(state_row["state_json"])
        new_state = engine.process_round(game, current_state, round_data, dbp)
        db.execute(
            "UPDATE plugin_minigames_states SET state_json = ?, updated_at = datetime('now') WHERE game_id = ? AND user_id = ?",
            (json.dumps(new_state), id, uid),
        )

        if engine.check_victory(game, new_state):
            db.execute(
                "UPDATE plugin_minigames_games SET status = 'complete', winner_user_id = ?, completed_at = datetime('now') WHERE id = ?",
                (uid, id),
            )

    db.commit()
    db.close()
    return redirect(url_for("minigames.game_detail", id=id))
```

- [ ] **Step 1: Create `blueprint.py`** with the content above
- [ ] **Step 2: Verify the file parses**

Run: `python -m py_compile plugins/pinsheet-minigames/blueprint.py`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add plugins/pinsheet-minigames/blueprint.py
git commit -m "feat(minigames): blueprint with all routes"
```

---

### Task 4: Dashboard Template

**Files:**
- Create: `plugins/pinsheet-minigames/templates/minigames_dashboard.html`

Template for `/minigames`. Shows active games, available game types catalog, and all-time stats.

```html
{% extends "base.html" %}
{% block content %}
<style>
.minigames-body {
  padding: 28px 48px 32px;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  height: 100%;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  --ink: #ecebe6;
  --ink-2: #a8a59d;
  --ink-3: #6c685f;
  --rule: #2a2925;
  --accent: #5db49a;
  --paper-2: #1c1c1a;
  --warn: #d96a6a;
}
.minigames-body .ey {
  font: 500 10px/1.45 'IBM Plex Mono', monospace;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.minigames-body h1 {
  font: 400 32px/1.05 'IBM Plex Mono', monospace;
  margin: 4px 0 0;
  letter-spacing: -0.025em;
}
.minigames-body h1 em { font-style: italic; color: var(--accent); font-weight: 400; }
.minigames-body h2 {
  font: 400 18px/1.2 'IBM Plex Mono', monospace;
  margin: 0;
}
.minigames-body .chip {
  display: inline-flex;
  padding: 5px 10px;
  font: 500 10px/1 'IBM Plex Mono', monospace;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  border: 1px solid var(--rule);
  color: var(--ink-2);
}
.minigames-body .chip.mint { border-color: var(--accent); color: var(--accent); }
.minigames-body .btn {
  font: 500 11px/1 'IBM Plex Mono', monospace;
  padding: 8px 16px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: #131312;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}
.minigames-body .btn.ghost {
  background: transparent;
  color: var(--ink);
}
.minigames-body .hero-num {
  font-family: 'Barlow Condensed', 'Oswald', sans-serif;
  font-weight: 200;
  line-height: 0.85;
  letter-spacing: -0.04em;
}
.minigames-body .pbar { height: 3px; background: var(--rule); width: 100%; }
.minigames-body .pfill { height: 100%; background: var(--accent); }
.minigames-body .game-card {
  background: var(--paper-2);
  border: 1px solid var(--rule);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  cursor: pointer;
  transition: border-color 200ms;
}
.minigames-body .game-card:hover { border-color: var(--ink-3); }
.minigames-body .game-type-row {
  display: grid;
  grid-template-columns: 200px 1fr 80px 100px 100px 90px;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--rule);
}
.minigames-body .game-type-row:last-child { border-bottom: none; }
a.game-card-link { text-decoration: none; color: inherit; display: block; }
a.game-card-link:hover { text-decoration: none; }
</style>

<div class="minigames-body">
  <div style="display: flex; justify-content: space-between; align-items: flex-end; padding-bottom: 12px; border-bottom: 1px solid var(--rule);">
    <div>
      <div class="ey">Games · Hub</div>
      <h1><em>Minigames</em></h1>
    </div>
    <div style="display: flex; gap: 8px;">
      <a href="{{ url_for('minigames.new_game') }}" class="btn">+ New game</a>
    </div>
  </div>

  <div style="flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 36px; padding-top: 24px;">

    {# Active games #}
    <div>
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px;">
        <div style="display: flex; align-items: baseline; gap: 10px;">
          <div class="ey">Active games</div>
          <span style="font-size: 11px; color: var(--ink-3);">{{ active_games|length }}</span>
        </div>
      </div>
      {% if active_games %}
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
        {% for g in active_games %}
        <a href="{{ url_for('minigames.game_detail', id=g.id) }}" class="game-card-link">
          <div class="game-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div class="ey">{{ g.game_type.replace('_', ' ') }}</div>
              <div style="display: flex; gap: 6px;">
                <span class="chip mint">Active</span>
              </div>
            </div>
            <div>
              <h2>{{ g.name }}</h2>
              <div style="font-size: 11px; color: var(--ink-3); margin-top: 4px;">
                {{ g.player_count }} players{% if g.buy_in %} · ${{ g.buy_in }} buy-in{% endif %}
              </div>
            </div>
            <div>
              <div class="ey" style="margin-bottom: 4px;">Pot</div>
              <div class="hero-num" style="font-size: 48px;">
                <span style="color: var(--ink-3);">$</span>{{ g.buy_in * g.player_count }}
              </div>
            </div>
          </div>
        </a>
        {% endfor %}
      </div>
      {% else %}
      <p style="color: var(--ink-3); font-size: 13px;">No active games. <a href="{{ url_for('minigames.new_game') }}" style="color: var(--accent);">Create one</a>.</p>
      {% endif %}
    </div>

    {# Available game types #}
    <div>
      <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px;">
        <div class="ey">Available game types</div>
        <span style="font-size: 11px; color: var(--ink-3);">{{ game_types|length }}</span>
      </div>
      <div style="display: grid; grid-template-columns: 200px 1fr 80px 100px 100px 90px; gap: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--ink);">
        <div class="ey">Game</div>
        <div class="ey">Description</div>
        <div class="ey" style="text-align: center;">Players</div>
        <div class="ey" style="text-align: center;">Duration</div>
        <div class="ey" style="text-align: center;">Level</div>
        <div></div>
      </div>
      {% for gt in game_types %}
      <div class="game-type-row">
        <div style="font-size: 14px; font-weight: 500;">{{ gt.name }}</div>
        <div style="font-size: 12px; color: var(--ink-2); line-height: 1.5;">{{ gt.description }}</div>
        <div style="font-size: 11px; color: var(--ink-3); text-align: center;">{{ gt.min_players }}–{{ gt.max_players }}</div>
        <div style="font-size: 11px; color: var(--ink-3); text-align: center;">{{ gt.duration }}</div>
        <div style="text-align: center;">
          <span class="chip">{{ gt.complexity }}</span>
        </div>
        <div style="text-align: right;">
          <a href="{{ url_for('minigames.new_game') }}" class="btn" style="font-size: 10px; padding: 6px 12px;">Create</a>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 1: Create directory**

```bash
mkdir -p plugins/pinsheet-minigames/templates
```

- [ ] **Step 2: Create `templates/minigames_dashboard.html`** with the content above

- [ ] **Step 3: Commit**

```bash
git add plugins/pinsheet-minigames/templates/minigames_dashboard.html
git commit -m "feat(minigames): dashboard template with active games and catalog"
```

---

### Task 5: Game Detail Template

**Files:**
- Create: `plugins/pinsheet-minigames/templates/minigames_detail.html`

Three-column Layout D — left info rail, center bingo card, right race leaderboard.

```html
{% extends "base.html" %}
{% block content %}
<style>
.minigames-detail {
  padding: 28px 48px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow: hidden;
  height: 100%;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  --ink: #ecebe6;
  --ink-2: #a8a59d;
  --ink-3: #6c685f;
  --rule: #2a2925;
  --accent: #5db49a;
  --paper-2: #1c1c1a;
  --warn: #d96a6a;
  --accent-dim: rgba(93,180,154,0.16);
}
.minigames-detail .ey {
  font: 500 10px/1.45 'IBM Plex Mono', monospace;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.minigames-detail h1 {
  font: 400 32px/1.05 'IBM Plex Mono', monospace;
  margin: 4px 0 0;
  letter-spacing: -0.025em;
}
.minigames-detail h1 em { font-style: italic; color: var(--accent); font-weight: 400; }
.minigames-detail .chip {
  display: inline-flex;
  padding: 5px 10px;
  font: 500 10px/1 'IBM Plex Mono', monospace;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  border: 1px solid var(--rule);
  color: var(--ink-2);
}
.minigames-detail .chip.mint { border-color: var(--accent); color: var(--accent); }
.minigames-detail .btn {
  font: 500 11px/1 'IBM Plex Mono', monospace;
  padding: 8px 16px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: #131312;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}
.minigames-detail .btn.ghost {
  background: transparent;
  color: var(--ink);
}
.minigames-detail .hero-num {
  font-family: 'Barlow Condensed', 'Oswald', sans-serif;
  font-weight: 200;
  line-height: 0.85;
  letter-spacing: -0.04em;
}
.minigames-detail .bingo {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--rule);
  border-left: 1px solid var(--rule);
}
.minigames-detail .bcell {
  border-right: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  aspect-ratio: 1;
}
.minigames-detail .bcell .hole {
  font-size: 22px;
  color: var(--ink-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.minigames-detail .bcell .hole .pl {
  font-size: 10px;
  color: var(--ink-3);
  letter-spacing: 0.08em;
}
.minigames-detail .bcell .checks {
  display: flex;
  gap: 6px;
  width: 100%;
}
.minigames-detail .bx {
  flex: 1;
  height: 28px;
  border: 1px solid var(--rule);
  display: flex;
  align-items: center;
  justify-content: center;
  font: 500 9px/1 'IBM Plex Mono', monospace;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.minigames-detail .bx.p { background: var(--ink); color: #131312; border-color: var(--ink); }
.minigames-detail .bx.b { background: var(--accent); color: #131312; border-color: var(--accent); }
.minigames-detail .pbar { height: 3px; background: var(--rule); width: 100%; }
.minigames-detail .pfill { height: 100%; background: var(--accent); }
</style>

<div class="minigames-detail">
  <div style="display: flex; justify-content: space-between; align-items: flex-end; padding-bottom: 12px; border-bottom: 1px solid var(--rule);">
    <div>
      <div class="ey">{{ game.game_type.replace('_', ' ') }} · Minigames</div>
      <h1><em>{{ game.name }}</em></h1>
    </div>
    <div style="display: flex; gap: 8px;">
      <a href="{{ url_for('minigames.dashboard') }}" class="btn ghost">← Games</a>
      {% if is_member and game.status == 'active' %}
      <button class="btn" onclick="document.getElementById('roundPicker').style.display='block'">Log round</button>
      {% elif not is_member and game.status in ('lobby', 'active') %}
      <form method="POST" action="{{ url_for('minigames.join_game', id=game.id) }}" style="display:inline;">
        <button class="btn">Join</button>
      </form>
      {% endif %}
    </div>
  </div>

  {% if game.status == 'complete' %}
  <div style="padding: 20px; background: var(--paper-2); border: 1px solid var(--rule); text-align: center;">
    <div class="ey">Game over</div>
    <div class="hero-num" style="font-size: 48px; margin-top: 8px; color: var(--accent);">
      {{ game.winner_user_id }}
    </div>
    <div style="font-size: 12px; color: var(--ink-3); margin-top: 4px;">
      Winner · {% for ps in player_states %}{% if ps.user_id == game.winner_user_id %}{{ ps.display_name }}{% endif %}{% endfor %}
    </div>
  </div>
  {% endif %}

  {% if is_member %}
  <div style="display: grid; grid-template-columns: 220px 450px 1fr; gap: 36px; flex: 1; min-height: 0;">
    {# Left: info rail #}
    <div style="display: flex; flex-direction: column; gap: 28px;">
      <div>
        <div class="ey">The pot</div>
        <div class="hero-num" style="font-size: 96px; margin-top: 8px;">
          <span style="color: var(--ink-3);">$</span>{{ game.buy_in * player_states|length }}
        </div>
        <div style="font-size: 12px; color: var(--ink-3); margin-top: 8px;">
          {{ player_states|length }} players{% if game.buy_in %} · ${{ game.buy_in }} buy-in{% endif %}
        </div>
      </div>
      <div style="border-top: 1px solid var(--rule); padding-top: 20px;">
        <div class="ey">Your card</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px;">
          <div>
            <div style="font-size: 32px; font-weight: 300; letter-spacing: -0.03em;">
              {{ my_pars }}<span style="font-size: 14px; color: var(--ink-3);">/18</span>
            </div>
            <div class="ey" style="margin-top: 4px;">Pars</div>
          </div>
          <div>
            <div style="font-size: 32px; font-weight: 300; letter-spacing: -0.03em; color: var(--accent);">
              {{ my_birdies }}<span style="font-size: 14px; color: var(--ink-3);">/18</span>
            </div>
            <div class="ey" style="margin-top: 4px;">Birdies</div>
          </div>
        </div>
      </div>
      {% if game.buy_in %}
      <div style="border-top: 1px solid var(--rule); padding-top: 20px;">
        <div class="ey">Exposure</div>
        <div style="font-size: 24px; font-weight: 300; margin-top: 8px; letter-spacing: -0.02em;">
          <span style="color: var(--ink-3);">$</span>{{ game.buy_in + 18 }}
          <span style="font-size: 12px; color: var(--ink-3); margin-left: 6px;">max</span>
        </div>
        <div style="font-size: 11px; color: var(--ink-3); margin-top: 4px;">
          ${{ game.buy_in }} buy-in + $18 birdie risk
        </div>
      </div>
      {% endif %}
      <div style="border-top: 1px solid var(--rule); padding-top: 20px;">
        <div class="ey">Status</div>
        <div style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
          <span class="chip mint">{{ game.status }}</span>
          <span class="chip">{{ unassigned_rounds|length }} unassigned</span>
        </div>
      </div>
    </div>

    {# Center: bingo card #}
    <div>
      <div class="ey" style="margin-bottom: 10px;">Your bingo card · holes 1–18</div>
      <div class="bingo">
        {% for i in range(1, 19) %}
        {% set h = i|string %}
        {% set s = my_state.get('holes', {}).get(h, {'par': false, 'birdie': false}) %}
        {% set complete = s.get('par') and s.get('birdie') %}
        <div class="bcell"{% if complete %} style="background: var(--accent-dim);"{% endif %}>
          <div class="hole">
            <span>{{ '%02d' % i }}</span>
            <span class="pl">p{{ hole_pars[i-1] }}</span>
          </div>
          <div class="checks">
            <div class="bx{% if s.get('par') %} p{% endif %}">par</div>
            <div class="bx{% if s.get('birdie') %} b{% endif %}">brd</div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>

    {# Right: the race #}
    <div style="border-left: 1px solid var(--rule); padding-left: 32px; display: flex; flex-direction: column;">
      <div class="ey" style="margin-bottom: 20px;">The race</div>
      <div style="display: flex; flex-direction: column;">
        {% for ps in player_states %}
        {% set total = ps.pars + ps.birdies %}
        <div style="display: grid; grid-template-columns: 24px 1fr 1.4fr 50px; gap: 14px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--rule);">
          <span style="font-size: 22px; font-weight: 200; font-family: 'Barlow Condensed', sans-serif; color: var(--ink-3);">{{ loop.index }}</span>
          <div>
            <div style="font-size: 13px; font-weight: 400; color: var(--ink-2);">{{ ps.display_name }}</div>
            <div style="font-size: 11px; color: var(--ink-3); margin-top: 2px;">{{ ps.pars }}p · {{ ps.birdies }}b</div>
          </div>
          <div style="height: 18px; background: var(--paper-2); border: 1px solid var(--rule); display: flex; overflow: hidden;">
            <div style="width: {{ (ps.pars / 36) * 100 }}%; background: var(--ink-3); display: flex; align-items: center; justify-content: center;">
              {% if ps.pars >= 5 %}<span style="font-size: 8px; color: var(--ink); letter-spacing: 0.08em; text-transform: uppercase;">{{ ps.pars }}p</span>{% endif %}
            </div>
            <div style="width: {{ (ps.birdies / 36) * 100 }}%; background: var(--accent); display: flex; align-items: center; justify-content: center;">
              {% if ps.birdies >= 3 %}<span style="font-size: 8px; color: #131312; letter-spacing: 0.08em;">{{ ps.birdies }}b</span>{% endif %}
            </div>
          </div>
          <div style="text-align: right; font-size: 16px; font-weight: 300; letter-spacing: -0.02em;">
            {{ total }}<span style="font-size: 11px; color: var(--ink-3);">/36</span>
          </div>
        </div>
        {% endfor %}
      </div>

      <div style="margin-top: auto; padding: 20px; background: var(--paper-2); border: 1px solid var(--rule);">
        <div class="ey" style="margin-bottom: 8px;">How it works</div>
        <div style="font-size: 12px; color: var(--ink-2); line-height: 1.6;">
          Play rounds and cross off pars and birdies as you earn them. First to fill the card wins the pot. Each birdie earns $1 from every other player. Max exposure per player: ${{ game.buy_in + 18 }}.
        </div>
      </div>
    </div>
  </div>

  {# Round picker modal #}
  <div id="roundPicker" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; align-items: center; justify-content: center;">
    <div style="background: #131312; border: 1px solid var(--rule); padding: 32px; min-width: 480px; max-height: 80vh; overflow-y: auto;">
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px;">
        <div class="ey">Select a round to log</div>
        <button class="btn ghost" onclick="document.getElementById('roundPicker').style.display='none'" style="font-size: 10px;">Close</button>
      </div>
      {% if unassigned_rounds %}
      <form method="POST" action="{{ url_for('minigames.log_round', id=game.id) }}">
        {% for r in unassigned_rounds %}
        <label style="display: block; padding: 12px; border: 1px solid var(--rule); margin-bottom: 8px; cursor: pointer; font-size: 13px;">
          <input type="radio" name="round_date" value="{{ r.date }}" required style="margin-right: 12px;">
          <input type="hidden" name="round_index" value="{{ r.round_index }}">
          {{ r.label }}
        </label>
        {% endfor %}
        <button class="btn" type="submit" style="margin-top: 12px; width: 100%;">Log round</button>
      </form>
      {% else %}
      <p style="color: var(--ink-3); font-size: 13px;">All your rounds have been assigned to this game. Go play some golf!</p>
      {% endif %}
    </div>
  </div>
  {% else %}
  <div style="display: flex; align-items: center; justify-content: center; flex: 1;">
    <div style="text-align: center;">
      <div class="ey" style="margin-bottom: 12px;">You haven't joined this game yet</div>
      <form method="POST" action="{{ url_for('minigames.join_game', id=game.id) }}">
        <button class="btn">Join game</button>
      </form>
    </div>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 1: Create `templates/minigames_detail.html`** with the content above
- [ ] **Step 2: Commit**

```bash
git add plugins/pinsheet-minigames/templates/minigames_detail.html
git commit -m "feat(minigames): game detail template with bingo card and race"
```

---

### Task 6: New Game Template

**Files:**
- Create: `plugins/pinsheet-minigames/templates/minigames_new.html`

```html
{% extends "base.html" %}
{% block content %}
<style>
.minigames-new {
  padding: 28px 48px 32px;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  --ink: #ecebe6;
  --ink-2: #a8a59d;
  --ink-3: #6c685f;
  --rule: #2a2925;
  --accent: #5db49a;
  --warn: #d96a6a;
}
.minigames-new .ey {
  font: 500 10px/1.45 'IBM Plex Mono', monospace;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.minigames-new h1 {
  font: 400 32px/1.05 'IBM Plex Mono', monospace;
  margin: 4px 0 0;
  letter-spacing: -0.025em;
}
.minigames-new h1 em { font-style: italic; color: var(--accent); font-weight: 400; }
.minigames-new .btn {
  font: 500 11px/1 'IBM Plex Mono', monospace;
  padding: 8px 16px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: #131312;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}
.minigames-new .btn.ghost {
  background: transparent;
  color: var(--ink);
}
.minigames-new label {
  display: block;
  font: 500 10px/1.45 'IBM Plex Mono', monospace;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 6px;
}
.minigames-new input, .minigames-new select {
  width: 100%;
  background: transparent;
  border: 1px solid var(--rule);
  padding: 10px 12px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: var(--ink);
  margin-bottom: 20px;
}
</style>

<div class="minigames-new" style="max-width: 520px; margin: 0 auto; padding-top: 60px;">
  <div class="ey" style="margin-bottom: 4px;">Create</div>
  <h1>New <em>game</em></h1>

  {% if error %}
  <div style="padding: 12px; border: 1px solid var(--warn); margin-top: 20px; font-size: 12px; color: var(--warn);">
    {{ error }}
  </div>
  {% endif %}

  <form method="POST" style="margin-top: 28px;">
    <label for="name">Game name</label>
    <input type="text" id="name" name="name" placeholder="e.g. Thursday Night Crew" required>

    <label for="game_type">Game type</label>
    <select id="game_type" name="game_type" required>
      <option value="">Select a game type…</option>
      {% for gt in game_types %}
      <option value="{{ gt.type_id }}">{{ gt.name }}</option>
      {% endfor %}
    </select>

    <label for="buy_in">Buy-in ($)</label>
    <input type="number" id="buy_in" name="buy_in" value="0" min="0" style="width: 120px;">
    <div style="font-size: 11px; color: var(--ink-3); margin-top: -16px; margin-bottom: 20px;">Set to 0 for free games</div>

    <div style="display: flex; gap: 8px; margin-top: 8px;">
      <button type="submit" class="btn">Create game</button>
      <a href="{{ url_for('minigames.dashboard') }}" class="btn ghost">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 1: Create `templates/minigames_new.html`** with the content above
- [ ] **Step 2: Commit**

```bash
git add plugins/pinsheet-minigames/templates/minigames_new.html
git commit -m "feat(minigames): new game form template"
```

---

### Task 7: CSS

**Files:**
- Create: `plugins/pinsheet-minigames/static/minigames.css`

```css
/* PinSheet Minigames — shared plugin styles */
/* Dark theme only — follows design-system/tokens.css */

.minigames-body,
.minigames-detail,
.minigames-new {
  --ps-paper: #131312;
  --ps-paper-2: #1c1c1a;
  --ps-ink: #ecebe6;
  --ps-ink-2: #a8a59d;
  --ps-ink-3: #6c685f;
  --ps-rule: #2a2925;
  --ps-accent: #5db49a;
  --ps-accent-dim: rgba(93, 180, 154, 0.16);
  --ps-warn: #d96a6a;
}
```

- [ ] **Step 1: Create directory**

```bash
mkdir -p plugins/pinsheet-minigames/static
```

- [ ] **Step 2: Create `static/minigames.css`** with the content above

The CSS is intentionally minimal — most styles are inline in the templates (following the PinSheet approach where each page defines its own component styles). This file provides the CSS variable fallback for when the page isn't fully themed.

- [ ] **Step 3: Commit**

```bash
git add plugins/pinsheet-minigames/static/minigames.css
git commit -m "feat(minigames): plugin CSS variables"
```

---

### Task 8: Integration Smoke Test

- [ ] **Step 1: Verify plugin loads without errors**

Run the PinSheet server and check for `"plugin loaded: pinsheet-minigames v0.1.0"` in the logs:

```bash
cd /mnt/Claude/repositories/pinsheet-server
python -c "
import sys
sys.path.insert(0, 'plugins')
from pinsheet_minigames import plugin_info
print(f'plugin_info: {plugin_info}')
"
```

Expected: plugin_info dict printed without errors.

- [ ] **Step 2: Verify all modules parse cleanly**

```bash
python -m py_compile plugins/pinsheet-minigames/__init__.py
python -m py_compile plugins/pinsheet-minigames/blueprint.py
python -m py_compile plugins/pinsheet-minigames/engine.py
```

Expected: no errors.

- [ ] **Step 3: Verify final commit**

```bash
cd /mnt/Claude/repositories/pinsheet-server/plugins/pinsheet-minigames
git status
git log --oneline -5
```

Expected: all 7 commits with clean working tree.

---

## Spec Coverage

| Spec Requirement | Task |
|---|---|
| Plugin scaffold with `plugin_info` + `register()` | Task 1 |
| DB tables for games, players, rounds, states | Task 1 |
| Nav link "Minigames" in sidebar | Task 1 |
| Game engine registry pattern | Task 2 |
| `ParBingoEngine` with `process_round`/`check_victory`/`prize_breakdown` | Task 2 |
| Course handicap + per-hole strokes calculation | Task 2 |
| Blueprint with all routes | Task 3 |
| `/minigames` dashboard with active games + type catalog | Task 3 + 4 |
| `/minigames/new` create game form | Task 3 + 6 |
| `/minigames/<id>` game detail with bingo card | Task 3 + 5 |
| `/minigames/<id>/join` POST endpoint | Task 3 |
| `/minigames/<id>/log-round` POST endpoint | Task 3 |
| Round picker modal on game detail page | Task 5 |
| Race leaderboard with stacked progress bars | Task 5 |
| Design system colors, typography, hairlines | Task 4, 5, 7 |
| Manually assigned rounds (no hooks) | Task 3 `log_round` |
