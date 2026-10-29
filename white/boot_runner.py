#!/usr/bin/env python3
"""SK-G7220 automated RAM-boot runner.
Resilient event-driven runner that catches U-Boot, authenticates,
and boots OpenWrt + custom PCIe Gen3 DTB into RAM.
Keeps connection open with command file interface for interactive shell.
"""
import os, sys, select, termios, time

PORT = "/dev/cu.usbserial-1120"
LOG_PATH = "backup/sk-g7220/uart-session.log"
CMD_FILE = "backup/sk-g7220/cmd.in"

if len(sys.argv) > 1 and sys.argv[1] != "--reboot":
    PASSWORD = sys.argv[1].encode()
elif "UBOOT_PWD" in os.environ:
    PASSWORD = os.environ["UBOOT_PWD"].encode()
else:
    print("Usage: python3 boot_runner.py <uboot_password> (or set UBOOT_PWD env)")
    sys.exit(1)

def get_port():
    while True:
        try:
            fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            a = termios.tcgetattr(fd)
            a[0] = a[1] = a[3] = 0
            a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            a[4] = a[5] = termios.B115200
            termios.tcsetattr(fd, termios.TCSANOW, a)
            # flush
            try:
                while True:
                    d = os.read(fd, 16384)
                    if not d: break
            except BlockingIOError:
                pass
            return fd
        except Exception:
            time.sleep(0.2)

fd = get_port()
log_f = open(LOG_PATH, "a")

def log_print(text):
    safe = text if isinstance(text, str) else text.decode("utf-8", errors="replace")
    log_f.write(safe)
    log_f.flush()
    sys.stdout.write(safe)
    sys.stdout.flush()

log_print("\n[runner] Armed and listening for U-Boot (Hit any key / UserName / U-Boot>)...\n")

tail = b""
state = "STOPPING_AUTOBOOT"
last_spam = 0.0
last_poke = 0.0

def send_cmd(cmd_str, expect_str=b"U-Boot>", timeout=60.0):
    try:
        while True:
            d = os.read(fd, 16384)
            if not d: break
            log_print(d)
    except BlockingIOError:
        pass
    except Exception:
        pass
    log_print(f"\n[runner] Executing: {cmd_str}\n")
    os.write(fd, cmd_str.encode() + b"\r")
    c_buf = b""
    c_start = time.time()
    while time.time() - c_start < timeout:
        r, _, _ = select.select([fd], [], [], 0.3)
        if fd in r:
            try:
                c = os.read(fd, 4096)
            except BlockingIOError:
                c = b""
            except OSError:
                c = b""
            if c:
                log_print(c)
                c_buf += c
                if expect_str in c_buf:
                    return True
    log_print(f"\n[runner] WARNING: Timeout waiting for {expect_str} after '{cmd_str}'\n")
    return False

