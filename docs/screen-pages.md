# Screen pages

The screen shows one page at a time. The home page shows the clock, date, battery, connection, and lock states. Other pages hold the uploaded image and the settings menu. Nobody has published a command that picks the page from the computer.

## Switch pages on the keyboard

1. Press **Fn** and the knob together. The knob switches from volume control to screen control. The Epomaker F75 Max manual lists this as "Toggle control between Screen and Volume".
2. Turn the knob to step through the pages. Stop on the image page.
3. Press **Fn** and the knob again to return the knob to volume control.

Pressing the knob without **Fn** only sends mute. Step 2 comes from a [Tech4Gamers review](https://tech4gamers.com/aula-f75-max-review/) ("You turn the volume knob to cycle between these layers") and the HardReset_Pro videos [How to Enter TFT Screen](https://www.youtube.com/watch?v=vncL7hUS27o) and [How to Use TFT Screen](https://www.youtube.com/watch?v=-JsSjmU73ng). The video lists the menu as System, RGB effect, colour, brightness, speed, PC volume, language, **Image Display**, and the main page.

## What the computer can do

- **Upload.** `04 72` stores the image and the screen shows it when the upload ends. parsiya/f108-pro confirmed this on the F108 Pro, which has the same USB ID (`ai-docs/lcd-upload-investigation.md`). No upload source sends an extra "show" command after `04 02`.
- **Slot byte.** Byte 2 of `04 72` is a storage slot. AULA's software and every driver use slot 1. No source links it to the displayed page.
- **Clock sync.** Simon-Martens/F75_Initializer says a clock sync moves the screen from the boot logo to the normal home page. Its three captures (`keyboard5`–`keyboard7.pcapng`) contain only the clock sync: `04 18`, `04 28` with byte 8 = `01`, the time report, and `04 02`. mohin7 calls byte 1 of the time report "the screen slot (1-based)". Every source sends `01` there. Nobody has tested other values.

## What sends the screen back to the clock

No source says. Uploads survive power cycles and the factory reset ([VitalyArt issue #20](https://github.com/VitalyArt/Aula-F75-Max-Driver/issues/20)), so a return to the clock is a page change, not lost data. Likely triggers are waking from sleep (the default is 5 minutes idle) and power cycles. Neither is confirmed.

## Open questions

- Whether a different byte 1 in the clock report changes the page. A test costs nothing in flash: send the clock sync with `02` there and watch the screen.
- Whether the settings block `04 17` has a page field. Bytes 7 and 9 to 61 of its report have no known meaning.
