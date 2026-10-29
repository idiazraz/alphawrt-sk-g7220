#!/bin/bash
# Read-only backup of a stock SK-G7220 over SSH. Writes nothing on the board:
# every remote command is a read (cat, sha256sum, tar -c to stdout).
#
#   ./stock-backup.sh [user@host]      default admin@192.168.0.1 (stock LAN IP)
#
# Each /dev/mtdNro is pulled twice and must hash the same both times and match
# the board's own sha256sum and the /proc/mtd size; otherwise the script stops.
# Output: backup/sk-g7220/dump-<date>/ (gitignored, private: holds MACs,
# calibration, GPON identity, verity hash).
set -euo pipefail
H=${1:-admin@192.168.0.1}
OUT=$(cd "$(dirname "$0")/.." && pwd)/dump-$(date +%Y%m%d-%H%M)
mkdir -p "$OUT"/mtd "$OUT"/info
cd "$OUT"
SSH="ssh -o ControlMaster=auto -o ControlPath=/tmp/sk-ssh-%r@%h -o ControlPersist=120 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/gn630v $H"
r() { $SSH "$@" < /dev/null; }

r 'cat /proc/mtd' > info/proc-mtd.txt
cat info/proc-mtd.txt

tail -n +2 info/proc-mtd.txt | while read -r dev size _ name; do
	n=${dev%:}; n=${n#mtd}; name=${name//\"/}
	f="mtd/mtd$n-$name.bin"
	want=$((16#$size))
	echo "== mtd$n $name ($want bytes)"
	remote=$(r "sha256sum /dev/mtd${n}ro" | cut -d' ' -f1)
	r "cat /dev/mtd${n}ro" > "$f"
	a=$(shasum -a 256 "$f" | cut -d' ' -f1)
	b=$(r "cat /dev/mtd${n}ro" | shasum -a 256 | cut -d' ' -f1)
	got=$(stat -f %z "$f")
	[ "$got" = "$want" ] || { echo "SIZE MISMATCH mtd$n: $got != $want"; exit 1; }
	[ "$a" = "$remote" ] && [ "$a" = "$b" ] || { echo "HASH MISMATCH mtd$n: local $a, 2nd read $b, board $remote"; exit 1; }
	for s in bad_blocks bbt_blocks ecc_failures corrected_bits; do
		printf '%s=%s ' "$s" "$(r "cat /sys/class/mtd/mtd$n/ecc_stats/$s /sys/class/mtd/mtd$n/$s 2>/dev/null" | head -1)"
	done >> info/mtd-stats.txt; echo "mtd$n" >> info/mtd-stats.txt
done

# Live FDT, boot and driver context.
r 'cat /sys/firmware/fdt' > info/stock.dtb
for c in 'cat /proc/cmdline' 'cat /proc/modules' 'cat /proc/cpuinfo' 'cat /proc/meminfo' \
	'cat /etc/openwrt_release' 'ubus call system board' 'opkg list-installed' \
	'ls -lR /lib/modules /lib/firmware /etc/wireless /userfs /apps' \
	'cat /proc/interrupts' 'cat /sys/kernel/debug/gpio' 'cat /sys/kernel/debug/pinctrl/*/pinmux-pins' \
	'lspci -vvv; ls -l /sys/bus/pci/devices/' 'ip -d link' 'i2cdetect -y 0' 'ps w' 'netstat -lntu'; do
	echo "### $c"; r "$c" 2>&1 || true
done > info/stock-info.txt

# Configs and vendor userland (configs may hold secrets: private dir).
r 'tar -c -C / etc userfs 2>/dev/null' > info/etc-userfs.tar || true
r 'tar -c -C / apps 2>/dev/null' > info/apps.tar || true
r 'tar -c -C / lib/modules lib/firmware usr/lib 2>/dev/null' > info/vendor-libs.tar || true

shasum -a 256 mtd/* info/* > SHA256SUMS
echo "Done: $OUT"; cat SHA256SUMS
