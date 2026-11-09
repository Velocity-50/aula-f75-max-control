# AULA F75 Max control

Control the RGB lighting, the screen, and the key assignments on an AULA F75 Max keyboard from macOS or Linux. AULA ships its configuration software only for Windows. This project talks to the keyboard directly over USB with a small Python library, and adds a command-line tool and a local web control panel on top.

You can:

- Set any of the 20 built-in lighting effects, with colour, rainbow, brightness, speed, and direction.
- Give every key its own colour.
- Put an image or animated GIF on the keyboard's screen.
- Sync the clock on the keyboard's screen.
- Remap keys on the base layer and the Fn layer, and store macros on the keyboard.
- Set the sleep timer, key response, Fn switch, and the Win, Alt+F4, and Alt+Tab locks.

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

The server listens only on `127.0.0.1`. To use another port, run `./server.py --port 8080`; `./server.py --help` lists the options. The dot in the top-right corner turns green when the keyboard is connected. The **Colors** and **Config** switch at the top picks what you edit.

On the **Per-key** tab:

1. Select keys. Click a key to select it, or drag across several keys. The buttons select common groups: **All**, **Top row**, **Home row**, **Bottom row**, **Arrows**, and **WASD**. The line under the board lists the selected keys; **Select none** or Esc clears the selection.
2. Pick a colour with the colour picker, type a hex value such as `#ff4000` or `f40`, or click a swatch.
3. Click **Paint selected**. **Reset to default** removes the colour from the selected keys.

The **Default colour** applies to every key that has no colour of its own.

On the **Effect** tab, pick an effect and set its colour, brightness, speed, and direction. The preview shows the colour or rainbow but does not animate the effect.

Click **Apply** to send the change to the keyboard. To send changes automatically, turn on **Auto-apply**. A per-key update takes about one second.

The keyboard cannot report its current lighting. After each successful apply, the server saves the lighting to `~/.config/aula-f75max/state.json` and loads it the next time you open the page.

On the **Screen** tab:

1. Drop an image or GIF on the drop area, or click it to choose a file.
2. Pick how the image fits the 128×128 screen: **Contain** shows the whole image with black bars, **Cover** crops it to fill the screen, and **Stretch** ignores the aspect ratio.
3. Check the preview, which shows the image in the screen's 16-bit colour, then click **Upload to keyboard**.
4. The screen shows the image when the upload finishes. If it later shows the clock again, press **Fn** and the knob together to switch the knob from volume to screen control, then turn the knob to the image page. Pressing the knob alone only mutes. You can also click **Upload again** under **On the keyboard** to send the last upload again. **Sync clock** (and `./aula.py clock`) also switches the screen to the clock page.

In wired USB mode, an animated image can show corrupted frames: part of a frame, or a whole frame, turns the wrong colours, and different frames break on each loop. This happens whether or not the app is running, and the stored image is fine. With the 2.4G receiver it plays cleanly, so upload over the cable, then switch to 2.4G.

An upload takes about 0.11 seconds per 4 KB chunk. A 28-frame GIF takes about 25 seconds. Lighting changes wait until the upload finishes. **On the keyboard** shows the last image uploaded from this app. The app keeps the exact bytes of that upload in `~/.config/aula-f75max/screen.bin`, so **Upload again** sends the same image without the original file. Each upload rewrites the screen's flash, so prefer the knob when it works.

### Remap keys and record macros

![Key remapping in the web control panel](assets/Keybind%20Settings.png)

Click **Config** at the top. The board shows the assignments for the selected layer. A remapped key is highlighted and shows what it sends in place of its printed label; in the screenshot above, Del sends Home. On the Fn layer below, Fn + F1 and Fn + F2 change the screen brightness, and Fn + Del sends Delete.

![Fn-layer remapping in the web control panel](assets/Keybind%20Fn%20Layer.png)

To remap keys:

1. Pick the **Base** or **Fn** layer. The Fn layer is active while you hold Fn.
2. Select keys on the board. The line under the board lists them.
3. Pick an action and click **Assign to selected keys**:

	| Action | What the key does |
	| --- | --- |
	| **Key** | Sends another key, with optional Ctrl, Shift, Alt, and Win. **Press a key** fills in the key and modifiers from your keyboard. |
	| **Media** | Play/pause, stop, previous or next track, volume up or down, mute, or screen brightness up or down |
	| **Macro** | Plays a macro stored on the keyboard |
	| **Disable** | Nothing |
	| **Default** | Its factory action, undoing a remap |

