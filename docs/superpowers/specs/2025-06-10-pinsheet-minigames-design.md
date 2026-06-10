# PinSheet Minigames — Design Spec

## Overview

A PinSheet Server plugin that lets groups of players participate in asynchronous golf games together. Players create or join a game with a buy-in, then manually assign rounds from their round history to make progress. First to meet the win condition takes the pot.

**Guiding constraint:** games are asynchronous — players can live anywhere and play on different days. There is no real-time component.

## Pages

### `/minigames` — Dashboard hub

Nav link: "Minigames" in the PinSheet sidebar.

Layout (based on demo_minigames_dashboard/):

- **Header**: eyebrow "Games · Hub", H1 "Minigames", action buttons "History" and "+ New game"
- **Active games section**: 3-column grid of game cards. Each card shows game type (eyebrow), name (h2), player count + buy-in, pot amount, your rank, and game-type-specific progress bars (pars/birdies for Par Bingo, skins for Skins, etc.)
- **Available game types catalog**: table with columns Game, Description, Players, Duration, Level, and a "Create" button per row
- **All-time stats strip**: games played, win rate, net earnings, best finish, active streak

### `/minigames/new` — Create game

Form with fields:
- Game name
- Game type (dropdown seeded from available game types)
- Buy-in amount ($0 = free)
- Submit creates the game in "lobby" status and redirects to the game detail page

### `/minigames/<id>` — Game detail

3-column layout (based on `demo_source_files/` Layout D):

- **Left rail**: pot amount, your card progress (pars X/18, birdies X/18), max exposure, status chips (in progress, round count, days left)
- **Center**: bingo card — 6×3 grid of holes 1-18. Each cell shows hole number, par value, and par/brd checkboxes (filled if earned).
- **Right**: race leaderboard — players ranked by total marks, stacked progress bars (pars in ink, birdies in accent), rules box at bottom.

Actions:
- "Log round" button → opens a round picker modal → player selects a round → server processes it against the game
- "Join" button (visible to non-members)

### `/minigames/<id>/join` — Join game

POST-only endpoint. Adds the current user to the game's player list in "lobby" or "active" status. Redirects to game detail.

## Data Model

Four tables in the PinSheet SQLite database, namespaced with `plugin_minigames_` prefix:

### `plugin_minigames_games`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | auto |
| game_type | TEXT NOT NULL | engine type_id, e.g. "par_bingo" |
| name | TEXT NOT NULL | human-readable game name |
| buy_in | INTEGER NOT NULL DEFAULT 0 | cents? or dollars stored as int |
| status | TEXT NOT NULL DEFAULT 'lobby' | lobby, active, complete |
| host_user_id | INTEGER NOT NULL | FK to users |
| winner_user_id | INTEGER | set when status becomes complete |
| created_at | TEXT NOT NULL DEFAULT datetime('now') | ISO 8601 |
| completed_at | TEXT | ISO 8601 |

### `plugin_minigames_players`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | auto |
| game_id | INTEGER NOT NULL | FK to games |
| user_id | INTEGER NOT NULL | FK to users |
| joined_at | TEXT NOT NULL DEFAULT datetime('now') | |
| UNIQUE(game_id, user_id) | | no duplicate joins |

### `plugin_minigames_rounds`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | auto |
| game_id | INTEGER NOT NULL | FK to games |
| user_id | INTEGER NOT NULL | FK to users |
| round_date | TEXT NOT NULL | date from the round |
| round_index | INTEGER NOT NULL DEFAULT 0 | distinguishes multi-round days |
| assigned_at | TEXT NOT NULL DEFAULT datetime('now') | |
| UNIQUE(game_id, user_id, round_date, round_index) | | can't assign same round twice |

### `plugin_minigames_states`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PRIMARY KEY | auto |
| game_id | INTEGER NOT NULL | FK to games |
| user_id | INTEGER NOT NULL | FK to users |
| state_json | TEXT NOT NULL DEFAULT '{}' | game-type-specific blob |
| updated_at | TEXT NOT NULL DEFAULT datetime('now') | |
| UNIQUE(game_id, user_id) | | one state per player per game |

## Engine Architecture

A registry-based game engine system in `engine.py`.

