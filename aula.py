#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["hidapi"]
# ///
"""Minimal wired (USB-C) control for the AULA F75 Max (0c45:800a).

Protocol from mohin7/aula-f75max Docs/Hardware-Protocol-Notes.md and thibaultmiclo/aula-driver.
"""

import argparse
import sys
import time
from datetime import datetime

import hid

VID, PID = 0x0C45, 0x800A
CMD_USAGE_PAGE = 0xFF13
PACKET = 64
DELAY = 0.035

MODES = [
    "off", "static", "singleon", "singleoff", "glittering", "falling", "colourful",
    "breath", "spectrum", "outward", "scrolling", "rolling", "rotating", "explode",
    "launch", "ripples", "flowing", "pulsating", "tilt", "shuttle",
]

# (name, label, led, width, gap before), sizes in key units. led is the light_index from
# layouts/rgb-keyboard.xml in AULA's F75 Max Windows driver 1.0.0.5; rctrl is missing there
# and was confirmed on hardware.
LAYOUT = [
    [
        ("esc", "Esc", 1),
        *[(f"f{n}", f"F{n}", n + 1, 1, 0.5 if n in (1, 5, 9) else 0) for n in range(1, 13)],
    ],
    [
        ("grave", "`", 19),
        *[(c, c, 20 + i) for i, c in enumerate("1234567890")],
        ("minus", "-", 30), ("equal", "=", 31), ("backspace", "Bksp", 103, 2), ("delete", "Del", 119),
    ],
    [
        ("tab", "Tab", 37, 1.5),
        *[(c, c.upper(), 38 + i) for i, c in enumerate("qwertyuiop")],
        ("lbracket", "[", 48), ("rbracket", "]", 49), ("backslash", "\\", 67, 1.5), ("pgup", "PgUp", 118),
    ],
    [
        ("caps", "Caps", 55, 1.75),
        *[(c, c.upper(), 56 + i) for i, c in enumerate("asdfghjkl")],
        ("semicolon", ";", 65), ("quote", "'", 66), ("enter", "Enter", 85, 2.25), ("pgdn", "PgDn", 121),
    ],
    [
        ("lshift", "Shift", 73, 2.25),
        *[(c, c.upper(), 74 + i) for i, c in enumerate("zxcvbnm")],
        ("comma", ",", 81), ("period", ".", 82), ("slash", "/", 83), ("rshift", "Shift", 84, 1.75),
        ("up", "↑", 101), ("end", "End", 120),
    ],
    [
        ("lctrl", "Ctrl", 91, 1.25), ("lwin", "Win", 92, 1.25), ("lalt", "Alt", 93, 1.25), ("space", "", 94, 6.25),
        ("ralt", "Alt", 95), ("fn", "Fn", 96), ("rctrl", "Ctrl", 98),
        ("left", "←", 99), ("down", "↓", 100), ("right", "→", 102),
    ],
]
LEDS = {key[0]: key[2] for row in LAYOUT for key in row}
CUSTOM_MODE = 0x80
TABLE_SIZE = 0x240  # 144 slots of (index, r, g, b), sent as 9 pages


def packet(*head: int, fields: dict[int, int] | None = None) -> bytes:
    buf = bytearray(PACKET)
    buf[: len(head)] = bytes(head)

    for i, v in (fields or {}).items():
        buf[i] = v

    return bytes(buf)


class KeyboardNotFound(RuntimeError):
    pass


