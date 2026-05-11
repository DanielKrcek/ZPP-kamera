import pigpio
import time

SERVO_PIN = 18
MIN_PW = 500
MAX_PW = 2500
STEP_DELAY = 0.05

def angle_to_pw(angle):
    return int(MIN_PW + (angle / 180) * (MAX_PW - MIN_PW))

def move_slow(pi, from_angle, to_angle):
    step = 1 if to_angle > from_angle else -1
    for angle in range(from_angle, to_angle + step, step):
        pi.set_servo_pulsewidth(SERVO_PIN, angle_to_pw(angle))
        time.sleep(STEP_DELAY)

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError('pigpiod not running')

try:
    print('Slowly opening to 110 degrees...')
    move_slow(pi, 0, 110)
    print('Holding for 3 seconds...')
    time.sleep(3)
    print('Slowly returning to 0...')
    move_slow(pi, 110, 0)
finally:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()
