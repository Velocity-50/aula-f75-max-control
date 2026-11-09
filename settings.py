"""Keyboard-wide settings for the AULA F75 Max: key locks, Fn switch, sleep timer, key response.

Format from mohin7/aula-f75max (tested on the F75 Max) and thibaultmiclo/aula-driver; see docs/reset.md.
"""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from protocol import PACKET

SLEEP_MINUTES = (0, 1, 5, 30)  # firmware byte = index; 0 = never sleep


class Settings(BaseModel):
    disable_win: bool = False
    disable_alt_f4: bool = False
    disable_alt_tab: bool = False
    fn_switch: bool = False
    sleep: int = 5  # idle minutes before sleeping in wireless mode
    response: Annotated[int, Field(ge=1, le=5)] = 2  # 1 fastest, 5 most debounce

    @field_validator("sleep")
    @classmethod
    def known_sleep(cls, value: int) -> int:
        if value not in SLEEP_MINUTES:
            raise ValueError(f"sleep must be one of {', '.join(map(str, SLEEP_MINUTES))} minutes")

        return value

    def encode(self) -> bytes:
        report = bytearray(PACKET)
        report[0:2] = b"\x00\x01"
        report[2:6] = bytes([self.disable_win, self.disable_alt_f4, self.disable_alt_tab, self.fn_switch])
        report[6] = SLEEP_MINUTES.index(self.sleep)
        report[8] = self.response
        report[62:64] = b"\xaa\x55"

        return bytes(report)
