from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from flask import Blueprint, current_app, render_template, request, redirect, url_for, g
from flask_login import login_required, current_user

from .engine import get_engine, get_available_types
from source.request_data import base_context

bp = Blueprint("minigames", __name__)


def _db_path() -> Path:
    return current_app.config["DB_PATH"]


def _get_games_for_user(user_id: int, db_path: Path, status: str | None = None) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    if status:
        rows = db.execute(
            """SELECT g.*, COUNT(DISTINCT p.id) as player_count
               FROM plugin_minigames_games g
               LEFT JOIN plugin_minigames_players p ON p.game_id = g.id
               WHERE g.status = ?
               AND (g.host_user_id = ? OR g.id IN (SELECT game_id FROM plugin_minigames_players WHERE user_id = ?))
               GROUP BY g.id
               ORDER BY g.created_at DESC""",
            (status, user_id, user_id),
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


def _get_all_active_games(db_path: Path) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT g.*, COUNT(DISTINCT p.id) as player_count
           FROM plugin_minigames_games g
           LEFT JOIN plugin_minigames_players p ON p.game_id = g.id
           WHERE g.status = 'active'
           GROUP BY g.id
           ORDER BY g.created_at DESC""",
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
                WHERE json_extract(value, '$.par') = 1
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
    dbp = _db_path()

    active_games = _get_all_active_games(dbp)
    my_games = _get_games_for_user(uid, dbp)
    completed = [g for g in my_games if g["status"] == "complete"]
    open_games = [g for g in my_games if g["status"] in ("lobby", "active")]
    game_types = get_available_types()

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row
    my_ids = set(r["game_id"] for r in db.execute(
        "SELECT game_id FROM plugin_minigames_players WHERE user_id = ?", (uid,)
    ).fetchall())
    db.close()

    return render_template(
        "minigames_dashboard.html",
        **base_context(
            active_games=active_games,
            open_games=open_games,
            completed=completed,
            user_id=uid,
            my_game_ids=my_ids,
            game_types=game_types,
            current_page="minigames",
        ),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_game():
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path()

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
                **base_context(
                    game_types=game_types,
                    error="Name and game type are required.",
                    current_page="minigames",
                ),
            )

        engine = get_engine(game_type)
        if engine is None:
            game_types = get_available_types()
            return render_template(
                "minigames_new.html",
                **base_context(
                    game_types=game_types,
                    error=f"Unknown game type '{game_type}'.",
                    current_page="minigames",
                ),
            )

        db = sqlite3.connect(str(dbp))
        cur = db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
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
        **base_context(
            game_types=game_types,
            current_page="minigames",
        ),
    )


@bp.route("/<int:id>")
@login_required
def game_detail(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path()

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

    max_birdies = max((ps["birdies"] for ps in player_states if ps["user_id"] != uid), default=0) if player_states else 0
    unassigned_rounds = _get_unassigned_rounds(uid, id, dbp) if is_member else []

    prize = {}
    if game["status"] == "complete" and engine:
        prize = engine.prize_breakdown(game, [
            {"user_id": ps["user_id"], "state": ps["state"]} for ps in player_states
        ])

    is_host = game["host_user_id"] == uid

    return render_template(
        "minigames_detail.html",
        **base_context(
            game=game,
            engine=engine,
            is_member=is_member,
            is_host=is_host,
            my_state=my_state,
            my_pars=my_pars,
            my_birdies=my_birdies,
            player_states=player_states,
            hole_pars=hole_pars,
            max_birdies=max_birdies,
            unassigned_rounds=unassigned_rounds,
            prize=prize,
            current_page="minigames",
        ),
    )


@bp.route("/<int:id>/join", methods=["POST"])
@login_required
def join_game(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path()

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
    dbp = _db_path()

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


@bp.route("/<int:id>/toggle", methods=["POST"])
@login_required
def toggle_hole(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path()

    hole_number = request.form.get("hole_number", "")
    toggle_type = request.form.get("type", "")

    if hole_number not in [str(i) for i in range(1, 19)] or toggle_type not in ("par", "birdie"):
        return {"ok": False}, 400

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row

    game_row = db.execute(
        "SELECT * FROM plugin_minigames_games WHERE id = ?", (id,)
    ).fetchone()
    if not game_row:
        db.close()
        return {"ok": False}, 404

    game = dict(game_row)

    state_row = db.execute(
        "SELECT * FROM plugin_minigames_states WHERE game_id = ? AND user_id = ?",
        (id, uid),
    ).fetchone()
    if not state_row:
        db.close()
        return {"ok": False}, 403

    state = json.loads(state_row["state_json"])
    holes = state.get("holes", {})
    hole = holes[hole_number]
    if toggle_type == "birdie":
        new_val = not hole["birdie"]
        hole["birdie"] = new_val
        hole["par"] = new_val
    elif toggle_type == "par":
        if not hole["birdie"]:
            hole["par"] = not hole["par"]

    db.execute(
        "UPDATE plugin_minigames_states SET state_json = ?, updated_at = datetime('now') WHERE game_id = ? AND user_id = ?",
        (json.dumps(state), id, uid),
    )

    victory = False
    engine = get_engine(game["game_type"])
    if engine:
        victory = engine.check_victory(game, state)
        if victory:
            db.execute(
                "UPDATE plugin_minigames_games SET status = 'complete', winner_user_id = ?, completed_at = datetime('now') WHERE id = ?",
                (uid, id),
            )

    db.commit()
    db.close()

    pars = sum(1 for h in holes.values() if h.get("par"))
    birdies = sum(1 for h in holes.values() if h.get("birdie"))

    return {
        "ok": True,
        "par": holes[hole_number]["par"],
        "birdie": holes[hole_number]["birdie"],
        "victory": victory,
        "pars": pars,
        "birdies": birdies,
    }


@bp.route("/<int:id>/close", methods=["POST"])
@login_required
def close_game(id):
    view_user = getattr(g, "view_user", None) or {"id": current_user.id}
    uid = view_user["id"]
    dbp = _db_path()

    db = sqlite3.connect(str(dbp))
    db.row_factory = sqlite3.Row
    game_row = db.execute(
        "SELECT * FROM plugin_minigames_games WHERE id = ?", (id,)
    ).fetchone()
    if not game_row:
        db.close()
        return "Game not found", 404

    game = dict(game_row)
    is_admin = getattr(current_user, "is_admin", False)
    if game["host_user_id"] != uid and not is_admin:
        db.close()
        return "Only the host or an admin can close a game", 403

    if game["status"] != "complete":
        db.close()
        return "Only completed games can be closed", 400

    db.execute("UPDATE plugin_minigames_games SET status = 'closed' WHERE id = ?", (id,))
    db.commit()
    db.close()
    return redirect(url_for("minigames.dashboard"))
