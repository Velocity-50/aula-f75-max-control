# AULA F75 Max control

Control the RGB lighting and the screen on an AULA F75 Max keyboard from macOS or Linux. AULA ships its configuration software only for Windows. This project talks to the keyboard directly over USB with a small Python library, and adds a command-line tool and a local web control panel on top.

You can:

- Set any of the 20 built-in lighting effects, with colour, rainbow, brightness, speed, and direction.
- Give every key its own colour.
- Put an image or animated GIF on the keyboard's screen.
- Sync the clock on the keyboard's screen.

![Per-key colours in the web control panel](assets/Key%20Selection.png)

![Built-in effects in the web control panel](assets/Effect%20Selection.png)

![Screen image upload in the web control panel](assets/Screen%20Selection.png)

## Requirements

- [uv](https://docs.astral.sh/uv/) and Python 3.11 or later. `pyproject.toml` lists the dependencies and `uv.lock` pins their versions. `uv` installs them into `.venv` the first time you run a script. To set up `.venv` ahead of time, for example for your editor, run `uv sync`.
- The keyboard connected with a USB data cable and switched to wired mode. The keyboard does not accept configuration over Bluetooth, and this project does not support the 2.4G receiver.

The project is tested on macOS. Linux should work through the same `hidapi` library, but your user needs read and write access to the keyboard's `/dev/hidraw*` device, and nobody has tested it there yet.

Run the scripts from the repository directory, because `uv` finds the project from the current directory. From anywhere else, use `uv run --project <path-to-repo> <path-to-repo>/aula.py`.

To update the dependencies, run `uv lock --upgrade` and commit the new `uv.lock`.

## Use the web control panel

1. Start the server:

	```sh
	./server.py
	```

2. Open <http://127.0.0.1:8075>.

The server listens only on `127.0.0.1`. The dot in the top-right corner turns green when the keyboard is connected.

On the **Per-key** tab:

1. Select keys. Click a key to select it, or drag across several keys. The buttons select common groups: **All**, **None**, **Top row**, **Home row**, **Bottom row**, **Arrows**, and **WASD**. Press Esc to clear the selection.
2. Pick a colour with the colour picker, type a hex value such as `#ff4000` or `f40`, or click a swatch.
3. Click **Paint selected**. **Reset to default** removes the colour from the selected keys.

The **Default colour** applies to every key that has no colour of its own.

On the **Effect** tab, pick an effect and set its colour, brightness, speed, and direction. The preview shows the colour or rainbow but does not animate the effect.

Click **Apply** to send the change to the keyboard. To send changes automatically, turn on **Auto-apply**. A per-key update takes about one second.

The keyboard cannot report its current lighting. After each successful apply, the server saves the settings to `~/.config/aula-f75max/state.json` and loads them the next time you open the page.

On the **Screen** tab:

1. Drop an image or GIF on the drop area, or click it to choose a file.
2. Pick how the image fits the 128×128 screen: **Contain** shows the whole image with black bars, **Cover** crops it to fill the screen, and **Stretch** ignores the aspect ratio.
3. Check the preview, which shows the image in the screen's 16-bit colour, then click **Upload to keyboard**.
4. To show the image, press the knob and choose the image display.

An upload takes about 0.11 seconds per 4 KB chunk. A 28-frame GIF takes about 25 seconds. Lighting changes wait until the upload finishes. **On the keyboard** shows the last image uploaded from this app.

## Use the command line

```sh
./aula.py light static ff0080 -b 5        # one colour, brightness 1-5
./aula.py light breath 00ff00 -s 2        # speed 1-5
./aula.py light rolling -r -s 4           # rainbow
./aula.py light off
./aula.py keys --all 8000ff a,s,d,f,j,k,l,semicolon=00ffff up,left,down,right=ff1493
./aula.py clock                           # sync the screen clock
./aula.py screen eyes.gif --fit cover     # upload an image or GIF to the screen
./aula.py screen eyes.gif --preview out.gif  # write what the screen will show, without uploading
```

`keys` takes groups of comma-separated key names, each followed by `=RRGGBB`. Keys you leave out get the `--all` colour, or turn off if you omit `--all`. Run `./aula.py keys --help` to list every key name, and `./aula.py light --help` to list the effects.

## How images are converted

The screen holds one image of up to 255 frames. Each frame shows for 30 to 500 ms.

- A frame longer than 500 ms becomes several copies of the same frame, so the timing stays the same.
- A GIF with more than 255 frames, after that split, keeps 255 evenly spaced frames. The kept frames take over the time of the dropped ones, so the animation runs for the same total time.
- Frames shorter than 30 ms are slowed to 30 ms.

The 255-frame limit protects the keyboard. The firmware writes the image straight to flash, and on a related AULA keyboard, data past the limit permanently overwrote the built-in menu graphics. `protocol.py` checks the frame count and stream size again just before sending.

## Limits

- Settings go over the USB cable only. The keyboard keeps them when you switch to Bluetooth or 2.4G.
- The knob's lighting and function cannot be changed.
- Key remapping is not implemented.
- Each upload rewrites the same area of flash. Uploading by hand is fine. Uploading in a tight loop, for example to show live system stats, wears the flash out.
- The direction values 0 to 3 are passed to the keyboard as-is. Nobody has documented which direction each value selects.

## How it works

The keyboard (USB ID `0c45:800a`) accepts 64-byte HID feature reports on its vendor interface (usage page `0xFF13`). Each change is a short exchange: begin, select a block, send the data, then apply. The keyboard acknowledges each step.

- The lighting, clock, per-key, and screen formats come from [mohin7/aula-f75max](https://github.com/mohin7/aula-f75max), [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver), and [VitalyArt/Aula-F75-Max-Driver](https://github.com/VitalyArt/Aula-F75-Max-Driver). The screen upload, 16-bit colour, and 2 ms frame-delay units were confirmed on the keyboard.
- The LED number for each key comes from `layouts/rgb-keyboard.xml` in AULA's F75 Max Windows driver, version 1.0.0.5. That file leaves out the right Ctrl key. Its LED number, 98, was found by testing on the keyboard.

A screen upload uses a second interface (usage page `0xFF68`). After a header command on the main interface, the image goes over in 4096-byte output reports, and the keyboard acknowledges each one.

| File | Contents |
| --- | --- |
| `aula.py` | Command-line tool |
| `protocol.py` | USB protocol: lighting, per-key colours, clock, and screen upload |
| `layout.py` | Key positions, LED numbers, and effect names |
| `screen.py` | Image and GIF conversion for the screen |
| `server.py` | FastAPI server for the web control panel |
| `web/` | The page that `server.py` serves |
| `pyproject.toml`, `uv.lock` | Dependencies and their pinned versions |

This project is unofficial and not affiliated with AULA or Epomaker.
