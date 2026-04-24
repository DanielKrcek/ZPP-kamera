# ZPP-kamera

## Syncing code:
- Bash: call `chmod +x ./push.sh`, which rsyncs the changes
- Windows: figure it out lol

## Setup Notes
- `pip install -r requirements.txt`
- for MacOS aarch64, portaudio may not be installed: `brew install portaudio`.

## Go2 LiDAR example (`webRTCgo2g1/go2_lidar.py`)

Live top-down point-cloud view from the Go2's LiDAR over WebRTC. Subscribes to
`rt/utlidar/voxel_map_compressed`, uses the `native` decoder to get `Nx3`
numpy points, and renders them with matplotlib (height → color).

### 1. Install deps

```bash
pip install -r webRTCgo2g1/requirements.txt
```

The one that matters is `unitree_webrtc_connect` (pulled from PyPI). The rest
are transitive (aiortc, av, numpy, matplotlib, etc.).

### 2. Connect to the robot

Per the manual (`docs/go2_pripojeni.pdf`): you **cannot** connect to the
robot's sensors directly from your laptop. You can only connect to the
**Jetson Orin** inside the robot, which in turn talks to the sensors. That
means the script needs to run *on the Jetson*, not on your laptop.

**Wired (primary path per manual):**

1. Plug Ethernet into the rear port on the robot.
2. Set your laptop to a static IP on `192.168.123.0/24`, mask `255.255.255.0`.
   Recommended `192.168.123.222`. Any host is fine **except** `1–25` and `161`
   (reserved). Gateway/DNS can be left blank.
3. SSH in:
   ```bash
   ssh unitree@192.168.123.18     # password: 123
   ```
4. Under `~/teams/` create your team subdir, copy/clone the script there,
   and run it on the Jetson.

Since the Jetson is headless, matplotlib can't pop a window. Options:
- `ssh -X unitree@192.168.123.18` (X forwarding) — slow but works.
- Save frames to disk (`plt.savefig(...)` in the `update` callback).
- Refactor the script so the asyncio WebRTC task runs on the Jetson and
  publishes points over a socket to your laptop for plotting.

**Wi-Fi AP path (alternative):**

Join the Go2's own SSID, then in `go2_lidar.py` line 25 use
`WebRTCConnectionMethod.LocalAP` (the current default). Laptop plots directly.

### 3. Run

```bash
python3 go2_lidar.py
```

You should see "Connected!" then "Subscribed to rt/utlidar/voxel_map_compressed",
and points start flowing through the callback.

### macOS vs Windows

| Thing | macOS | Windows |
|---|---|---|
| matplotlib backend | Script hardcodes `matplotlib.use("MacOSX")` on line 5 — works as-is | **Change line 5** to `matplotlib.use("TkAgg")` (or just delete the `use(...)` call and let it pick the default) |
| venv activate | `source venv/bin/activate` | `venv\Scripts\activate` |
| PyAudio / portaudio | `brew install portaudio` before `pip install` | Wheels install fine from pip, no system dep needed |
| Joining Go2 AP | macOS will warn "no internet" — ignore, and turn off Auto-Join on your main Wi-Fi so it doesn't bounce back | Windows may mark it as a metered / unknown network — accept and allow |

### Troubleshooting

- **Hangs on `connect()`** — you're not on the robot's AP, or firewall is blocking UDP. Check `ping 192.168.12.1`.
- **Window opens but no points** — confirm the callback is firing (print in `lidar_callback`). If `msg["data"]["data"]["points"]` is missing, the decoder didn't switch to `native`; make sure `set_decoder("native")` is before the subscribe.
- **`Callback error: ... keys=[...]`** — the message shape changed; print `msg` once to see the new layout.
