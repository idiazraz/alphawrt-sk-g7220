#!/usr/bin/env python3
"""SK-G7220 Black runner & interactive console for ECNT> prompt.
Logs all output to backup/sk-g7220/black-uart.log.
Listens for commands from backup/sk-g7220/cmd.in.

Auto-login flow after power-cycle:
  1. Intercept "Hit any key to stop autoboot" with Enter.
  2. Wait for "UserName:" -> send "telecomadmin".
  3. Wait for "Password:" -> send $UBOOT_PWD (never logged).
  4. Wait for "ECNT>" -> announce ready.

Note: the password is read from $UBOOT_PWD at startup.
It is never written to the log or to stdout.
"""
import os, sys, select, termios, time

PORT = "/dev/cu.usbserial-1120"
if os.path.isdir("backup/sk-g7220"):
    LOG_PATH = "backup/sk-g7220/black-uart.log"
    CMD_FILE = "backup/sk-g7220/cmd.in"
else:
    os.makedirs("backup", exist_ok=True)
    LOG_PATH = "backup/black-uart.log"
    CMD_FILE = "backup/cmd.in"

UBOOT_PWD = os.environ.get("UBOOT_PWD", "")

def open_port():
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    # Drain stale data
    try:
        while True:
            d = os.read(fd, 16384)
            if not d:
                break
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
if not UBOOT_PWD:
    log_print("[listen_black] WARNING: UBOOT_PWD not set — auto-login disabled.\n")

tail = b""
# Login state machine: idle -> wait_user -> wait_pass -> wait_prompt -> ready
login_state = "idle"
login_attempts = 0

while True:
    # --- cmd.in injection ---
    if os.path.exists(CMD_FILE):
        try:
            with open(CMD_FILE, "rb") as cf:
                cmds = cf.read()
            os.remove(CMD_FILE)
            if cmds:
                log_print(f"\n[cmd] {cmds.decode('utf-8', errors='replace').strip()}\n")
                for line in cmds.splitlines():
                    line = line.strip()
                    if line:
                        os.write(fd, line + b"\r")
                        time.sleep(0.5)
        except Exception as e:
            log_print(f"\n[error] {e}\n")

    # --- serial read ---
    r, _, _ = select.select([fd], [], [], 0.05)
    if fd in r:
        try:
            chunk = os.read(fd, 4096)
            if chunk:
                log_print(chunk)
                tail = (tail + chunk)[-600:]

                # 1. Autoboot intercept
                if b"Hit any key to stop autoboot" in tail:
                    os.write(fd, b"\r")
                    log_print("\n[listen_black] Intercepted autoboot -> sending Enter\n")
                    login_state = "wait_user"
                    login_attempts = 0
                    tail = b""

                # 2. UserName prompt
                elif login_state in ("wait_user", "wait_prompt") and b"UserName:" in tail:
                    if UBOOT_PWD:
                        time.sleep(0.3)
                        os.write(fd, b"telecomadmin\r")
                        log_print("\n[listen_black] Sent username\n")
                        login_state = "wait_pass"
                        login_attempts += 1
                    tail = b""

                # 3. Password prompt
                elif login_state == "wait_pass" and b"Password:" in tail:
                    time.sleep(0.3)
                    os.write(fd, UBOOT_PWD.encode() + b"\r")
                    log_print("\n[listen_black] Sent password\n")
                    login_state = "wait_prompt"
                    tail = b""

                # 4. ECNT> prompt — login succeeded
                elif login_state == "wait_prompt" and b"ECNT>" in tail:
                    log_print("\n[listen_black] === ECNT> prompt ready ===\n")
                    login_state = "ready"
                    tail = b""

                # 5. Already ready — keep detecting ECNT> for cmd.in feedback
                elif login_state == "ready" and b"ECNT>" in tail:
                    # Just clear tail so it doesn't re-trigger
                    tail = b""

        except (BlockingIOError, OSError):
            pass
