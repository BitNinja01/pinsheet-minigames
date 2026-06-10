import json

from .conftest import seed_course, seed_round


class TestDashboard:
    def test_redirects_when_not_logged_in(self, minigames_app):
        with minigames_app.test_client() as c:
            resp = c.get("/minigames/")
            assert resp.status_code == 302

    def test_renders_empty_dashboard(self, client):
        resp = client.get("/minigames/")
        assert resp.status_code == 200

    def test_includes_game_types(self, client):
        resp = client.get("/minigames/")
        assert resp.status_code == 200
        assert b"Par Bingo" in resp.data


class TestNewGame:
    def test_new_game_form_renders(self, client):
        resp = client.get("/minigames/new")
        assert resp.status_code == 200
        assert b"Par Bingo" in resp.data

    def test_create_game_requires_name(self, client):
        resp = client.post("/minigames/new", data={"name": "", "game_type": "par_bingo"})
        assert resp.status_code == 200
        assert b"required" in resp.data

    def test_create_game_requires_type(self, client):
        resp = client.post("/minigames/new", data={"name": "Test Game", "game_type": ""})
        assert resp.status_code == 200
        assert b"required" in resp.data

    def test_create_game_unknown_type(self, client):
        resp = client.post("/minigames/new", data={"name": "Test Game", "game_type": "unknown_type"})
        assert resp.status_code == 200
        assert b"Unknown" in resp.data

    def test_create_game_success(self, client):
        resp = client.post("/minigames/new", data={"name": "Test Game", "game_type": "par_bingo", "buy_in": "5"},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert "/minigames/" in resp.location

    def test_created_game_shows_on_dashboard(self, client):
        client.post("/minigames/new", data={"name": "My Game", "game_type": "par_bingo", "buy_in": "10"})
        resp = client.get("/minigames/")
        assert b"My Game" in resp.data
        assert b"10" in resp.data

    def test_buy_in_defaults_to_zero(self, client):
        resp = client.post("/minigames/new", data={"name": "Free Game", "game_type": "par_bingo"},
                           follow_redirects=False)
        assert resp.status_code == 302


class TestGameDetail:
    def test_404_for_missing_game(self, client):
        resp = client.get("/minigames/9999")
        assert resp.status_code == 404

    def test_shows_game_info(self, client):
        client.post("/minigames/new", data={"name": "Detail Test", "game_type": "par_bingo"})
        resp = client.get("/minigames/1")
        assert resp.status_code == 200
        assert b"Detail Test" in resp.data

    def test_non_member_sees_join_button(self, client, minigames_app, db_path, user_id):
        import source.store as store_mod
        store_mod.create_user("player2", "Player 2", "pass1234")
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Other Game", 0, user_id),
        )
        game_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (game_id, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (game_id, user_id, '{"holes":{}}'))
        db.commit()
        db.close()

        with minigames_app.test_client() as c:
            c.post("/login", data={"username": "player2", "password": "pass1234"})
            resp = c.get(f"/minigames/{game_id}")
            assert resp.status_code == 200

    def test_member_sees_unassigned_rounds(self, client, db_path, user_id):
        seed_course(db_path)
        seed_round(db_path, user_id)
        client.post("/minigames/new", data={"name": "Round Test", "game_type": "par_bingo"})
        resp = client.get("/minigames/1")
        assert resp.status_code == 200


