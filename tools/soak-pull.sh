#!/bin/sh
# Pull the SK-G7220 soak logs over SSH into soak/<time>-black. Read-only on the board.
# Output stays local: never copy it into the repo.
H=${1:-sk-g7220-mgmt}
O=$(cd "$(dirname "$0")/../../.." && pwd)/soak/$(date +%Y%m%d-%H%M)-black
mkdir -p "$O" || exit 1
m() { sed -E 's/development serial [0-9a-f]+/development serial XXXX/; s/([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}/xx:xx/g'; }
S="ssh -n -o BatchMode=yes -o ConnectTimeout=8 $H"
$S 'cat /overlay/soak/samples.tsv' > "$O/samples.tsv" || { echo "board not reachable"; exit 1; }
$S 'cat /overlay/soak/events.log' > "$O/events.log"
$S 'for f in $(find /tmp /var -maxdepth 3 -name events.log -o -maxdepth 3 -name line.hist 2>/dev/null); do echo "== $f"; cat $f; done' | m > "$O/linemon.txt"
$S 'dmesg' | m > "$O/dmesg.txt"
$S 'logread' | m | grep -v 'dropbear\[' > "$O/logread.txt"
$S 'uptime; omcictl status | grep -E "^(state|onu-id|gem-port|channel-up|agent-operational|olt-)"; free | head -2' > "$O/status.txt"
echo "$O"; cat "$O/status.txt"; wc -l "$O/samples.tsv" "$O/events.log" | head -2
