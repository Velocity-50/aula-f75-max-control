"""Key remaps and macros for the AULA F75 Max: action names, slot encoding, and the macro buffer.

Formats from thibaultmiclo/aula-driver (aula/protocol.py), tested on the F75 Max; see docs/keymap.md and docs/macros.md.
"""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from layout import LEDS
from protocol import MACRO_BUFFER_MAX, PACKET, TABLE_SIZE

FILE = Path.home() / ".config" / "aula-f75max" / "keymap.json"

# remapping fn cuts off the Fn layer; the firmware ignores backspace's Fn slot (tested)
RESERVED = {"base": {"fn"}, "fn": {"fn", "backspace"}}

# name: (label, HID usage, KeyboardEvent.code)
KEYS: dict[str, tuple[str, int, str]] = {
    **{c: (c.upper(), 0x04 + i, f"Key{c.upper()}") for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")},
    **{c: (c, 0x1E + i, f"Digit{c}") for i, c in enumerate("1234567890")},
    "enter": ("Enter", 0x28, "Enter"), "esc": ("Esc", 0x29, "Escape"), "backspace": ("Bksp", 0x2A, "Backspace"),
    "tab": ("Tab", 0x2B, "Tab"), "space": ("Space", 0x2C, "Space"), "minus": ("-", 0x2D, "Minus"),
    "equal": ("=", 0x2E, "Equal"), "lbracket": ("[", 0x2F, "BracketLeft"), "rbracket": ("]", 0x30, "BracketRight"),
    "backslash": ("\\", 0x31, "Backslash"), "semicolon": (";", 0x33, "Semicolon"), "quote": ("'", 0x34, "Quote"),
    "grave": ("`", 0x35, "Backquote"), "comma": (",", 0x36, "Comma"), "period": (".", 0x37, "Period"),
    "slash": ("/", 0x38, "Slash"), "caps": ("Caps", 0x39, "CapsLock"),
    **{f"f{n}": (f"F{n}", 0x3A + n - 1, f"F{n}") for n in range(1, 13)},
    "print": ("PrtSc", 0x46, "PrintScreen"), "scrolllock": ("ScrLk", 0x47, "ScrollLock"),
    "pause": ("Pause", 0x48, "Pause"), "insert": ("Ins", 0x49, "Insert"), "home": ("Home", 0x4A, "Home"),
    "pgup": ("PgUp", 0x4B, "PageUp"), "delete": ("Del", 0x4C, "Delete"), "end": ("End", 0x4D, "End"),
    "pgdn": ("PgDn", 0x4E, "PageDown"), "right": ("→", 0x4F, "ArrowRight"), "left": ("←", 0x50, "ArrowLeft"),
    "down": ("↓", 0x51, "ArrowDown"), "up": ("↑", 0x52, "ArrowUp"), "numlock": ("NumLk", 0x53, "NumLock"),
    "menu": ("Menu", 0x65, "ContextMenu"),
    **{f"f{n}": (f"F{n}", 0x68 + n - 13, f"F{n}") for n in range(13, 25)},
    "lctrl": ("Ctrl", 0xE0, "ControlLeft"), "lshift": ("Shift", 0xE1, "ShiftLeft"), "lalt": ("Alt", 0xE2, "AltLeft"),
    "lwin": ("Win", 0xE3, "MetaLeft"), "rctrl": ("RCtrl", 0xE4, "ControlRight"),
    "rshift": ("RShift", 0xE5, "ShiftRight"), "ralt": ("RAlt", 0xE6, "AltRight"), "rwin": ("RWin", 0xE7, "MetaRight"),
}
MODS = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}
MEDIA = {
    "play": ("Play/pause", 0xCD), "stop": ("Stop", 0xB7), "prev": ("Previous track", 0xB6),
    "next": ("Next track", 0xB5), "volup": ("Volume up", 0xE9), "voldown": ("Volume down", 0xEA),
    "mute": ("Mute", 0xE2),
}
MOUSE = {  # name: (label, buttons, wheel)
    "left": ("Left click", 0x01, 0), "right": ("Right click", 0x02, 0), "middle": ("Middle click", 0x04, 0),
    "wheelup": ("Wheel up", 0, 0x01), "wheeldown": ("Wheel down", 0, 0xFF),
}
MACRO_MODES = {"once": 0, "times": 1, "toggle": 2, "hold": 3}
MACRO_BUTTONS = {"mouse_left": 0x01, "mouse_right": 0x02, "mouse_middle": 0x04}
MACRO_SLOTS = 100
MACRO_BUDGET = 2700  # vendor check: (macros + events) * 8


class KeyAction(BaseModel):
    kind: Literal["key"] = "key"
    key: Literal[tuple(KEYS)]
    mods: list[Literal[tuple(MODS)]] = []

    def slot(self) -> bytes:
        usage = KEYS[self.key][1]
        mods = sum(MODS[m] for m in set(self.mods))

        if usage >= 0xE0:
            return bytes((0x02, mods | 1 << (usage - 0xE0), 0, 0))

        return bytes((0x02, mods, usage, 0))


class MediaAction(BaseModel):
    kind: Literal["media"] = "media"
    media: Literal[tuple(MEDIA)]

    def slot(self) -> bytes:
        return bytes((0x03, MEDIA[self.media][1], 0, 0))


class MouseAction(BaseModel):
    kind: Literal["mouse"] = "mouse"
    mouse: Literal[tuple(MOUSE)]

    def slot(self) -> bytes:
        return bytes((0x07, *MOUSE[self.mouse][1:], 0))


