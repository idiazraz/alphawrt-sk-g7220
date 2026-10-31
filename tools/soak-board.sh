#!/bin/sh
# Soak logger for the SK-G7220, run from cron every 5 minutes. Keeps its files on
# flash, so they survive a crash or reboot. Holds no identity values.
D=/overlay/soak; S=$D/samples.tsv; E=$D/events.log
mkdir -p $D
[ -f $S ] || echo "time uptime load1 mem_avail_kb state onu_id temp_mc rx_uw tx_uw pon_rx pon_tx pon_rx_drop pon_tx_drop lan1_up lan1_rx lan1_tx wan_loss_pct gw_loss_pct oops" | tr ' ' '\t' > $S
h=/sys/class/hwmon/hwmon0; n=/sys/class/net
st=$(omcictl status 2>/dev/null); f() { echo "$st" | sed -n "s/^$1: //p"; }
loss() { ping -c3 -W2 "$1" 2>/dev/null | sed -n 's/.* \([0-9]*\)% packet loss.*/\1/p'; }
echo "$(date '+%F_%T') $(cut -d' ' -f1 /proc/uptime) $(cut -d' ' -f1 /proc/loadavg) $(awk '/MemAvailable/{print $2}' /proc/meminfo) $(f state) $(f onu-id) $(cat $h/temp1_input) $(cat $h/power2_input) $(cat $h/power1_input) $(cat $n/pon0/statistics/rx_packets $n/pon0/statistics/tx_packets $n/pon0/statistics/rx_dropped $n/pon0/statistics/tx_dropped | tr '\n' ' ')$(cat $n/lan1/carrier $n/lan1/statistics/rx_packets $n/lan1/statistics/tx_packets | tr '\n' ' ')$(loss 1.1.1.1) $(loss 192.168.100.2) $(dmesg | grep -c -i -E 'oops|call trace|panic')" | tr ' ' '\t' >> $S
# Kernel events since the last run. A new boot id starts again from the top.
b=$(cat /proc/sys/kernel/random/boot_id); l=0; [ "$(cat $D/.boot 2>/dev/null)" = "$b" ] && l=$(cat $D/.seen 2>/dev/null)
[ "$l" = 0 ] && echo "=== boot $(date '+%F_%T') uptime $(cut -d' ' -f1 /proc/uptime)" >> $E
dmesg | awk -v l="${l:-0}" '{t=$2; if ($1=="[") {sub(/\]/,"",t)} else {t=$1; gsub(/[\[\]]/,"",t)}} t+0>l+0' | grep -E 'GPON (state|O5|TO1|digital|netdev)|Deactivate|Disable|LOS|LOF|MIB reset|Oops|panic|Call trace|WARNING|FE interrupt|hung|timeout|airoha-eth .*(Link|error)' | sed -E 's/development serial [0-9a-f]+/development serial XXXX/; s/([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}/xx:xx/g' | cut -c1-140 >> $E
echo "$b" > $D/.boot; dmesg | tail -1 | sed -E 's/^\[ *([0-9.]+)\].*/\1/' > $D/.seen
# Stop either file growing past 2 MiB.
for x in $S $E; do [ "$(wc -c < $x)" -gt 2097152 ] && tail -n 5000 $x > $x.new && mv $x.new $x; done
exit 0
