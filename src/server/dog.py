import asyncio
import json
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

MOVE_HZ = 10
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


class Dog:
    def __init__(self, conn: Optional[UnitreeWebRTCConnection]):
        self._conn = conn
        self._lock = asyncio.Lock()

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


@asynccontextmanager
async def connect_dog():
    method_name = os.getenv("GO2_METHOD", "LocalSTA")
    ip = os.getenv("GO2_IP", "192.168.123.18")
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
