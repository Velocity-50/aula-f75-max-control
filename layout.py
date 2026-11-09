"""Key layout and lighting effect names for the AULA F75 Max."""

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
