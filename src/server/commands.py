import re
from typing import Awaitable, Callable, Optional

from dog import Dog

LINEAR_VEL = 0.3   # m/s
ANGULAR_VEL = 0.5  # rad/s

Handler = Callable[[Dog, Optional[int]], Awaitable[None]]


def _duration(n: Optional[int]) -> float:
    # Numeric arg is duration in deciseconds (0.1 s). Default 10 = 1.0 s.
    return (n or 10) / 10


COMMANDS: dict[str, Handler] = {
    "forward":   lambda d, n: d.move_for( LINEAR_VEL, 0, 0, _duration(n)),
    "back":      lambda d, n: d.move_for(-LINEAR_VEL, 0, 0, _duration(n)),
    "left":      lambda d, n: d.move_for(0,  LINEAR_VEL, 0, _duration(n)),
    "right":     lambda d, n: d.move_for(0, -LINEAR_VEL, 0, _duration(n)),
    "turnleft":  lambda d, n: d.move_for(0, 0,  ANGULAR_VEL, _duration(n)),
    "turnright": lambda d, n: d.move_for(0, 0, -ANGULAR_VEL, _duration(n)),

    "stop":      lambda d, _: d.call("StopMove"),
    "stand":     lambda d, _: d.call("StandUp"),
    "standdown": lambda d, _: d.call("StandDown"),
    "balance":   lambda d, _: d.call("BalanceStand"),
    "recover":   lambda d, _: d.call("RecoveryStand"),
    "damp":      lambda d, _: d.call("Damp"),
    "sit":       lambda d, _: d.call("Sit"),
    "rise":      lambda d, _: d.call("RiseSit"),

    "hello":     lambda d, _: d.call("Hello"),
    "stretch":   lambda d, _: d.call("Stretch"),
    "heart":     lambda d, _: d.call("FingerHeart"),
    "scrape":    lambda d, _: d.call("Scrape"),
    "dance":     lambda d, _: d.call("Dance1"),
    "dance2":    lambda d, _: d.call("Dance2"),
    "frontflip": lambda d, _: d.call("FrontFlip"),
    "backflip":  lambda d, _: d.call("BackFlip"),
    "leftflip":  lambda d, _: d.call("LeftFlip"),
    "jump":      lambda d, _: d.call("FrontJump"),
    "pounce":    lambda d, _: d.call("FrontPounce"),
}

_CMD_RE = re.compile(r"^([a-z]+)(\d+)?$")


def parse(token: str):
    m = _CMD_RE.match(token.strip().lower())
    if not m:
        return None
    name, num = m.group(1), m.group(2)
    if name not in COMMANDS:
        return None
    return name, int(num) if num else None
