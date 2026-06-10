from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

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
                result[uid] = (n - 1) * (buy_in + winner_birdies)
            else:
                result[uid] = -buy_in - winner_birdies

        return result
