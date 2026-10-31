#!/bin/sh
# Build the SK-G7220 Black images with LuCI and the AlphaWRT UI: initramfs (RAM boot)
# and the stock-format flash image.
# Usage: black/build.sh [tree] [flash-image]   (default tree: openwrt at the repo root)
# Needs the GNU tools from AlphaWRT's env.sh on PATH on macOS.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ALPHAWRT_PKGS=${ALPHAWRT_PKGS:-$HERE/../../alphawrt/package}
TREE=${1:-$HERE/../openwrt}
# Sirherobrine23's openwrt branch "airoha" (kernel 6.18 xPON drivers); the Black's tree is this plus openwrt-tree.patch
FORK=https://github.com/Sirherobrine23/openwrt.git
REV=f9bc9c77798104939f0de9c9208276fae97bd153   # his "airoha: sync config and kernel configs"; 4efad26d54 was force-pushed away

if [ ! -d "$TREE/.git" ]; then
	git clone --filter=blob:none "$FORK" "$TREE"
	git -C "$TREE" checkout -b alphawrt-black "$REV"
	git -C "$TREE" apply "$HERE/openwrt-tree.patch"
fi
cp "$HERE/en7581-skyworth-sk-g7220.dts" "$TREE/target/linux/airoha/dts/"
mkdir -p "$TREE/target/linux/airoha/patches-6.18"
if [ -d "$HERE/patches" ]; then
	cp "$HERE/patches/"*.patch "$TREE/target/linux/airoha/patches-6.18/"
fi
mkdir -p "$TREE/target/linux/airoha/base-files/lib/preinit"
cp "$HERE/79_alphawrt_ubi" "$TREE/target/linux/airoha/base-files/lib/preinit/"
mkdir -p "$TREE/target/linux/airoha/an7581/base-files/etc/board.d"
cp "$HERE/02_network" "$TREE/target/linux/airoha/an7581/base-files/etc/board.d/"

# AlphaWRT UI packages
mkdir -p "$TREE/package/alphawrt"
for p in alphawrt-ui luci-app-alphawrt luci-theme-alphawrt; do
	rm -rf "$TREE/package/alphawrt/$p"
	cp -R "$ALPHAWRT_PKGS/$p" "$TREE/package/alphawrt/"
done

cd "$TREE"
cp "$HERE/feeds.conf" feeds.conf   # pinned: the versions the working image was built from
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
"$HERE/mk_flash_image.sh" "$TREE" ${2:+"$2"}