class Keyboard:
    def __init__(self):
        path = next(
            (d["path"] for d in hid.enumerate(VID, PID) if d["usage_page"] == CMD_USAGE_PAGE),
            None,
        )

        if path is None:
            raise KeyboardNotFound("AULA F75 Max not found on USB; connect the cable and switch to wired mode.")

        self.dev = hid.device()
        self.dev.open_path(path)

    def close(self):
        self.dev.close()

    def send(self, data: bytes):
        time.sleep(DELAY)

        if self.dev.send_feature_report(b"\x00" + data) < 0:
            raise IOError(f"SET_REPORT failed: {self.dev.error()}")

    def read(self) -> bytes:
        time.sleep(DELAY)
        reply = bytes(self.dev.get_feature_report(0, PACKET + 1))

        # hidapi prefixes the report id on some platforms
        return reply[1:] if len(reply) == PACKET + 1 else reply

    def send_ack(self, data: bytes):
        self.send(data)
        reply = self.read()

        if len(reply) < 4 or reply[3] != 0x01:
            raise IOError(f"no ack for {data[:2].hex(' ')}: {reply[:8].hex(' ')}")

    def lighting(self, mode: int, rgb: tuple[int, int, int], brightness: int, speed: int,
                 direction: int, rainbow: bool):
        payload = bytearray(PACKET)
        payload[0] = mode

        if mode:
            payload[1:4] = bytes(rgb)
            payload[8] = int(rainbow)
            payload[9] = brightness
            payload[10] = speed
            payload[11] = direction

        payload[14:16] = b"\xaa\x55"

        self.send_ack(packet(0x04, 0x18))
        self.send_ack(packet(0x04, 0x13, fields={8: 0x01}))
        self.send(bytes(payload))
        self.send_ack(packet(0x04, 0x02))
        self.send(packet(0x04, 0xF0))

    def clock(self, now: datetime):
        data = bytearray(PACKET)
        data[0:3] = b"\x00\x01\x5a"
        data[3:9] = bytes([now.year - 2000, now.month, now.day, now.hour, now.minute, now.second])
        data[10] = (now.weekday() + 1) % 7  # firmware: 0 = Sunday
        data[62:64] = b"\xaa\x55"

        self.send_ack(packet(0x04, 0x18))
        self.send_ack(packet(0x04, 0x28, fields={8: 0x01}))
        self.send(bytes(data))
        self.read()  # echoes the data, no ack flag
        self.send_ack(packet(0x04, 0x02))

    def per_key(self, colors: dict[int, tuple[int, int, int]], brightness: int):
        self.lighting(CUSTOM_MODE, (0, 0, 0), brightness, 0, 0, False)

        table = bytearray(TABLE_SIZE)

        for idx, rgb in colors.items():
            table[idx * 4 : idx * 4 + 4] = bytes((idx, *rgb))

        table[-2:] = b"\xaa\x55"

        self.send_ack(packet(0x04, 0x18))
        self.send_ack(packet(0x04, 0x23, fields={8: TABLE_SIZE // PACKET}))

        for offset in range(0, TABLE_SIZE, PACKET):
            self.send(bytes(table[offset : offset + PACKET]))

        self.read()  # last page is read back before apply
        self.send_ack(packet(0x04, 0x02))
        self.send(packet(0x04, 0xF0))
        self.read()


def color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")

    if len(value) != 6:
        raise argparse.ArgumentTypeError("expected RRGGBB")

    return tuple(bytes.fromhex(value))


def assignment(value: str) -> list[tuple[int, tuple[int, int, int]]]:
    names, _, hex_color = value.rpartition("=")

    if not names:
        raise argparse.ArgumentTypeError("expected KEY[,KEY...]=RRGGBB")

    names = [n.lower() for n in names.split(",")]
    unknown = [n for n in names if n not in LEDS]

    if unknown:
        raise argparse.ArgumentTypeError(f"unknown key(s): {', '.join(unknown)}")

    rgb = color(hex_color)

    return [(LEDS[n], rgb) for n in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    light = sub.add_parser("light", help="set a firmware lighting effect")
    light.add_argument("mode", choices=MODES)
    light.add_argument("color", nargs="?", type=color, default=(255, 255, 255), help="RRGGBB")
    light.add_argument("-b", "--brightness", type=int, choices=range(1, 6), default=5)
    light.add_argument("-s", "--speed", type=int, choices=range(1, 6), default=3)
    light.add_argument("-d", "--direction", type=int, choices=range(0, 4), default=0)
    light.add_argument("-r", "--rainbow", action="store_true", help="multicolour instead of COLOR")

    keys = sub.add_parser("keys", help="per-key colours", epilog="key names: " + " ".join(LEDS))
    keys.add_argument("assign", nargs="*", type=assignment, metavar="KEY[,KEY...]=RRGGBB")
    keys.add_argument("--all", type=color, default=(0, 0, 0), help="colour for unlisted keys (default off)")
    keys.add_argument("-b", "--brightness", type=int, choices=range(1, 6), default=5)

    sub.add_parser("clock", help="sync the screen clock to local time")

    args = parser.parse_args()

    try:
        kb = Keyboard()
    except KeyboardNotFound as err:
        sys.exit(str(err))

    try:
        if args.cmd == "light":
            kb.lighting(MODES.index(args.mode), args.color, args.brightness, args.speed,
                        args.direction, args.rainbow)
        elif args.cmd == "keys":
            colors = dict.fromkeys(LEDS.values(), args.all)

            for group in args.assign:
                colors.update(group)

            kb.per_key(colors, args.brightness)
        else:
            kb.clock(datetime.now())
    finally:
        kb.close()

    print("ok")


if __name__ == "__main__":
    main()
