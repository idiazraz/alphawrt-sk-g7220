# SK-G7220 Black: TEL (FXS) port

Desk findings, 2026-11-04. Nothing built or run on the board yet.

## What stock tells us

| Item | Finding | Source |
|---|---|---|
| Lines | 1 FXS, 0 FXO (`FxsNum '1'`) | stock `/etc/config/skyworth_user_config` |
| PCM block | `pcm@bfbd0000`, `econet,ecnt-pcm`, reg `0x1fbd0000`, GIC SPI 27 | stock FDT (`backup/ref/fdt-black.dts`) |
| `voip_hook` | GPIO 23, in `gpio-leds`: the VoIP **LED**, not a hook input | stock FDT, `HARDWARE.md` |
| SLIC | **Not identified.** Stock `voip_loader` autodetects at boot: ZSI (Zarlink/Microchip `zl88601`, `le9642`...), then ISI (Silabs `si32192`, `si32185`...), then CSI (Lantiq/MaxLinear `pef3xxxx`). The FDT and the configs name no part. | `userfs/bin/voip_loader` strings |
| Bus | ISI, ZSI or CSI over the PCM pins (follows from the part). Stock `spi.ko` resets the SLIC by GPIO from the DTS/led.conf, which this FDT doesn't carry. | stock modules |
| Stock modules | `pcm1 spi slic3{,_silicon,_intel} fxs3{,_silicon} DSPCore ovdsp lec acodec_x ortp ksocket foip sys_mod`, kernel 5.4.55. Won't load on 6.18. | stock rootfs |
| DC-DC BOM | Unknown. The Silabs module has no BOM string. | |

## Pins (AN7581, kernel `pinctrl-airoha.c`)

- `pcm_spi`: pins 18-25 (GPIO 5-12). `pcm_spi_cs1`: pin 43 (GPIO 30). INT pin 14 (GPIO 1), RST pin 15 (GPIO 2).
- The Black uses GPIO 0, 17-20, 22, 23, 25, 27, 33, 42. No overlap with `pcm_spi` or CS1.
- GPIO 2 is in the Black's `mdio_pins`. The Gemtek XG2010G has the same overlap: its ISI node uses the SCU reset sequence and claims only `pcm_spi` and `pcm_spi_cs1`, not INT/RST.
- RAM is 1 GiB at `0x80000000`, inside the PCM DMA window (bit 31 set, 30-bit payload).

## Driver: airoha_voip on EN7581

- Upstream Sirherobrine23/airoha_voip (`c2748c1`) has no EN7581 compatibles. It knows EN7581 pin and SCU layout in its docs only.
- **Precedent:** naoki66/ImmortalWrt-for-Gemtek-brightspeed, `package/kernel/airoha-voice`. Pins airoha_voip `4222576`, adds `airoha,en7581-pcm` and `airoha,en7581-isi-spi` (patch 010), plus slot skew, gain and routing fixes. On the XG2010G (AN7581 + Si32192 over ISI) it has: `REG0=0xaa`, `ProSLIC_Init ret=0`, hook, ring, clean playback (`playback_slot_adj=1`), capture at `txgain_db=-13`, and SIP calls through Asterisk. Working values: `0x1fa20218 = 0x00031000`, `0x1fa201d0 = 0x00000c01`.
- Its DTS nodes (`an7581-gemtek-xg2010g-ubi.dts`) are the template for the Black if the part is ISI.
- Also built for AN7581 6.18.55 in Sirherobrine's AN7581 image: `en75xx-pcm`, `en75xx-isi-spi`, `en75xx-zsi`, `en75xx-slic-le9642` load with no DT node (`backup/sirherobrine-an7581-initramfs-ramboot.log`).
- **Supported parts:** Si32192/Si3219x (ISI, BOM `lcqc` only), Le9642/Le9641 (ZSI), MaxLinear DXS (CSI). An Si3218x/Si3217x/Si3228x or Zarlink zl88601 would need new driver work.
- **Licence:** the Si3219x driver compiles the Skyworks ProSLIC API (proprietary). Under rule 10 it goes in a gitignored folder that `build.sh` adds when present, never in the public repo.

## Char device (for baresip)

`/dev/en75xx-fxs0`, uapi `include/uapi/linux/en75xx_voice.h`, ABI 1, magic `'V'`.

- Audio: `read`/`write` 16-bit signed linear, 8 kHz mono, 80-sample frames (160 bytes, 10 ms).
- `poll`: `EPOLLIN` when a whole frame is queued, `EPOLLOUT` when a frame fits, `EPOLLPRI` on a line event (hook change). Read the new state with `GET_STATE`; that call clears the event.
- ioctls: `GET_INFO` (0x00), `GET_STATE` (0x01: hook, linefeed, ringing, faults), `SET_RING` (0x02: enable, cadence on/off ms), `SET_LINEFEED` (0x03: open/standby/active/reverse), `FLUSH` (0x04), `GET_STATS` (0x05), `SET_TONE` (0x06: two freqs, dBm, on/off ms), `SET_ALC` (0x07).
- No DTMF from the Si32192 (no hardware decoder): detect digits in software from the capture audio.

## Box test plan

The Black is the house router. Every step that reboots it needs the user's OK, a quiet hour, and the soak finished.

1. **Identify the part (no power to the line).** Best: during a quiet hour, power off, open the case, photograph the chip next to the TEL port and the DC-DC parts around it (inductor, MOSFET, diode). House offline about 15 min. Otherwise step 2 in identify-only mode.
2. **Probe by RAM boot (no flash write).** Build a test kernel with the voice nodes and the kmods from the gitignored folder. TFTP-boot it (`tools/run_ramboot.sh`, UART needed). A local probe-only patch stops after `REG0` is read, before `ProSLIC_Init` powers the DC-DC. Pass: `REG0=0xaa` (Si3219x, part 0x5). Other values name a different part: stop and rework. Power-cycle back to the installed AlphaWRT.
3. **Init, only if the part is Si3219x and the BOM matches LCQC.** Same RAM boot with init on: `ProSLIC_Init ret=0`, VBAT about 59 V, LB cal OK. Phone on TEL: hook, `ring`, tone, loopback. Watch for heat or whine at the DC-DC; stop if either.
4. **Image.** Once it works by RAM boot: add the DTS nodes and `alphawrt-voice` to the Black seed, the kmods via the `build.sh` proprietary hook, build, flash with the user's OK.
