# SK-G7220 (white): hardware inventory, RAM test and port plan

Private working notes (gitignored). Source of every fact: the stock UART transcript
(`~/Desktop/sk-g7220-uboot.txt`, 2026-10-28) unless marked otherwise. No unit
identifiers are copied here, so this file can later move into the repo.

## Verified from stock

| Block | Stock evidence | Upstream OpenWrt (r37758, main) |
|---|---|---|
| SoC | FDT `airoha,an7583`, 2x A53, Linux 5.4.55, OpenWrt 21.02 | `airoha/an7583` subtarget, kernel 6.18 |
| RAM | 512 MiB at 0x80000000; U-Boot reserves 0x80000000-0x8003ffff | dtsi reserves ATF, NPU, QDMA regions |
| NAND | Foresee F35SQB002G (mfr 0xcd, dev 0x52), 256 MiB, 2 KiB page, 128 KiB block, vendor BMT | `airoha,en7581-snand`, ECC "none" like Nokia |
| Partitions | see below; Linux and U-Boot `mtd list` agree; env `partitions=` is wrong | needs our DTS |
| Bootflag | U-Boot FDT `u-boot,bootflag-offset = 0x0be80000` (= `others`); kernel cmdline `bootflag=0` | n/a |
| Second bank | U-Boot FDT `u-boot,spl-payload-offset = 0x04b80000` (= `kernel_slave`) | n/a |
| Switch | Internal GSW PHYs 9, 10, 11, 12 initialised (= `gsw_phy1..4`) | `airoha,an7583-switch`, ports 1-4 |
| 2.5G PHY | EN8811H answers at MDIO 0x0e ("SERDES_PON") and 0x0f ("SERDES_ETH"), FW 25030316 | `air_en8811h` + firmware package (Nokia uses it on gdm3, `2500base-x`) |
| LAN | `br-lan` = eth0.2, eth0.3, eth0.4, eth0.5 (eth0.1 exists, down) | jack mapping unknown |
| WAN | GPON (`pon`, `pon_veip`, `omci`), VLAN subinterfaces `nas_vidNNN@pon` | no PON/OMCI driver for AN7583 |
| BOSA | EN7571 on I2C bus 0, vendor driver `en7571` | none |
| Wi-Fi | MT7992 BE6500 (SKU "MT7992-BE6500-7978-7979", iPA/iLNA): `14c3:7992` on PCIe1 (1fa92000), `14c3:799a` (HIF2) on PCIe0 (1fc20000) | `mt7996e` supports MT7992; **an7583.dtsi has no PCIe nodes** (driver patches 036 + 602-04 are in) |
| Wi-Fi cal | `E2pAccessMode=2` (EEPROM in flash), `MacAddrAdj=0x0` | needs ART offset from the dump |
| USB | xHCI 1fab0000, USB PHY up | `usb0` + `usb_phy` nodes exist |
| Voice | Si32192 (part 0x5 rev 0x2) found over ISI after Zarlink probe fails; vendor `DSPCore`, `pcm1`, `fxs3_silicon`, `slic3_silicon`, `ovdsp`, `foip` | `ASoC airoha AFE/I2S` patch exists for AN7581 only |
| Power LED | GPIO 7 (active low), verified from U-Boot and `7581_54_led.conf` | `leds` in DTS |
| Other GPIOs | Decoded from stock `userfs/7581_54_led.conf` and `stock.dts`: <br>- GPIO 0: Reset button (active low)<br>- GPIO 1: LAN1 LED<br>- GPIO 2: LAN2 LED<br>- GPIO 3: LAN3 LED<br>- GPIO 4: LAN4 LED<br>- GPIO 5: WPS button (active low)<br>- GPIO 7: Power LED (active low)<br>- GPIO 12: PON / Optical LED<br>- GPIO 15: Optical TX disable<br>- GPIO 26: Internet LED<br>- GPIO 27: PON LOS LED (red)<br>- GPIO 29: VoIP / Phone LED<br>- GPIO 33: Wi-Fi / WPS LED<br>- GPIO 38: USB LED | Complete map ready for DTS |
| PCIe | `pcie0@1fc20000` (HIF2: 14c3:799a, IRQ 39, range 0x20000000-0x24000000)<br>`pcie1@1fa92000` (MT7992: 14c3:7992, IRQ 40, range 0x24000000-0x28000000) | Extracted from `stock.dts` |
| Thermal | `airoha-thermal_phy` AN7583 | supported |
| Offload | vendor `hw_nat` (PPE, L2B/IPv4/IPv6), QDMA LAN/WAN, NPU, `npu_wifi` | airoha_eth PPE + NPU; mt76 NPU glue only for AN7581 |

