"""Convert images and animated GIFs into the F75 Max screen stream."""

import math
from io import BytesIO

from PIL import Image, ImageOps, ImageSequence

from protocol import SCREEN_CHUNK, SCREEN_HEADER, SCREEN_MAX_FRAMES, SCREEN_SIZE, screen_chunks

FITS = ("contain", "cover", "stretch")
MIN_DELAY, MAX_DELAY = 30, 500  # ms per frame; stored as one byte in 2 ms units
SIZE = (SCREEN_SIZE, SCREEN_SIZE)


def fit_frame(image: Image.Image, fit: str) -> Image.Image:
    image = image.convert("RGBA")

    if fit == "stretch":
        image = image.resize(SIZE, Image.LANCZOS)
    elif fit == "cover":
        image = ImageOps.fit(image, SIZE, Image.LANCZOS)
    else:
        image = ImageOps.contain(image, SIZE, Image.LANCZOS)

    canvas = Image.new("RGB", SIZE)
    canvas.paste(image, ((SCREEN_SIZE - image.width) // 2, (SCREEN_SIZE - image.height) // 2), image)

    return canvas


def normalize(frames: list[Image.Image], delays: list[int]) -> tuple[list[Image.Image], list[int]]:
    """Fit frame timing to what the screen supports, keeping the total duration where possible."""
    out_frames, out_delays = [], []

    # a frame can show for at most MAX_DELAY, so longer frames become repeats
    for frame, delay in zip(frames, delays):
        repeats = max(1, math.ceil(delay / MAX_DELAY))
        out_frames += [frame] * repeats
        out_delays += [delay / repeats] * repeats

    # too many frames: keep evenly spaced ones and fold the dropped frames' time into them
    if len(out_frames) > SCREEN_MAX_FRAMES:
        total = len(out_frames)
        keep = [i * total // SCREEN_MAX_FRAMES for i in range(SCREEN_MAX_FRAMES)]
        ends = keep[1:] + [total]
        out_delays = [sum(out_delays[start:end]) for start, end in zip(keep, ends)]
        out_frames = [out_frames[i] for i in keep]

    return out_frames, [round(min(max(d, MIN_DELAY), MAX_DELAY)) for d in out_delays]


def load(data: bytes, fit: str = "contain") -> tuple[list[Image.Image], list[int]]:
    """Decode an image or animation into screen-sized frames and per-frame delays in ms."""
    if fit not in FITS:
        raise ValueError(f"fit must be one of {', '.join(FITS)}")

    source = Image.open(BytesIO(data))
    frames, delays = [], []

    for frame in ImageSequence.Iterator(source):
        frames.append(fit_frame(frame, fit))
        delays.append(frame.info.get("duration") or source.info.get("duration") or 100)

    return normalize(frames, delays)


def rgb565(frame: Image.Image) -> bytes:
    out = bytearray(SCREEN_SIZE * SCREEN_SIZE * 2)
    rgb = frame.tobytes()

    for i in range(SCREEN_SIZE * SCREEN_SIZE):
        r, g, b = rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2]
        value = (r >> 3) << 11 | (g >> 2) << 5 | b >> 3
        out[i * 2] = value & 0xFF
        out[i * 2 + 1] = value >> 8

    return bytes(out)


def encode(frames: list[Image.Image], delays: list[int]) -> bytes:
    header = bytearray(SCREEN_HEADER)
    header[0] = len(frames)

    for i, delay in enumerate(delays):
        header[1 + i] = round(delay / 2)

    stream = bytes(header) + b"".join(rgb565(frame) for frame in frames)

    return stream + bytes(screen_chunks(len(frames)) * SCREEN_CHUNK - len(stream))


def preview(frames: list[Image.Image], delays: list[int]) -> bytes:
    """Animated GIF of the frames reduced to the screen's 16-bit colour."""
    reduced = [
        Image.merge("RGB", [band.point(lambda v, bits=bits: v >> bits << bits) for band, bits in zip(f.split(), (3, 2, 3))])
        for f in frames
    ]
    out = BytesIO()
    reduced[0].save(out, "GIF", save_all=True, append_images=reduced[1:], duration=delays, loop=0, disposal=1)

    return out.getvalue()
