#!/bin/sh
# Build the SK-G7220 Black initramfs (RAM boot) image with LuCI and the AlphaWRT UI.
# Usage: black/build.sh [tree]   (default tree: /path/to/openwrt-sk-g7220)
# Needs the GNU tools from AlphaWRT's env.sh on PATH on macOS.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ALPHAWRT_PKGS=${ALPHAWRT_PKGS:-$HERE/../../alphawrt/package}
TREE=${1:-/path/to/openwrt-sk-g7220}
REV=795f369b18   # snapshot r37896, the kernel that first booted on black

if [ ! -d "$TREE/.git" ]; then
	git clone --filter=blob:none https://github.com/openwrt/openwrt.git "$TREE"
	git -C "$TREE" checkout -b sk-g7220 "$REV"
	git -C "$TREE" apply "$HERE/openwrt-an7581.patch"
fi
cp "$HERE/en7581-skyworth-sk-g7220.dts" "$TREE/target/linux/airoha/dts/"
mkdir -p "$TREE/target/linux/airoha/patches-6.18"
if [ -d "$HERE/patches" ]; then
	cp "$HERE/patches/"*.patch "$TREE/target/linux/airoha/patches-6.18/"
fi
mkdir -p "$TREE/target/linux/airoha/base-files/lib/preinit"
cp "$HERE/79_wipe_foreign_overlay" "$TREE/target/linux/airoha/base-files/lib/preinit/"
mkdir -p "$TREE/target/linux/airoha/an7581/base-files/etc/board.d"
cp "$HERE/02_network" "$TREE/target/linux/airoha/an7581/base-files/etc/board.d/"

# AlphaWRT UI packages
mkdir -p "$TREE/package/alphawrt"
for p in alphawrt-ui luci-app-alphawrt luci-theme-alphawrt; do
	rm -rf "$TREE/package/alphawrt/$p"
	cp -R "$ALPHAWRT_PKGS/$p" "$TREE/package/alphawrt/"
done

cd "$TREE"
grep -E '^src-git (packages|luci) ' feeds.conf.default > feeds.conf
./scripts/feeds update -a
./scripts/feeds install -a
cp "$HERE/config.seed" .config
if [ "$(uname)" = Darwin ]; then
	B=$(brew --prefix)
	cat >> .config <<EOC
CONFIG_BPF_TOOLCHAIN_HOST=y
CONFIG_BPF_TOOLCHAIN_HOST_PATH="$B/opt/llvm"
CONFIG_GOLANG_EXTERNAL_BOOTSTRAP_ROOT="$B/opt/go/libexec"
# CONFIG_GOLANG_BUILD_BOOTSTRAP is not set
EOC
fi
make defconfig
make -j"$(getconf _NPROCESSORS_ONLN)"
ls bin/targets/airoha/an7581/*sk-g7220*initramfs*
