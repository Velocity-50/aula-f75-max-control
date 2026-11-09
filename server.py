#!/usr/bin/env -S uv run
"""Local web UI for the AULA F75 Max: ./server.py, then open http://127.0.0.1:8075"""

import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import hid
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator

import protocol
import screen
from layout import LAYOUT, LEDS, MODES

CONFIG_DIR = Path.home() / ".config" / "aula-f75max"
STATE_FILE = CONFIG_DIR / "state.json"
SCREEN_FILE = CONFIG_DIR / "screen.gif"  # preview of the last image uploaded to the screen
SCREEN_STREAM = CONFIG_DIR / "screen.bin"  # exact bytes of that upload, for sending it again
SECONDS_PER_CHUNK = 0.11  # measured: 225 chunks in 24 s
WEB_DIR = Path(__file__).parent / "web"

Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Level = Annotated[int, Field(ge=1, le=5)]


class Effect(BaseModel):
    mode: str = "rolling"
    color: Color = "#ffffff"
    rainbow: bool = True
    brightness: Level = 5
    speed: Level = 3
    direction: Annotated[int, Field(ge=0, le=3)] = 0

    @field_validator("mode")
    @classmethod
    def known_mode(cls, value: str) -> str:
        if value not in MODES:
            raise ValueError(f"unknown mode {value!r}")

        return value


class Custom(BaseModel):
    base: Color = "#000000"
    brightness: Level = 5
    keys: dict[str, Color] = {}

    @field_validator("keys")
    @classmethod
    def known_keys(cls, value: dict[str, Color]) -> dict[str, Color]:
        unknown = set(value) - set(LEDS)

        if unknown:
            raise ValueError(f"unknown keys: {', '.join(sorted(unknown))}")

        return value


class State(BaseModel):
    active: Literal["effect", "custom"] = "effect"
    effect: Effect = Effect()
    custom: Custom = Custom()


def rgb(value: str) -> tuple[int, int, int]:
    return tuple(bytes.fromhex(value[1:]))


def layout() -> dict:
    keys = []

    for row_index, row in enumerate(LAYOUT):
        x = 0.0
        y = 0.0 if row_index == 0 else row_index + 0.25

        for key in row:
            name, label, led = key[:3]
            width = key[3] if len(key) > 3 else 1
            x += key[4] if len(key) > 4 else 0

            keys.append({"name": name, "label": label, "led": led, "x": x, "y": y, "w": width})
            x += width

    return {"keys": keys, "modes": MODES, "width": 16, "height": len(LAYOUT) + 0.25}


device_lock = threading.Lock()
upload = {"state": "idle", "done": 0, "total": 0, "frames": 0, "error": None}
app = FastAPI()


def with_keyboard(action):
    if upload["state"] == "uploading":
        raise HTTPException(409, "screen upload in progress")

    with device_lock:
        try:
            kb = protocol.Keyboard()
        except protocol.KeyboardNotFound as err:
            raise HTTPException(503, str(err)) from err

        try:
            action(kb)
        except OSError as err:
            raise HTTPException(502, f"keyboard rejected the command: {err}") from err
        finally:
            kb.close()


def decode_image(data: bytes, fit: str) -> tuple[list, list[int]]:
    try:
        return screen.load(data, fit)
    except UnidentifiedImageError as err:
        raise HTTPException(400, "not a supported image file") from err
    except ValueError as err:
        raise HTTPException(400, str(err)) from err


def run_upload(stream: bytes, preview: bytes):
    def progress(done: int, total: int):
        upload.update(done=done, total=total)

    try:
        with device_lock:
            kb = protocol.Keyboard()

            try:
                kb.upload_screen(stream, progress)
            finally:
                kb.close()

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SCREEN_STREAM.write_bytes(stream)
        SCREEN_FILE.write_bytes(preview)
        upload.update(state="done")
    except (protocol.KeyboardNotFound, OSError, ValueError) as err:
        upload.update(state="error", error=str(err))


def load_state() -> State:
    if STATE_FILE.exists():
        return State.model_validate_json(STATE_FILE.read_text())

    return State()


@app.get("/api/layout")
def get_layout():
    return layout()


@app.get("/api/status")
def get_status():
    connected = any(d["usage_page"] == protocol.CMD_USAGE_PAGE for d in hid.enumerate(protocol.VID, protocol.PID))

    return {"connected": connected}


@app.get("/api/state")
def get_state() -> State:
    return load_state()


@app.put("/api/state")
def put_state(state: State) -> State:
    def apply(kb: protocol.Keyboard):
        if state.active == "effect":
            e = state.effect
            kb.lighting(MODES.index(e.mode), rgb(e.color), e.brightness, e.speed, e.direction, e.rainbow)
        else:
            c = state.custom
            colors = dict.fromkeys(LEDS.values(), rgb(c.base))
            colors.update({LEDS[name]: rgb(value) for name, value in c.keys.items()})
            kb.per_key(colors, c.brightness)

    with_keyboard(apply)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(state.model_dump_json(indent=2))

    return state


@app.post("/api/clock")
def sync_clock():
    with_keyboard(lambda kb: kb.clock(datetime.now()))

    return {"ok": True}


@app.post("/api/screen/preview")
async def preview_screen(request: Request, fit: str = "contain"):
    frames, delays = await run_in_threadpool(decode_image, await request.body(), fit)
    image = await run_in_threadpool(screen.preview, frames, delays)
    chunks = protocol.screen_chunks(len(frames))

    return {
        "frames": len(frames),
        "duration_ms": sum(delays),
        "chunks": chunks,
        "upload_seconds": round(chunks * SECONDS_PER_CHUNK),
        "image": "data:image/gif;base64," + base64.b64encode(image).decode(),
    }


@app.get("/api/screen")
def get_screen():
    return {**upload, "saved": SCREEN_STREAM.exists() and SCREEN_FILE.exists()}


def begin_upload(stream: bytes, preview: bytes) -> dict:
    if upload["state"] == "uploading":
        raise HTTPException(409, "screen upload in progress")

    upload.update(state="uploading", done=0, total=len(stream) // protocol.SCREEN_CHUNK, frames=stream[0], error=None)
    threading.Thread(target=run_upload, args=(stream, preview), daemon=True).start()

    return upload


@app.post("/api/screen")
async def start_screen(request: Request, fit: str = "contain"):
    if upload["state"] == "uploading":
        raise HTTPException(409, "screen upload in progress")

    frames, delays = await run_in_threadpool(decode_image, await request.body(), fit)
    stream = await run_in_threadpool(screen.encode, frames, delays)
    preview = await run_in_threadpool(screen.preview, frames, delays)

    return begin_upload(stream, preview)


@app.post("/api/screen/resend")
async def resend_screen():
    if not (SCREEN_STREAM.exists() and SCREEN_FILE.exists()):
        raise HTTPException(404, "no saved upload to send again")

    stream = await run_in_threadpool(SCREEN_STREAM.read_bytes)
    preview = await run_in_threadpool(SCREEN_FILE.read_bytes)

    return begin_upload(stream, preview)


@app.get("/api/screen/current")
def current_screen():
    if not SCREEN_FILE.exists():
        raise HTTPException(404, "nothing uploaded from this app yet")

    return FileResponse(SCREEN_FILE, media_type="image/gif", headers={"cache-control": "no-store"})


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8075)