4. Click **Apply** to write both layers and all macros to the keyboard.

**Reset layer** asks for confirmation, then returns the layer to the factory assignments and writes it to the keyboard straight away, together with any other unapplied changes.

To make a macro:

1. Under **Macros**, click **New macro** and give it a name.
2. Click **Record**, type the sequence, and click **Stop**. Recording keeps the time between key presses as the delays. You can also add, edit, or delete events by hand: each event is a key or mouse button press or release, followed by a delay of 10 to 65535 ms. **Add mouse click** adds a button press and release.
3. Select the keys that should play it, pick the **Macro** action and the macro, and choose how it plays: **once**, a set number of **times**, **toggle** (repeats until you press the key again), or **hold** (repeats while you hold the key).
4. Click **Apply**.

The keyboard holds up to 100 macros in a small memory. The panel shows how much is used; every macro and every event takes 8 of the 2700 available bytes. Deleting a macro also removes the keys bound to it, and later macros move up one number.

Keys that the firmware reserves are greyed out: Fn on both layers, and Backspace on the Fn layer. Assigning a mouse click directly to a key does nothing on this keyboard, so use a macro with **Add mouse click** instead. The keyboard cannot report its key assignments, so the app saves them to `~/.config/aula-f75max/keymap.json`, which `./aula.py remap` uses too.

### Change keyboard settings

![Keyboard settings in the web control panel](assets/Keyboard%20Settings.png)

Click **Config** at the top, then the **Settings** tab, change any of these, and click **Apply**:

| Setting | What it does | Factory default |
| --- | --- | --- |
| **Sleep after** | Idle time before the keyboard sleeps in 2.4G or Bluetooth mode: never, 1, 5, or 30 minutes. The firmware offers nothing longer than 30 minutes except never. | 5 minutes |
| **Key response** | Debounce level 1 to 5. 1 is fastest; raise it if keys double-type. | 2 |
| **Block keys** | Disables the Win key, Alt+F4, or Alt+Tab, for example so a game isn't closed or left by accident | All off |
| **Fn switch** | In Mac mode the top row sends media keys no matter what this is set to. In Windows mode it probably swaps the top row between F1–F12 and media keys; not yet tested. | Off |

The keyboard takes all of these in one message, so **Apply** writes every setting at once. It cannot report them back, so the server saves them to the `settings` part of `~/.config/aula-f75max/state.json` and the page starts from those values, or from the factory defaults if nothing was saved. Settings changed with other software are replaced on the next apply.

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
- The Win/Mac/iOS/Android system mode can only be changed on the keyboard's screen menu. Nobody has published a USB command for it. In Mac mode the top row sends media keys no matter what the **Fn switch** says.
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
- The keyboard settings format comes from [mohin7/aula-f75max](https://github.com/mohin7/aula-f75max), which tested it on the F75 Max, and from [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver). Writing a 30-minute sleep timer was acknowledged by the keyboard; [docs/reset.md](docs/reset.md) has the byte layout.

A screen upload uses a second interface (usage page `0xFF68`). After a header command on the main interface, the image goes over in 4096-byte output reports, and the keyboard acknowledges each one.

| File | Contents |
| --- | --- |
| `aula.py` | Command-line tool |
| `protocol.py` | USB protocol: lighting, per-key colours, clock, screen upload, remaps, macros, and settings |
| `keymap.py` | Remap actions, macro events, and their encoding; saves `keymap.json` |
| `settings.py` | Keyboard settings (sleep timer, key response, key locks, Fn switch) and their encoding |
| `layout.py` | Key positions, LED numbers, and effect names |
| `screen.py` | Image and GIF conversion for the screen |
| `server.py` | FastAPI server for the web control panel |
| `web/` | The page that `server.py` serves |
| `docs/` | Research notes on features this project does not implement yet |
| `pyproject.toml`, `uv.lock` | Dependencies and their pinned versions |

This project is unofficial and not affiliated with AULA or Epomaker.
