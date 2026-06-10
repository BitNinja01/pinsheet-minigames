import sys
import sqlite3

import pytest


@pytest.fixture
def plugin(minigames_app):
    mod = sys.modules.get("pinsheet-minigames")
    assert mod is not None, "Plugin was not loaded by the Flask app fixture"
    return mod


class TestPluginInfo:
    def test_has_required_fields(self, plugin):
        info = plugin.plugin_info
        assert info["name"] == "pinsheet-minigames"
        assert "version" in info
        assert "description" in info

    def test_version_is_string(self, plugin):
        assert isinstance(plugin.plugin_info["version"], str)


class TestRegister:
    def test_creates_db_tables(self, minigames_app):
        db = sqlite3.connect(str(minigames_app.config["DB_PATH"]))
        tables = [
            "plugin_minigames_games",
            "plugin_minigames_players",
            "plugin_minigames_rounds",
            "plugin_minigames_states",
        ]
        for table in tables:
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert cursor.fetchone() is not None, f"Table {table} not found"
        db.close()

    def test_injects_css_block(self, minigames_app):
        head = minigames_app._plugin_blocks.get("head", "")
        assert "minigames.css" in head

    def test_adds_nav_entry(self, minigames_app):
        nav_items = minigames_app._plugin_nav
        assert any(n.get("page_id") == "minigames" for n in nav_items)

    def test_registers_blueprint(self, minigames_app):
        assert "minigames" in minigames_app.blueprints


class TestUnregister:
    def test_removes_css_block(self, minigames_app, plugin):
        plugin.unregister(minigames_app)
        head = minigames_app._plugin_blocks.get("head", "")
        assert "minigames.css" not in head

    def test_removes_nav_entry(self, minigames_app, plugin):
        plugin.unregister(minigames_app)
        nav_items = minigames_app._plugin_nav
        assert not any(n.get("page_id") == "minigames" for n in nav_items)