### NAND map (Linux `/proc/mtd`, the only map to trust)

| mtd | name | start | size |
|---|---|---|---|
| 0 | bootloader | 0x0000000 | 0x080000 |
| 1 | kernel | 0x0080000 | 0x700000 |
| 2 | filesystem | 0x0780000 | 0x4400000 |
| 3 | kernel_slave | 0x4b80000 | 0x700000 |
| 4 | filesystem_slave | 0x5280000 | 0x4400000 |
| 5 | rootfs_data | 0x9680000 | 0x800000 (JFFS2 overlay) |
| 6 | ubifs | 0x9e80000 | 0x2000000 (UBI, `/apps`) |
| 7 | others | 0xbe80000 | 0x200000 (bootflag) |
| — | (hole) | 0xc080000 | 0x1c00000, not exposed by stock |
| 8 | art | 0xdc80000 | 0x380000 |
| — | BMT pool | 0xe000000 | 0x2000000 |

The `/dev/mtdNro` dump covers mtd0-8 only. The hole and the BMT pool need a
separate read (U-Boot `mtd read` to RAM + `md`, or the RAM-test kernel's `gap`
and `reserved_bmt` partitions). None of these reads include OOB.

## Boot chain and signing

- BL2 v2.10 + BL31 + OP-TEE + U-Boot, all from `bootloader`. BL2 prints
  `SECURE_INVAILD` / "Secure key does not exist"; BL31 "Disabling authentication
  of images dynamically".
- `bootcmd=ldkernel;init_iNIC;bargsenv;bootm 0x81800000#conf-1`. Stock FIT kernel
  loads at 0x80088000, signed `sha1,rsa4096:dev`.
- **U-Boot's control FDT has `signature/key-dev { required = "image"; }`.** So
  `bootm` of an unsigned FIT is expected to fail. That is why the RAM test uses
  `booti`, which does not check FIT signatures. `lzmadec` and `booti` are both
  in this U-Boot's command list.
- Consequence for later: a flashed OpenWrt image either has to go through the
  stock `ldkernel`/`bootm` path (needs a key we don't have, or a policy we can
  avoid), or boot via a bootcmd that uses `booti`, which means changing the
  U-Boot env. That is a board change and needs the user's approval. Decided
  later, after the RAM test.

## RAM test (no flash writes, no `saveenv`)

Files in `port/ramtest/` (see `SHA256SUMS` there):
- `kernel-1.lzma`: kernel + initramfs from the official snapshot
  `openwrt-airoha-an7583-nokia_xg-040g-mf-initramfs-uImage.itb` (r37758,
  sha256 checked against downloads.openwrt.org). Chosen over the EVB image
  because it carries the EN8811H driver and firmware.
- `Image`: the same, decompressed (0x1561008 bytes; header image_size 0x15c0000).
- `ramtest.dtb`: `an7583-skyworth_sk-g7220-ramtest.dts` built against upstream
  main `an7583.dtsi`. All partitions read-only, no BMT, only the power LED.
- `sk-g7220-ramtest.itb`: unsigned FIT, only for probing the signature policy.

Setup: Mac on 192.168.1.126/24 cabled to a LAN jack, TFTP server serving
`port/ramtest` (`python3 -I tools/tftp_lockstep.py --dir backup/sk-g7220/port/ramtest --bind 0.0.0.0 --port 69`),
UART at 115200. U-Boot env already has `ipaddr=192.168.1.1`, `serverip=192.168.1.126`.

Checked 2026-10-28 on the board: U-Boot 2023.04 asks for a UserName/Password
after autoboot is stopped (`port/uboot-login.sh` sends them through `uart.py`'s
FIFO without the password reaching any log). Ping works, and whole-file
`tftpboot` works (7 MB at ~357 KiB/s, crc32 matches), so the GN630V chunking
is not needed. `booti` takes compressed Images only with `kernel_comp_addr_r`
set, so we use `lzmadec` first.

