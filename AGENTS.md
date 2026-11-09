# Repository Guidelines

## Project Overview

Controls an AULA F75 Max keyboard (USB `0c45:800a`) from macOS or Linux over HID, replacing AULA's Windows-only software. Features: 20 firmware lighting effects, per-key RGB, screen clock sync, image/GIF uploads to the 128×128 screen, and key remaps (base and Fn layers) with macros. Two front ends share one protocol library: a CLI (`aula.py`) and a local FastAPI web UI (`server.py` + `web/`). `README.md` is the user-facing doc; keep it in sync with behaviour changes.

## Architecture & Data Flow

```
layout.py   (data: MODES, LAYOUT, LEDS)        no project imports
protocol.py (HID: Keyboard, constants)          imports hid only
screen.py   (Pillow: image → screen stream)     imports protocol constants, never the device
keymap.py   (pydantic: remaps, macros → bytes)  imports layout, protocol constants, never the device
aula.py     (CLI)        → layout, protocol, screen, keymap
server.py   (FastAPI)    → layout, protocol, screen, keymap   → serves web/ statically
```

- **Command channel** (usage page `0xFF13`): 64-byte feature reports, 35 ms (`DELAY`) before each send/read. Every operation is `04 18` begin → select block (`04 13` lighting, `04 23` per-key table, `04 11`/`04 27` base/Fn remap table, `04 28` clock, `04 72` screen header; `fields[8]` = page/chunk count) → data → `04 02` apply (some flows end with `04 F0`). 576-byte tables go through `Keyboard.write_table`. Macros differ: `04 19` → `04 15` → buffer → `04 02`, no begin/finalize. `send_ack` requires reply byte 3 == `0x01`. Build packets with `packet(0x04, cmd, fields={offset: value})`.
- **Display channel** (usage page `0xFF68`): `Keyboard.upload_screen` opens a second HID handle and writes 4096-byte output reports, reading one ack per chunk.
- **Web lighting apply**: `PUT /api/state` → pydantic `State` → `with_keyboard()` → `kb.lighting(...)` or `kb.per_key(...)` → on success, persist to `~/.config/aula-f75max/state.json`. The keyboard cannot report its config, so that file is the source of truth for the UI.
- **Screen upload**: `POST /api/screen?fit=` (raw file body) → `screen.load/encode/preview` in a threadpool → `begin_upload` → daemon thread `run_upload` holds `device_lock` and updates the module-level `upload` dict → client polls `GET /api/screen` (adds `saved`) every 500 ms → on success writes `~/.config/aula-f75max/screen.gif` (preview) and `screen.bin` (exact stream). `POST /api/screen/resend` sends `screen.bin` again through `begin_upload`. No known command selects the screen page; the user switches to the image with Fn + knob, then turns the knob.
- **Keymap apply**: `PUT /api/keymap` (or `aula.py remap`) → `keymap.Keymap` (actions discriminated by `kind`; validators reject reserved keys in `keymap.RESERVED`, dangling macro indices, and over-budget macros) → `Keymap.encode()` → `kb.keymap(macros, base, fn)` writes all three every time → on success `keymap.save()` to `~/.config/aula-f75max/keymap.json`, shared by the CLI and web UI. A key's remap slot is its LED number. Layer keys are physical `LEDS` names; action/macro keys are `keymap.KEYS` names.
- **CLI**: argparse subcommands `light | keys | clock | screen | remap`; open `Keyboard()`, run, `kb.close()` in `finally`, print `ok`. `remap` with no arguments prints `keymap.json` without opening the device.

### Hardware safety invariants (do not weaken)

