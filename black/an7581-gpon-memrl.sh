#!/bin/sh
# AN7581 GPON register snapshot using the vendor sys memrl command.
# Usage: sh an7581-gpon-memrl.sh disconnected|o5 [output-directory]

case "$1" in
	disconnected|o5) state=$1 ;;
	*) echo "Usage: sh $0 disconnected|o5 [output-directory]" >&2; exit 2 ;;
esac
command -v sys >/dev/null 2>&1 || { echo 'ERROR: sys command not found' >&2; exit 1; }
command -v dmesg >/dev/null 2>&1 || { echo 'ERROR: dmesg command not found' >&2; exit 1; }
outdir=${2:-/tmp}
[ -d "$outdir" ] && [ -w "$outdir" ] || { echo "ERROR: cannot write to $outdir" >&2; exit 1; }
stamp=$(date +%Y%m%d-%H%M%S 2>/dev/null) || stamp=unknown
base="$outdir/an7581-gpon-$state-$stamp-$$"
before="$base.before"
after="$base.after"
prefix="$base.prefix"
log="$base.txt"
trap 'rm -f "$before" "$after" "$prefix"' EXIT HUP INT TERM
umask 077
if ! dmesg >"$before" 2>/dev/null; then
	echo 'ERROR: cannot read dmesg; run as root and check firmware permissions' >&2
	exit 1
fi
{
	echo "AN7581 GPON register snapshot: $state"
	echo "Time: $(date 2>/dev/null)"
	echo "Kernel: $(uname -a 2>/dev/null)"
	echo 'Output below includes sys command stdout/stderr and new kernel log lines.'
	echo 'Read requests:'
} >"$log"
fail=0
# Only named configuration and status registers used by the SDK's PHY dump
# or regular driver operations are included. No bulk scan or MMIO writes.
while read -r addr name; do
	[ -n "$addr" ] || continue
	echo "REQUEST $addr $name" >>"$log"
	if ! sys memrl "$addr" >>"$log" 2>&1; then
		echo "ERROR: sys memrl $addr failed" >>"$log"
		fail=1
	fi
done <<'REGISTERS'
1fb00070 SCU_WAN_CONF
1faf0104 GEPON_PHYSET2
1faf0108 GEPON_PHYSET3
1faf0110 GEPON_PHYSET5
1faf0124 GEPON_PHYSET10
1faf0130 GEPON_PHYSTA1
1faf020c GEPON_GPON_PSYNC_CTL
1faf0210 GEPON_GPON_INDENT_CTL
1faf0214 GEPON_RS_CTL
1faf021c GEPON_PHYRX_STATUS
1fa8a000 ANA_CMN_EN
1fa8a004 ANA_JCPLL_IB_EXT_EN
1fa8a008 ANA_JCPLL_LPF_BR
1fa8a010 ANA_JCPLL_KBAND_KFC
1fa8a014 ANA_JCPLL_MMD_PREDIV_MODE
1fa8a01c ANA_JCPLL_RST_DLY
1fa8a050 ANA_TXPLL_CHP_IBIAS
1fa8a054 ANA_TXPLL_LPF_BP
1fa8a058 ANA_TXPLL_KBAND_CODE
1fa8a05c ANA_TXPLL_KBAND_KS
1fa8a060 ANA_TXPLL_PHY_CK1_EN
1fa8b450 PMA_PON_CK_SET
1fa8b854 PMA_FORCE_TXPLL_CKOUT
1fb64000 GPON_ONU_ID
1fb64004 GPON_GBL_CFG
1fb6400c GPON_INT_ENABLE
1fb64160 GPON_MBI_MPI_STOP
1fb64208 GPON_DBG_DLY
1fb6420c GPON_DBG_IDLE_GEM_THLD
REGISTERS
if ! dmesg >"$after" 2>/dev/null; then
	echo 'ERROR: cannot read dmesg after collection' >>"$log"
	fail=1
else
	lines=$(wc -l <"$before")
	sed -n "1,${lines}p" "$after" >"$prefix"
	if cmp -s "$before" "$prefix"; then
		echo '--- New kernel log lines ---' >>"$log"
		awk -v n="$lines" 'NR > n { print }' "$after" >>"$log"
	else
		echo 'WARNING: kernel log changed or wrapped; complete final dmesg follows.' >>"$log"
		cat "$after" >>"$log"
		fail=1
	fi
fi
# Check for an address/value pair, whether printed by sys or by the kernel.
missing=$(awk '
/^REQUEST / { want[tolower($2)] = 1; next }
{
 line=tolower($0)
 for (a in want) if (index(line,a) && line ~ /0x[0-9a-f]+[[:space:]]+0x[0-9a-f]+/) found[a]=1
}
END { for (a in want) if (!found[a]) { print "MISSING " a; count++ } exit count ? 1 : 0 }
' "$log") || fail=1
if [ -n "$missing" ]; then
	printf '%s\n' "$missing" >>"$log"
	echo 'WARNING: some values were not found; inspect the file for errors.' >&2
fi
cat "$log"
exit $fail