At the `U-Boot>` prompt (stop autoboot). `setenv` changes RAM only; never `saveenv`:
```
setenv bootargs "console=ttyS0,115200n8 earlycon"
tftpboot 0x82000000 kernel-1.lzma
lzmadec 0x82000000 0x80200000
tftpboot 0x83000000 ramtest.dtb
booti 0x80200000 - 0x83000000
```
Fallback if `lzmadec` fails: `tftpboot 0x80200000 Image` instead of the first three lines.
Memory: Image 0x80200000-0x817c0000, LZMA 0x82000000-0x826cf000, DTB 0x83000000; all
below U-Boot's relocated copy at 0x9f35d5c0.

Optional probe of the signing policy (harmless, expected to fail):
`tftpboot 0x81800000 sk-g7220-ramtest.itb; bootm 0x81800000`.

Recovery if anything hangs: power-cycle. Nothing above touches NAND or the
persistent env, so the stock firmware boots as before.

### Result, 2026-10-28 (first RAM boot, snapshot r37758 + ramtest.dtb)
- `lzmadec` + `booti` boot the upstream 6.18.55 kernel; stock U-Boot does not
  block it. Userspace (procd, shell, SSH) works. 2x A53, ~429 MiB usable,
  thermal zones read 46-49 °C.
- Ethernet verified on the board:
  - **2.5G WAN**: EN8811H PHY 14 (MDIO 0x0e, `SERDES_PON`), wired to `gdm2` (`pon_pcs`).
  - **2.5G LAN1**: EN8811H PHY 15 (MDIO 0x0f, `SERDES_ETH`), wired to `gdm3` (`eth_pcs`, `eth25g`). Tested live at 1 Gbps/Full.
  - **LAN2**: Internal GSW port 2 (`gsw2`), 1 Gbps. Tested live with ping/SSH to Mac.
  - **LAN3**: Internal GSW port 3 (`gsw3`), 1 Gbps. Tested live.
  - **LAN4**: Internal GSW port 4 (`gsw4`), 1 Gbps. Tested live.
  - (Note: `gsw1` is unpopulated/internal since LAN1 is driven by the 2.5G EN8811H PHY).
- **NAND not probed:** `spi-nand: unknown raw ID cd5252cd52`. Upstream vanilla lacks
  F35SQB002G ID; our tree's `patches-6.18/205-mtd-spinand-add-Foresee-F35SQB002G`
  (same chip as the GN630V) adds it, so full flash recognition will come with our
  own image build. Zero flash was touched during testing.
- **USB Tested Live:** `xhci-mtk` initialized USB 2.0 (480M) and USB 3.2 Gen 2 (10 Gbps) root hubs.
- **Switch & Conduit:** `&gdm1` enabled as the 10G conduit for `switch@1fb58000`. `lan2-4` DSA ports operational.
- **WPS Button Polarity:** Inverted to `GPIO_ACTIVE_HIGH` (reads 0 when unpressed), successfully preventing false failsafe boots.
- **Thermals:** Three zones reading 45.9 °C - 49.3 °C under live Linux.

### What to check once booted
1. `cat /proc/mtd`; `md5sum /dev/mtd*ro` vs the stock dump (BMT-remapped blocks may differ).
2. `ip link`; plug one cable per jack and note which of `gsw1-4` / `eth25g` gets carrier and at what speed.
3. `i2cdetect -y 0` (EN7571 at its address), `cat /sys/kernel/debug/gpio`.
4. Thermal, USB stick, `dmesg` errors.
5. Network config: `board.d` doesn't know the board yet, so set it by hand:
   `ip addr add 192.168.1.1/24 dev <lan-port>; ip link set <lan-port> up`.

## Hardware Variant Comparison: White vs. Black SK-G7220

Source: White stock dump (`dump-20261028-1959/`), Black stock image (`SK-G7220_V1.0.0.8_20260416.bin`), and Airoha AN7553 Datasheet v0.8.

