#!/usr/bin/env python3
"""Run a command on the SK-G7220 OpenWrt serial console and return output cleanly."""
import os, sys, select, termios, time

PORT = "/dev/cu.usbserial-1120"

if len(sys.argv) < 2:
    print("Usage: python3 serial_cmd.py <command>")
    sys.exit(1)

cmd = sys.argv[1].strip()

fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = a[1] = a[3] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)

# Flush any existing buffer
try:
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            break
except Exception:
    pass

def send_and_wait(line, wait_sec=0.5):
    os.write(fd, line.encode() + b"\n")
    time.sleep(wait_sec)
    buf = b""
    while True:
        r, _, _ = select.select([fd], [], [], 0.2)
        if fd in r:
            try:
                c = os.read(fd, 4096)
                if c:
                    buf += c
                else:
                    break
            except Exception:
                break
        else:
            break
    return buf.decode("utf-8", errors="replace")

# Send command redirected to /tmp/out
send_and_wait(f"{cmd} > /tmp/cmd.out 2>&1", wait_sec=0.5)

# Now read /tmp/out
out = send_and_wait("cat /tmp/cmd.out", wait_sec=0.5)

os.close(fd)

# Clean up cat command echo
lines = out.replace("\r", "").split("\n")
filtered = []
recording = False
for line in lines:
    if "cat /tmp/cmd.out" in line:
        recording = True
        continue
    if recording:
        if "root@OpenWrt" in line:
            break
        filtered.append(line)

if filtered:
    print("\n".join(filtered).strip())
else:
    print(out.strip())
