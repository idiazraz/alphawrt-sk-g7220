#!/usr/bin/env python3
"""Assemble a flashable SK-G7220 Black tclinux image, byte-shaped like stock.

Stock layout (verified against SK-G7220_V1.0.0.8_20260416.bin):
  0x0000  0x2000-byte vendor table + dev cert (fixed boilerplate, copied verbatim;
          ignored because secure boot is off on this unit)
  0x2000  HDRs header, 0x100 bytes (see below)
  0x2100  FIT: fdt@1 (first), kernel@1 (lzma, load 0x80200000), filesystem@1
          (our squashfs, embedded), conf@1. Stock U-Boot "flash imgread" reads
          the first 0x800 bytes and looks up fdt@1/kernel@1 by name.

HDRs header (little-endian), the part blapi_cmd image_check verifies:
  0x00 "HDRs"              0x50 u32 kernel size
  0x04 u32 hdrlen=0x100    0x54 u32 rootfs size
  0x08 u32 total=0x100+FIT 0x58 u32 romfile=0
  0x0c u32 CRC-32/JAMCRC of the FIT   0x5c model[32] "THN21\n"
  0x10 version[32]         0x7c u32 loadaddr field = 0
  0x30 customer ver[32]    0x80 reserved[128] = 0

CRC and model are what stock checks; we match them exactly. Load address in the
FIT is 0x80200000 (2 MiB-aligned, what our arm64 kernel RAM-boots at), not
stock's 0x80088000 which a modern arm64 kernel will not accept.

Usage:
  mk_tclinux.py --kernel k.lzma --dtb board.dtb --rootfs root.squashfs \
    --prefix stock-fmt/prefix-2000.bin --version "<v>" --out out.bin [--mkimage PATH]
"""
import argparse, os, struct, subprocess, sys, tempfile, zlib

LOAD = 0x80200000
MODEL = "THN21"

ITS = """/dts-v1/;
/ {{
    description = "AlphaWRT SK-G7220 Black";
    #address-cells = <1>;
    images {{
        fdt@1 {{
            description = "device tree";
            data = /incbin/("{dtb}");
            type = "flat_dt";
            arch = "arm64";
            compression = "none";
            hash@1 {{ algo = "sha1"; }};
        }};
        kernel@1 {{
            description = "kernel";
            data = /incbin/("{kernel}");
            type = "kernel";
            arch = "arm64";
            os = "linux";
            compression = "lzma";
            load = <{load:#x}>;
            entry = <{load:#x}>;
            hash@1 {{ algo = "sha1"; }};
        }};
        filesystem@1 {{
            description = "rootfs";
            data = /incbin/("{rootfs}");
            type = "filesystem";
            arch = "arm64";
            os = "linux";
            compression = "none";
            hash@1 {{ algo = "sha1"; }};
        }};
    }};
    configurations {{
        default = "conf@1";
        conf@1 {{
            description = "AlphaWRT";
            kernel = "kernel@1";
            fdt = "fdt@1";
        }};
    }};
}};
"""


def field(s, n):
    b = (s + "\n").encode()
    if len(b) >= n:
        sys.exit(f"string too long for {n}-byte field: {s!r}")
    return b + b"\0" * (n - len(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--dtb", required=True)
    ap.add_argument("--rootfs", required=True)
    ap.add_argument("--prefix", required=True, help="stock 0x2000 leading block")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mkimage", default="mkimage")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as t:
        its = os.path.join(t, "image.its")
        fit = os.path.join(t, "image.fit")
        open(its, "w").write(ITS.format(dtb=a.dtb, kernel=a.kernel, rootfs=a.rootfs, load=LOAD))
        subprocess.run([a.mkimage, "-f", its, fit], check=True, stdout=subprocess.DEVNULL)
        fitb = open(fit, "rb").read()

    # fdt@1 must sit in the first 0x800 bytes stock U-Boot reads
    i = fitb.find(b"fdt@1\0", struct.unpack(">I", fitb[8:12])[0])
    if not 0 <= i < 0x800:
        sys.exit(f"fdt@1 not in first 0x800 bytes (at {i:#x})")

    prefix = open(a.prefix, "rb").read()
    if len(prefix) != 0x2000:
        sys.exit(f"prefix must be 0x2000 bytes, got {len(prefix):#x}")

    ksz = len(open(a.kernel, "rb").read())
    rsz = len(open(a.rootfs, "rb").read())
    total = 0x100 + len(fitb)
    crc = zlib.crc32(fitb) ^ 0xFFFFFFFF  # CRC-32/JAMCRC, over the FIT

    h = bytearray(0x100)
    h[0:4] = b"HDRs"
    struct.pack_into("<III", h, 4, 0x100, total, crc)
    h[0x10:0x30] = field(a.version, 0x20)
    h[0x30:0x50] = field(a.version, 0x20)
    struct.pack_into("<III", h, 0x50, ksz, rsz, 0)
    h[0x5c:0x7c] = field(MODEL, 0x20)
    struct.pack_into("<I", h, 0x7c, 0)

    out = prefix + bytes(h) + fitb
    open(a.out, "wb").write(out)
    print(f"{a.out}: {len(out)} bytes  FIT={len(fitb)}  kernel={ksz}  rootfs={rsz}  crc={crc:#010x}")


if __name__ == "__main__":
    main()
