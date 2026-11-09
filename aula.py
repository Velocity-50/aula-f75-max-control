#!/usr/bin/env -S uv run
"""Wired (USB-C) control for the AULA F75 Max (0c45:800a): lighting, per-key RGB, screen, clock, and key remaps."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

import keymap
import screen
from layout import LEDS, MODES
from protocol import SCREEN_CHUNK, Keyboard, KeyboardNotFound

REMAP_EPILOG = """KEY is the physical key; names as in `keys --help`, e.g. delete, caps, j.
ACTION is one of:
  default                    the key's factory action
  disable                    do nothing
  [MOD+...]KEY               a key, optionally with ctrl/shift/alt/win, e.g. home, ctrl+shift+t
  media:NAME                 {media}
  macro:N[:MODE[:COUNT]]     play macro N (from the web UI); MODE once (default), times, toggle, hold
KEY names in ACTION: {keys}""".format(media=" ".join(keymap.MEDIA), keys=" ".join(keymap.KEYS))


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


def parse_action(spec: str) -> dict | None:
    kind, _, rest = spec.partition(":")

    if spec == "default":
        return None

    if spec == "disable":
        return {"kind": "disable"}

    if kind == "media":
        return {"kind": "media", "media": rest}

    if kind == "macro":
        number, _, mode = rest.partition(":")
        mode, _, count = mode.partition(":")

        return {"kind": "macro", "macro": int(number) - 1, "mode": mode or "once", "count": int(count or 1)}

    if rest:
        raise argparse.ArgumentTypeError(f"unknown action type {kind!r}; see `remap --help`")

    *mods, key = spec.split("+")

    return {"kind": "key", "key": key, "mods": mods}


def remap_assignment(value: str) -> tuple[str, dict | None]:
    name, _, spec = value.lower().partition("=")

    if not spec:
        raise argparse.ArgumentTypeError(f"expected KEY=ACTION: {value}")

    if name not in LEDS:
        raise argparse.ArgumentTypeError(f"unknown key {name!r}; see `keys --help`")

    action = parse_action(spec)

    try:
        if action:
            TypeAdapter(keymap.Action).validate_python(action)
    except ValidationError as err:
        raise argparse.ArgumentTypeError(f"invalid action {spec!r}: {err.errors()[0]['msg']}") from err

    return name, action


def format_action(action: keymap.Action) -> str:
    match action:
        case keymap.KeyAction():
            return "+".join([*action.mods, action.key])
        case keymap.MediaAction():
            return f"media:{action.media}"
        case keymap.MacroAction():
            mode = "" if action.mode == "once" else f":{action.mode}"
            count = f":{action.count}" if action.mode == "times" else ""

            return f"macro:{action.macro + 1}{mode}{count}"

    return "disable"


def print_keymap(km: keymap.Keymap):
    for layer in ("base", "fn"):
        for name, action in getattr(km, layer).items():
            print(f"{layer:5} {name}={format_action(action)}")

    for i, macro in enumerate(km.macros):
        print(f"macro {i + 1}: {macro.name} ({len(macro.events)} events)")

    if not (km.base or km.fn or km.macros):
        print("factory default: no remaps, no macros")


def updated_keymap(args) -> keymap.Keymap:
    data = keymap.load().model_dump()

    if args.reset:
        data["base"], data["fn"] = {}, {}

    for layer, assignments in (("base", args.assign), ("fn", args.fn)):
        for name, action in assignments:
            if action:
                data[layer][name] = action
            else:
                data[layer].pop(name, None)

    try:
        return keymap.Keymap.model_validate(data)
    except ValidationError as err:
        sys.exit(f"invalid keymap: {err.errors()[0]['msg']}")


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

    remap = sub.add_parser("remap", help="remap keys; no arguments prints the saved keymap",
                           description=f"Remaps are saved in {keymap.FILE} and shared with the web UI. "
                                       "Each write replaces both layers on the keyboard.",
                           epilog=REMAP_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    remap.add_argument("assign", nargs="*", type=remap_assignment, metavar="KEY=ACTION", help="base layer")
    remap.add_argument("--fn", action="append", type=remap_assignment, default=[], metavar="KEY=ACTION",
                       help="Fn layer (repeat for more keys)")
    remap.add_argument("--reset", action="store_true", help="clear both layers first (macros are kept)")

    args = parser.parse_args()
    stream = None
    new_keymap = None

    if args.cmd == "remap":
        if not (args.assign or args.fn or args.reset):
            print_keymap(keymap.load())
            return

        new_keymap = updated_keymap(args)

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
        elif args.cmd == "remap":
            kb.keymap(*new_keymap.encode())
            keymap.save(new_keymap)
            print_keymap(new_keymap)
        else:
            kb.clock(datetime.now())
    finally:
        kb.close()

    print("ok")


if __name__ == "__main__":
    main()
