# Screen pages

The screen shows one page at a time. The home page shows the clock, date, battery, connection, and lock states. Other pages hold the uploaded image and the settings menu. Clock sync switches to the clock page (see below). No command is known that switches to the image page.

## Switch pages on the keyboard

1. Press **Fn** and the knob together. The knob switches from volume control to screen control. The Epomaker F75 Max manual lists this as "Toggle control between Screen and Volume".
2. Turn the knob to step through the pages. Stop on the image page.
3. Press **Fn** and the knob again to return the knob to volume control.

Pressing the knob without **Fn** only sends mute. This procedure was confirmed on an F75 Max on 2026-11-09. In screen control, the knob also reaches the keyboard's other settings pages. The [Tech4Gamers review](https://tech4gamers.com/aula-f75-max-review/) and the HardReset_Pro videos [How to Enter TFT Screen](https://www.youtube.com/watch?v=vncL7hUS27o) and [How to Use TFT Screen](https://www.youtube.com/watch?v=-JsSjmU73ng) describe the same pages: System, RGB effect, colour, brightness, speed, PC volume, language, **Image Display**, and the main page.

## What the computer can do

- **Upload.** `04 72` stores the image and the screen shows it when the upload ends. parsiya/f108-pro confirmed this on the F108 Pro, which has the same USB ID (`ai-docs/lcd-upload-investigation.md`). No upload source sends an extra "show" command after `04 02`.
- **Slot byte.** Byte 2 of `04 72` is a storage slot. AULA's software and every driver use slot 1. No source links it to the displayed page.
- **Clock sync.** Simon-Martens/F75_Initializer says a clock sync moves the screen from the boot logo to the normal home page. Its three captures (`keyboard5`–`keyboard7.pcapng`) contain only the clock sync: `04 18`, `04 28` with byte 8 = `01`, the time report, and `04 02`. mohin7 calls byte 1 of the time report "the screen slot (1-based)". Every source sends `01` there. Nobody has tested other values.

## What sends the screen back to the clock

**Clock sync does.** On 2026-11-09, `POST /api/clock` (the same exchange as `aula.py clock`) switched an F75 Max from the image page to the clock page. Our time report starts `00 01 5A`, so byte 1 is `01`. **Sync clock** in the web UI and `aula.py clock` therefore hide the uploaded image until you turn the knob back to it.

Uploads survive power cycles and the factory reset ([VitalyArt issue #20](https://github.com/VitalyArt/Aula-F75-Max-Driver/issues/20)), so other returns to the clock are page changes, not lost data. Other likely triggers are waking from sleep (the default is 5 minutes idle) and power cycles. Neither is confirmed.

## Playback glitches in wired mode

In wired USB mode, the keyboard sometimes corrupts frames as it plays an animation. The bad frames differ from loop to loop: a frame goes wrong from some row to the bottom, or a whole frame is wrong, and the next loop is clean. With the 2.4G receiver, the same upload plays cleanly. Reported on 2026-11-09.

The glitches happen whether or not any program on the computer talks to the keyboard. Thirty-second tests with `hid.enumerate` loops, the web server, and the CLI seemed at first to show a link to the server, but the glitches come and go on their own, and later watching showed them without any of these running. So this project's software is not the cause.

The stored data is fine: `screen.bin` decodes cleanly, every upload chunk was acked, and four independent encoders (this project, VitalyArt, mohin7, stimong's F75Probe) build the same stream layout. The cause is somewhere in wired operation: USB power, or the keyboard servicing USB traffic from macOS while it reads frames from flash. A different cable, port, or powered hub has not been tried.

Configuration only works over the cable, so upload in wired mode, then switch to the 2.4G receiver for clean playback.

## Open questions

- Whether a different byte 1 in the clock report changes the page, for example to the image page. A test costs nothing in flash: send the clock sync with `02` there and watch the screen.
- Whether the settings block `04 17` has a page field. Bytes 7 and 9 to 61 of its report have no known meaning.
- Why wired mode corrupts playback, and whether a different cable, port, or powered hub changes it.
