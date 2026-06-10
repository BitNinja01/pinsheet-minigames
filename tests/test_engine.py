import importlib.util
import math
import sqlite3
import json
from pathlib import Path

import pytest

_plugin_dir = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("_minigames_engine", str(_plugin_dir / "engine.py"))
_engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_engine)

ParBingoEngine = _engine.ParBingoEngine
_compute_course_handicap = _engine._compute_course_handicap
_strokes_received = _engine._strokes_received
register_engine = _engine.register_engine
get_engine = _engine.get_engine
get_available_types = _engine.get_available_types


class TestHandicapHelpers:
    def test_compute_course_handicap_zero_index(self):
        assert _compute_course_handicap(0.0, 113, 72.0, 72) == 0

    def test_compute_course_handicap_positive(self):
        result = _compute_course_handicap(15.0, 113, 72.0, 72)
        assert result == 15

    def test_compute_course_handicap_different_slope(self):
        result = _compute_course_handicap(15.0, 130, 72.0, 72)
        assert result == round(15.0 * (130 / 113) + (72.0 - 72))

    def test_compute_course_handicap_rating_difference(self):
        result = _compute_course_handicap(15.0, 113, 75.0, 72)
        assert result == 18

    def test_strokes_received_zero_or_negative(self):
        assert _strokes_received(0, 1) == 0
        assert _strokes_received(-5, 1) == 0

    def test_strokes_received_less_than_18(self):
        for h in range(1, 19):
            s = _strokes_received(5, h)
            assert s == (1 if h <= 5 else 0)

    def test_strokes_received_more_than_18(self):
        s = _strokes_received(22, 5)
        assert s == 1  # full=1, extra=4, hole 5 > extra → no extra stroke
        s2 = _strokes_received(22, 1)
        assert s2 == 2  # full=1, extra=4, hole 1 <= extra → extra stroke
        s3 = _strokes_received(22, 18)
        assert s3 == 1  # full=1, extra=4, hole 18 > extra → no extra stroke

    def test_strokes_received_exact_multiple(self):
        s = _strokes_received(18, 1)
        assert s == 1
        s = _strokes_received(18, 18)
        assert s == 1


class TestParBingoEngineCreateState:
    def test_creates_18_holes(self):
        engine = ParBingoEngine()
        state = engine.create_state({"buy_in": 0})
        assert "holes" in state
        assert len(state["holes"]) == 18

    def test_all_holes_start_false(self):
        engine = ParBingoEngine()
        state = engine.create_state({})
        for h in state["holes"].values():
            assert h["par"] is False
            assert h["birdie"] is False

    def test_hole_keys_are_string_numbers(self):
        engine = ParBingoEngine()
        state = engine.create_state({})
        for k in state["holes"]:
            assert 1 <= int(k) <= 18


