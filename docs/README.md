# Protocol research notes

These notes cover keyboard protocol research: key remapping and macros (now implemented in `keymap.py` and `protocol.py`), and the knob, factory reset, and screen pages, which are not implemented. They collect what other projects and AULA's software reveal, so nobody has to download and read them again. The [main README](../README.md) documents how to use the implemented features.

| Topic | Keyboard supports it? | Status of the evidence | Notes |
| --- | --- | --- | --- |
| Key remap, base layer and Fn layer | Yes | Tested on the F75 Max, one key at a time. Backspace cannot be set on the Fn layer | [keymap.md](keymap.md) |
| Macros stored on the keyboard | Yes | Tested on the F75 Max: one macro played once from a Fn-layer key | [macros.md](macros.md) |
| Knob rotation and press | Unknown | Input codes known. No write format known | [knob.md](knob.md) |
| Factory reset | Partly | A reset sequence exists. A user reports that it leaves screen images and settings in place | [reset.md](reset.md) |
| Choosing the screen page from the computer | Unknown | No source has a command. On the keyboard, Fn + knob and then turning the knob switches pages (confirmed on hardware) | [screen-pages.md](screen-pages.md) |

## Sources

Each note names the source behind each fact. Commits are the versions read on 2026-11-09.

| Source | Commit | What it contributes |
| --- | --- | --- |
| [thibaultmiclo/aula-driver](https://github.com/thibaultmiclo/aula-driver) | `abd11df` | Python driver for the AULA **EA75MAX** (`0c45:800a`). The only source with working remap and macro writes, cross-checked against the vendor's `DeviceDriver.exe`. Key data is in `aula/data/ea75max.json`. Code is in `aula/protocol.py` and `aula/keycodes.py`. |
| [VitalyArt/Aula-F75-Max-Driver](https://github.com/VitalyArt/Aula-F75-Max-Driver) | `66f93c9` | Swift driver for the F75 Max. Factory reset sequence and an unfinished knob probe, in `Sources/AulaF75MaxDriver/AulaDevice.swift`. |
| [mohin7/aula-f75max](https://github.com/mohin7/aula-f75max) | `bc6fcbd` | Swift app for the F75 Max. Knob input codes are in `Sources/AulaKit/Keymap/Layouts/F75MaxLayout.swift`. Open questions are in `Docs/Hardware-Protocol-Notes.md`. No remap or macro code. |
| [tarikmanoar/aula-f75-max](https://github.com/tarikmanoar/aula-f75-max) | `12dc9b6` | Survey of public `0c45:800a` projects in `docs/packet-catalog.md` and a USB capture guide in `docs/windows-capture-guide.md`. It predates thibaultmiclo's findings and says no remap or macro payload was public. |
| [Epomaker F75 Max manual](https://epomaker.com/cdn/shop/files/EPOMAKER_AULA_F75_MAX_manual.pdf) | | Fn shortcuts, including the knob and reset combinations |

### The EA75MAX is a sibling, not the same keyboard

The EA75MAX shares the USB ID and the command set, but its hardware differs. Its screen is 135×240 with a 141-frame limit, where the F75 Max screen is 128×128 with 255 frames. Its key list has no PgUp or PgDn and adds Home. Treat every EA75MAX fact as likely for the F75 Max, not confirmed. One fact supports the shared format: `04 23` carries per-key colours on both keyboards, and `protocol.py` uses it on the F75 Max.

## Local files

| File | What it is |
| --- | --- |
| `~/Downloads/AULA F75 Setup v2.0 20260514.exe` | Inno Setup installer (`OemDrv.exe`) for the regular **F75**, USB ID `258a:010c`, wireless `3554:fa09`. It uses a different chip, so its formats do not apply to the F75 Max. Unpack it with `innoextract`. Its `.ini` and `.xml` files are UTF-16. |
| `~/Downloads/AulaF75MaxDriver-v1.7.0.dmg` | Release build of VitalyArt's app (`vitalyart.aula-macos-driver` 1.7.0). |

The F75 installer still shows what AULA's software offers on that model. Its UI strings include a macro editor (record, insert, delay, cycle until released, cycle until any key pressed), key **Disable**, and media keys. Its key table `Dev/kb/fr/KB.ini` lists the knob press as a remappable key:

```ini
;Wheel
K82=0,0,0,0, 0x09,0x01,0x0700001D,84
```

The F75 Max driver files that `layout.py` used (`layouts/rgb-keyboard.xml` from AULA's F75 Max Windows driver 1.0.0.5) are not on this machine. That XML has a `key_index` attribute per key. thibaultmiclo's `tools/layout_from_vendor.py` turns it into a key list. With that file, the F75 Max key indices in [keymap.md](keymap.md) would no longer be inferred.

## Confirm a fact on the keyboard

A USB capture of AULA's Windows software decodes any remaining question. Record one action at a time, such as one remap, one macro, or one knob change. tarikmanoar's `docs/windows-capture-guide.md` gives a USBPcap and Wireshark procedure. The keyboard cannot report its configuration back, so a capture is the only way to read what the vendor software writes.
