# SK-G7220 Black: installing from stock (web GUI / SSH), not U-Boot

Goal: flash AlphaWRT without the serial console, using stock's own upgrade
path. Verified on hardware; see below. The findings come from the stock dump
(`backup/dump-20261028-1959`, `backup/black-dump`).

## Stock is OpenWrt

Stock firmware (Linux 5.4.55, V1.0.0.6, model `THN21`) is itself OpenWrt-based:
LuCI, `/sbin/sysupgrade`, `/lib/upgrade/platform.sh`, `default_do_upgrade`.
So an AlphaWRT image that passes stock's `platform_check_image` can be flashed
through the stock GUI or `sysupgrade` over SSH, no U-Boot needed.

## What stock checks (`lib/upgrade/platform.sh` & `skgupgrade.js`)

Stock GUI (`/www/luci-static/resources/view/skTmCombo/skgupgrade.js`) executes:
1. `ubus call system validate_firmware_image '{"path":"/tmp/firmware.bin"}'`
   - Requires `result[1].valid == true` and `result[1].tests.fwtool_signature == true`.
   - Calls `/usr/libexec/validate_firmware_image`, which runs `platform_check_image`.
2. `ubus call file exec '{"command":"/sbin/sysupgrade","params":["--test","/tmp/firmware.bin"]}'`
   - Requires exit code 0.
3. `ubus call file exec '{"command":"/sbin/sysupgrade","params":["-u","/tmp/firmware.bin"]}'`
   - Flashes the inactive bank (`tclinux_slave` when booted on bank 0).

Inside `platform_check_image`:
1. **FIP TOC check (`/userfs/bin/blapi_cmd system check_secure_tclinux 0 "$1"`):**
   Stock kernel exposes `/proc/tc3162/secure_boot_check_key` (even when empty).
   Because the file exists, `platform_check_image` unconditionally calls
   `check_secure_tclinux 0`. This opens `/dev/secure_upgrade` (`secureupgrade.ko`)
   and verifies the FIP (Firmware Image Package) table at offset 0x0.
   The entry for BL33 (UUID `d6d0eea7-fcea-d54b-9782-9934f234b6e4`) offset must be
   `0x2000`, and its **size field must match the exact payload length** (`0x100 + len(FIT)`).
   If size does not match, the kernel driver hits EOF when hashing and fails with -1.
2. **Fixed Chip ID check at offset 8785:**
   Stock runs `get_magic_long_offset "$NEW_FILE" "8785"` and checks `case "$GET_CHIPID" in 31383537 | 37353831` (ASCII `'7581'`).
   8785 is 0x2100 + 337 (0x151) into the FIT. By setting the root node `model` in the DTB
   to `"Skyworth SK-G7220 :  7581"`, the ASCII substring `'7581'` falls precisely at offset 8785.
3. **Magic check at offset `$FIP_HEADER` (8192):**
   Reads 4 bytes at offset 0x2000 and requires `HDRs` (`73524448 | 48445273`).
4. **Bootloader write skip:**
   Since offset 532480 (0x82000) does not contain `HDRs`, stock skips the `bootloader`
   (tcboot) partition rewrite and proceeds with tclinux upgrade only.

**Secure boot is off on this unit (confirmed).** On every boot the board's
BL2 (ARM Trusted Firmware v2.10.0) prints `NOTICE: SECURE_INVAILD` (sic) and
`Secure key does not exist`, and U-Boot then prints `Verifying Hash Integrity
... sha1+ OK` — a hash check, not a signature. A provisioned secure-boot efuse
would make BL2 enforce signatures and reject the `rsa4096:dev` dev-key image;
instead it boots. So `image_check` reduces to the CRC32/header check.
(`secureupgrade.ko` also logs `eFuse value = 0x9` at init; the BL2 root-of-trust
verdict above is the authority.) Evidence: `backup/uart-session.log`,
`backup/black-uart.log`.

## The vendor header (reuse GN630V tooling)

The bank starts with a 0x2000 vendor table, then at 0x2000 a 0x100-byte header,
then the FIT at 0x2100. The upgrade *file* is header(0x100) + FIT, same shape as
the GN630V factory image.

