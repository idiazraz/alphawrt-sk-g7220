#!/bin/sh
# Assemble the SK-G7220 Black flashable image (stock tclinux shape) from a built
# tree. Produces a file installable via the stock web GUI or `sysupgrade -F` over
# SSH from stock. Needs CONFIG_TARGET_ROOTFS_SQUASHFS=y and CONFIG_PACKAGE_fitblk=y.
# Usage: black/mk_flash_image.sh [tree] [out.bin]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
TREE=${1:-$HERE/../openwrt}
OUT=${2:-$HERE/../backup/flash/sk-g7220-black-tclinux-factory.bin}
KD="$TREE/build_dir/target-aarch64_cortex-a53_musl/linux-airoha_an7581"
S="$TREE/staging_dir/host/bin"
VER="AlphaWRT-$(cat "$TREE/version.buildinfo" 2>/dev/null || echo snapshot)"
[ -f "$HERE/stock-fmt/prefix-2000.bin" ] || { echo "Missing stock-fmt/prefix-2000.bin: the first 0x2000 bytes of a stock Black image. It is vendor data, so it is not in git." >&2; exit 1; }
tmp=$(mktemp -d)
"$S/lzma" e "$KD/Image" -lc1 -lp2 -pb2 "$tmp/Image.lzma"   # OpenWrt's kernel lzma options
python3 -I "$HERE/mk_tclinux.py" \
	--kernel "$tmp/Image.lzma" \
	--dtb "$KD/image-en7581-skyworth-sk-g7220.dtb" \
	--rootfs "$KD/root.squashfs" \
	--prefix "$HERE/stock-fmt/prefix-2000.bin" \
	--version "$VER" --out "$OUT" --mkimage "$S/mkimage"
rm -rf "$tmp"
python3 -I "$HERE/check_tclinux.py" "$OUT"