| Feature | SK-G7220 (White - Our Unit) | SK-G7220 (Black) | Impact on Port |
|---|---|---|---|
| **SoC** | Airoha **AN7553** (packaged as `an7583`), 2x Cortex-A53 @ 1.2GHz | Airoha / Econet **EN7581**, 4x Cortex-A53 @ 1.3GHz | White needs `airoha/an7583` target; Black is standard `airoha/en7581` |
| **PCIe Ports** | 2 ports: `pcie0@1fc20000` (Gen2) & `pcie1@1fa92000` (Gen3) | 3 ports: `pcie0@1fc00000`, `pcie1@1fc20000`, `pcie2@1fc40000` | White uses Gen3 for MT7992 main radio, Gen2 for HIF2 |
| **Wi-Fi 7 Radio** | MT7992 (BE6500) | MT7992 (BE6500) | Identical radio! |
| **Wi-Fi Calibration** | In `art` (`mtd8`) at **offset `0x40000`**, size 0x15c000 (magic `0x7992`) | In `art` (`mtd6` / `Factory`) at **offset `0x40000`**, size 0x15c000 | Confirmed byte-for-byte layout in both firmware images |
| **MAC Address** | In `art` (`mtd8`) at offset `0x0000` as ASCII string (`3C:A0:0E:...`) | In `art` / `Factory` at offset `0x0000` | Simple NVMEM cell definition in DTS |
| **Switch & 2.5G** | Dual EN8811H PHYs (MDIO 0x0e, 0x0f) -> `gdm2` (2.5G WAN), `gdm3` (2.5G LAN1); Internal GSW ports 2-4 | `p2l_usxgmii@1fa50000` + SerDes common PHY | White has dedicated external dual-channel 2.5G PHYs |
| **Power LED** | GPIO 7 (active low) | GPIO 17 (active low) | Different GPIO pinout! |
| **PON Status LED** | GPIO 12 | GPIO 18 | Different GPIO pinout |
| **PON LOS LED** | GPIO 27 (Red) | GPIO 19 | Different GPIO pinout |
| **Internet LED** | GPIO 26 | GPIO 20 | Different GPIO pinout |
| **VoIP Phone LED** | GPIO 29 | GPIO 23 | Different GPIO pinout |
| **Wi-Fi / WPS LED** | GPIO 33 | GPIO 25 | Different GPIO pinout |
| **USB LED** | GPIO 38 | GPIO 27 | Different GPIO pinout |
| **Reset Button** | GPIO 0 (active low) | GPIO 0 (active low) | **Identical!** |
| **WPS Button** | GPIO 5 (active low) | GPIO 22 (active low) | Different GPIO pinout |
| **Optical TX Disable** | GPIO 15 | GPIO 38 | Different GPIO pinout |
| **Partitions** | Split `kernel` (7M) + `filesystem` (68M) with `dm-verity` | Single combined `tclinux` (60M) per bank | White uses separate kernel/rootfs partitions |

## Port slices

1. **Inventory (this slice):** read-only dump with `port/stock-backup.sh`
   (pulls each mtd twice, checks size and board-side sha256), stock DTB,
   configs, vendor modules. *Needs the board on the network and the stock
   login.* Then the hole and BMT pool via the RAM-test kernel.
2. **RAM test:** above. Pass = serial shell, NAND readable, each jack mapped.
3. **Device profile:** real DTS (port names, LEDs/buttons from
   `7581_54_led.conf` + GPIO debugfs, MAC from `others`/`art`), `an7583.mk`
   device, `02_network` case. Builds need a build tree: today's `openwrt/` is
   EN7523 and claimed; an AN7583 build means either a second tree or a claim
   and a config switch (toolchain rebuild).
4. **Wi-Fi:** write PCIe + PCIe PHY nodes for AN7583 (none upstream), MT7992
   EEPROM from `art` (offset from the dump), HIF2 on PCIe0. NPU Wi-Fi offload
   is a later, separate gate (mt76 enables it for AN7581 only).
5. **Flash/update path:** decide boot method against the `required = "image"`
   policy, bank use (keep stock in one bank), sysupgrade, verified recovery.
   Needs the user's approval before any write.
6. **AlphaWRT userland:** generic packages behind board capability checks;
   fibre pages hidden until slice 7.
7. **GPON/OMCI:** no open AN7583 PON MAC driver; AlphaWRT's GN630V stack is
   EN7523-specific. Paths to study: AN7583 PON PCS in upstream (`pon_pcs`),
   the vendor `xpon`/`xpon_hal`/`ponvlan`/`xponmap` + OMCI userland ABI (5.4
   modules, so reuse means a 5.4 kernel or a rewrite), EN7571 BOSA calibration
   in flash.
8. **Voice:** Si32192 over ISI/PCM; vendor DSP stack is binary for 5.4. The
   GN630V's `local-voip/` work (private, proprietary ProSLIC API) is the
   nearest reference.

Full parity is not claimed until 7 and 8 are demonstrated.