class MacroAction(BaseModel):
    kind: Literal["macro"] = "macro"
    macro: Annotated[int, Field(ge=0, lt=MACRO_SLOTS)]  # 0-based position in Keymap.macros
    mode: Literal[tuple(MACRO_MODES)] = "once"
    count: Annotated[int, Field(ge=1, le=255)] = 1  # plays for mode "times"

    def slot(self) -> bytes:
        return bytes((0x06, self.macro, MACRO_MODES[self.mode], self.count))


class DisableAction(BaseModel):
    kind: Literal["disable"] = "disable"

    def slot(self) -> bytes:
        return b"\x05\x03\x00\x00"


Action = Annotated[KeyAction | MediaAction | MouseAction | MacroAction | DisableAction, Field(discriminator="kind")]


class MacroEvent(BaseModel):
    key: Literal[tuple(KEYS) + tuple(MACRO_BUTTONS)]
    down: bool
    delay: Annotated[int, Field(ge=10, le=0xFFFF)] = 10  # ms after this event

    def records(self) -> bytes:
        if self.key in MACRO_BUTTONS:
            event = bytes((0, 0, MACRO_BUTTONS[self.key], 0x90 if self.down else 0x10))
        else:
            event = bytes((0, 0, KEYS[self.key][1], 0xB0 if self.down else 0x30))

        return event + bytes((self.delay & 0xFF, self.delay >> 8, 0, 0x50))


class Macro(BaseModel):
    name: Annotated[str, Field(max_length=40)] = "Macro"
    events: list[MacroEvent] = []


def layer_table(layer: dict[str, Action]) -> bytes:
    table = bytearray(TABLE_SIZE)

    for name, action in layer.items():
        led = LEDS[name]  # the remap slot is the key's LED number (tested on the F75 Max)
        table[led * 4 : led * 4 + 4] = action.slot()

    table[-2:] = b"\xaa\x55"

    return bytes(table)


def macro_buffer(macros: list[Macro]) -> bytes:
    """All macros as the vendor serialiser writes them: 100 offset slots, then each macro's records."""
    if (len(macros) + sum(len(m.events) for m in macros)) * 8 > MACRO_BUDGET:
        raise ValueError("macros too large for keyboard memory")

    buf = bytearray(MACRO_BUFFER_MAX)
    offset = MACRO_SLOTS * 4

    for i, macro in enumerate(macros):
        if not macro.events:
            buf[i * 4 : i * 4 + 4] = b"\xff\xff\xff\xff"
            continue

        records = b"".join(event.records() for event in macro.events)
        buf[i * 4 : i * 4 + 2] = offset.to_bytes(2, "little")
        buf[offset : offset + 2] = (len(records) // 4).to_bytes(2, "little")
        buf[offset + 8 : offset + 8 + len(records)] = records
        offset += 8 + len(records)

    size = (offset // PACKET + (1 if offset % PACKET == 0 else 2)) * PACKET  # always one spare report

    if size > MACRO_BUFFER_MAX:
        raise ValueError("macros too large for keyboard memory")

    buf[size - 2 : size] = b"\xaa\x55"

    return bytes(buf[:size])


class Keymap(BaseModel):
    base: dict[str, Action] = {}
    fn: dict[str, Action] = {}
    macros: Annotated[list[Macro], Field(max_length=MACRO_SLOTS)] = []

    @field_validator("base", "fn")
    @classmethod
    def known_keys(cls, value: dict[str, Action]) -> dict[str, Action]:
        unknown = set(value) - set(LEDS)

        if unknown:
            raise ValueError(f"unknown keys: {', '.join(sorted(unknown))}")

        return value

    @model_validator(mode="after")
    def consistent(self) -> "Keymap":
        for layer in ("base", "fn"):
            reserved = RESERVED[layer] & set(getattr(self, layer))

            if reserved:
                raise ValueError(f"{', '.join(sorted(reserved))} cannot be remapped on the {layer} layer")

            for name, action in getattr(self, layer).items():
                if isinstance(action, MacroAction) and action.macro >= len(self.macros):
                    raise ValueError(f"{name} on the {layer} layer plays macro {action.macro + 1}, which does not exist")

        macro_buffer(self.macros)

        return self

    def encode(self) -> tuple[bytes, bytes, bytes]:
        """(macro buffer, base table, Fn table), in the order they are written."""
        return macro_buffer(self.macros), layer_table(self.base), layer_table(self.fn)


def options() -> dict:
    """Choices for the web UI."""
    return {
        "keys": [{"name": n, "label": label, "code": code} for n, (label, _, code) in KEYS.items()],
        "mods": list(MODS),
        "media": [{"name": n, "label": label} for n, (label, _) in MEDIA.items()],
        "mouse": [{"name": n, "label": m[0]} for n, m in MOUSE.items()],
        "macro_modes": list(MACRO_MODES),
        "macro_buttons": list(MACRO_BUTTONS),
        "reserved": {layer: sorted(keys) for layer, keys in RESERVED.items()},
        "macro_slots": MACRO_SLOTS,
        "macro_budget": MACRO_BUDGET,
    }


def load() -> Keymap:
    if FILE.exists():
        return Keymap.model_validate_json(FILE.read_text())

    return Keymap()


def save(keymap: Keymap):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(keymap.model_dump_json(indent=2))
