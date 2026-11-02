# AlphaWRT for the Skyworth SK-G7220

OpenWrt (kernel 6.18) for the Skyworth SK-G7220 GPON ONT with Wi-Fi 7 (MT7992). It is a sister project of [AlphaWRT for the GN630V](https://github.com/idiazraz/gn630v-alphawrt) and uses the same Simple UI, Pi-hole and theme packages.

> **Status: the Black (EN7581) works as a router and installs from stock firmware. [Download the image](https://github.com/idiazraz/alphawrt-sk-g7220/releases/latest).** Fibre (GPON) worked on a real line on an earlier build and hasn't been retested on this one. The White (AN7583) only boots from RAM.

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

## Install on the Black
Black only: this image won't work on the White.

1. On stock, connect to a LAN port. Stock is at `192.168.0.1`. If your home router uses the same address, connect only to the board.
2. On the firmware upgrade page, upload `sk-g7220-black-alphawrt-tclinux-factory.bin`. Keep `tclinux` in the file name, stock needs it.
3. The board writes the spare bank and restarts. Stock stays in the other bank.
4. Open `http://192.168.1.1`. The root password is blank, as on any OpenWrt install. Set one in Quick Setup.
5. Choose Router in Quick Setup to use the 2.5G WAN port. The board restarts to switch.

The WAN port and fibre can't run together: a switch on the board routes one link to either the optics or the WAN chip, so the mode is chosen at boot. Details and the SSH route: [black/STOCK-UPGRADE.md](black/STOCK-UPGRADE.md). Have a serial console ready if you can, in case an install goes wrong.

## Progress

| | Black (EN7581) | White (AN7583) |
|---|---|---|
| Flash install | Yes, from the stock web page | No, signed FIT blocks it |
| RAM boot | Yes, kernel 6.18 | Yes, kernel 6.18 |
| WAN | Yes, 2.5G. 935 Mb/s routed, limited by the 1G LAN port; peak not measured | 2x 2.5G (EN8811H) in the device tree |
| LAN | LAN2-4 1G. LAN1 2.5G linked and passed traffic on a RAM image | 1G switch LAN2-4 |
| Hardware offload | Yes, wired and Wi-Fi through the NPU; 0 interrupts at 935 Mb/s | Not tried |
| Pi-hole, WireGuard, DDNS, UPnP, usteer | Yes, the same packages as the GN630V | Not tried |
| Wi-Fi | Yes, Wi-Fi 7, 160 MHz. 867 down, 647 up on an iPhone | PCIe link not up yet |
| USB, LEDs, buttons | Yes | Yes |
| GPON | Registered and passed traffic on a real line on 31 Oct, earlier build; not retested on this image | Not tried |

Hardware details: [docs/HARDWARE.md](docs/HARDWARE.md).

## Layout
- `white/`: the AN7583 port. `an7583-skyworth-sk-g7220.dts`, `02_network` (from `target/linux/airoha/an7583/base-files/etc/board.d/`), `boot_runner.py` (handles the U-Boot login, PCIe register writes and TFTP RAM boot; the password comes from `UBOOT_PWD`), `uboot-login.sh`, the minimal `ramtest/` DTS and FIT, and the bring-up log in `BRINGUP.md`.
- `black/`: the EN7581 port. The device tree (`en7581-skyworth-sk-g7220.dts`, with the stock tree `stock-fdt.dts` as reference), kernel patches, `build.sh`, `config.seed` and the flash image tools (`mk_flash_image.sh`, `mk_tclinux.py`, `check_tclinux.py`). `mk_tclinux.py` also needs the 0x2000 prefix from a stock image, which isn't in this repo.
- `tools/`: `uart.py` (UART logger that stops autoboot and takes commands from a FIFO), `serial_cmd.py`, `stock-backup.sh` (read-only partition dump over SSH from stock).
- `docs/`: hardware notes for both boards and the RAM-boot procedure.
- `white/openwrt-an7583.patch`: the device profile and board.d changes for the OpenWrt tree.
- The AlphaWRT packages (`alphawrt-ui`, `alphawrt-pihole`, `luci-theme-alphawrt`, ...) are not copied here. The build takes them all from the GN630V repo, so both boxes get the same features. `bridger` is left out on the Black until it's ported.

Run the serial scripts from this repo's root. Logs, `cmd.in`, dumps and TFTP files go in `backup/`, which git ignores.

## License
GPL-2.0, see [LICENSE](LICENSE).
