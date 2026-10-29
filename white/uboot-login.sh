#!/bin/bash
# Log in to the SK-G7220 U-Boot through uart.py's FIFO. The password is read
# without echo and goes only to the board (which echoes '*').
F=$(dirname "$0")/../tools/uart.in
read -r -p "U-Boot user [telecomadmin]: " U
read -rs -p "U-Boot password: " PW; echo
printf '%s\r' "${U:-telecomadmin}" > "$F"
sleep 1
printf '%s\r' "$PW" > "$F"
unset PW
echo "Sent."
