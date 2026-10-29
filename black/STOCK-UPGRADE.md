# SK-G7220 Black: installing from stock (web GUI / SSH), not U-Boot

Goal: flash AlphaWRT without the serial console, using stock's own upgrade
path. This is feasible. The findings below come from the stock dump
(`backup/dump-20261028-1959`, `backup/black-dump`), not yet from a live test.

## Stock is OpenWrt

Stock firmware (Linux 5.4.55, V1.0.0.6, model `THN21`) is itself OpenWrt-based:
LuCI, `/sbin/sysupgrade`, `/lib/upgrade/platform.sh`, `default_do_upgrade`.
So an AlphaWRT image that passes stock's `platform_check_image` can be flashed
through the stock GUI or `sysupgrade` over SSH, no U-Boot needed.

## What stock checks (`lib/upgrade/platform.sh`)

`platform_check_image` on the uploaded file:
1. **Model string.** `uci -c /etc/skBoard/ get skboard.skboard.model` = `THN21`,
   compared as hex ASCII against bytes read from the image at a fixed offset
   (`dd bs=16 skip=458747`, path 1; `skip=688123`, path 2 — offsets into the
   *upload file*, not the flash bank).
2. **FIT magic** `d00dfeed` present.
3. `/userfs/bin/blapi_cmd system image_check "$1"` — the real gate.

Path 2 also treats the first 0x80000 bytes as a `tcboot` (bootloader) and
writes it to the `bootloader` partition; path 1 does not. We use **path 1**
(no bootloader rewrite — safer).

### `blapi_cmd system image_check` = header + CRC32, not a signature

In `lib/libblapi_system.so`: `do_blapi_system_image_check` →
`blapi_system_checkimageCrc` / `blapi_system_calculate_crc32`. Error strings:
"Bad trx header", "crc32 check fail, checksum error", "image checksum is ok".
It is a TRX/HDR-header + CRC32 check.

A separate signature path (`blapi_system_secure_trx`,
`do_blapi_system_check_secure_tclinux`, FIP header) runs **only if secure boot
is enabled**, read as an efuse via `/dev/secure_upgrade` ioctl `SECURE_IOC_GET`
(`secureupgrade.ko` → `tc3162/secure_boot_check_key`).

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

## Not yet verified on hardware (do before trusting it)

1. **Root mounts from flash.** Stock splits `tclinux` into kernel+rootfs with a
   vendor "fit-fw" MTD parser and roots on the rootfs sub-partition; our build
   must do the same via `fitblk` (included). If root doesn't mount, fix the
   fitblk/cmdline/partition wiring and rebuild — this is the main open risk.
2. **Stock writes the inactive bank.** `get_current_partition` should write the
   spare bank and flip the boot flag, leaving stock as fallback. Confirm on the
   first flash.

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
