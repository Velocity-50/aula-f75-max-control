# Factory reset

There are two resets. Neither one is known to clear everything.

## Hold Fn and Esc

The Epomaker F75 Max manual lists a long press of **Fn** + **Esc** as "reset keyboard settings". A user in [VitalyArt issue #20](https://github.com/VitalyArt/Aula-F75-Max-Driver/issues/20) reports that the combination resets lighting only and keeps Bluetooth pairings.

## Send the reset sequence over USB

VitalyArt's `AulaDevice.factoryReset` sends five exchanges. The meanings in the right column come from matching each exchange with thibaultmiclo's command map and with `protocol.py`. VitalyArt's own step labels differ, so the table lists them as well.

| Step | Reports | VitalyArt's label | Probable effect |
| --- | --- | --- | --- |
| 1 | `04 19`, `04 15` with byte 8 = `08`, 8 zero reports, `04 02` | Clearing display memory | Writes an empty macro buffer. See [macros.md](macros.md). |
| 2 | `04 18`, `04 11` with byte 8 = `09`, 9 zero reports, `04 02`, `04 F0` | Resetting keymap and macro data | Resets every base-layer key to default |
| 3 | `04 18`, `04 27` with byte 8 = `09`, 9 zero reports, `04 02`, `04 F0` | Resetting lighting data | Resets every Fn-layer key to default |
| 4 | `04 18`, `04 13` with byte 8 = `01`, lighting report, `04 02`, `04 F0` | Sending reset footer | Sets lighting to the default effect |
| 5 | `04 18`, `04 17` with byte 2 = `01` and byte 8 = `01`, settings report, `04 02` | Resetting display config | Resets the key locks, sleep timer, and response level |

The zero reports in steps 2 and 3 have no `AA 55` trailer, unlike thibaultmiclo's tables. The keyboard acks the steps anyway.

### Step 4: lighting report

`0b ff 00 00 00 00 00 00 01 05 03 00 00 00 aa 55`, then zeros. With the lighting layout in `protocol.py`, this report sets:

- mode 11, `rolling` in `layout.MODES`
- colour `ff0000`
- rainbow on
- brightness 5
- speed 3
- direction 0

### Step 5: settings report

`00 01 00 00 00 00 02 00 02`, then zeros. thibaultmiclo's settings format (`function_packet`) reads it like this:

| Byte | Setting | Value in the reset |
| --- | --- | --- |
| 0–1 | Header `00 01` | |
| 2 | Disable Win key | 0, off |
| 3 | Disable Alt+F4 | 0, off |
| 4 | Disable Alt+Tab | 0, off |
| 5 | Fn toggle mode | 0, momentary |
| 6 | Sleep timer: 0 never, 1 one minute, 2 five minutes, 3 thirty minutes | 2, five minutes |
| 8 | Response level | 2 |

thibaultmiclo confirmed only the Win key byte on hardware. Its settings report also ends with `AA 55` at bytes 62 and 63. VitalyArt's report has no trailer.

The sources disagree on the response level range. thibaultmiclo (EA75MAX) sends 0 to 4 and labels 2 as about 8 ms to 9 ms. mohin7 (F75 Max) sends 1 to 5, labels 2 as about 5 ms to 6 ms wired, and says it tested the whole settings report on the F75 Max. VitalyArt's 2.4G code also sends 1 to 5. `settings.py` follows the F75 Max sources: 1 to 5, default 2.

### Write settings on the F75 Max

`settings.Settings.encode` builds this report and `Keyboard.settings` sends it with `04 18`, `04 17` (byte 2 = `01`, byte 8 = `01`), the report, then `04 02`. With every other setting at its default and the sleep timer at 3 (30 minutes), the keyboard acknowledged each step (2026-11-09). Whether the keyboard then stays awake for 30 minutes in wireless mode has not been timed yet.

## What the reset leaves behind

In issue #20, a user with firmware `0x0108` reports that the sequence runs, the keyboard reboots during the `04 F0` steps, and screen images and settings survive a power cycle. The user adds that the reset in AULA's Windows software behaves the same. The maintainer sees the same behaviour.

The table above explains the screen images: no step writes the screen block (`04 72`). Why the settings survive is still open.

## Recover a bad remap or macro set

Write an all-zero table to `04 11`, then another to `04 27`, as steps 2 and 3 do. To clear macros, upload an empty buffer as step 1 does. Both writes work without the computer remembering the old state.

VitalyArt's code comments note that the keyboard reboots on `04 F0` and drops the HID connection mid-sequence. A long sequence on one connection needs a retry or a reconnect after each `04 F0`.
