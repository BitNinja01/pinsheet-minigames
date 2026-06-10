[![Release](https://img.shields.io/github/v/release/BitNinja01/pinsheet-minigames.svg?style=for-the-badge&color=green)](https://github.com/BitNinja01/pinsheet-minigames/releases)
[![Downloads](https://img.shields.io/github/downloads/BitNinja01/pinsheet-minigames/total.svg?style=for-the-badge&color=green)](https://github.com/BitNinja01/pinsheet-minigames/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/BitNinja01/pinsheet-minigames/ci.yml?branch=dev&style=for-the-badge&label=CI)](https://github.com/BitNinja01/pinsheet-minigames/actions)
[![Platform](https://img.shields.io/badge/Platforms-Linux%20|%20macOS%20|%20Windows-white.svg?style=for-the-badge&color=green)](https://github.com/BitNinja01/pinsheet-minigames)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&color=green)](https://www.python.org/downloads/)

---

> Group golf minigames — bragging rights, buy-in optional.

---

A plugin for [PinSheet Server](https://github.com/BitNinja01/pinsheet-server) that adds multiplayer golf minigames. Ships with **Par Bingo** — first to par all 18 holes wins the pot. Extensible via a game-engine registry for custom game types.

- **Par Bingo** — cross off pars (and birdies) on your 18-hole card; first to fill the card wins
- **Race bar** — live progress per player, pars and birdies tracked separately
- **Buy-in support** — optional $ wagers with per-player prize breakdown on completion
- **Engine registry** — `@register_engine` decorator to add new game types
- **Multi-round** — win over multiple rounds; players log rounds from their PinSheet history
- **Manual toggle** — click-to-toggle par/birdie on any hole (birdie-preference enforced)

---

## Installation

### Prerequisites

- **Python 3.11+**
- **PinSheet Server** — the parent app must be installed on the `dev` branch

### Setup

```bash
# From your PinSheet install directory
cd plugins
git clone https://github.com/BitNinja01/pinsheet-minigames.git
```

Restart the server. A **Minigames** nav entry appears. The plugin creates its own database tables on startup — no additional configuration needed.

---

## Quick Start

### 1. Create a game

From the Minigames dashboard, click **+ New game**. Give it a name, select **Par Bingo**, set an optional buy-in, and create.

### 2. Join

Other players navigate to the game and click **Join**. The game transitions from lobby to active automatically.

### 3. Log rounds

Players click **Log round** and pick an unassigned round from their PinSheet history. The engine checks each hole — net score ≤ par marks the hole green.

### 4. Toggle holes (manual)

Any time during the game, click the **par** or **brd** (birdie) box on the bingo card to toggle manually:

| Action | Result |
|--------|--------|
| Toggle birdie ON | Sets both birdie and par |
| Toggle birdie OFF | Clears both |
| Toggle par (birdie OFF) | Toggles par independently |
| Toggle par (birdie ON) | No-op (birdie takes precedence) |

### 5. Win

First player to par all 18 holes wins. The game detail page shows a winner banner with per-player payouts. Birdies increase the winner's take — each birdie costs every other player $1.

### 6. Close

Host or admin clicks **Close game** when ready to remove it from the dashboard.

---

## Routes

All mounted at `/minigames`:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard — active, completed, and available game types |
| GET | `/new` | New game form |
| POST | `/new` | Create a game |
| GET | `/<id>` | Game detail page — bingo card, race bar, log/toggle controls, prize breakdown |
| POST | `/<id>/join` | Join a game |
| POST | `/<id>/log-round` | Assign a played round to the game |
| POST | `/<id>/toggle` | Manually toggle par/birdie on a hole (JSON response) |
| POST | `/<id>/close` | Close a completed game (host/admin only) |

---

## Architecture

```
pinsheet-minigames/
├── __init__.py        # Plugin registration: DB tables, blueprint, CSS, nav
├── engine.py          # Game engine abstract base + registry + ParBingoEngine
├── blueprint.py       # Flask Blueprint with all routes
├── static/
│   └── minigames.css  # Shared CSS variables (dark theme)
├── templates/
│   ├── minigames_dashboard.html
│   ├── minigames_detail.html
│   └── minigames_new.html
└── tests/
    ├── conftest.py        # Fixtures: Flask app with plugin, seed helpers
    ├── test_engine.py     # Engine logic: scoring, handicaps, victory, prizes
    ├── test_blueprint.py  # HTTP routes: CRUD, join, log, toggle, close
    └── test_plugin.py     # Plugin lifecycle: register/unregister
```

### Engine Registry

New game types subclass `GameEngine` and register via decorator — no central registry to update:

```python
from .engine import GameEngine, register_engine

@register_engine
class MyGame(GameEngine):
    type_id = "my_game"
    display_name = "My Game"
    description = "..."
    min_players = 2
    max_players = 8

    def create_state(self, game: dict) -> dict: ...
    def process_round(self, game, player_state, round_data, db_path) -> dict: ...
    def check_victory(self, game, player_state) -> bool: ...
    def prize_breakdown(self, game, player_states) -> dict: ...
```

### Database

Four tables prefixed `plugin_minigames_`:

| Table | Purpose |
|-------|---------|
| `games` | Game metadata: type, name, buy-in, status, host, winner |
| `players` | Many-to-many game-to-user membership |
| `rounds` | Which rounds have been assigned to which games |
| `states` | Per-player per-game state JSON (the bingo card) |

### Handicap Integration

During round processing, the engine computes a course handicap from the player's handicap index, course slope/rating, and course par. Strokes are distributed per the course hole index (WHS-style). A net score of ≤ par marks the hole.

---

## Development

```bash
# Run tests (from parent pinsheet-server directory)
cd pinsheet-server
PYTHONPATH=source:plugins pytest plugins/pinsheet-minigames/tests/ -v

# Compile check
find plugins/pinsheet-minigames -name "*.py" -not -path "*/tests/*" -exec python -m py_compile {} +
find plugins/pinsheet-minigames/tests -name "*.py" -exec python -m py_compile {} +
```

### Tech Stack

- **Python** 3.11+ / Flask
- **SQLite** — all game data
- **Jinja2** — server-side templates
- **Flask-Login** — user authentication
- **Flask-WTF** — CSRF (fetch-based via `X-CSRFToken` header)
