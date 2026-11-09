# Key remapping

The keyboard stores two remap tables in firmware: the base layer and the Fn layer. Each table holds one 4-byte slot per key. A zero slot keeps the key's default action. Source: thibaultmiclo/aula-driver, `aula/protocol.py` (`Action.slot`, `remap_table`, `Keyboard.set_remap`) and `aula/keycodes.py`. That project tested remaps on an EA75MAX. Nobody has tested them on an F75 Max.

## Write a table

The exchange uses the command channel and framing that `protocol.py` already uses (usage page `0xFF13`, 64-byte feature reports, 35 ms between reports, ack when reply byte 1 echoes the command and byte 3 is `0x01`).

| Step | Report | Ack read |
| --- | --- | --- |
| 1 | `04 18` begin | Yes |
| 2 | `04 11` for the base layer, or `04 27` for the Fn layer, with byte 8 = `09` | Yes |
| 3 | The 576-byte table as 9 reports of 64 bytes | After the last report only |
| 4 | `04 02` apply | Yes |
| 5 | `04 F0` finalize | Yes |

Every write replaces the whole layer. The keyboard cannot report a table back. VitalyArt's `inspectKeymapPages` tries a read, and tarikmanoar's survey says a GET_REPORT after a block select returns only the ack. Keep the full intended table on the computer, as this project does with `state.json`.

## Table layout

- 576 bytes (`0x240`), so 144 slots of 4 bytes.
- Slot `n` is bytes `n*4` to `n*4+3`, where `n` is the key index.
- Slot 0 is unused. thibaultmiclo accepts key indices 1 to 142.
- The last two bytes of the table are the trailer `AA 55`.
- An all-zero table, with the trailer, restores every key on that layer.

## Slot formats

| Action | Bytes | Notes |
| --- | --- | --- |
| Default | `00 00 00 00` | |
| Disable | `05 03 00 00` | |
| Key, optional modifiers | `02 mods usage 00` | `usage` is a HID keyboard usage, for example `0x04` for A. `mods` bits: `01` Ctrl, `02` Shift, `04` Alt, `08` Win. |
| Modifier alone | `02 bit 00 00` | `bit` = `1 << (usage - 0xE0)`, so `01` to `80` cover left Ctrl to right Win. |
| Media (consumer usage) | `03 usage 00 00` | One byte only. Known values are listed below. |
| Macro | `06 macro mode count` | `macro` is the 0-based macro position. See [macros.md](macros.md). |
| Mouse | `07 buttons wheel 00` | Buttons: `01` left, `02` right, `04` middle. Wheel: `01` up, `FF` down. |
| Special function | `01 p1 p2 00` | Values are from the vendor `DeviceDriver.exe`. |

An example: Caps Lock (index 55) as Ctrl sets bytes 220 to 223 of the base table to `02 01 00 00`. F12 (index 13) as Ctrl+Shift+T sets bytes 52 to 55 to `02 03 17 00`.

### Media usages

| Action | Usage |
| --- | --- |
| Play or pause | `CD` |
| Stop | `B7` |
| Previous track | `B6` |
| Next track | `B5` |
| Volume up | `E9` |
| Volume down | `EA` |
| Mute | `E2` |

### Special functions

| Function | `p1 p2` |
| --- | --- |
| Caps Lock | `01 02` |
| Num Lock | `01 01` |
| Scroll Lock | `01 04` |
| Calculator | `03 01` |

## Key indices

In the EA75MAX key data, every key's `key_index` (remap slot) equals its `light_index` (per-key colour slot). 79 of the F75 Max's 81 keys have the same light index in `layout.py`, which comes from the F75 Max vendor XML, and in `ea75max.json`. The F75 Max has PgUp (118) and PgDn (121). The EA75MAX has neither and has Home at 117.

So the F75 Max key index is probably the LED number in `layout.py`'s `LEDS`. For example, Esc is 1, F1 is 2, Caps Lock is 55, and right Ctrl is 98. This is inferred, not confirmed. AULA's F75 Max `rgb-keyboard.xml` holds the real `key_index` values, and a one-key remap on the keyboard confirms them.

Fn (index 96) is in the table too. Remapping Fn probably cuts off the Fn layer and the Fn shortcuts, including the wired-mode switch. Leave it at default.

## Open questions

- Whether the knob press has a key index. See [knob.md](knob.md).
- The full list of special-function and consumer values that the firmware accepts.
- What the vendor software writes to the Fn-layer table for keys that keep their printed Fn shortcuts.
