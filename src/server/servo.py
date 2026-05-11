import asyncio
import pigpio

# ── Edit these to match your wiring ──────────────────────────────────────────
SERVO_PINS = {
    1: 18,
    2: 19,
    3: 20,
    4: 21,
}
OPEN_ANGLE = 110   # degrees
MIN_PW     = 500
MAX_PW     = 2500
STEP_DELAY = 0.05
# ─────────────────────────────────────────────────────────────────────────────

_pi = None


def init():
    global _pi
    _pi = pigpio.pi()
    if not _pi.connected:
        raise RuntimeError("pigpiod not running")


def stop():
    for pin in SERVO_PINS.values():
        _pi.set_servo_pulsewidth(pin, 0)
    _pi.stop()


def _angle_to_pw(angle: int) -> int:
    return int(MIN_PW + (angle / 180) * (MAX_PW - MIN_PW))


async def _move_slow(pin: int, from_angle: int, to_angle: int):
    step = 1 if to_angle > from_angle else -1
    for angle in range(from_angle, to_angle + step, step):
        _pi.set_servo_pulsewidth(pin, _angle_to_pw(angle))
        await asyncio.sleep(STEP_DELAY)


def _pin(servo_num: int) -> int:
    if servo_num not in SERVO_PINS:
        raise ValueError(f"unknown servo {servo_num!r}; valid: {sorted(SERVO_PINS)}")
    return SERVO_PINS[servo_num]


async def open_servo(servo_num: int):
    pin = _pin(servo_num)
    await _move_slow(pin, 0, OPEN_ANGLE)


async def close_servo(servo_num: int):
    pin = _pin(servo_num)
    await _move_slow(pin, OPEN_ANGLE, 0)
    _pi.set_servo_pulsewidth(pin, 0)
