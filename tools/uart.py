#!/usr/bin/env python3
"""Own the SK-G7220 UART: log every byte, stop U-Boot autoboot, take input from a FIFO.

  python3 -I uart.py [--port /dev/cu.usbserial-1120] [--log FILE] [--fifo FILE] [--no-stop]

Send a line:  printf 'printenv\\r' > FIFO      (bytes go out verbatim)
The log is private: it holds MACs, serials and the verity hash.
"""
import os, select, sys, termios, time

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

here = os.path.dirname(os.path.abspath(__file__))
PORT = opt("--port", "/dev/cu.usbserial-1120")
LOG = opt("--log", os.path.join(here, "..", "backup", "uart-%s.log" % time.strftime("%Y%m%d-%H%M%S")))
FIFO = opt("--fifo", os.path.join(here, "uart.in"))
STOP = "--no-stop" not in sys.argv

fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = a[1] = a[3] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)

if not os.path.exists(FIFO):
    os.mkfifo(FIFO)
fin = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)  # RDWR: never sees EOF
log = open(LOG, "ab", buffering=0)
print("port %s  log %s  fifo %s" % (PORT, os.path.abspath(LOG), FIFO), flush=True)

tail = b""
while True:
    r, _, _ = select.select([fd, fin], [], [])
    if fd in r:
        try:
            data = os.read(fd, 4096)
        except BlockingIOError:  # select woke us with nothing to read
            data = b""
        log.write(data)
        tail = (tail + data)[-200:]
        # Note: one key per prompt; U-Boot only needs one to stop.
        if STOP and b"Hit any key to stop autoboot" in tail:
            os.write(fd, b"\r")
            log.write(b"\n[uart.py: sent key to stop autoboot]\n")
            tail = b""
    if fin in r:
        try:
            cmd = os.read(fin, 4096)
        except BlockingIOError:
            cmd = b""
        if cmd:
            os.write(fd, cmd)