class TestJoinGame:
    def test_join_nonexistent_game_returns_404(self, client):
        resp = client.post("/minigames/9999/join")
        assert resp.status_code == 404

    def test_join_closed_game_returns_400(self, client, db_path):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'complete')",
            ("par_bingo", "Closed", 0, 1),
        )
        db.commit()
        db.close()
        resp = client.post("/minigames/1/join")
        assert resp.status_code == 400

    def test_join_active_game(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Active", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, '{"holes":{}}'))
        db.commit()
        db.close()

        import source.store as store_mod
        store_mod.create_user("joiner", "Joiner", "pass1234")
        with client.application.test_client() as c:
            c.post("/login", data={"username": "joiner", "password": "pass1234"})
            resp = c.post("/minigames/1/join", follow_redirects=False)
            assert resp.status_code == 302
            assert "/minigames/1" in resp.location

    def test_join_promotes_lobby_to_active(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'lobby')",
            ("par_bingo", "Lobby", 0, user_id),
        )
        db.commit()
        db.close()

        import source.store as store_mod
        store_mod.create_user("joiner2", "Joiner 2", "pass1234")
        with client.application.test_client() as c:
            c.post("/login", data={"username": "joiner2", "password": "pass1234"})
            c.post("/minigames/1/join")
            db2 = __import__("sqlite3").connect(str(db_path))
            db2.row_factory = __import__("sqlite3").Row
            row = db2.execute("SELECT status FROM plugin_minigames_games WHERE id = 1").fetchone()
            assert row["status"] == "active"
            db2.close()

    def test_join_duplicate_redirects(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Dup", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, '{"holes":{}}'))
        db.commit()
        db.close()
        resp = client.post("/minigames/1/join", follow_redirects=False)
        assert resp.status_code == 302


class TestLogRound:
    def test_log_round_nonexistent_game_returns_404(self, client):
        resp = client.post("/minigames/9999/log-round", data={"round_date": "2025-01-01", "round_index": "0"})
        assert resp.status_code == 404

    def test_log_round_nonexistent_round_returns_404(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Log Test", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, '{"holes":{}}'))
        db.commit()
        db.close()
        resp = client.post("/minigames/1/log-round", data={"round_date": "2025-01-01", "round_index": "0"})
        assert resp.status_code == 404

    def test_log_round_updates_state(self, client, db_path, user_id):
        seed_course(db_path)
        seed_round(db_path, user_id, gross=72)
        client.post("/minigames/new", data={"name": "Log Test", "game_type": "par_bingo"})
        resp = client.post("/minigames/1/log-round",
                           data={"round_date": "2025-06-10", "round_index": "0"},
                           follow_redirects=False)
        assert resp.status_code == 302

    def test_duplicate_log_redirects(self, client, db_path, user_id):
        seed_course(db_path)
        seed_round(db_path, user_id, gross=72)
        client.post("/minigames/new", data={"name": "Dup Log", "game_type": "par_bingo"})
        client.post("/minigames/1/log-round", data={"round_date": "2025-06-10", "round_index": "0"})
        resp = client.post("/minigames/1/log-round",
                           data={"round_date": "2025-06-10", "round_index": "0"},
                           follow_redirects=False)
        assert resp.status_code == 302

    def test_victory_on_log_triggers_win(self, client, db_path, user_id):
        seed_course(db_path)
        seed_round(db_path, user_id, gross=36, handicap_index="0.0")
        client.post("/minigames/new", data={"name": "Win Test", "game_type": "par_bingo"})
        client.post("/minigames/1/log-round", data={"round_date": "2025-06-10", "round_index": "0"})

        db = __import__("sqlite3").connect(str(db_path))
        db.row_factory = __import__("sqlite3").Row
        row = db.execute("SELECT status, winner_user_id FROM plugin_minigames_games WHERE id = 1").fetchone()
        db.close()
        assert row["status"] == "complete"
        assert row["winner_user_id"] == user_id


class TestToggleHole:
    def test_toggle_nonexistent_game_returns_404(self, client):
        resp = client.post("/minigames/9999/toggle", data={"hole_number": "1", "type": "par"})
        assert resp.status_code == 404

    def test_toggle_not_member_returns_403(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Toggle", 0, 999),
        )
        db.commit()
        db.close()
        resp = client.post("/minigames/1/toggle", data={"hole_number": "1", "type": "par"})
        assert resp.status_code == 403

    def test_toggle_invalid_hole_returns_400(self, client):
        resp = client.post("/minigames/9999/toggle", data={"hole_number": "99", "type": "par"})
        assert resp.status_code == 400

    def test_toggle_invalid_type_returns_400(self, client):
        resp = client.post("/minigames/9999/toggle", data={"hole_number": "1", "type": "eagle"})
        assert resp.status_code == 400

    def test_toggle_par(self, client, db_path, user_id):
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Toggle", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, '{"holes":{}}'))
        db.execute(
            "UPDATE plugin_minigames_states SET state_json = ? WHERE game_id = ? AND user_id = ?",
            (json.dumps({"holes": {str(i): {"par": False, "birdie": False} for i in range(1, 19)}}), 1, user_id),
        )
        db.commit()
        db.close()

        resp = client.post("/minigames/1/toggle", data={"hole_number": "1", "type": "par"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["par"] is True
        assert data["birdie"] is False

    def test_toggle_off(self, client, db_path, user_id):
        holes = {str(i): {"par": True, "birdie": True} for i in range(1, 19)}
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Toggle Off", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, json.dumps({"holes": holes})))
        db.commit()
        db.close()

        resp = client.post("/minigames/1/toggle", data={"hole_number": "1", "type": "par"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["par"] is False

    def test_toggle_triggers_victory(self, client, db_path, user_id):
        holes = {str(i): {"par": True, "birdie": True} for i in range(1, 18)}
        holes["18"] = {"par": False, "birdie": False}
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Victory Toggle", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, json.dumps({"holes": holes})))
        db.commit()
        db.close()

        resp = client.post("/minigames/1/toggle", data={"hole_number": "18", "type": "par"})
        data = resp.get_json()
        assert data["victory"] is False

        resp2 = client.post("/minigames/1/toggle", data={"hole_number": "18", "type": "birdie"})
        data2 = resp2.get_json()
        assert data2["victory"] is True

    def test_toggle_returns_counts(self, client, db_path, user_id):
        holes = {str(i): {"par": True if i <= 5 else False, "birdie": False} for i in range(1, 19)}
        db = __import__("sqlite3").connect(str(db_path))
        db.execute(
            "INSERT INTO plugin_minigames_games (game_type, name, buy_in, host_user_id, status) VALUES (?, ?, ?, ?, 'active')",
            ("par_bingo", "Counts", 0, user_id),
        )
        db.execute("INSERT INTO plugin_minigames_players (game_id, user_id) VALUES (?, ?)", (1, user_id))
        db.execute("INSERT INTO plugin_minigames_states (game_id, user_id, state_json) VALUES (?, ?, ?)",
                    (1, user_id, json.dumps({"holes": holes})))
        db.commit()
        db.close()

        resp = client.post("/minigames/1/toggle", data={"hole_number": "1", "type": "birdie"})
        data = resp.get_json()
        assert data["pars"] == 5
        assert data["birdies"] == 1
