#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["hidapi", "pillow"]
# ///
"""Wired (USB-C) control for the AULA F75 Max (0c45:800a): lighting, per-key RGB, screen, and clock."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import screen
from layout import LEDS, MODES
from protocol import SCREEN_CHUNK, Keyboard, KeyboardNotFound


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

    screen_cmd = sub.add_parser("screen", help="upload an image or animated GIF to the screen")
    screen_cmd.add_argument("file", type=Path)
    screen_cmd.add_argument("--fit", choices=screen.FITS, default="contain")
    screen_cmd.add_argument("--preview", type=Path, metavar="OUT.gif",
                            help="write what the screen will show to OUT.gif instead of uploading")

    args = parser.parse_args()
    stream = None

    if args.cmd == "screen":
        frames, delays = screen.load(args.file.read_bytes(), args.fit)

        if args.preview:
            args.preview.write_bytes(screen.preview(frames, delays))
            print(f"wrote {args.preview}: {len(frames)} frames, {sum(delays) / 1000:.2f} s loop")
            return

        stream = screen.encode(frames, delays)
        print(f"{len(frames)} frames, {sum(delays) / 1000:.2f} s loop, {len(stream) // SCREEN_CHUNK} chunks")

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
        elif args.cmd == "screen":
            def report(done: int, total: int):
                print(f"\ruploading {done}/{total}", end="", file=sys.stderr, flush=True)

            acked = kb.upload_screen(stream, report)
            print(file=sys.stderr)
            total = len(stream) // SCREEN_CHUNK

            if acked != total:
                print(f"warning: keyboard acknowledged {acked} of {total} chunks", file=sys.stderr)
        else:
            kb.clock(datetime.now())
    finally:
        kb.close()

    print("ok")


if __name__ == "__main__":
    main()