```python
class GameEngine:
    """Interface all game types implement."""
    type_id: str  # matches game_type in DB

    def create_state(self, game: dict) -> dict:
        """Initial state_json for a new player joining."""

    def process_round(self, game: dict, player_state: dict, round_data: dict) -> dict:
        """Given current state and a round, return updated state."""

    def check_victory(self, game: dict, player_state: dict) -> bool:
        """True if this player has won."""

    def prize_breakdown(self, game: dict, player_states: list[dict]) -> dict:
        """Compute payouts. Returns dict of user_id -> amount.
           For Par Bingo: winner gets pot, birdie assessment per extra birdie."""
```

Engines register themselves via a `register_engine()` call during plugin startup. The registry is a dict keyed by `type_id`.

### Par Bingo Engine

**State shape (`state_json`):**
```json
{
  "holes": {
    "1": {"par": false, "birdie": false},
    "2": {"par": false, "birdie": false},
    ...
  }
}
```

**`process_round` logic:**
- Read each hole from `round_data["holes"]`
- For each hole, parse `gross` and compare to the hole's par (looked up from the course the round was played on)
- If gross == par + handicap_strokes → mark `par: true`
- If gross < par + handicap_strokes → mark `par: true` and `birdie: true`
- Return the merged state

**`check_victory`:** all 18 holes have both `par: true` and `birdie: true`.

**`prize_breakdown`:**
- Winner gets the full pot (sum of all buy-ins)
- Additionally: for each birdie the winner earned beyond their own, every other player owes $1 per birdie
- Max exposure per player: buy_in + (18 birdies × $1) = $38

**Handicap consideration:** Net scoring. A player gets handicap strokes per hole based on their course handicap and the hole index. Par Bingo uses net score relative to par — a net par or better marks the square.

## Data Flow — Log Round

1. Player clicks "Log round" on game detail page
2. Server loads player's unassigned rounds (rounds not in `plugin_minigames_rounds` for this game)
3. Player picks a round from the list
4. Server POSTs the assignment
5. Server loads the round data and the player's current state
6. Server instantiates the correct engine by `game_type`
7. Engine's `process_round` returns updated state
8. New state is saved to `plugin_minigames_states`
9. Engine's `check_victory` is called — if True, game status set to "complete", winner recorded
10. Response redirects to game detail page with updated state

## Design System

Follows the PinSheet design language exactly (`demo_minigames_dashboard/design-system/`):

- **Fonts**: IBM Plex Mono (body, labels, table cells), Barlow Condensed (large numerals)
- **Colors**: Dark theme — paper `#131312`, paper-2 `#1c1c1a`, ink `#ecebe6`/`#a8a59d`/`#6c685f`, accent mint `#5db49a`, rule `#2a2925`
- **Shapes**: 1px hairlines, hard corners (no border-radius), no shadows, no gradients
- **Typography**: uppercase eyebrows at 0.16em tracking, chips at 0.12em tracking, tabular-nums on all numeric columns
- **Page frame**: 1920×1080 base, sidebar 200px fixed, content scales to viewport

CSS in `static/minigames.css`, templates extend `base.html` with `ps-dark` class.

## File Structure

```
plugins/pinsheet-minigames/
  __init__.py           # plugin_info, register(), unregister()
  blueprint.py          # Flask Blueprint with all routes
  engine.py             # GameEngine base, ParBingoEngine, registry
  models.py             # dataclasses or dict builders for game/player/state
  templates/
    dashboard.html      # /minigames — hub page
    game_detail.html    # /minigames/<id> — game detail (Layout D)
    new_game.html       # /minigames/new — create form
  static/
    minigames.css       # all plugin styles
    minigames.js        # JS for round picker modal, interactivity
```

Design artifacts (`demo_source_files/`, `demo_minigames_dashboard/`) live at the project root for reference but are not part of the plugin runtime.

## Future Game Types (not in scope)

The dashboard mockup lists these in the available game types catalog: Skins, Nassau, Closest to Pin, Wolf, Stroke Play Showdown. These are placeholders — only Par Bingo is implemented. Adding a new game type means:

1. Create a new engine class implementing `GameEngine`
2. Register it in `engine.py`
3. That's it — pages, data model, and round assignment are all generic

## Open Questions

- **Buy-in currency**: store as cents (integer) or dollars? Cents avoids float issues.
- **Handicap strokes**: need a helper to compute per-hole strokes from course handicap + hole index. The core doesn't expose this directly yet.
- **Round picker**: should show unassigned rounds for the current user. Need to query PinSheet's `rounds` table and exclude already-assigned rounds.
