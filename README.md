# AlphaWRT for the Skyworth SK-G7220

OpenWrt (kernel 6.18) for the Skyworth SK-G7220 GPON ONT with Wi-Fi 7 (MT7992). It is a sister project of [AlphaWRT for the GN630V](https://github.com/idiazraz/gn630v-alphawrt) and uses the same Simple UI, Pi-hole and theme packages.

> **Status: bring-up. No flashable image yet.** Nothing here has been written to flash. So far the board has only been booted from RAM over U-Boot TFTP.

## Which SK-G7220 do you have?
There are two SK-G7220 boards with different SoCs. They need separate builds.

| | Black | White |
|---|---|---|
| SoC | Airoha EN7581, 4x Cortex-A53 at 1.3 GHz | Airoha AN7553 / AN7583, 2x Cortex-A53 at 1.2 GHz |
| RAM | 1 GiB | 512 MiB |
| Flash | 256 MiB SPI NAND (Winbond W25N02K) | 256 MiB SPI NAND (Foresee F35SQB002G) |
| Wi-Fi | MT7992 (Wi-Fi 7) | MT7992 (Wi-Fi 7) |
| U-Boot | `ECNT>` prompt, no login | `U-Boot>` prompt, login required |
| Image signing | SHA-1 hash only, unsigned images boot | RSA-4096 signed FIT required |
| Flash layout | Dual-bank `tclinux` (same as the GN630V) | Split `kernel` + `filesystem` with dm-verity |
| OpenWrt subtarget | `airoha/an7581` | `airoha/an7583` |

Check the SoC marking or the U-Boot banner. The colour alone may not tell you the board.

## Progress

| | Black (EN7581) | White (AN7583) |
|---|---|---|
| Serial console | Yes | Yes |
| RAM boot (initramfs) | Not yet | Yes, kernel 6.18 |
| Device tree | Stock reference only | Written, compiles |
| Ethernet | — | 2x 2.5G (EN8811H), 1G switch LAN2-4 |
| USB, LEDs, buttons | — | Yes |
| Wi-Fi (PCIe + MT7992) | — | PCIe link not up yet |
| Flash install | — | — (signed FIT blocks it) |

Hardware details: [docs/HARDWARE.md](docs/HARDWARE.md).

## Layout
- `white/`: the AN7583 port. `an7583-skyworth-sk-g7220.dts`, `02_network` (from `target/linux/airoha/an7583/base-files/etc/board.d/`), `boot_runner.py` (handles the U-Boot login, PCIe register writes and TFTP RAM boot; the password comes from `UBOOT_PWD`), `uboot-login.sh`, the minimal `ramtest/` DTS and FIT, and the bring-up log in `BRINGUP.md`.
- `black/`: the EN7581 port. So far only the stock device tree (`stock-fdt.dts`, the reference for `en7581-skyworth-sk-g7220.dts`) and `listen_black.py` (UART logger).
- `tools/`: `uart.py` (UART logger that stops autoboot and takes commands from a FIFO), `serial_cmd.py`, `stock-backup.sh` (read-only partition dump over SSH from stock).
- `docs/`: hardware notes for both boards and the RAM-boot procedure.

Run the serial scripts from the AlphaWRT workspace root. They write logs and `cmd.in` under `backup/sk-g7220/`, outside this repo.
- The AlphaWRT packages (`alphawrt-ui`, `alphawrt-pihole`, `luci-theme-alphawrt`, ...) are not copied here. The build takes them from the GN630V repo, so both boxes get the same UI.

## License
GPL-2.0, see [LICENSE](LICENSE).
