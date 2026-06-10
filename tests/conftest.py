import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

_parent_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_parent_root) not in sys.path:
    sys.path.insert(0, str(_parent_root))


@pytest.fixture
def minigames_app(tmp_path, monkeypatch):
    """Create a Flask app with the minigames plugin discovered and registered."""
    import source.database
    sys.modules["database"] = source.database
    import source.store
    sys.modules["store"] = source.store

    from source import plugin, plugin_loader

    import source.main as main_mod
    main_mod.limiter.enabled = False

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "drafts").mkdir()
    (data_dir / "plugins" / "pinsheet-minigames").mkdir(parents=True)

    db_path = str(data_dir / "pinsheet.db")
    source.database.set_db_path(db_path)
    source.database.init_db()

    from source.store import create_user
    create_user("player", "Player", "pass1234")

    import source.store as store_mod
    monkeypatch.setattr(store_mod, "_DATA_DIR", data_dir)

    app = main_mod.app
    original_got_first = getattr(app, "_got_first_request", False)

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["DB_PATH"] = Path(db_path)
    app.config["DATA_DIR"] = data_dir
    app._plugin_blocks = {}
    app._plugin_nav = []
    app._plugin_course_actions = []
    app._discovered_plugins = []
    app._plugin_states_at_startup = {}

    plugins_dir = Path(__file__).resolve().parent.parent.parent
    monkeypatch.setattr(plugin_loader, "_plugins_dir", lambda: plugins_dir)

    plugin._plugins.clear()
    plugin_loader.discover_plugins(app)

    if "login_page" not in app.view_functions:
        from source.routes import register_routes
        register_routes(app, main_mod.limiter, main_mod.csrf, main_mod.User)

    yield app

    for p in list(plugin._plugins):
        if hasattr(p, "unregister"):
            p.unregister(app)
    plugin._plugins.clear()
    app._plugin_blocks.clear()
    app._plugin_nav.clear()
    app._got_first_request = original_got_first

    for bp_name in list(app.blueprints.keys()):
        if bp_name.startswith("minigames"):
            del app.blueprints[bp_name]
    static_endpoint = "_plugin_pinsheet-minigames_static"
    if static_endpoint in app.view_functions:
        del app.view_functions[static_endpoint]


@pytest.fixture
def client(minigames_app):
    with minigames_app.test_client() as c:
        c.post("/login", data={"username": "player", "password": "pass1234"})
        yield c


@pytest.fixture
def db_path(minigames_app):
    return minigames_app.config["DB_PATH"]


@pytest.fixture
def user_id(minigames_app):
    import source.store as store_mod
    return store_mod.get_user("player")["id"]


def seed_course(db_path: Path, name: str = "Test GC") -> dict:
    holes = {}
    for i in range(1, 19):
        par = 3 if i in (4, 8, 12, 16) else (5 if i in (2, 6, 10, 14, 18) else 4)
        holes[str(i)] = {"par": par, "hole_index": i}
    course = {
        "name": name,
        "par": sum(h["par"] for h in holes.values()),
        "tees": {"White": {"slope": 113, "rating": 72.0}},
        "holes": holes,
    }
    db = sqlite3.connect(str(db_path))
    db.execute("INSERT OR IGNORE INTO courses (name, data) VALUES (?, ?)", (name, json.dumps(course)))
    db.commit()
    db.close()
    return course


def seed_round(db_path: Path, user_id: int, course: str = "Test GC", date: str = "2025-06-10",
               gross: int = 90, tees: str = "White", handicap_index: str = "15.0",
               round_index: int = 0) -> dict:
    base = max(1, gross // 18)
    extra = gross % 18
    holes = {}
    for i in range(1, 19):
        g = base + (1 if i <= extra else 0)
        holes[str(i)] = {"gross": str(g)}
    round_data = {
        "holes": holes,
    }
    db = sqlite3.connect(str(db_path))
    db.execute(
        """INSERT OR IGNORE INTO rounds
           (user_id, course_name, date, round_index, tee_name, holes, total_gross, computed_handicap)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, course, date, round_index, tees, json.dumps(round_data["holes"]),
         str(gross), handicap_index),
    )
    db.commit()
    db.close()
    return round_data
