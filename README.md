# AULA F75 Max control

Control the RGB lighting, the screen, and the key assignments on an AULA F75 Max keyboard from macOS or Linux. AULA ships its configuration software only for Windows. This project talks to the keyboard directly over USB with a small Python library, and adds a command-line tool and a local web control panel on top.

You can:

- Set any of the 20 built-in lighting effects, with colour, rainbow, brightness, speed, and direction.
- Give every key its own colour.
- Put an image or animated GIF on the keyboard's screen.
- Sync the clock on the keyboard's screen.
- Remap keys on the base layer and the Fn layer, and store macros on the keyboard.

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

The server listens only on `127.0.0.1`. The dot in the top-right corner turns green when the keyboard is connected. The **Lighting** and **Keys** switch at the top picks what you edit.

On the **Per-key** tab:

1. Select keys. Click a key to select it, or drag across several keys. The buttons select common groups: **All**, **Top row**, **Home row**, **Bottom row**, **Arrows**, and **WASD**. The line under the board lists the selected keys; **Select none** or Esc clears the selection.
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
4. The screen shows the image when the upload finishes. If it later shows the clock again, press **Fn** and the knob together to switch the knob from volume to screen control, then turn the knob to the image page. Pressing the knob alone only mutes. You can also click **Upload again** under **On the keyboard** to send the last upload again.

An upload takes about 0.11 seconds per 4 KB chunk. A 28-frame GIF takes about 25 seconds. Lighting changes wait until the upload finishes. **On the keyboard** shows the last image uploaded from this app. The app keeps the exact bytes of that upload in `~/.config/aula-f75max/screen.bin`, so **Upload again** sends the same image without the original file. Each upload rewrites the screen's flash, so prefer the knob when it works.

In **Keys**:

1. Pick the **Base** or **Fn** layer. The Fn layer is active while you hold Fn.
2. Select keys on the board, then pick an action: **Key** (with optional modifiers; **Press a key** fills it in from your keyboard), **Media**, **Macro**, **Disable**, or **Default** to undo a remap. Click **Assign to selected keys**. A remapped key is highlighted and shows its assignment in place of its printed label.
3. Click **Apply** to write both layers and all macros to the keyboard. **Reset layer** asks for confirmation, then returns the layer to the factory assignments and writes it to the keyboard straight away, together with any other unapplied changes.

Under **Macros**, click **New macro**, then **Record** and type the sequence, or add events by hand with a delay after each one. **Record** stores the time between key presses as the delays. **Add mouse click** adds a left, right, or middle button press and release, so a macro is also how a key clicks the mouse. Bind the macro to a key with the **Macro** action. A macro can play once, a set number of times, until you press the key again (**toggle**), or while you hold the key. Macro memory is limited; the panel shows how much is used.

Keys that the firmware reserves are greyed out: Fn on both layers, and Backspace on the Fn layer. The keyboard cannot report its key assignments, so the app saves them to `~/.config/aula-f75max/keymap.json`, which `./aula.py remap` uses too.

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
./aula.py remap delete=home --fn delete=delete  # Del sends Home, Fn + Del sends Delete
./aula.py remap                          # print the saved remaps
./aula.py remap --reset                  # back to the factory key assignments
```

`keys` takes groups of comma-separated key names, each followed by `=RRGGBB`. Keys you leave out get the `--all` colour, or turn off if you omit `--all`. Run `./aula.py keys --help` to list every key name, and `./aula.py light --help` to list the effects.

`remap` takes `KEY=ACTION` pairs for the base layer and `--fn KEY=ACTION` for the Fn layer. An action is a key with optional modifiers (`home`, `ctrl+shift+t`), `media:mute`, `macro:1`, `disable`, or `default` to undo a remap. Run `./aula.py remap --help` for the full list. The command adds to the remaps saved in `~/.config/aula-f75max/keymap.json`, which the web control panel shares, and writes both layers and all macros to the keyboard. Macros are created in the web control panel.

## How images are converted

The screen holds one image of up to 255 frames. Each frame shows for 30 to 500 ms.

- A frame longer than 500 ms becomes several copies of the same frame, so the timing stays the same.
- A GIF with more than 255 frames, after that split, keeps 255 evenly spaced frames. The kept frames take over the time of the dropped ones, so the animation runs for the same total time.
- Frames shorter than 30 ms are slowed to 30 ms.

The 255-frame limit protects the keyboard. The firmware writes the image straight to flash, and on a related AULA keyboard, data past the limit permanently overwrote the built-in menu graphics. `protocol.py` checks the frame count and stream size again just before sending.

## Limits

- Settings go over the USB cable only. The keyboard keeps them when you switch to Bluetooth or 2.4G.
- This project cannot change the knob's lighting or function. Nobody has published how.
- The firmware ignores a Fn-layer remap of Backspace, so the app does not offer it. Fn itself cannot be remapped. Other keys may be reserved on the Fn layer too; nobody has tested each one.
- Assigning a mouse click or wheel directly to a key does nothing on this keyboard, so the app does not offer it. Mouse clicks do work inside a macro. The wheel has no macro equivalent.
- The keyboard cannot report its key assignments. The app writes what `keymap.json` holds, so remaps made by other software are replaced on the next apply.
- Each upload rewrites the same area of flash. Uploading by hand is fine. Uploading in a tight loop, for example to show live system stats, wears the flash out.
- The direction values 0 to 3 are passed to the keyboard as-is. Nobody has documented which direction each value selects.

## How it works

The keyboard (USB ID `0c45:800a`) accepts 64-byte HID feature reports on its vendor interface (usage page `0xFF13`). Each change is a short exchange: begin, select a block, send the data, then apply. The keyboard acknowledges each step.

- The lighting, clock, per-key, and screen formats come from [mohin7/aula-f75max](https://github.com/mohin7/aula-f75max), [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver), and [VitalyArt/Aula-F75-Max-Driver](https://github.com/VitalyArt/Aula-F75-Max-Driver). The screen upload, 16-bit colour, and 2 ms frame-delay units were confirmed on the keyboard.
- The LED number for each key comes from `layouts/rgb-keyboard.xml` in AULA's F75 Max Windows driver, version 1.0.0.5. That file leaves out the right Ctrl key. Its LED number, 98, was found by testing on the keyboard.
- Remaps and macros use the formats from [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver), written for the EA75MAX. A key's remap slot is its LED number. Both were confirmed on the keyboard; [docs/keymap.md](docs/keymap.md) and [docs/macros.md](docs/macros.md) record the tests.

A screen upload uses a second interface (usage page `0xFF68`). After a header command on the main interface, the image goes over in 4096-byte output reports, and the keyboard acknowledges each one.

| File | Contents |
| --- | --- |
| `aula.py` | Command-line tool |
| `protocol.py` | USB protocol: lighting, per-key colours, clock, screen upload, remaps, and macros |
| `keymap.py` | Remap actions, macro events, and their encoding; saves `keymap.json` |
| `layout.py` | Key positions, LED numbers, and effect names |
| `screen.py` | Image and GIF conversion for the screen |
| `server.py` | FastAPI server for the web control panel |
| `web/` | The page that `server.py` serves |
| `docs/` | Research notes on features this project does not implement yet |
| `pyproject.toml`, `uv.lock` | Dependencies and their pinned versions |

This project is unofficial and not affiliated with AULA or Epomaker.
