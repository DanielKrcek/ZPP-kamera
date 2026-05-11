import math
from typing import Awaitable, Callable, Optional

from dog import Dog
from servo import close_servo, open_servo

LINEAR_VEL = 0.3   # m/s
YAW_SPEED  = 0.8   # rad/s

Handler = Callable[[Dog, Optional[float]], Awaitable[None]]


def _duration(n: Optional[float]) -> float:
    return n if n is not None else 1.0


async def _rotate(d: Dog, degrees: Optional[float]) -> None:
    deg = degrees if degrees is not None else 90.0
    duration_s = abs(deg) * (math.pi / 180) / YAW_SPEED
    vyaw = YAW_SPEED if deg > 0 else -YAW_SPEED
    await d.move_for(0, 0, vyaw, duration_s)


COMMANDS: dict[str, Handler] = {
    "forward":   lambda d, n: d.move_for( LINEAR_VEL, 0, 0, _duration(n)),
    "back":      lambda d, n: d.move_for(-LINEAR_VEL, 0, 0, _duration(n)),
    "left":      lambda d, n: d.move_for(0,  LINEAR_VEL, 0, _duration(n)),
    "right":     lambda d, n: d.move_for(0, -LINEAR_VEL, 0, _duration(n)),
    "rotate":    _rotate,

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

    "open":      lambda d, n: open_servo(n),
    "close":     lambda d, n: close_servo(n),
}


def parse(token: str):
    parts = token.strip().lower().split(":", 1)
    name = parts[0]
    if name not in COMMANDS:
        return None
    arg = float(parts[1]) if len(parts) == 2 else None
    return name, arg
