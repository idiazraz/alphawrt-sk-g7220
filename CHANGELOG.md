# Changelog

Every AlphaWRT release for the Skyworth SK-G7220 Black, newest first, in plain words. The full notes for each release (downloads, what was tested) are on the [releases page](https://github.com/idiazraz/alphawrt-sk-g7220/releases).

The web UI, Pi-hole, Wi-Fi and VPN packages are shared by every AlphaWRT model and come from the [GN630V](https://github.com/idiazraz/gn630v-alphawrt) project. The shared changes the Black carries are listed here too.

How this file is kept:
- Every change a user or tester would notice gets a line under **Unreleased**, in the same commit as the change.
- The groups are **Added**, **Changed**, **Fixed** and **Known issues**. Lines say what the user sees, not how the code does it. A line ends with the GitHub issue it closes, if any.
- At a release, **Unreleased** becomes `## <version> (<date>)`, and the release notes' "What's new" section is copied from it.

## Unreleased

### Added
- **Tailscale**, with a Tailscale card on the VPN page.
- **Block a device's internet** from the Devices page: tap a device and switch on "Block its Internet". It stays on Wi-Fi and the home network, but can't reach the internet until you unblock it. Not in bridge mode.
- **Network page:** this box's address and DHCP range, where names are looked up (DNS), IPv6, local names and port forwards, all in one place.
- **DNS choice:** encrypted DNS (the default), your provider's DNS, or servers you pick. Pi-hole keeps working with any of them.
- **IPv6 card** on the Network page.
- **Crash log kept across a reboot:** if the box restarts after a crash, the kernel's last messages are still there after the reboot.
- **Kernel modules for zapret and SQM:** NFQUEUE, CAKE and IFB are now included, so both can be installed. SQM only shapes traffic the hardware packet engine doesn't handle; turn offload off if you want it to shape everything ([#4](https://github.com/idiazraz/gn630v-alphawrt/issues/4)).

### Changed
- **Fibre traffic goes through the hardware packet engine:** wired IPv4 and IPv6 routing over fibre is offloaded, so the CPU stays nearly idle under load. Wi-Fi traffic still goes through the CPU path.
- **Pi-hole catches devices with their own DNS:** with Pi-hole on, devices that set their own plain DNS server are sent to the box anyway, and browsers are told to fall back to it. Devices with strict encrypted DNS (for example Android Private DNS set to dns.google, or an iPhone DNS profile) keep working. Blocking encrypted DNS as well is a switch on the Pi-hole page, "Stop devices skipping Pi-hole", off by default.
- **Every page tidied** on desktop and phone: the VPN page uses the same cards as the rest, Fibre charts are readable on a phone, and notes have an info icon.
- **Home** names the encrypted DNS servers, and the **Wi-Fi page** points printers and older devices to WPA2 only.

### Fixed
- **Unifi (TM) fibre: no internet, the line registers but never gets service.** The box now tells the provider's equipment about every kind of setting the stock firmware supports, so TM's Nokia equipment no longer stops before setting up the internet connection. Not yet confirmed on a Unifi line.
- **Network page could show only "Something went wrong"** after an upgrade, when a port forward had been made in Advanced (LuCI). The page now opens and lists that forward.
- **Fibre downloads stalled to a crawl** with hardware offload on. Hardware offload is now on by default on fibre too.
- **WireGuard could never be set up:** the VPN page sent you back to the login screen.
- **Guest Wi-Fi had no internet:** with Pi-hole on, guest devices got no DNS server.
- **Renaming many devices stopped the internet** until a reboot: the DNS and DHCP service gave up restarting. It now always comes back.

### Known issues
- The TEL (phone) port doesn't work yet: its chip isn't identified.
- Combo and Bridge modes don't get hardware-offloaded bridging yet.

## black-2026-11-02c (2026-11-02)

### Added
- **The same packages as the GN630V:** Pi-hole ad blocking, WireGuard, dynamic DNS, UPnP, Wi-Fi band steering, policy routing and the Prometheus node exporter.

### Known issues
- GPON on a real line and LAN1 at 2.5G weren't tested on this image. GPON registered and passed traffic on a real line with an earlier build.
- A real WireGuard tunnel wasn't tested, and setting one up from the VPN page doesn't work (fixed in Unreleased).

## black-2026-11-02b (2026-11-02)

### Fixed
- **2.5G WAN carried no traffic on a freshly installed box:** the box now sets the board's WAN/fibre switch itself instead of relying on the bootloader setting.

## black-2026-11-02 (2026-11-02)

### Added
- **First public image:** installs from the stock firmware upgrade page, and keeps stock in the other firmware bank.
- **Fibre (GPON) or 2.5G WAN**, chosen at boot. Router in Quick Setup picks the WAN port.
- **Simple UI** with Quick Setup, and LuCI under Advanced.
- **Hardware offload** for wired routing, and **Wi-Fi 7** through the network processor. 5 GHz runs at 160 MHz.
- LEDs, buttons and USB work.

### Known issues
- On a freshly installed box the 2.5G WAN carries no traffic (fixed in black-2026-11-02b).
- The root password is blank until you set one in Quick Setup.
