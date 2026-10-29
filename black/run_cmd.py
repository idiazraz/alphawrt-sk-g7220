#!/usr/bin/env python3
import os, sys, time, uuid

SERIAL_PORT = "/dev/cu.usbserial-1120"
LOG_FILE = "sk-g7220-uboot.txt"

def exec_cmd(cmd_str, timeout=12):
    tag = str(uuid.uuid4())[:8]
    start_tag = f"B_{tag}"
    end_tag = f"E_{tag}"
    
    start_pos = os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0
    
    # We send command writing to /tmp/_o, then echo markers around cat
    # Separate echo start_tag on newline
    script = f"({cmd_str}) > /tmp/_o 2>&1; echo; echo {start_tag}; cat /tmp/_o; echo; echo {end_tag}; rm -f /tmp/_o\n"
    
    fd = os.open(SERIAL_PORT, os.O_RDWR | os.O_NONBLOCK)
    os.write(fd, b"\r\n")
    time.sleep(0.05)
    os.write(fd, script.encode("utf-8"))
    os.close(fd)
    
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.2)
        if not os.path.exists(LOG_FILE):
            continue
        cur_size = os.path.getsize(LOG_FILE)
        if cur_size <= start_pos:
            continue
        with open(LOG_FILE, "rb") as f:
            f.seek(start_pos)
            chunk = f.read().decode("utf-8", errors="replace")
            # We look for \nstart_tag\n and \nend_tag\n
            if f"\n{end_tag}" in chunk or f"\r\n{end_tag}" in chunk:
                # Find the line that has only start_tag
                lines = chunk.replace("\r", "").split("\n")
                s_line = None
                e_line = None
                for idx, line in enumerate(lines):
                    if line.strip() == start_tag:
                        s_line = idx
                    elif line.strip() == end_tag and s_line is not None:
                        e_line = idx
                        break
                if s_line is not None and e_line is not None:
                    return "\n".join(lines[s_line + 1 : e_line]).strip()
    return "TIMEOUT waiting for command output"

if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "uname -a"
    print(exec_cmd(cmd))
