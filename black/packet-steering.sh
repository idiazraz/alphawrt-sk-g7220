#!/bin/sh
# Note: OpenWrt's packet-steering.uc places RPS by NAPI thread. airoha_eth runs
# NAPI unthreaded here, so it steers every Ethernet RX queue (eth0 and pon0) to
# CPU0, where both Ethernet interrupts already land, and CPU1-2 sit idle. On the
# SK-G7220 send LAN receive work to CPU1 and WAN to CPU2; Wi-Fi keeps the stock
# placement (CPU3).

/usr/libexec/network/packet-steering.uc "$@"

[ "$1" = 1 ] || exit 0
. /lib/functions.sh
[ "$(board_name)" = "skyworth,sk-g7220" ] || exit 0

for q in /sys/class/net/eth0/queues/rx-*/rps_cpus; do
	[ -e "$q" ] && echo 2 > "$q"
done
for q in /sys/class/net/pon0/queues/rx-*/rps_cpus; do
	[ -e "$q" ] && echo 4 > "$q"
done
exit 0
