# Prod setup: Pi bridging Laravel ↔ Go2

The Python server in `src/server/` turns HTTP POSTs into Unitree sport
commands over WebRTC. In prod it runs on a Raspberry Pi that sits between
your Laravel app (on the LAN) and the Go2 (on its own Wi-Fi AP).

## Topology

```
[Laravel host] ──LAN──▶ [Pi: eth0]  ─┐
                                     │ runs uvicorn on :8000
                        [Pi: wlan0] ─┘──Go2 AP──▶ [Go2 MCU 192.168.12.1]
```

- `eth0` on the Pi → your home/office router. Gets a LAN IP (DHCP or
  static — your choice). This is the interface Laravel talks to.
- `wlan0` on the Pi → joined to the Go2's own Wi-Fi SSID. The Go2's
  WebRTC signaling only listens on the AP network (`192.168.12.1`),
  not on the wired Jetson port.
- The uvicorn server binds to `0.0.0.0:8000` so it's reachable on both
  interfaces. Laravel hits it on the LAN side; WebRTC flows to the dog
  via Wi-Fi.

The Pi is dual-homed: default route via `eth0` (internet / LAN),
`192.168.12.0/24` automatically via `wlan0` (dog). The dog's AP does
not advertise a default gateway, so no manual route tweaking is needed.

## 1. Base OS

64-bit Raspberry Pi OS (Debian 12 / bookworm). The library's native deps
(`aiortc`, `av`, `pylibsrtp`, `cryptography`) ship aarch64 wheels.

```
sudo apt update
sudo apt install -y python3-pip python3-venv portaudio19-dev git
```

## 2. Clone & install

```
cd /opt
sudo git clone <repo-url> zpp-kamera
sudo chown -R pi:pi zpp-kamera
cd zpp-kamera
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 3. Join the Go2 Wi-Fi on wlan0

Use `nmcli` (bookworm's default). Keep `eth0` as the default route.

```
# one-time: pair the Pi with the dog's SSID
sudo nmcli device wifi connect '<Go2-SSID>' password '<Go2-password>' ifname wlan0

# verify
ip -4 addr show wlan0          # should show 192.168.12.x
ip route                        # default via eth0; 192.168.12.0/24 dev wlan0
ping -c2 192.168.12.1           # should respond
```

If the Pi insists on making `wlan0` the default route, demote it:

```
sudo nmcli connection modify '<Go2-SSID>' ipv4.never-default yes
sudo nmcli connection up '<Go2-SSID>'
```

## 4. Run the server

Manual smoke test:

```
cd /opt/zpp-kamera/src/server
GO2_METHOD=LocalAP /opt/zpp-kamera/.venv/bin/uvicorn server:app \
    --host 0.0.0.0 --port 8000
```

Expected startup log includes `[dog] connected (LocalAP, ip=192.168.12.1)`.
Ignore the `ERROR:root:` lines about port 8081 — that's the library trying
the old signaling path before falling through to the new one.

From the Laravel host:

```
curl http://<pi-lan-ip>:8000/api/health
# {"status":"ok","dry_run":false}

curl -X POST http://<pi-lan-ip>:8000/api/move/sit
# dog sits
```

## 5. systemd service

```
sudo tee /etc/systemd/system/go2-server.service >/dev/null <<'EOF'
[Unit]
Description=Go2 REST bridge (FastAPI + unitree_webrtc_connect)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zpp-kamera/src/server
Environment=GO2_METHOD=LocalAP
ExecStart=/opt/zpp-kamera/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now go2-server
sudo systemctl status go2-server
journalctl -u go2-server -f       # follow logs
```

## 6. Env config

Read by `src/server/dog.py`:

| Var | Default | Notes |
|---|---|---|
| `GO2_METHOD` | `LocalSTA` | Use `LocalAP` on the Pi (Wi-Fi-joined to dog). |
| `GO2_IP` | `192.168.123.18` | Only used in `LocalSTA` mode. |

## 7. Laravel integration

```php
Http::timeout(15)->post("http://{$piHost}:8000/api/move/" . urlencode($cmd));
```

Command grammar: comma-separated tokens, each optionally followed by a
duration in deciseconds. Examples:

- `sit` — Sit action.
- `forward20` — forward for 2.0 s.
- `forward20,turnleft10,hello` — chain.

Full list: `GET /api/commands`.

## 8. Upgrades

```
cd /opt/zpp-kamera
git pull
.venv/bin/pip install -r requirements.txt     # if requirements changed
sudo systemctl restart go2-server
```

## 9. Troubleshooting

- `[warn] dog not reachable at 192.168.12.1 ...` → Pi isn't associated
  with the Go2 AP, or dog is in 4G-only mode. Re-run
  `sudo nmcli device wifi connect '<Go2-SSID>' ...`.
- `dry_run: true` but `[dog] connected` printed on startup → check you
  don't have a second uvicorn running on :8000 from an editor or earlier
  shell (`sudo lsof -iTCP:8000 -sTCP:LISTEN`).
- `Signaling State: ⚫ closed` in the log after startup → the dog
  renegotiated connectivity (commonly because the Unitree mobile app
  connected). Close the mobile app; systemd will restart us.
- `GET /api/debug` — returns whether the WebRTC peer connection and
  data channel are open; use when triaging in-flight issues.