class TestParBingoEngineProcessRound:
    def _make_course_db(self, tmp_path, holes=None):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        db.execute("CREATE TABLE courses (name TEXT UNIQUE, data TEXT)")
        if holes is None:
            holes = {str(i): {"par": 4, "hole_index": i} for i in range(1, 19)}
        course = {"name": "Test GC", "par": 72, "tees": {"White": {"slope": 113, "rating": 72.0}}, "holes": holes}
        db.execute("INSERT INTO courses (name, data) VALUES (?, ?)", ("Test GC", json.dumps(course)))
        db.commit()
        db.close()
        return db_path

    def test_no_course_returns_state_unchanged(self, tmp_path):
        engine = ParBingoEngine()
        state = engine.create_state({})
        db_path = tmp_path / "empty.db"
        db = sqlite3.connect(str(db_path))
        db.execute("CREATE TABLE courses (name TEXT UNIQUE, data TEXT)")
        db.commit()
        db.close()
        result = engine.process_round(
            {},
            state,
            {"course": "NoCourse", "tees": "White", "computed_handicap": "15.0", "holes": {}},
            db_path,
        )
        assert result == state

    def test_all_bogeys_marks_nothing(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {str(i): {"gross": "5"} for i in range(1, 19)},
        }
        result = engine.process_round({}, state, round_data, db_path)
        for h in result["holes"].values():
            assert h["par"] is False
            assert h["birdie"] is False

    def test_all_pars_marks_par(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {str(i): {"gross": "4"} for i in range(1, 19)},
        }
        result = engine.process_round({}, state, round_data, db_path)
        for h in result["holes"].values():
            assert h["par"] is True
            assert h["birdie"] is False

    def test_all_birdies_marks_both(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {str(i): {"gross": "3"} for i in range(1, 19)},
        }
        result = engine.process_round({}, state, round_data, db_path)
        for h in result["holes"].values():
            assert h["par"] is True
            assert h["birdie"] is True

    def test_handicap_turns_bogey_into_par(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})

        # Hole index 1, course handicap 18 → 1 stroke on hole 1
        # Gross 5, net 4 → par
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "18.0",
            "holes": {"1": {"gross": "5"}},
        }
        result = engine.process_round({}, state, round_data, db_path)
        assert result["holes"]["1"]["par"] is True
        assert result["holes"]["1"]["birdie"] is False

    def test_multiple_rounds_merge(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})

        round1 = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {"1": {"gross": "4"}, "2": {"gross": "5"}},
        }
        result = engine.process_round({}, state, round1, db_path)
        assert result["holes"]["1"]["par"] is True
        assert result["holes"]["2"]["par"] is False

        round2 = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {"2": {"gross": "4"}},
        }
        result = engine.process_round({}, result, round2, db_path)
        assert result["holes"]["1"]["par"] is True
        assert result["holes"]["2"]["par"] is True

    def test_handles_varied_pars(self, tmp_path):
        holes = {
            "1": {"par": 3, "hole_index": 1},
            "2": {"par": 5, "hole_index": 2},
            "3": {"par": 4, "hole_index": 3},
        }
        db_path = self._make_course_db(tmp_path, holes)
        engine = ParBingoEngine()
        state = engine.create_state({})

        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {
                "1": {"gross": "3"},  # par-3 → par
                "2": {"gross": "4"},  # par-5 → birdie
                "3": {"gross": "5"},  # par-4 → bogey → nothing
            },
        }
        result = engine.process_round({}, state, round_data, db_path)
        assert result["holes"]["1"]["par"] is True
        assert result["holes"]["1"]["birdie"] is False
        assert result["holes"]["2"]["par"] is True
        assert result["holes"]["2"]["birdie"] is True
        assert result["holes"]["3"]["par"] is False
        assert result["holes"]["3"]["birdie"] is False

    def test_skips_unknown_hole_numbers(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {"99": {"gross": "3"}, "1": {"gross": "4"}},
        }
        result = engine.process_round({}, state, round_data, db_path)
        assert "99" not in result["holes"]
        assert result["holes"]["1"]["par"] is True

    def test_invalid_handicap_defaults_to_zero(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "not-a-number",
            "holes": {"1": {"gross": "5"}},
        }
        result = engine.process_round({}, state, round_data, db_path)
        assert result["holes"]["1"]["par"] is False

    def test_invalid_gross_skips_hole(self, tmp_path):
        db_path = self._make_course_db(tmp_path)
        engine = ParBingoEngine()
        state = engine.create_state({})
        round_data = {
            "course": "Test GC",
            "tees": "White",
            "computed_handicap": "0.0",
            "holes": {"1": {"gross": "abc"}, "2": {"gross": "4"}},
        }
        result = engine.process_round({}, state, round_data, db_path)
        assert result["holes"]["1"]["par"] is False
        assert result["holes"]["2"]["par"] is True


