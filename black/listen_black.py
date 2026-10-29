#!/usr/bin/env python3
"""SK-G7220 Black runner & interactive console for ECNT> prompt.
Logs all output to backup/sk-g7220/black-uart.log.
Listens for commands from backup/sk-g7220/cmd.in.
"""
import os, sys, select, termios, time

PORT = "/dev/cu.usbserial-1120"
LOG_PATH = "backup/sk-g7220/black-uart.log"
CMD_FILE = "backup/sk-g7220/cmd.in"

def open_port():
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    try:
        while True:
            d = os.read(fd, 16384)
            if not d: break
    except (BlockingIOError, OSError):
        pass
    return fd

fd = open_port()
log_f = open(LOG_PATH, "ab", buffering=0)

def log_print(text):
    if isinstance(text, str):
        b = text.encode("utf-8", errors="replace")
    else:
        b = text
    log_f.write(b)
    sys.stdout.buffer.write(b)
    sys.stdout.flush()

log_print(f"\n[listen_black] Connected to {PORT}. Streaming mode active...\n")

# Interactive loop: forwards any commands from CMD_FILE directly to serial
while True:
    if os.path.exists(CMD_FILE):
        try:
            with open(CMD_FILE, "rb") as cf:
                cmds = cf.read()
            os.remove(CMD_FILE)
            if cmds:
                log_print(f"\n[cmd] {cmds.decode('utf-8', errors='replace').strip()}\n")
                os.write(fd, cmds)
                if not cmds.endswith(b"\r") and not cmds.endswith(b"\n"):
                    os.write(fd, b"\r")
        except Exception as e:
            log_print(f"\n[error] {e}\n")

    r, _, _ = select.select([fd], [], [], 0.05)
    if fd in r:
        try:
            chunk = os.read(fd, 4096)
            if chunk:
                log_print(chunk)
        except (BlockingIOError, OSError):
            pass
