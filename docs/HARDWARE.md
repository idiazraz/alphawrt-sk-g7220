# SK-G7220 hardware

Two boards share the SK-G7220 name. Unless a section says otherwise, everything below was read on the live boards over UART at 115200 baud.

## Black vs white

| Part | Black | White | What it means for the port |
|---|---|---|---|
| SoC | Airoha EN7581 (4x A53, 1.3 GHz) | Airoha AN7553 / AN7583 (2x A53, 1.2 GHz) | Black uses OpenWrt `airoha/an7581`. White needs AN7583 PCIe work. |
| RAM | 1 GiB (`0x80000000`-`0xc0000000`) | 512 MiB | |
| SPI NAND | Winbond W25N02K, 256 MiB (mfr `0xef`, dev `0xaa 0x22`) | Foresee F35SQB002G, 256 MiB | Both have drivers in OpenWrt. |
| U-Boot | `ECNT>`, no login | U-Boot 2023.04, `telecomadmin` login | The white board's password stays out of this repo. |
| Image check | SHA-1 (`sha1+`), no signature | RSA-4096, `required = "image"` | Black boots custom FIT images from flash. White only boots them from RAM so far. |
| Flash layout | Dual-bank `tclinux` (60 MiB per bank) | `kernel` 7 MiB + `filesystem` 68 MiB, dm-verity | Black can use the GN630V `tclinux` image tooling. |
| Wi-Fi | MT7992 | MT7992 | `kmod-mt7996e` + `mt7992-firmware` |
| Wi-Fi offload (NPU) | `airoha-en7581-npu-firmware` | Not in upstream mt76 for AN7583 | |
| Ethernet | 1x 2.5G (LAN1), 3x 1G (LAN2-4), USXGMII SerDes | 2x EN8811H 2.5G (MDIO `0x0e` WAN, `0x0f` LAN1), 1G switch LAN2-4 | |
| U-Boot network port | `ecnt_eth` on PHY 15 (2.5G, LAN1) | | Plug the TFTP cable into LAN1. |
| `art` partition | MAC as ASCII at `0x0`, MT7992 EEPROM at `0x40000` (magic `0x7992`) | Same | Same NVMEM layout on both. |

## Flash map (black)

```text
0x00000000-0x00080000  bootloader     512 KiB  BL2, BL31, U-Boot
0x00080000-0x03c80000  tclinux        60 MiB   bank 0 (kernel lzma, fdt, squashfs)
0x03c80000-0x07880000  tclinux_slave  60 MiB   bank 1
0x07880000-0x08080000  rootfs_data    8 MiB    JFFS2 overlay
0x08080000-0x0a080000  ubifs          32 MiB   UBI (/apps)
0x0a080000-0x0a280000  others         2 MiB    boot flag, config env
0x0a280000-0x0dc80000  (unused)       56 MiB
0x0dc80000-0x0e000000  art            3.5 MiB  MAC (0x0), MT7992 EEPROM (0x40000-0x19c000)
0x0e000000-0x10000000  bmt pool       32 MiB   bad block management
```

On stock, bank 0 contains a 3.6 MiB lzma kernel (load/entry `0x80088000`), a 14.5 KiB DTB and a 37.4 MiB squashfs.

## GPIO

| Function | Black | White |
|---|---|---|
| Reset button | 0 (active low) | 0 (active low) |
| WPS button | 22 (active low) | 5 (active high, measured on the board) |
| Power LED | 17 (active low) | 7 (active low) |
| PON LED | 18 | 12 |
| LOS LED (red) | 19 | 27 |
| Internet LED | 20 | 26 |
| VoIP LED | 23 | 29 |
| Wi-Fi / WPS LED | 25 | 33 |
| USB LED | 27 | 38 |
| Optical TX disable | 38 | 15 |
| MT7992 reset | | `gpio510` (stock boot log) |

## White: PCIe for the MT7992
- Port 1 (`1fa92000`, Gen2) needs `compatible = "airoha,en7523-pcie", "mediatek,mt7622-pcie"`. With that, `mtk-pcie` probes.
- Port 0 (`1fc20000`, Gen3) PHY `airoha,an7583-pcie-gen3-phy`: `g3-ana` `0x1fc7f000`, `g3-pma` `0x1fc7e000`, `xr-dtime` `0x1fc10044`, `rx-aeq` `0x1fc15030`.
- Stock U-Boot leaves PERST# asserted. Before `booti`, run `mw.l 0x1fa2018c 0x7` (SerDes) and `mw.l 0x1fa20088 0x24c00003` (releases PERSTOUT0/1).
- Don't list `AN7583_PCIE_HB_RST` in `phy_resets`. Asserting it locks the bus.
- Not confirmed yet: the link still stopped in LTSSM `detect.quiet` before these fixes, and they haven't been tested on a boot yet.

## RAM boot (no flash writes)

Both boards: serve the files over TFTP from the Mac at `192.168.1.126`, with the cable in LAN1.

```text
setenv ipaddr 192.168.1.1
setenv serverip 192.168.1.126
tftpboot 0x82000000 kernel.lzma
lzmadec 0x82000000 0x80200000
tftpboot 0x83000000 board.dtb
booti 0x80200000 - 0x83000000
```

On the white board, U-Boot clears its input buffer during PHY init, just before the autoboot countdown. To stop autoboot, keep sending Enter until the login prompt appears.

## Black: WAN or fibre switch
A switch on the board routes the PON SerDes lanes. GPIO 33 low sends them to the EN8811H (WAN port), high to the optics. GPIO 34 is low in both. U-Boot sets them from its `switch_flag` env, and AlphaWRT's kernel then sets GPIO 33 from its own WAN flag (`wan-path-gpios`). The EN8811H also needs its reset on GPIO 42.