while True:
    now = time.time()

    # Active Enter spamming while stopping autoboot
    if state == "STOPPING_AUTOBOOT" and (now - last_spam > 0.06):
        os.write(fd, b"\r")
        last_spam = now

    # Periodic Enter poke while waiting for prompt
    if state == "WAIT_UBOOT" and (now - last_poke > 0.5):
        os.write(fd, b"\r")
        last_poke = now

    try:
        r, _, _ = select.select([fd], [], [], 0.05)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        fd = get_port()
        continue

    if fd in r:
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            chunk = b""
        except OSError:
            try:
                os.close(fd)
            except Exception:
                pass
            fd = get_port()
            chunk = b""

        if chunk:
            log_print(chunk)
            tail = (tail + chunk)[-500:]

            # If board reboots, reset state to STOPPING_AUTOBOOT
            if b"NOTICE:  BL2:" in tail or b"U-Boot TPL" in tail or b"DRAM FLOW DONE" in tail:
                if state != "STOPPING_AUTOBOOT":
                    log_print("\n[runner] Board reboot detected, resetting state to STOPPING_AUTOBOOT.\n")
                    state = "STOPPING_AUTOBOOT"
                    tail = tail[-100:]

            if state == "STOPPING_AUTOBOOT":
                if b"UserName:" in tail:
                    log_print("\n[runner] At UserName prompt. Sending telecomadmin...\n")
                    time.sleep(0.15)
                    os.write(fd, b"telecomadmin\r")
                    tail = b""
                    state = "WAIT_PASSWORD"
                elif b"U-Boot>" in tail:
                    log_print("\n[runner] At U-Boot prompt directly!\n")
                    tail = b""
                    state = "AT_UBOOT"

            elif state == "WAIT_PASSWORD":
                if b"Password:" in tail:
                    log_print("\n[runner] At Password prompt. Sending password...\n")
                    time.sleep(0.15)
                    os.write(fd, PASSWORD + b"\r")
                    tail = b""
                    state = "WAIT_UBOOT"
                    last_poke = time.time()
                elif b"UserName:" in tail:
                    time.sleep(0.15)
                    os.write(fd, b"telecomadmin\r")
                    tail = b""

            elif state == "WAIT_UBOOT":
                if b"U-Boot>" in tail:
                    log_print("\n[runner] Reached U-Boot prompt!\n")
                    tail = b""
                    state = "AT_UBOOT"
                elif b"UserName:" in tail:
                    log_print("\n[runner] Prompted UserName again, sending telecomadmin...\n")
                    time.sleep(0.15)
                    os.write(fd, b"telecomadmin\r")
                    tail = b""
                    state = "WAIT_PASSWORD"

    if state == "AT_UBOOT":
        time.sleep(0.2)
        send_cmd('setenv bootargs "console=ttyS0,115200n8 earlycon"', timeout=5.0)
        send_cmd("mw.l 0x1fa2018c 0x00000007", timeout=5.0)
        send_cmd("mw.l 0x1fa20088 0x24c00003", timeout=5.0)
        send_cmd("tftpboot 0x82000000 kernel-1.lzma", timeout=45.0)
        send_cmd("lzmadec 0x82000000 0x80200000", timeout=15.0)
        send_cmd("tftpboot 0x83000000 ramtest.dtb", timeout=15.0)

        log_print("\n[runner] Booting kernel with booti...\n")
        os.write(fd, b"booti 0x80200000 - 0x83000000\r")
        state = "BOOTING_KERNEL"
        boot_start = time.time()
        last_enter = 0.0
        prompt_handled = False
        continue

    if state == "BOOTING_KERNEL":
        # Check for user command injection via CMD_FILE
        if os.path.exists(CMD_FILE):
            try:
                with open(CMD_FILE, "r") as cf:
                    user_cmd = cf.read()
                os.remove(CMD_FILE)
                if user_cmd.strip():
                    log_print(f"\n[runner] Executing user command: {user_cmd.strip()}\n")
                    for line in user_cmd.splitlines():
                        if line.strip():
                            os.write(fd, (line.strip() + "\r\n").encode())
                            time.sleep(0.3)
            except Exception as e:
                log_print(f"\n[runner] Error handling CMD_FILE: {e}\n")

        # Periodically poke enter if waiting for console
        if time.time() - boot_start > 25.0 and time.time() - last_enter > 2.0 and not prompt_handled:
            os.write(fd, b"\r\n")
            last_enter = time.time()

        # Check prompt
        if chunk and (b"root@OpenWrt:" in chunk or b"root@OpenWrt:/#" in chunk or b"root@OpenWrt:" in tail):
            if not prompt_handled:
                prompt_handled = True
                log_print("\n[runner] OpenWrt prompt reached! Configuring networking and checking PCIe...\n")
                net_cmds = [
                    "ip link set eth0 nomaster",
                    "ip link set eth0 up",
                    "ip link set lan1 master br-lan",
                    "ip link set lan2 master br-lan",
                    "ip link set lan3 master br-lan",
                    "ip link set lan4 master br-lan",
                    "ip link set lan1 up",
                    "ip link set lan2 up",
                    "ip link set lan3 up",
                    "ip link set lan4 up",
                    "ip link set br-lan up",
                    "ip addr replace 192.168.1.1/24 dev br-lan",
                    "/etc/init.d/dropbear restart",
                    "lspci -nn -vv",
                    "dmesg | grep -i -E 'pcie|mt7996|mt76'",
                ]
                for nc in net_cmds:
                    os.write(fd, (nc + "\r\n").encode())
                    time.sleep(0.4)
