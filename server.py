#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["fastapi", "uvicorn", "hidapi"]
# ///
"""Local web UI for the AULA F75 Max lighting: ./server.py, then open http://127.0.0.1:8075"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import hid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import aula

STATE_FILE = Path.home() / ".config" / "aula-f75max" / "state.json"
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
        if value not in aula.MODES:
            raise ValueError(f"unknown mode {value!r}")

        return value


class Custom(BaseModel):
    base: Color = "#000000"
    brightness: Level = 5
    keys: dict[str, Color] = {}

    @field_validator("keys")
    @classmethod
    def known_keys(cls, value: dict[str, Color]) -> dict[str, Color]:
        unknown = set(value) - set(aula.LEDS)

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

    for row_index, row in enumerate(aula.LAYOUT):
        x = 0.0
        y = 0.0 if row_index == 0 else row_index + 0.25

        for key in row:
            name, label, led = key[:3]
            width = key[3] if len(key) > 3 else 1
            x += key[4] if len(key) > 4 else 0

            keys.append({"name": name, "label": label, "led": led, "x": x, "y": y, "w": width})
            x += width

    return {"keys": keys, "modes": aula.MODES, "width": 16, "height": len(aula.LAYOUT) + 0.25}


device_lock = threading.Lock()
app = FastAPI()


def with_keyboard(action):
    with device_lock:
        try:
            kb = aula.Keyboard()
        except aula.KeyboardNotFound as err:
            raise HTTPException(503, str(err)) from err

        try:
            action(kb)
        except OSError as err:
            raise HTTPException(502, f"keyboard rejected the command: {err}") from err
        finally:
            kb.close()


def load_state() -> State:
    if STATE_FILE.exists():
        return State.model_validate_json(STATE_FILE.read_text())

    return State()


@app.get("/api/layout")
def get_layout():
    return layout()


@app.get("/api/status")
def get_status():
    connected = any(d["usage_page"] == aula.CMD_USAGE_PAGE for d in hid.enumerate(aula.VID, aula.PID))

    return {"connected": connected}


@app.get("/api/state")
def get_state() -> State:
    return load_state()


@app.put("/api/state")
def put_state(state: State) -> State:
    def apply(kb: aula.Keyboard):
        if state.active == "effect":
            e = state.effect
            kb.lighting(aula.MODES.index(e.mode), rgb(e.color), e.brightness, e.speed, e.direction, e.rainbow)
        else:
            c = state.custom
            colors = dict.fromkeys(aula.LEDS.values(), rgb(c.base))
            colors.update({aula.LEDS[name]: rgb(value) for name, value in c.keys.items()})
            kb.per_key(colors, c.brightness)

    with_keyboard(apply)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(state.model_dump_json(indent=2))

    return state


@app.post("/api/clock")
def sync_clock():
    with_keyboard(lambda kb: kb.clock(datetime.now()))

    return {"ok": True}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8075)