Black header @0x2000 (`HDRs`):

| off | field | value in dump |
|---|---|---|
| 0x00 | magic | `HDRs` |
| 0x04 | format | 1 |
| 0x08 | size (LE) | FIT total + 0x100 |
| 0x0c | CRC32 | stored |
| 0x10 | version | `V1.0.0.6\n` |
| 0x28 | version | `V1.0.0.6\n` |
| 0x5c | model | `THN21\n` |

This is the EcoNet/Airoha header family. The GN630V (EN7523) factory image is
the `HDR2` variant of the same 0x100-byte layout (magic, format, size, CRC32,
model at 0x5c), and `tools/check_tclinux.py` in the GN630V workspace already
decodes and verifies it. Building a black GUI image = adapt that factory tooling
to emit `HDRs`, model `THN21`, over the black an7581 FIT.

## Dual-bank safety

`get_current_partition` writes the **inactive** bank and flips the boot flag to
it, keeping the other bank as fallback. So a GUI/SSH upgrade from stock leaves
stock in the spare bank. To use the stock GUI the board must be booted from
flash (stock) — our image is in RAM now, so this route starts with a reboot to
stock.

## Open, before a flash

- Exact model-string offset in the *upload file* (need a stock upgrade `.bin`,
  or derive from the two `dd` offsets once the file layout is fixed).
- Confirm the CRC32 range/seed against `check_tclinux.py` (stored CRC in the
  dump didn't match a plain crc32 of the FIT body — range/seed differ).
- FIT image node names: U-Boot/stock look up `kernel@1`/`fdt@1`/`filesystem@1`
  by name (OpenWrt emits `kernel-1`/`fdt-1`) — the GN630V install solved this
  same problem; reuse that.

## Build (done) — the flashable image

`black/mk_tclinux.py` + `black/mk_flash_image.sh` assemble a file byte-shaped
like the genuine stock upgrade (`SK-G7220_V1.0.0.8`): the stock 0x2000 prefix
verbatim, an `HDRs` header (model `THN21`, our version, CRC-32/JAMCRC of the
FIT), then a FIT with `fdt@1` (first), `kernel@1` (lzma, load 0x80200000) and
`filesystem@1` (our squashfs). `black/check_tclinux.py` verifies it offline.

Needs `CONFIG_TARGET_ROOTFS_SQUASHFS=y` and `CONFIG_PACKAGE_fitblk=y`. Run:

    black/mk_flash_image.sh          # -> backup/flash/sk-g7220-black-tclinux-factory.bin

`black/check_tclinux.py` passes on the result: prefix identical to stock, HDRs
magic/model match, CRC matches, FIT nodes present, `fdt@1` within the first
0x800 bytes, sha1 hashes valid, kernel load 0x80200000, `filesystem@1` squashfs.

## Verified on hardware (2026-11-01)

The stock web GUI installed the clean build from Bank 0: it wrote `tclinux_slave`,
set the boot flag to 1 and rebooted. U-Boot booted the second image, root mounted
and `mount_root` switched to the UBI overlay, with the existing settings kept.
This was one run on one board, with a stock overlay restored from backup.

Stock's LAN is 192.168.0.1. If that's also your home router's address, connect
only to the board, or the browser reaches the router instead.

A damaged `rootfs_data` leaves stock with no LAN, web page or login. Our early
overlay tests caused that once; `backup/black-dump/mtd7.bin` restored it.

## How to flash (supervised, serial recovery ready)

Board must be booted from flash (stock) for either route. Flash writes the
**inactive** bank, so stock stays in the other bank.

- **SSH (robust):** `scp` the image to stock, then `sysupgrade -n -F <image>`.
  `-F` skips stock's model/magic/CRC checks, so it works even if a header
  detail is off.
- **Stock web GUI:** upload the image on the firmware-upgrade page (the page
  wants a name containing `tclinux`). Stock checks model `THN21`, the FIT magic
  and the CRC — all matched by this image.

If the new bank fails to boot, U-Boot should fall back to the stock bank; worst
case, recover over serial (RAM-boot an initramfs).
