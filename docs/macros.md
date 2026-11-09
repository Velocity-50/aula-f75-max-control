# Macros

The keyboard stores up to 100 macros in one buffer and plays them without the computer. A key plays a macro when its remap slot points at that macro (see [keymap.md](keymap.md)). Source: thibaultmiclo/aula-driver, `aula/protocol.py` (`macro_buffer`, `Keyboard.set_macros`), which follows the vendor serialiser (`DeviceDriver.exe` function at `0x42d5d0`). That project tested macros on an EA75MAX. They also work on the F75 Max; see [Tested on the F75 Max](#tested-on-the-f75-max).

## Upload the buffer

The upload differs from other blocks: no `04 18` begin and no `04 F0` finalize.

| Step | Report | Ack read |
| --- | --- | --- |
| 1 | `04 19` | Yes |
| 2 | `04 15` with byte 8 = number of 64-byte reports in the buffer | Yes |
| 3 | Wait 30 ms, then send the buffer as 64-byte reports | After the last report only |
| 4 | Wait 30 ms, then `04 02` apply | Yes |

Every upload replaces all macros. Upload the full set each time.

On the F75 Max, the read after the last buffer report returns all zeros.

## Tested on the F75 Max

Tested on 2026-11-09 with a one-off script. It uploaded one macro, `h` down, `h` up, `i` down, `i` up with 10 ms delays (an 8-report buffer), and then wrote a Fn-layer table with J (62) set to `06 00 00 01` (macro 0, play once). Fn + J typed `hi`. The other play modes were not tested.

## Buffer layout

The buffer starts with a 400-byte header: 100 slots of 4 bytes, one per macro position.

| Header slot `i` | Meaning |
| --- | --- |
| `lo hi 00 00` | Macro `i` starts at byte offset `hi*256 + lo` from the start of the buffer |
| `FF FF FF FF` | Macro `i` exists but has no events |
| `00 00 00 00` | Position not used. thibaultmiclo leaves unused positions as zeros. What the vendor writes there is unknown. |

The first macro starts at offset 400 (`90 01`). Each macro is an 8-byte header followed by its records:

| Bytes | Meaning |
| --- | --- |
| 0–1 | Number of 4-byte records, little-endian. Each event has two records, so this is twice the event count. |
| 2–7 | Zero |
| 8 onward | Records, in pairs: an event record and then a delay record |

The next macro starts right after the last record.

### Records

| Record | Bytes | Notes |
| --- | --- | --- |
| Key down | `00 00 usage B0` | HID keyboard usage |
| Key up | `00 00 usage 30` | |
| Mouse button down | `00 00 button 90` | `01` left, `02` right, `04` middle |
| Mouse button up | `00 00 button 10` | |
| Delay | `lo hi 00 50` | Milliseconds to wait after the preceding event, 10 to 65535 |

Every event has a delay record after it, even when the delay is the 10 ms minimum.

### Padding and limits

- Let `end` be the offset just past the last record. The buffer is `end // 64 + 1` reports long when `end` is a multiple of 64, and `end // 64 + 2` reports otherwise. It always has at least one spare report.
- Zero-fill the buffer to that length. The last two bytes are the trailer `AA 55`.
- The buffer is at most `0xE00` bytes (3584, 56 reports).
- The vendor software also rejects a set when `(macros + events) * 8` is more than 2700.

## Example

One macro that types `a`: key down, 10 ms, key up, 10 ms.

```text
offset 0     90 01 00 00            header slot 0: macro 0 starts at 400
offset 4     00 00 00 00 ...        header slots 1–99 unused
offset 400   04 00 00 00 00 00 00 00  4 records
offset 408   00 00 04 B0  0A 00 00 50  key down A, delay 10 ms
offset 416   00 00 04 30  0A 00 00 50  key up A, delay 10 ms
```

`end` is 424, so the buffer is 424 // 64 + 2 = 8 reports (512 bytes), and byte 8 of `04 15` is `08`. Bytes 510 and 511 are `AA 55`.

## Bind a macro to a key

Set the key's remap slot to `06 macro mode count`. `macro` is the 0-based header position. thibaultmiclo's CLI numbers macros from 1 and subtracts 1.

| Mode | Value | `count` |
| --- | --- | --- |
| Play once | `00` | Ignored. thibaultmiclo sends `01`. |
| Play `count` times | `01` | 1 to 255 |
| Toggle: repeat until the key is pressed again | `02` | Ignored |
| Repeat while the key is held | `03` | Ignored |
| Click | `04` | Ignored |

The meaning of click mode is not documented.

## Related: the reset sequence clears this buffer

VitalyArt's factory reset starts with `04 19`, then `04 15` with byte 8 = `08`, then 8 zero reports, then `04 02`. The code labels the step "Clearing display memory". It has the same shape as a macro upload, so it most likely writes an empty macro buffer and leaves the screen alone. This fits the report that the reset keeps screen images. See [reset.md](reset.md).
