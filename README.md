# AULA F75 Max lighting control

Control the RGB lighting on an AULA F75 Max keyboard from macOS or Linux. AULA ships its configuration software only for Windows. This project talks to the keyboard directly over USB with a small Python library, and adds a command-line tool and a local web control panel on top.

You can:

- Set any of the 20 built-in lighting effects, with colour, rainbow, brightness, speed, and direction.
- Give every key its own colour.
- Sync the clock on the keyboard's screen.

![Per-key colours in the web control panel](assets/Key%20Selection.png)

![Built-in effects in the web control panel](assets/Effect%20Selection.png)

## Requirements

- [uv](https://docs.astral.sh/uv/). Both scripts declare their own dependencies, and `uv` installs them on first run.
- The keyboard connected with a USB data cable and switched to wired mode. The keyboard does not accept configuration over Bluetooth, and this project does not support the 2.4G receiver.

The project is tested on macOS. Linux should work through the same `hidapi` library, but your user needs read and write access to the keyboard's `/dev/hidraw*` device, and nobody has tested it there yet.

## Use the web control panel

1. Start the server:

	```sh
	./server.py
	```

2. Open <http://127.0.0.1:8075>.

The server listens only on `127.0.0.1`. The dot in the top-right corner turns green when the keyboard is connected.

On the **Per-key** tab:

1. Select keys. Click a key to select it, or drag across several keys. The buttons select common groups: **All**, **None**, **Top row**, **Home row**, **Bottom row**, **Arrows**, and **WASD**. Press Esc to clear the selection.
2. Pick a colour, or click a swatch.
3. Click **Paint selected**. **Reset to default** removes the colour from the selected keys.

The **Default colour** applies to every key that has no colour of its own.

On the **Effect** tab, pick an effect and set its colour, brightness, speed, and direction. The preview shows the colour or rainbow but does not animate the effect.

Click **Apply** to send the change to the keyboard. To send changes automatically, turn on **Auto-apply**. A per-key update takes about one second.

The keyboard cannot report its current lighting. After each successful apply, the server saves the settings to `~/.config/aula-f75max/state.json` and loads them the next time you open the page.

## Use the command line

```sh
./aula.py light static ff0080 -b 5        # one colour, brightness 1-5
./aula.py light breath 00ff00 -s 2        # speed 1-5
./aula.py light rolling -r -s 4           # rainbow
./aula.py light off
./aula.py keys --all 8000ff a,s,d,f,j,k,l,semicolon=00ffff up,left,down,right=ff1493
./aula.py clock                           # sync the screen clock
```

`keys` takes groups of comma-separated key names, each followed by `=RRGGBB`. Keys you leave out get the `--all` colour, or turn off if you omit `--all`. Run `./aula.py keys --help` to list every key name, and `./aula.py light --help` to list the effects.

## Limits

- Settings go over the USB cable only. The keyboard keeps them when you switch to Bluetooth or 2.4G.
- The knob's lighting and function cannot be changed.
- Screen image and GIF uploads and key remapping are not implemented.
- The direction values 0 to 3 are passed to the keyboard as-is. Nobody has documented which direction each value selects.

## How it works

The keyboard (USB ID `0c45:800a`) accepts 64-byte HID feature reports on its vendor interface (usage page `0xFF13`). Each change is a short exchange: begin, select a block, send the data, then apply. The keyboard acknowledges each step.

- The lighting, clock, and per-key packet formats come from [mohin7/aula-f75max](https://github.com/mohin7/aula-f75max) and [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver), and also match [VitalyArt/Aula-F75-Max-Driver](https://github.com/VitalyArt/Aula-F75-Max-Driver).
- The LED number for each key comes from `layouts/rgb-keyboard.xml` in AULA's F75 Max Windows driver, version 1.0.0.5. That file leaves out the right Ctrl key. Its LED number, 98, was found by testing on the keyboard.

`aula.py` holds the protocol, the key layout, and the command-line tool. `server.py` is the FastAPI server, and `web/` holds the page it serves.

This project is unofficial and not affiliated with AULA or Epomaker.
