#!/bin/bash
# One-shot RAM-boot runner for Skyworth SK-G7220 Black
# Usage: sudo ./tools/run_ramboot.sh [/dev/cu.usbserial-0001]
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$HERE/.." && pwd)
PORT=${1:-/dev/cu.usbserial-0001}
IP="192.168.1.126"
CHUNKS_DIR="/tmp/sk7220_chunks"
ITB="${OPENWRT_TREE:-$(dirname "$0")/../openwrt}/bin/targets/airoha/an7581/openwrt-airoha-an7581-skyworth_sk-g7220-black-initramfs-uImage.itb"

if [ ! -f "$ITB" ]; then
    echo "ERROR: ITB image not found at $ITB"
    exit 1
fi

echo "=== 1. Preparing 256 KiB chunks ==="
mkdir -p "$CHUNKS_DIR"
rm -f "$CHUNKS_DIR"/*
split -b 262144 -a 3 -d "$ITB" "$CHUNKS_DIR/chunk"
NUM_CHUNKS=$(ls -1 "$CHUNKS_DIR"/chunk* | wc -l | tr -d ' ')
echo "Generated $NUM_CHUNKS chunks in $CHUNKS_DIR"

echo "=== 2. Starting lockstep TFTP server on $IP:69 ==="
# Kill any existing server on port 69
pkill -f "tftp_lockstep.py" 2>/dev/null || true
python3 "$HERE/tftp_lockstep.py" --dir "$CHUNKS_DIR" --bind "$IP" --port 69 &
TFTP_PID=$!

cleanup() {
    echo "Cleaning up TFTP server (PID $TFTP_PID)..."
    kill "$TFTP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1

echo ""
echo "=========================================================="
echo " Make sure router is at the ECNT> prompt on $PORT"
echo " (If your terminal/screen/picocom is open on $PORT, CLOSE IT NOW)"
echo "=========================================================="
read -p "Press [Enter] when ready to start transfer..."

python3 "$HERE/tftp_chunk_boot.py" "$CHUNKS_DIR" --port "$PORT"
