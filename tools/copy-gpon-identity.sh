#!/bin/sh
# Copy the GPON identity from the GN630V to the SK-G7220 Black. xpon.agent reads
# /etc/config/xpon, not omci, and the OLT also checks the OMCC version.
# Run it yourself: it asks for each board's root password and prints no values.
# Usage: tools/copy-gpon-identity.sh [from-host] [to-host]
set -e
FROM=${1:-192.168.100.1}
TO=${2:-192.168.1.1}
umask 077
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT HUP INT TERM
OPTS='-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR'
echo "Reading from $FROM"
ssh $OPTS "root@$FROM" 'cat /etc/config/omci' > "$tmp"
grep -q "config " "$tmp" || { echo "No omci config read from $FROM" >&2; exit 1; }
echo "Writing to $TO"
ssh $OPTS "root@$TO" 'umask 077; cat > /etc/config/omci && uci commit omci
for o in serial vendor_id password equipment_id hardware_version software_version_0 software_version_1 omcc_version traffic_management_option olt_profile olt_profile_force; do
	v=$(uci -q get omci.main.$o); [ -n "$v" ] && uci set xpon.main.$o="$v"
done
uci commit xpon
for k in serial vendor_id password equipment_id omcc_version; do [ -n "$(uci -q get xpon.main.$k)" ] && echo "$k: set" || echo "$k: empty"; done' < "$tmp"