class TestParBingoEngineCheckVictory:
    def test_empty_state_is_victory(self):
        engine = ParBingoEngine()
        assert engine.check_victory({}, {"holes": {}}) is True

    def test_all_incomplete_is_not_victory(self):
        engine = ParBingoEngine()
        state = engine.create_state({})
        assert engine.check_victory({}, state) is False

    def test_one_hole_incomplete_is_not_victory(self):
        engine = ParBingoEngine()
        state = engine.create_state({})
        holes = state["holes"]
        for k in list(holes.keys())[:17]:
            holes[k]["par"] = True
            holes[k]["birdie"] = True
        assert engine.check_victory({}, state) is False

    def test_all_complete_is_victory(self):
        engine = ParBingoEngine()
        state = engine.create_state({})
        for h in state["holes"].values():
            h["par"] = True
            h["birdie"] = True
        assert engine.check_victory({}, state) is True

    def test_partial_holes_is_victory_when_all_present_complete(self):
        engine = ParBingoEngine()
        state = {"holes": {"1": {"par": True, "birdie": True}}}
        assert engine.check_victory({}, state) is True


class TestParBingoEnginePrizeBreakdown:
    def test_no_winner_returns_empty(self):
        engine = ParBingoEngine()
        states = [
            {"user_id": 1, "state": {"holes": {str(i): {"par": False, "birdie": False} for i in range(1, 19)}}},
            {"user_id": 2, "state": {"holes": {str(i): {"par": False, "birdie": False} for i in range(1, 19)}}},
        ]
        result = engine.prize_breakdown({"buy_in": 5}, states)
        assert result == {}

    def test_winner_takes_all(self):
        engine = ParBingoEngine()
        winner_holes = {str(i): {"par": True, "birdie": True} for i in range(1, 19)}
        loser_holes = {str(i): {"par": False, "birdie": False} for i in range(1, 19)}
        states = [
            {"user_id": 1, "state": {"holes": winner_holes}},
            {"user_id": 2, "state": {"holes": loser_holes}},
            {"user_id": 3, "state": {"holes": loser_holes}},
        ]
        result = engine.prize_breakdown({"buy_in": 10}, states)
        # 3 players, buy-in 10, winner birdies = 18
        # Winner gets (3-1) * (10 + 18) = 56
        # Each loser pays -10 - 18 = -28
        assert result[1] == (3 - 1) * (10 + 18)
        assert result[2] == -10 - 18
        assert result[3] == -10 - 18

    def test_no_winner_without_both_par_and_birdie(self):
        engine = ParBingoEngine()
        all_pars = {str(i): {"par": True, "birdie": False} for i in range(1, 19)}
        states = [
            {"user_id": 1, "state": {"holes": all_pars}},
            {"user_id": 2, "state": {"holes": all_pars}},
        ]
        result = engine.prize_breakdown({"buy_in": 5}, states)
        assert result == {}

    def test_first_winner_in_list_wins(self):
        engine = ParBingoEngine()
        both_win = {str(i): {"par": True, "birdie": True} for i in range(1, 19)}
        states = [
            {"user_id": 1, "state": {"holes": both_win}},
            {"user_id": 2, "state": {"holes": both_win}},
        ]
        result = engine.prize_breakdown({"buy_in": 5}, states)
        assert result[1] > 0


class TestEngineRegistry:
    def test_register_engine_stores_class(self):
        orig = dict(_engine._engines)
        _engine._engines.clear()
        try:
            @register_engine
            class FakeEngine(_engine.GameEngine):
                type_id = "fake"

            assert "fake" in _engine._engines
        finally:
            _engine._engines.update(orig)

    def test_get_engine_returns_instance(self):
        engine = get_engine("par_bingo")
        assert engine is not None
        assert isinstance(engine, ParBingoEngine)

    def test_get_engine_unknown_returns_none(self):
        engine = get_engine("nonexistent")
        assert engine is None

    def test_get_available_types_includes_par_bingo(self):
        types = get_available_types()
        names = [t["type_id"] for t in types]
        assert "par_bingo" in names

    def test_get_available_types_has_metadata(self):
        types = get_available_types()
        pb = next(t for t in types if t["type_id"] == "par_bingo")
        assert pb["name"] == "Par Bingo"
        assert pb["min_players"] == 2
        assert pb["max_players"] == 8
        assert "description" in pb
