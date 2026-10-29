#!/bin/sh
# Runs on the RAM-booted box: print a CARRIER line whenever a port's link changes.
for i in gsw1 gsw2 gsw3 gsw4 eth25g; do ip link set $i up; done
old=""
while true; do
	now=""
	for i in gsw1 gsw2 gsw3 gsw4 eth25g; do
		c=$(cat /sys/class/net/$i/carrier 2>/dev/null)
		[ "$c" = 1 ] && now="$now $i@$(cat /sys/class/net/$i/speed)"
	done
	[ "$now" != "$old" ] && echo "CARRIER up:${now:- none}" > /dev/console
	old=$now
	sleep 1
done