- Screen data goes straight to flash. `SCREEN_MAX_FRAMES = 255` (AULA's own limit); past it, firmware on related boards permanently overwrote menu graphics. The cap is enforced in `screen.normalize` and again in `upload_screen` (frame count and exact stream length) right before sending. Never add an override.
- Frame delays are one byte in 2 ms units, clamped to 30–500 ms (`screen.MIN_DELAY/MAX_DELAY`); longer frames are split into repeats.
- Repeated uploads wear flash. Don't build anything that uploads in a loop (for example live stats).
- One device user at a time: `device_lock`; lighting endpoints return 409 while `upload["state"] == "uploading"`.

## Key Directories

- `/` (repo root): all Python modules; no package directory.
- `web/`: vanilla ES modules, no bundler. `app.js` handles the Lighting/Keys section switch, lighting state, tabs, and apply; `board.js` renders the shared board and selection; `api.js` (`api`, `message`, status), `hex.js` (colour fields); `screen.js` exports `initScreen({ api, message })` for the Screen tab; `keymap.js` (`initKeymap`) and `macros.js` (`initMacros`) drive the Keys section, with `options.js` indexing `GET /api/keymap/options` by `KeyboardEvent.code` and reading held modifiers; `style.css` holds theme variables.
- `assets/`: README screenshots (filenames contain spaces; link as `assets/Key%20Selection.png`).
- `docs/`: protocol research (keymap, macros, knob, factory reset, screen pages), with sources and F75 Max hardware test results. Facts copied from the EA75MAX sibling are unverified on the F75 Max until a test section says otherwise.

## Development Commands

```sh
uv sync                                   # create .venv (editor support); scripts also auto-sync
./server.py                               # web UI at http://127.0.0.1:8075 (localhost only); --port N, --help
./aula.py light rolling -r -s 4           # effects: ./aula.py light --help
./aula.py keys --all 8000ff a,s,d,f=00ffff
./aula.py clock
./aula.py screen eyes.gif --fit cover
./aula.py screen eyes.gif --preview out.gif   # encode only, no device access
uv add <pkg> / uv lock --upgrade          # change deps; commit uv.lock
```

Run scripts from the repo root; `uv` finds the project from the cwd. From elsewhere: `uv run --project <repo> <repo>/aula.py`.

## Code Conventions & Common Patterns

- **Python**: modern type hints (`dict[int, tuple[int, int, int]]`, `X | None`); `snake_case` functions, `UPPER_SNAKE` constants with prefixes (`SCREEN_*`, `CMD_*`); double quotes and f-strings; long lines (~120) are fine. Comments are sparse and record hardware facts (`# firmware: 0 = Sunday`).
- **Blank lines** (both languages): two between top-level Python definitions; a blank line after `if`/`for` blocks and before `return`/`raise`; blank lines between logical groups.
- **Errors**: `protocol` raises `KeyboardNotFound(RuntimeError)` (no device), `IOError`/`OSError` (no ack or failed report), and `ValueError` (invalid stream). `server.py` maps these to `HTTPException` 503 / 502 / 400, with 409 for busy and 404 for no `screen.gif`, always `raise ... from err`. The CLI turns `KeyboardNotFound` into `sys.exit(str(err))`. Validate only at boundaries: pydantic models (`Color` regex, `Level` 1–5, `field_validator` against `MODES`/`LEDS`) and argparse types (`color`, `assignment`).
- **Layout data**: `LAYOUT` rows of `(name, label, led[, width[, gap_before]])` tuples; `LEDS` is derived from it. LED numbers come from AULA's driver XML (`rctrl` = 98 was found by hardware testing). Add keys there, not in the UI.
- **Concurrency**: sync FastAPI endpoints for device calls (they run in a threadpool); CPU-heavy image work in async endpoints goes through `run_in_threadpool`; long uploads use a background thread plus a polled status dict.
- **JS**: 2-space indent, double quotes, semicolons, `const` and arrow functions, camelCase names, kebab-case DOM ids, a `$` helper per file. Wire events by looping over `data-*` attributes (`data-view`, `data-select`, `data-for`). Handlers mutate `state` and then call `changed()` (sync → paint → optional 400 ms auto-apply). `view` (visible tab) is separate from `state.active` (what goes to the keyboard); `.lighting-only` elements hide on the Screen tab. `api()` sends JSON only for string bodies (raw for files); surface errors with `message(text, true)`.
- **CSS**: theme custom properties in `:root`; `--unit` is the 1u key size that JS reads; keycaps use `color-mix(... var(--led) var(--level) ...)`.
- **Docs and UI copy**: British spelling ("colour"), sentence case, bold for UI labels.
- **Keep files under ~300 lines**: split into modules, as with `protocol`/`layout`/`screen` and `web/screen.js`.
- **Commits**: Conventional Commits with scope, lowercase imperative subjects: `feat(web): …`, `feat(screen): …`, `docs: …`, `build: …`.

## Important Files

| File | Role |
| --- | --- |
| `aula.py` | CLI entry point (`#!/usr/bin/env -S uv run`) |
| `server.py` | FastAPI app, pydantic models, upload job, static mount of `web/` |
| `protocol.py` | All HID constants and the `Keyboard` class |
| `screen.py` | Fit, timing normalisation, RGB565 encode, preview GIF |
| `layout.py` | Effect names (list index = firmware mode byte), key geometry, LED numbers |
| `web/app.js`, `web/screen.js` | Front end |
| `pyproject.toml`, `uv.lock` | Dependencies (fastapi, uvicorn, hidapi, pillow); not packaged, no `[tool.*]` config |

## Runtime/Tooling Preferences

- `uv` only; Python ≥ 3.11 (Pillow 13 dropped 3.10). Don't reintroduce PEP 723 inline script metadata.
- No front-end build step or `package.json`. Keep `web/` as plain ES modules served by FastAPI.
- Tested on macOS; Linux needs read/write access to `/dev/hidraw*` (untested).
- Config only works over the USB cable in wired mode; Bluetooth exposes no configuration channel and the 2.4G receiver is unsupported.
- The server binds `127.0.0.1:8075` (`--port` changes the port; the host stays localhost). Stop any server you start; a leftover process blocks the port.

## Testing & QA

- No test suite, test framework, linter, formatter, or CI exists.
- Checks that don't touch the device:
  ```sh
  ./aula.py --help
  ./aula.py screen FILE --preview /tmp/out.gif
  HOME=$(mktemp -d) ./aula.py remap         # prints the keymap; parse/validation errors exit before the device
  uv run python -m py_compile aula.py server.py protocol.py layout.py screen.py keymap.py
  for f in web/*.js; do node --check "$f"; done
  ```
- Pure, hardware-free units: `screen.normalize/encode/rgb565/load/preview`, `protocol.packet/screen_chunks`, `keymap.Keymap.encode/layer_table/macro_buffer` (byte-identical to thibaultmiclo's `remap_table`/`macro_buffer`), `server.layout`, the pydantic models, and `GET /api/layout` / `GET /api/keymap/options` / `POST /api/screen/preview`.
- Hardware behaviour was verified on the real keyboard. Commands that write to it change the user's lighting, screen, or key assignments: prefer `--preview`. To restore lighting after a test, re-PUT the saved `GET /api/state`; to restore keys, re-PUT `GET /api/keymap`. Test a new Fn-layer key with a one-key write first; the firmware silently ignores reserved slots (Backspace). Test new screen-protocol changes with a single still frame (9 chunks) before a full GIF. The CLI warns if acked chunks ≠ total.
- Verify UI changes in a real browser against a running `./server.py`.
