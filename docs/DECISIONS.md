# Decisions

## 2025-06-10 — Game engine registry pattern
Chose Approach B (engine registry with abstract base class) over monolithic or data-driven approaches. New game types just implement `GameEngine` and register via decorator. This matches PinSheet's own extensibility philosophy.

## 2025-06-10 — Manual round assignment
No lifecycle hooks (`on_round_saved`, `post_save_redirect`). Players explicitly assign rounds to games via the "Log round" button on the game detail page.

## 2025-06-10 — No url_prefix on Blueprint
The Blueprint defines routes without prefix (`/`, `/new`, `/<id>`). The prefix `/minigames` is applied at registration in `__init__.py` via `app.register_blueprint(bp, url_prefix="/minigames")`.

## 2025-06-10 — Branch convention
`main` is the stable release branch. `dev` is the active development branch. All work is committed to `dev`.
