# Knob

Nobody has published a way to change what the knob does. What it sends is known, and a few clues point at where its setting might live.

## What the knob sends

The knob acts as a consumer-control (media) device. Source: mohin7/aula-f75max, `Sources/AulaKit/Keymap/Layouts/F75MaxLayout.swift`, which shows live knob events from a real F75 Max.

| Action | Consumer usage |
| --- | --- |
| Turn clockwise | `E9` volume up |
| Turn anticlockwise | `EA` volume down |
| Press | `E2` mute |

Over Bluetooth, the keyboard's report descriptor has report ID 8 ("consumer, 16-bit array: knob volume and media") and report ID 9 ("digitizer or dial"). Report 9's purpose is not known. Source: mohin7, `Docs/Hardware-Protocol-Notes.md`.

## Fn shortcuts

According to the Epomaker F75 Max manual, **Fn** + knob press switches the knob between screen control and volume. The knob lighting has no known setting.

## Evidence about a write format

- **No source writes a knob setting.** thibaultmiclo's EA75MAX data has no knob entry. mohin7 lists "the layout of block `04 11`, including knob actions" as an open question.
- **VitalyArt probed `04 11` for the knob press.** `AppViewModel.testKeymapByteWrite` writes a full base-layer table that is all zero except page 8, bytes 0 to 31. Those bytes default to `CD`. Page 8 bytes 0 to 31 are table bytes 512 to 543, which are slots 128 to 135. The app then asks the user to press the knob. The repo has no results. `CD CD CD CD` is not a valid slot in thibaultmiclo's format (see [keymap.md](keymap.md)), so a negative result from that probe proves little.
- **The regular F75 treats the knob press as a key.** AULA's installer for the regular F75 (a different chip, `258a:010c`) lists the press as key `K82` with the comment `;Wheel` in `KB.ini`. Its key table has no entry for turning the knob. If the F75 Max firmware follows the same model, the press has a remap slot, and rotation may not.

## Find the knob's slot

This experiment uses the remap format in [keymap.md](keymap.md). It assumes that the F75 Max key index equals the LED number in `layout.py`.

1. List the base-layer slots that no key uses. With the 81 keys in `layout.py`, those slots are 14–18, 32–36, 50–54, 68–72, 86–90, 97, 104–117, and 122–142.
2. Write a base-layer table that sets half of those slots to `03 CD 00 00` (play or pause) and leaves every other slot at zero.
3. Press the knob. If it sends play or pause instead of mute, the slot is in that half.
4. Halve the set and repeat until one slot remains.
5. Write an all-zero base-layer table to restore every key.

If no unused slot changes the press, the knob setting is somewhere else. Then the next step is a USB capture of AULA's F75 Max Windows software while it changes the knob, if the software can change it.
