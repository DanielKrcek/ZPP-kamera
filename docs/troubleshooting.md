# Go2 troubleshooting notes

## Known issue: Dog #1 — Jetson unreachable

**Date observed:** 2026-04-24
**Status:** Unresolved, dog #2 used as substitute.

### Symptoms

With laptop statically configured on `192.168.123.67/24` (Ethernet via rear
port of the robot, per `go2_pripojeni.pdf`):

- `ping 192.168.123.18` → `Request timeout` / `No route to host`
- `arp -an | grep 192.168.123.18` → `(incomplete)` — ARP never resolves
- `ssh unitree@192.168.123.18` → hangs indefinitely, no banner, no timeout
- Full subnet sweep (`ping` all of `192.168.123.0/24`) reveals only one
  other host: **`.161`**, MAC `7e:1d:75:60:f5:89` — the low-level
  motion controller board.
- Persisted across a full robot reboot.

### Interpretation

The cable, laptop config, and Ethernet port are **not** at fault: the
motion controller at `.161` responds to ARP and ping with ~1 ms RTT, so
Layer 1 / Layer 2 to the robot is healthy.

The Jetson Orin itself is either:

1. not powered on (possible separate power rail / switch inside the robot),
2. booted but its Ethernet interface is down / on a different network, or
3. hardware-faulted.

### How to verify quickly when testing a new dog

```bash
# 1. Link is up, static IP on en5 (replace with your iface)
ifconfig en5 | grep -E "inet |status"
#   expect:  inet 192.168.123.67  netmask 0xffffff00 ...
#            status: active

# 2. Jetson reachable
ping -c 3 192.168.123.18
#   expect: 3 replies, <2 ms

# 3. SSH open
ssh unitree@192.168.123.18      # password: 123
```

If step 2 fails but `ping 192.168.123.161` succeeds, it is the same
failure mode as dog #1 — the Jetson is not on the link.

### Confirmed working: Dog #2

Same laptop, same cable, just moved between robots. Jetson at
`192.168.123.18` answered ARP immediately (MAC `3c:6d:66:03:bd:3d`,
<1 ms ping). No laptop-side changes required.

## Laptop network setup (reference)

Per `go2_pripojeni.pdf`:

- Static IPv4 on the Ethernet interface, anywhere in `192.168.123.0/24`
  **except** hosts `1–25` (reserved) and `161` (motion controller).
- Recommended: `192.168.123.222`. This repo's sessions have been using
  `192.168.123.67` which also works.
- Netmask `255.255.255.0`. No gateway, no DNS needed.
- Disable Wi-Fi while debugging, or at least confirm traffic is leaving
  the Ethernet interface (`route -n get 192.168.123.18` should show
  `interface: en5` or whichever your USB-Ethernet shows as).

## What lives where on the internal network

| IP | Device | Accessible? |
|---|---|---|
| `192.168.123.18` | Jetson Orin (user compute) | Yes, SSH `unitree@...` pw `123` |
| `192.168.123.161` | Low-level motion controller (MCU) | Ping only — no user services |
| `192.168.123.1–25` | Reserved by manual | Don't use for your laptop |
