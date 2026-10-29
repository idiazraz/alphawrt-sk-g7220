#!/usr/bin/env python3
"""Offline check of an SK-G7220 Black tclinux image, the way stock reads it.

Checks the HDRs header (magic, CRC-32/JAMCRC, model) that blapi_cmd image_check
verifies, and the FIT the way stock U-Boot "flash imgread" walks it (fdt@1 in
the first 0x800 bytes, kernel@1/fdt@1/filesystem@1 by name, sha1 hashes).

Usage: check_tclinux.py IMAGE
Exits non-zero on the first failed check.
"""
import hashlib, struct, sys, zlib

d = open(sys.argv[1], "rb").read()
ok = lambda c, m: print(("  ok  " if c else "  FAIL") + " " + m) or c or sys.exit(1)

h = d[0x2000:0x2100]
magic = h[:4]
hlen, total, crc = struct.unpack_from("<III", h, 4)
ksz, rsz = struct.unpack_from("<II", h, 0x50)
model = h[0x5c:0x7c].split(b"\0")[0].strip()
print(f"HDRs: hdrlen={hlen:#x} total={total:#x} crc={crc:#010x} kernel={ksz:#x} rootfs={rsz:#x} model={model!r}")
ok(magic == b"HDRs", "magic HDRs")
ok(hlen == 0x100, "header length 0x100")
ok(model == b"THN21", "model THN21")
ok(0x2000 + total <= len(d), "total within file")
fit = d[0x2100:0x2000 + total]
ok((zlib.crc32(fit) ^ 0xFFFFFFFF) == crc, "CRC-32/JAMCRC of the FIT matches header")

ok(fit[:4] == b"\xd0\x0d\xfe\xed", "FIT magic at 0x2100")
ostruct, ostr = struct.unpack(">II", fit[8:16])
name = lambda o: fit[ostr + o:fit.index(b"\0", ostr + o)].decode()
p, path, props = ostruct, [], {}
while True:
    tok = struct.unpack(">I", fit[p:p + 4])[0]; p += 4
    if tok == 1:
        e = fit.index(b"\0", p); path.append(fit[p:e].decode()); p = (e + 4) & ~3
    elif tok == 2:
        path.pop()
    elif tok == 3:
        ln, no = struct.unpack(">II", fit[p:p + 8]); p += 8
        props["/".join(path[1:]) + ":" + name(no)] = fit[p:p + ln]; p = (p + ln + 3) & ~3
    elif tok == 9:
        break
for n in ("fdt@1", "kernel@1", "filesystem@1"):
    ok(f"images/{n}:data" in props, f"node /images/{n} with data")
i = fit.find(b"fdt@1\0", ostruct)
ok(0 <= i < 0x800, f"fdt@1 within the first 0x800 bytes U-Boot reads (at {i:#x})")
for n in ("fdt@1", "kernel@1", "filesystem@1"):
    want = props.get(f"images/{n}/hash@1:value")
    algo = (props.get(f"images/{n}/hash@1:algo") or b"").rstrip(b"\0")
    data = props[f"images/{n}:data"]
    ok(algo == b"sha1" and hashlib.sha1(data).digest() == want, f"{n} sha1 hash matches")
load = struct.unpack(">I", props["images/kernel@1:load"])[0]
ok(load == 0x80200000, f"kernel load 0x80200000 (got {load:#x})")
ok(props["images/filesystem@1:data"][:4] == b"hsqs", "filesystem@1 is squashfs")
print("all checks passed")
