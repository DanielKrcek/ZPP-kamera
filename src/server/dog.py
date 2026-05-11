import asyncio
import json
import math
import os
import socket
from contextlib import asynccontextmanager
from typing import Optional

from unitree_webrtc_connect import (
    RTC_TOPIC,
    SPORT_CMD,
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)
from unitree_webrtc_connect.webrtc_datachannel import WebRTCDataChannel as _WDC

_orig_set_decoder = _WDC.set_decoder

def _set_decoder_with_fallback(self, decoder_type='libvoxel'):
    try:
        _orig_set_decoder(self, decoder_type)
    except RuntimeError:
        _orig_set_decoder(self, 'native')

_WDC.set_decoder = _set_decoder_with_fallback

MOVE_HZ = 10
YAW_SPEED = 0.8        # rad/s applied during closed-loop rotation
_ROTATE_POLL = 0.05    # s between yaw samples
_ROTATE_THRESHOLD = math.radians(2)  # accept within 2° of target
# Dog signaling ports (new firmware: 9991, old: 8081).
SIGNALING_PORTS = (9991, 8081)
PROBE_TIMEOUT_S = 2.0


def _probe(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _reachable(ip: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: any(_probe(ip, p, PROBE_TIMEOUT_S) for p in SIGNALING_PORTS),
    )


def _signed_angle_diff(a: float, b: float) -> float:
    """Signed angular distance from b to a, in (-π, π]."""
    d = (a - b) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d


class Dog:
    def __init__(self, conn: Optional[UnitreeWebRTCConnection]):
        self._conn = conn
        self._lock = asyncio.Lock()
        self._yaw: Optional[float] = None
        if conn is not None:
            self._subscribe_low_state()

    def _subscribe_low_state(self):
        def _on_low_state(msg):
            try:
                self._yaw = msg["data"]["imu_state"]["rpy"][2]
            except (KeyError, IndexError, TypeError):
                pass
        self._conn.datachannel.pub_sub.subscribe(RTC_TOPIC["LOW_STATE"], _on_low_state)

    @property
    def dry_run(self) -> bool:
        return self._conn is None

    async def _send(self, cmd: str, parameter: Optional[dict] = None):
        if self.dry_run:
            print(f"[dry] sport.{cmd}({parameter or {}})")
            return None
        return await self._conn.datachannel.pub_sub.publish_request_new(
            RTC_TOPIC["SPORT_MOD"],
            {
                "api_id": SPORT_CMD[cmd],
                "parameter": json.dumps(parameter or {}),
            },
        )

    async def call(self, cmd: str, parameter: Optional[dict] = None):
        if cmd not in SPORT_CMD:
            raise ValueError(f"unknown sport command: {cmd}")
        async with self._lock:
            return await self._send(cmd, parameter)

    async def move_for(self, vx: float, vy: float, vyaw: float, duration_s: float):
        async with self._lock:
            if self.dry_run:
                print(f"[dry] Move({vx}, {vy}, {vyaw}) for {duration_s}s -> StopMove")
                return
            period = 1.0 / MOVE_HZ
            loop = asyncio.get_event_loop()
            deadline = loop.time() + duration_s
            while loop.time() < deadline:
                await self._send("Move", {"x": vx, "y": vy, "z": vyaw})
                await asyncio.sleep(period)
            await self._send("StopMove")

    async def rotate(self, degrees: float):
        if self.dry_run:
            print(f"[dry] rotate({degrees:.1f}°)")
            return

        target_rad = math.radians(degrees)
        direction = 1.0 if degrees >= 0 else -1.0
        # generous timeout: allow at least 5s plus time for a slow rotation
        timeout = abs(degrees) / 10 + 5

        async with self._lock:
            start_yaw = self._yaw
            if start_yaw is None:
                # no IMU data yet — fall back to timed rotation
                duration = abs(target_rad) / YAW_SPEED
                loop = asyncio.get_event_loop()
                deadline = loop.time() + duration
                while loop.time() < deadline:
                    await self._send("Move", {"x": 0, "y": 0, "z": direction * YAW_SPEED})
                    await asyncio.sleep(_ROTATE_POLL)
                await self._send("StopMove")
                return

            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout
            while loop.time() < deadline:
                traveled = _signed_angle_diff(self._yaw, start_yaw)
                remaining = target_rad - traveled
                if direction * remaining < _ROTATE_THRESHOLD:
                    break
                await self._send("Move", {"x": 0, "y": 0, "z": direction * YAW_SPEED})
                await asyncio.sleep(_ROTATE_POLL)

            await self._send("StopMove")


@asynccontextmanager
async def connect_dog():
    method_name = os.getenv("GO2_METHOD", "LocalSTA")
    ip = os.getenv("GO2_IP", "192.168.123.161")
    method = getattr(WebRTCConnectionMethod, method_name)

    conn: Optional[UnitreeWebRTCConnection] = None
    probe_ip = "192.168.12.1" if method == WebRTCConnectionMethod.LocalAP else ip
    if not await _reachable(probe_ip):
        print(f"[warn] dog not reachable at {probe_ip} (ports {SIGNALING_PORTS}) — running in dry-run")
    else:
        try:
            if method == WebRTCConnectionMethod.LocalAP:
                conn = UnitreeWebRTCConnection(method)
            else:
                conn = UnitreeWebRTCConnection(method, ip=ip)
            await conn.connect()
            print(f"[dog] connected ({method_name}, ip={conn.ip})")
        except Exception as e:
            print(f"[warn] WebRTC connect failed, running in dry-run: {e}")
            conn = None

    try:
        yield Dog(conn)
    finally:
        if conn is not None:
            try:
                await conn.disconnect()
            except Exception as e:
                print(f"[warn] disconnect failed: {e}")
