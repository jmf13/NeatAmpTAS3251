| Target | ESP-IDF |
| ------ | ------- |
| ESP32-S3 (ESP32-S3-WROOM-1U-N8R8) | 6.1 |

# Tas — ESP32-S3 Controller Firmware

ESP32-S3 firmware for the [NeatAmpTAS3251](../README.md) Class-D amplifier
board: a C++ class-based driver stack (see
[Firmware Architecture](#firmware-architecture) below) that sequences the
power rails, brings the TAS3251 out of reset, configures it over I2C, and
monitors /FAULT, /CLIP_OTW and the 13.2V rail — see
[ESP32-S3 Hardware IO](#esp32-s3-hardware-io) for the underlying pin map.

This firmware targets the ESP32-S3 only — the board and this project are not
built for any other Espressif chip.

## Installing ESP-IDF (macOS, command line)

ESP-IDF is installed with the ESP-IDF Installation Manager (`eim`). The
command-line `eim` is more reliable than the GUI app, which ignores the shell
`PATH` and may fail to find a suitable Python.

**Prerequisite — Python 3.10 to 3.13.** `eim` runs a Python sanity check and
refuses to install with anything outside that range. Homebrew's default
`python3` may be newer (e.g. 3.15) and will fail with `[FAIL] Python Version`.
Install a supported version alongside it and put it first on the `PATH` for the
shell used to run `eim`:

```sh
brew install python@3.13 espressif/eim/eim
export PATH=/opt/homebrew/opt/python@3.13/libexec/bin:$PATH
python3 --version   # must print 3.13.x
```

Use `libexec/bin`, not `bin`: only `libexec/bin` provides the unversioned
`python3`/`python` names that `eim` looks up. `eim` itself only needs to be
reachable from that shell, so the default `python3` does not have to be changed
system-wide.

Then install ESP-IDF for the ESP32-S3 (this clones ESP-IDF and downloads the
toolchains into `~/.espressif`, several GB; run it from a scratch directory
because `eim` can drop an `eim_config.toml` into the current directory):

```sh
eim install -n true -t esp32s3 -i v6.1
```

When it finishes it prints the activation command, which is used in each new
shell (see [Local setup](#local-setup)):

```sh
source ~/.espressif/tools/activate_idf_v6.1.sh
```

Verified: `idf.py set-target esp32s3 && idf.py build` completes on ESP-IDF
6.1 with this setup.

## Local setup

The repository uses a local Python virtual environment for project-side Python
commands. Create it once from the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Initialize the ESP-IDF toolchain in each new shell. This sets `IDF_PATH`, adds
`idf.py` to `PATH`, and selects the ESP-IDF tools and its compatible managed
Python environment required by the build:

```sh
source ~/.espressif/tools/activate_idf_v6.1.sh
```

This script is created by `eim` (see
[Installing ESP-IDF](#installing-esp-idf-macos-command-line)); ESP-IDF itself
lives in `~/.espressif/v6.1/esp-idf`. Adjust the version in the file name if
you installed a different one.

Run the ESP-IDF commands after activation; ESP-IDF may replace the active
`.venv` interpreter with its managed environment so all ESP-IDF dependencies
match the installed ESP-IDF release.

Select the target and build:

```sh
idf.py set-target esp32s3
idf.py build
```

The generated `build/compile_commands.json` is used by clangd and C/C++
IntelliSense. Keeping the project build configured ensures ESP-IDF headers
such as `esp_system.h` and `esp_flash.h` resolve without missing-include
warnings.

`sdkconfig.defaults` sets the flash size (8 MB) and PSRAM (8 MB **Octal**) to
match the ESP32-S3-WROOM-1U-N8R8 module actually used on this board. Octal
PSRAM claims GPIO35/36/37 (module pins 28/29/30) internally — see
[Reserved pins](#reserved-pins-do-not-use) below.

> **Existing `sdkconfig` after pulling the Octal PSRAM change:**
> `sdkconfig.defaults` only seeds a *new* `sdkconfig`; an existing one keeps
> `CONFIG_SPIRAM_MODE_QUAD=y`. Either delete `sdkconfig` and run
> `idf.py reconfigure`, or set *Component config → ESP PSRAM → SPI RAM
> config → Mode (QUAD/OCT) of SPI RAM chip in use* to **Octal Mode PSRAM**
> in menuconfig. Check with `grep SPIRAM_MODE sdkconfig`.

If a
fresh `sdkconfig` ever comes up as 2 MB flash / no PSRAM again (check the
boot log — see
[Chip and firmware info logging](#chip-and-firmware-info-logging) — or
`grep CONFIG_SPIRAM sdkconfig`), run `idf.py reconfigure`; if it's still
missing, confirm `esp_psram` is still in `main`'s `PRIV_REQUIRES` in
`main/CMakeLists.txt` — this project builds with `MINIMAL_BUILD ON`
(root `CMakeLists.txt`), which silently drops `CONFIG_SPIRAM` from the
Kconfig tree entirely if nothing depends on `esp_psram`.

The test dependencies are listed by `pytest_tas.py`. Install them into the
active virtual environment when PyPI access is available:

```sh
python -m pip install pytest pytest-embedded-idf pytest-embedded-qemu
python -m pytest -q pytest_tas.py
```

## Configuration (menuconfig)

The portable way to open the config menu, on any machine, once the toolchain
is exported as above:

```sh
idf.py menuconfig
```

### VSCode SDK Configuration Editor

If the ESP-IDF extension's "SDK Configuration Editor" (GUI menuconfig) does
not open, it is almost always because `.vscode/settings.json`'s
`idf.currentSetup` does not match an installation known to the ESP-IDF
Installation Manager (`eim`) on this machine. That setting must hold an
**install ID** (e.g. `esp-idf-<hash>`), not a filesystem path — a path there
looks plausible but silently fails to resolve.

To fix it on any machine after installing ESP-IDF via `eim`:

```sh
cat ~/.espressif/tools/eim_idf.json
```

Copy the `idfSelectedId` value (or the `id` of the entry matching the ESP-IDF
version you want) into `.vscode/settings.json`:

```json
"idf.currentSetup": "esp-idf-<hash-from-eim_idf.json>"
```

This ID is generated per machine by `eim`, so it will differ on every
computer — re-run this step after cloning the repo onto a new machine or
after reinstalling ESP-IDF. Reload the VSCode window afterwards.

`idf.port` in the same file is also machine-specific (the serial device path
of the connected board): `/dev/tty.usbmodem*` on macOS, `/dev/ttyUSB*` or
`/dev/ttyACM*` on Linux, `COM*` on Windows. Update it to match your board
before flashing or monitoring from VSCode.

## Debugging (OpenOCD)

The `gdbtarget` debug configuration in `.vscode/launch.json` has
`runOpenOCD` default to `true` (see the extension's `package.json`), so
**every** "Start Debugging" tries to spawn a fresh OpenOCD server. If a
previous session was force-stopped, crashed, or otherwise didn't shut its
OpenOCD process down cleanly, that old server keeps holding ports 3333
(GDB), 4444 (telnet) and 6666 (Tcl) — the new one then fails to bind them,
which is what "server already started" / can't-start-debug means.

`.vscode/launch.json`'s debug configuration now runs a `preLaunchTask`
("Reset OpenOCD", defined in `.vscode/tasks.json`) before every debug
session, which kills any leftover OpenOCD process first
(`pkill -f 'bin/openocd'` on macOS/Linux, `taskkill /IM openocd.exe` on
Windows) so the new one always gets a clean set of ports. If you ever need
to do this by hand instead: **Terminal → Run Task… → Reset OpenOCD**, or
directly:

```sh
pkill -f 'bin/openocd'    # macOS / Linux
```

### Debug launches an old binary / doesn't flash first

The `gdbtarget` `attach` config's `buildFlashMonitor` option (build, flash
and monitor before attaching) defaults to `false`. With it unset, clicking
Debug just attaches GDB via OpenOCD to **whatever is already on the
chip** — it does not build or flash your current source first. If the
serial log shown by a debug/monitor session doesn't match your code (e.g.
still shows the stock `hello_world` example, an old project name, or an old
compile timestamp in the `app_init:` banner lines — see
[Chip and firmware info logging](#chip-and-firmware-info-logging) below for
where to check that), this is almost always why: the board was never
actually reflashed with the current build, only attached to.

`.vscode/launch.json`'s debug configuration now sets `"buildFlashMonitor":
true`, so every Debug launch builds, flashes and monitors before attaching.
If you ever want to attach without reflashing (e.g. to inspect a crash
without touching the board's current state), temporarily set it back to
`false` for that session, or flash explicitly first instead:

```sh
idf.py -p PORT flash
```

## ESP32-S3 Hardware IO

The firmware pin definitions are kept in [tas_pins.h](main/tas_pins.h). GPIO
configuration and default power-up states are owned by
[PowerSupplies](main/power_supplies.cpp) and [Tas3251](main/tas3251.cpp) (see
[Firmware Architecture](#firmware-architecture)); the shared I2C master bus
(`I2C_NUM_0`, 400 kHz) is created by [I2cBus](main/i2c_bus.cpp).

| Signal | ESP32-S3 IO | Direction / interface | Purpose | Jumper needed |
|--------|-------------|-----------------------|---------|---------------|
| I2C SDA | IO0 | I2C data | Shared I2C data line for TAS3251 and optional ADAU1466 | No |
| I2C SCL | IO45 | I2C clock | Shared I2C clock line for TAS3251 and optional ADAU1466 | No |
| AMP RESET | IO42 | GPIO output | Releases or holds the TAS3251 in reset; active low | Yes — U14 pins 5-6 (IO42 to TAS_RESET) |
| DAC MUTE | IO1 | GPIO output | Hardware mute control for the TAS3251; active low | Yes — U14 pins 1-2 (IO1 to TAS_MUTE) |
| AMP FAULT | IO41 | GPIO input / interrupt | Receives latched TAS3251 fault indications | Yes — U14 pins 7-8 (IO41 to TAS_FAULT) |
| AMP CLIP/OTW | IO2 | GPIO input / interrupt | Receives clipping or over-temperature warning indications | Yes — U14 pins 3-4 (IO2 to TAS_CLIP) |
| AMP ADDRESS | IO12 | GPIO input | Reads the TAS3251 ADR strap state for I2C address selection | Yes — H2 pins 13-14 (TAS_ADR to ESP_TAS_ADR) |
| GOOD 13.2V | IO39 | GPIO input | Confirms that the 13.2 V intermediate rail is ready through jumper U15 | Yes — U15 pins 5-6 (IO39 to GOOD_13.2V) |
| ENABLE 12V | IO38 | GPIO output | Enables the 12 V GVDD analog supply after 13.2 V is good through jumper U15 | Yes — U15 pins 7-8 (IO38 to ENABLE_12V) |
| ENABLE 3.3V analog | IO40 | GPIO output | Enables the isolated 3.3 V analog rail for TAS3251 DAC_AVDD | Yes — U15 pins 3-4 (IO40 to ENABLE_3.3V) |
| STATUS LED SDI | IO8 | GPIO output (bit-banged) | SK9822 data into U8 SDI via R18 | V1.0/V1.1: rework, see [V1.0/V1.1 rework checklist](#hardware-v10v11-rework-checklist-before-first-power-up). V1.2: no |
| STATUS LED CKI | IO9 | GPIO output (bit-banged) | SK9822 clock into U8 CKI via R17 | V1.0/V1.1: rework, see [V1.0/V1.1 rework checklist](#hardware-v10v11-rework-checklist-before-first-power-up). V1.2: no |

Header U14 (2x4, 2.54 mm) carries the amplifier control/status lines between
the ESP32-S3 and the TAS3251, and header U15 (2x4, 2.54 mm) carries the power
sequencing lines between the ESP32-S3 and the rail-good/enable signals; on
both, each ESP32-S3 GPIO net and its counterpart signal are broken out to
adjacent pins in the same column so that a 2-pin shunt bridges them. Header
H2 (2x12) is the main board-to-board connector, and only its pins 13-14 need
a jumper to route the TAS3251 ADR strap to the ESP32-S3. None of these
headers ship with shunts populated by default, so populate the pin pairs
above per the current firmware pin mapping in [tas_pins.h](main/tas_pins.h)
before relying on these signals; per the netlist
(`Netlist_Class_D_amp_2026-07-23.enet` at the repository root), leaving a
pair open floats that signal instead of connecting it.

As the very first action of `SystemController::startup()` (`Tas3251::assertSafeState()`,
also called again as part of `Tas3251::init()`'s own GPIO configuration),
RESET_AMP and DAC_MUTE are driven to their safe defaults — reset asserted,
muted, together, since both are active low — before any other peripheral is
touched; both the 12 V and 3.3 V analog rails start disabled. `startup()`
then runs the sequence in [Firmware Architecture](#firmware-architecture) to
bring everything up in order. The I2C lines rely on the board-level 6.8 kOhm
pull-ups.

### Reserved pins (do not use)

| Module pin | ESP32-S3 IO | Reserved for | HW V1.0/V1.1 (wrong) | HW V1.2 |
|------------|-------------|--------------|----------------------|---------|
| 28 | IO35 | Octal PSRAM (internal, N8R8) | SW2 + C51 (100 nF) to GND, TP12 | Not connected (SW2 → IO10, R51 pull-up) |
| 29 | IO36 | Octal PSRAM (internal, N8R8) | R18 → `L_SDI` (status LED data) | Not connected (`L_SDI` ← IO8) |
| 30 | IO37 | Octal PSRAM (internal, N8R8) | R17 → `L_CKI` (status LED clock) | Not connected (`L_CKI` ← IO9) |
| 13 / 14 | IO19 / IO20 | USB D− / D+ (native USB-Serial-JTAG) | R16 / R15 → USB-C | unchanged |
| 36 / 37 | RXD0 / TXD0 | UART0 console / ROM download | H2 pin 5 / H2 pin 3 | unchanged |

`L_SDI` / `L_CKI` are the V1.0/V1.1 net names. In the V1.2 netlist these
nets are unnamed (`$4N…`), but they connect the same parts (R18 → U8 SDI,
R17 → U8 CKI).

`tas_pins.h` contains a `static_assert` that fails the build if any pin
macro is set to IO35-IO37 while `CONFIG_SPIRAM_MODE_OCT` is enabled.

Strapping pins IO0 (I2C SDA, 6.8 kΩ pull-up → normal SPI boot), IO3 and
IO46 (H2 pins 4/6) also need care. Do not load them in a way that changes
their level at reset.

### Key SW configuration (`sdkconfig.defaults`)

| Setting | Value | Why |
|---------|-------|-----|
| `CONFIG_ESPTOOLPY_FLASHSIZE_8MB` | `y` | N8R8 has 8 MB (Quad) flash |
| `CONFIG_SPIRAM` | `y` | Enable the 8 MB PSRAM |
| `CONFIG_SPIRAM_MODE_OCT` | `y` | N8R8 PSRAM is **Octal**. Quad mode fails PSRAM init. This mode is why IO35-IO37 are reserved |
| `CONFIG_SPIRAM_SPEED_80M` | `y` | Max reliable PSRAM clock for this module |
| `MINIMAL_BUILD` (root `CMakeLists.txt`) | `ON` | `esp_psram` must stay in `main`'s `PRIV_REQUIRES`, or `CONFIG_SPIRAM` disappears |

## Potential DSP (ADAU1466) Connectivity

The board breaks out a DSP interface on connector U10 (1x6, 2.54 mm) for a
future ADAU1466 DSP module. RESET and SELFBOOT are direct GPIO connections;
the I2C lines join the shared TAS3251 bus through 22 Ohm series resistors
rather than a separate bus.

| Signal | ESP32-S3 IO | U10 pin | Direction / interface | Purpose | Jumper needed |
|--------|-------------|---------|-----------------------|---------|---------------|
| DSP_RESET | IO47 | 3 | GPIO output | Resets the ADAU1466 DSP | No |
| DSP_SELFBOOT | IO48 | 6 | GPIO output | Sets the ADAU1466 self-boot mode strap | No |
| DSP SDA | IO0 | 4 | I2C data | Joins the shared I2C data line via 22 Ohm series resistor R19 | No |
| DSP SCL | IO45 | 5 | I2C clock | Joins the shared I2C clock line via 22 Ohm series resistor R20 | No |

U10 pins 1 and 2 carry GND and 3.3V respectively for powering the DSP module.

## Firmware Architecture

The firmware is C++ (`gnu++26`, exceptions and RTTI disabled per
`sdkconfig`, matching the rest of ESP-IDF). Each hardware concern is owned by
one class; `tas_pins.h` remains the single source of truth for GPIO numbers.

| Class | Files | Owns |
|-------|-------|------|
| `tas::I2cBus` | [i2c_bus.hpp](main/i2c_bus.hpp) / [.cpp](main/i2c_bus.cpp) | The shared I2C master bus (SDA/SCL), device attach/probe |
| `tas::Tas3251` | [tas3251.hpp](main/tas3251.hpp) / [.cpp](main/tas3251.cpp) | RESET_AMP, DAC_MUTE, /FAULT + /CLIP_OTW IRQs, AMP ADDRESS strap, book/page I2C register access |
| `tas::Dsp` | [dsp_adau1466.hpp](main/dsp_adau1466.hpp) / [.cpp](main/dsp_adau1466.cpp) | DSP_RESET, DSP_SELFBOOT, I2C presence probe for the optional ADAU1466 |
| `tas::PowerSupplies` | [power_supplies.hpp](main/power_supplies.hpp) / [.cpp](main/power_supplies.cpp) | GOOD_13.2V sense, ENABLE_12V, ENABLE_3.3V analog |
| `tas::I2sBus` | [i2s_bus.hpp](main/i2s_bus.hpp) / [.cpp](main/i2s_bus.cpp) | ESP-IDF I2S std-mode TX channel for the shared TAS3251/DSP audio bus |
| `tas::StatusLed` | [status_led.hpp](main/status_led.hpp) / [.cpp](main/status_led.cpp) | Bit-banged SK9822 (APA102-compatible) driver for the U8/U9 status LED chain |
| `tas::SystemController` | [system_controller.hpp](main/system_controller.hpp) / [.cpp](main/system_controller.cpp) | Startup sequencing, fault/clip handling, and the steady-state monitor loop, composing the classes above |

`main/tas_main.cpp` (`app_main`) only constructs a `SystemController` and
calls `startup()` then `runForever()`.

⚠️ **`I2sPins` in `i2s_bus.hpp` has no wired GPIOs on the current board.**
Per `Netlist_Class_D_amp_2026-07-23.enet` (repository root), connector U11
(MCLK/LRCK/SCLK/SDIN) only reaches the TAS3251 — the ESP32-S3 has no *PCB*
net in common with the I2S bus on this revision, despite the top-level
README's "ESP32-S3 directly (for testing/streaming)" bullet. `I2sBus` is a
working scaffold for a future revision (or rework) that does wire it up; it
isn't used by `SystemController` yet. See
[I2S Test Tone (H2-to-U11 Patch)](#i2s-test-tone-h2-to-u11-patch) below for a
way to exercise it today with a manual patch instead of a board respin.

### Startup sequence

`SystemController::startup()` runs the following states, logging each
transition at `ESP_LOGI` and any failure at `ESP_LOGE` (aborting the sequence
on failure, leaving the amplifier held in reset and muted):

```
AMP_RESET               → RESET_AMP asserted, DAC_MUTE asserted together (both active low),
                           as the very first action of startup(), before any other peripheral
INIT                    → status LED (blue), I2C bus, GPIOs, /FAULT + /CLIP_OTW IRQs, DSP probe
WAIT_POWER_STABLE       → 2 ms delay (see ⚠️ below)
CHECK_13V2              → poll GOOD_13.2V; abort if not good
ENABLE_12V              → enable the 12V GVDD analog rail
ENABLE_3V3_ANALOG       → enable the 3.3V analog (DAC_AVDD) rail
WAIT_PRE_RESET_RELEASE  → 5 ms delay (see ⚠️ below)
MUTE_I2C                → mute both DACs over I2C (B0-P0-R3, bit0 left + bit4 right) —
                           RESET_AMP is still asserted at this point
CONFIGURE               → placeholder for DSP config (EQ/crossover) and volume setup —
                           not implemented yet, see ⚠️ below
DSP_STANDBY             → bring the DSP out of standby (B0-P0-R2 DEVICE_CTRL_2, bit7 DSPR = 1)
WAIT_BEFORE_UNMUTE      → 200 ms delay
UNMUTE                  → DAC_MUTE released
WAIT_BEFORE_RESET_RELEASE → 205 ms delay
RELEASE_RESET           → RESET_AMP released, audio path active
READY                   → status LED (green), hand off to runForever()
```

Any failure along the way aborts the sequence, sets `SystemController::status()`
to `StartupFailed`, and turns the status LED amber (see
[Status LED (U8/U9)](#status-led-u8u9) below) — the amplifier stays held in
reset and muted.

`SystemController::runForever()` then polls `/FAULT`, `/CLIP_OTW` and
GOOD_13.2V every 50 ms, logging state changes and reacting to `/FAULT` and
`/CLIP_OTW` as described in [Status LED (U8/U9)](#status-led-u8u9).

⚠️ **Open questions carried over from architecture review, marked `TODO` in
the code (`system_controller.cpp`, `tas3251.hpp`) — verify against the actual
TAS3251 datasheet before trusting them in the field:**

- The 2 ms `WAIT_POWER_STABLE`, 5 ms `WAIT_PRE_RESET_RELEASE`, 200 ms
  `WAIT_BEFORE_UNMUTE` and 205 ms `WAIT_BEFORE_RESET_RELEASE` delays come
  from the hardware bring-up spec. If `GOOD_13.2V` already guarantees the
  rails have settled, `WAIT_POWER_STABLE` may be unnecessary.
- Whether the 3.3V analog (AVDD) rail must be enabled a fixed time
  before/after the 12V (GVDD) rail, rather than immediately after it as
  implemented, is unconfirmed.
- `CONFIGURE` (DSP config / volume setup) is a placeholder today —
  `SystemController::startup()` does not write any EQ/crossover coefficients
  or set a startup volume between muting the DACs and bringing the DSP out
  of standby. `Tas3251::setVolumeDb()`'s dB-to-register-code formula also
  follows a common TI PurePath convention but is **unverified for TAS3251
  specifically** — confirm against the datasheet before writing arbitrary
  volumes in the field.
- `Dsp`'s placeholder I2C address (`0x38`) is unconfirmed; harmless today
  since no board has the ADAU1466 populated.

### Status LED (U8/U9)

U8 and U9 are SK9822 (APA102-compatible) addressable RGB LEDs, chained in
series and driven from the ESP32-S3 over a bit-banged two-wire link:
IO8 → `L_SDI` (data, into U8) and IO9 → `L_CKI` (clock); U8's
CKO/SDO feed U9's CKI/SDI. HW V1.0/V1.1 drove these from IO36/IO37 through
R18/R17, which collides with the Octal PSRAM. On those boards the LEDs only
work after the [V1.0 rework](#hardware-v10v11-rework-checklist-before-first-power-up).
HW V1.2 routes IO8/IO9 directly. This is **not** a WS2812B (single-wire) — see the
correction in the top-level [README.md](../README.md#visual-indicators).
`tas::StatusLed` treats the chain as two independently-addressable LEDs and
gives them different jobs:

- **LED 0 (U8) — persistent `SystemController::Status`:**

  | Status | Color | Meaning |
  |--------|-------|---------|
  | `Booting` | Blue | `startup()` is running |
  | `Ready` | Green | Startup succeeded; amp unmuted, nominal volume |
  | `Fault` | Red | `/FAULT` latched; amp muted at low volume (see below) |
  | `StartupFailed` | Amber | `startup()` aborted before reaching `Ready` |

- **LED 1 (U9) — transient `/CLIP_OTW` indicator:** off normally; flashes
  amber for ~120 ms each time `/CLIP_OTW` fires, then returns to off. Purely
  a visual cue — it does not reflect or change `Status`.

**Fault vs. clip handling** (`SystemController::handleFault()` /
`handleClipOtw()`, called from `runForever()`):

- **`/FAULT`**: logs the latched fault bytes (B0-P0-R94/R95), re-asserts
  `DAC_MUTE` and sets both channels to the same conservative low volume used
  at startup, sets `Status` to `Fault` (LED 0 red), and **stays there** —
  there's no automatic recovery yet (see the `TODO` in
  `SystemController::handleFault()` and the existing "Fault Handling"
  section in the top-level README for the intended recovery policy: wait for
  thermal recovery, then toggle `RESET_AMP`).
- **`/CLIP_OTW`**: logs only (`ESP_LOGW`) and flashes LED 1 — no mute, no
  volume change, no `Status` change. This is a deliberate design choice:
  clipping is common/non-latching and shouldn't itself silence the amp,
  unlike a real `/FAULT`.

### Chip and firmware info logging

Before the `INIT` state, `startup()` logs everything readily available about
the running chip and firmware image at `ESP_LOGI`: target/core
count/silicon revision/radio features, flash size and type, WiFi-STA MAC
address, current and minimum-ever free heap, the firmware's project
name/version/build timestamp/ESP-IDF version (from `esp_app_get_description()`,
i.e. this project's actual name/version, not a stale one), and the reason
for the last reset (power-on, software, watchdog, brownout, etc.). This is
the first thing to check in a serial capture — the project name and compile
timestamp there is the ground truth for what's actually running on the
board, e.g. if it still says `hello_world` instead of `tas`, the board was
never flashed with this project's build; see
[Debug launches an old binary / doesn't flash first](#debug-launches-an-old-binary--doesnt-flash-first)
above.

### Generating documentation

All classes are commented for Doxygen (`@file`/`@brief`/`@param`/`@return`/
`@note`/`@warning`). Generate HTML docs from the `tas/` directory:

```sh
doxygen Doxyfile
open docs/html/index.html
```

## I2S Test Tone (H2-to-U11 Patch)

**Status: proposed / not yet implemented in firmware.** This is a bring-up
idea for exercising the audio path without a board respin, recorded here
before writing the code.

Connector H2 (2x12, the main board-to-board header) breaks out several
ESP32-S3 GPIOs that this firmware does not otherwise use. Checked against
`Netlist_Class_D_amp_2026-07-23.enet`, the following H2 pins are genuinely
spare (not assigned to any signal in [ESP32-S3 Hardware IO](#esp32-s3-hardware-io)
or [Potential DSP (ADAU1466) Connectivity](#potential-dsp-adau1466-connectivity)):

| H2 pin | ESP32-S3 IO | Notes |
|--------|-------------|-------|
| 16 | IO13 | free |
| 18 | IO14 | free |
| 20 | IO21 | free |
| 4 | IO3 | free, but an ESP32-S3 strapping pin (JTAG source select) — avoid |
| 6 | IO46 | free, but an ESP32-S3 strapping pin (ROM print control) — avoid |
| 7 | IO8 | V1.0/V1.1: **in use** after LED rework. V1.2: not connected |
| 8 | IO9 | V1.0/V1.1: **in use** after LED rework. V1.2: not connected |
| 10 | IO10 | V1.0/V1.1: free. V1.2: not connected (IO10 is the SW2 button) |
| 12 | IO11 | free |

Since connector U11 (the I2S input header, see
[Firmware Architecture](#firmware-architecture) above) only reaches the
TAS3251 and nothing else drives it, a user-installed patch from four of the
free H2 pins to U11 lets the ESP32-S3 act as a temporary I2S source for the
amplifier — no board respin needed:

| U11 pin | Signal | Patch to H2 pin | ESP32-S3 IO |
|---------|--------|------------------|-------------|
| 4 | LRCK (WS) | 18 | IO14 |
| 5 | SCLK (BCLK) | 16 | IO13 |
| 6 | SDIN (DOUT, ESP32 → TAS3251) | 20 | IO21 |
| 3 | MCLK | 12 | IO11 |
| 1 | GND | any H2 GND pin (15/17/19/21-24) | — |

⚠️ **Do not patch H2 to U11 while a DIR9001 module (or anything else) is also
connected to U11** — the ESP32-S3 would then be driving LRCK/SCLK/SDIN into
whatever else is driving those same lines.

### Planned firmware behavior

Once implemented: 5 seconds after `SystemController::startup()` reaches the
`READY` state (i.e. after the amplifier is configured and unmuted), the
firmware logs a new state (e.g. `TEST_TONE_START`) and starts writing a
continuous 1 kHz sine wave to both channels via `I2sBus::writeSamples()` —
same 16-bit/48 kHz stereo interleaved format `I2sBus` already assumes. This
would likely live in a small new class (e.g. `TestToneGenerator`) that owns
the sample buffer and reuses `I2sBus` rather than being folded into
`SystemController` directly, so it can be compiled out entirely once no
longer needed for bring-up.

## Project folder contents

```
├── CMakeLists.txt
├── Doxyfile                     Doxygen config (see Generating documentation above)
├── sdkconfig                    Board-specific build configuration (see Configuration above)
├── pytest_tas.py                 Automated test entry point
├── main
│   ├── CMakeLists.txt
│   ├── tas_main.cpp               App entry point (app_main)
│   ├── tas_pins.h                 GPIO/I2C pin definitions, single source of truth
│   ├── i2c_bus.hpp / .cpp          tas::I2cBus
│   ├── tas3251.hpp / .cpp          tas::Tas3251
│   ├── dsp_adau1466.hpp / .cpp     tas::Dsp
│   ├── power_supplies.hpp / .cpp   tas::PowerSupplies
│   ├── i2s_bus.hpp / .cpp          tas::I2sBus
│   └── system_controller.hpp / .cpp  tas::SystemController
└── README.md
```

## Troubleshooting

* Program upload failure

    * Hardware connection is not correct: run `idf.py -p PORT monitor`, and reboot your board to see if there are any output logs.
    * The baud rate for downloading is too high: lower your baud rate via [Configuration (menuconfig)](#configuration-menuconfig), and try again.


### Hardware V1.0/V1.1 rework checklist (before first power-up)

Known hardware issues on the built V1.0/V1.1 boards, and what to do about each
before the first power-up (details in
[hw_review_2026-11-06.md](../hw_review_2026-11-06.md)):

| # | Issue | Effect if not handled | Before power-up |
|---|-------|-----------------------|-----------------|
| 1 | **USB-C rotated 180°** (V1.0 only, fixed in V1.1) | No USB power, no native USB flashing, no JTAG | Nothing to rework. Flash over UART (section C) |
| 2 | **IO35/IO36/IO37 (module pins 28/29/30) used on an N8R8 module** (V1.0 and V1.1, fixed in V1.2). These pins belong to the internal Octal PSRAM. SW2/C51 sit on IO35; the SK9822 LEDs hang off IO36/IO37 via R18/R17 | PSRAM corruption, firmware crashes | **Rework**: steps A1–A5 |
| 3 | **ESP32 EN (CHIP_PU) has no pull-up**, only C48 1 µF + SW1 (review P0-1, all revisions) | EN floats: the ESP32 may not start, or resets at random | **Rework**: step A6 |
| 4 | **I²C on strapping pins IO0 (SDA) / IO45 (SCL)** (review P0-2, all revisions) | If the module's eFuse doesn't override the IO45 strap, flash/PSRAM get 1.8 V and the board doesn't boot (no damage) | **Check**: step 11a |
| 5 | **Inrush**: 3 × 2200 µF on PVDD behind fast-acting F1 (review P0-4) | Plugging into a stiff 36 V supply can blow F1 | **Procedure**: step 13 (current-limited supply). Optional rework: step P3 (time-lag fuse, as in V1.3) |
| 6 | **Q1 reverse-polarity FET is mounted the wrong way round** (source to input, drain to PVDD; review P0-6, fixed in the KiCad redraw) | Correct polarity works normally. A **reversed** supply is not blocked: Q1's body diode and D2 conduct and F1 must blow | **Procedure**: step 12a. Not reworkable on V1.0/V1.1 |
| 7 | **RESET_AMP and ENABLE_12V default to "on"** (R45 10 kΩ and R7 100 kΩ pull **up** to 3.3 V; review P0-7, fixed in V1.3) | For the ~0.3 s while the ESP32 boots, GVDD turns on and the power stage leaves reset with no configuration. Then the firmware resets it again. You hear a click or two at switch-on | Optional rework: step P1 |
| 8 | **No PVDD sense** (review P0-7, added in V1.3 on IO8) | At mains-off the firmware can't see PVDD falling, so the amp runs until GVDD collapses. You hear a thump at switch-off | Optional rework: step P2 (PVDD sense on IO4). Without it, use the soft-off procedure (step P4) |
| 9 | **C1 = 10 nF feed-forward cap on U1** (13.2 V buck), about 50× over the LMQ66430 limit of ~180 pF (review P0-5, DNP from V1.3) | U1 may not set up for the 13.2 V divider at start-up (wrong GOOD_13.2V rail voltage), or its control loop may be unstable or oscillate | **Rework**: step A7 |
| 10 | **No 1 µF ceramic at the TAS3251 PVDD pins 35/40** (nearest PVDD caps are 13–20 mm away; TAS3251 datasheet §8.3.1.2; fixed in V1.3 with C108/C109 on the bottom) | Output ringing at high PVDD and high power can exceed the SPK_OUT absolute maximum (50 V incl. peaks) and damage U12 | Bring-up at reduced PVDD and low volume is fine. **Before 35 V / high power**: rework step A8 |

The board works at the correct input voltage once items 2, 3 and 9 are reworked
and item 4 checks out. Do item 10 before running at full PVDD and high power. Items 1, 5 and 6 are handled by procedure, not
rework. Items 7 and 8 only affect switch-on and switch-off noise, not
function. Do the optional [pop-free rework](#optional-pop-free-rework-v13-equivalent)
if the board is used for firmware development, so the power sequencing code
behaves the same as on V1.3.

Do all of the steps below **before connecting the 36 V supply**. On V1.1,
do sections A and B, then flash over USB-C instead of section C.

#### A. Rework (soldering iron, board unpowered)

1. **Remove C51** (100 nF, across SW2). It loads the IO35 PSRAM line.
2. **SW2: remove it, or never press it.** Pressing it shorts a PSRAM line to
   GND and crashes the ESP32. The firmware does not use SW2 yet (on any
   revision). To make it work like V1.2 (optional), see
   [SW2 on IO10](#optional-sw2-on-io10-v12-equivalent) below.
3. **Remove R18 and R17** (27 Ω, 0402). This frees IO36/IO37 from the LED
   lines.
4. **Bodge the status LEDs to IO8/IO9** (the pins the firmware now uses):
   - H2 pin 7 (IO8) → R18 pad on the `L_SDI` side (continuity to U8 pin 1, SDI)
   - H2 pin 8 (IO9) → R17 pad on the `L_CKI` side (continuity to U8 pin 2, CKI)

   Use the pad that beeps to U8, **not** the one that beeps to the ESP32
   module (pins 29/30). Use short, thin wire (e.g. 30 AWG). This step is
   optional: if you skip it, the firmware still runs, but the status LEDs
   stay dark.
5. **Continuity check:**
   - No connection between H2 pin 7/8 and module pins 29/30.
   - No short between H2 pins 7 and 8.
   - No short from either pin to GND or 3.3V.
   - Nothing else is connected to H2 pins 7/8. They now carry the LED bus.
6. **Add the EN pull-up:** solder a **10 kΩ** (0402/0603) from **TP9** (EN)
   to the nearest 3.3V pad, for example C48's neighbourhood or any 3.3V test
   point. With the existing C48 1 µF this gives the RC reset delay Espressif
   recommends. Check: TP9 measures ~10 kΩ to 3.3V and does not beep to GND.
7. **Remove C1** (10 nF, 0402), the feed-forward cap across R3 (100 kΩ)
   between U1 pin 11 (VOUT/FB) and +13.2V. Leave the pads empty. TI
   specifies no feed-forward cap at 2.2 MHz. Leave **C23** (10 pF on U3, the
   5 V buck) in place. Check: R3's two pads measure ~100 kΩ, not a short.
   After the first 36 V power-up (section D), TP2 (+13.2V) should read
   **13.2 V ±2 %**.
8. **Add a 1 µF PVDD bypass cap at each TAS3251 PVDD pin** (pin 40 =
   PVDD_A, pin 35 = PVDD_B). TI requires a 1 µF ceramic as close to each
   PVDD pin as possible (datasheet §8.1.4.1.1 and §8.3.1.2). V1.3 has them as
   C108/C109 on the bottom.
   - **Part:** 1 µF, **X7R, ≥ 50 V** (100 V preferred: it keeps more of its
     capacitance at 35 V). For example Samsung CL31B105KCHNNNE (1206,
     LCSC C13832), the same as V1.3's C108/C109. A radial through-hole
     1 µF 100 V X7R ceramic (2.5 mm lead pitch) also works if it's easier
     to mount.
   - **Where:** from the PVDD copper (trace or via) **nearest to pin 40**,
     and again nearest to pin 35, to the closest GND copper (GND pins 37/38/42
     area, a GND via or GND pour). Scrape the solder mask a few mm from the
     pin if needed. Keep the loop as short as possible (total lead length
     well under 10 mm). A 1206 on the bottom side, across a PVDD via and a
     GND via, is ideal if the V1.0 layout has vias there.
   - **Never solder onto the pin row itself.** The neighbouring pins are
     SPK_OUT outputs (pins 34/36/39/41) switching 35 V at 0.635 mm pitch. A
     bridge there destroys the output stage.
   - **Check:** no short between PVDD and GND (> 1 kΩ, rising as the bulk
     caps charge from the meter), and no continuity from the new cap to any
     SPK_OUT pin. Optional: at full PVDD, scope SPK_OUTx at the pin and
     confirm the overshoot stays well below 50 V.

#### Optional: SW2 on IO10 (V1.2 equivalent)

On V1.0/V1.1, the SW2 pad, the C51 pad and TP12 connect directly to module
pin 28 (IO35). No resistor sits in between, so you cannot just add a wire.

1. Cut the trace between module pin 28 and SW2/C51/TP12. Check that the SW2
   pad no longer beeps to module pin 28.
2. Wire the SW2 signal pad to H2 pin 10 (IO10).
3. Add a 10 kΩ pull-up from H2 pin 10 to 3.3V (this is R51 on V1.2).
4. Optional: refit C51 (100 nF) on its pads as the debounce cap. It now sits
   on IO10, not on a PSRAM line.

Skip this section until the firmware actually uses the button. The planned
use is a **soft-off** (long press: mute, reset, GVDD off; see step P4).

#### Optional: pop-free rework (V1.3 equivalent)

The V1.3 hardware changes from review P0-7, done as bodges. After P1 and P2, a
V1.0/V1.1 board behaves like V1.3 at switch-on and switch-off. The only
difference is the ADC pin of the PVDD sense: **IO4** here, IO8 on V1.3. None
of these steps is needed for the board to work.

**P1. RESET_AMP and ENABLE_12V default to off** (issue 7)

- **ENABLE_12V:** keep R7 and solder a **4.7 kΩ** (THT or 0805 on wires)
  from **U15 pin 8** (ENABLE_12V) to **U15 pin 1** (GND). Fit it on the
  bottom side of the header. With R7 (100 kΩ to 3.3 V) the line now idles at
  about 0.15 V, so GVDD stays off. When IO38 drives high through the U15 7-8
  shunt, it sources about 0.7 mA, which is fine.
- **RESET_AMP:** **remove R45** (10 kΩ 0603, the pull-up from TAS_RESET to
  3.3 V. Find it by continuity: one pad beeps to TP29, the other to 3.3 V).
  Then solder a **10 kΩ** from **U14 pin 6** (TAS_RESET) to GND (U15 pin 1,
  U7 pin 1 or an H2 GND pin, using a short wire).
  - Alternative without removing R45: add a 1 kΩ from U14 pin 6 to GND
    instead (about 0.3 V idle level with R45). Check that this is below the
    TAS3251 RESET_AMP V_IL before relying on it.
- **Check**, with 5 V only on H2 pin 1 and the shunts fitted, while holding
  SW1 (ESP32 in reset):
  - U14 pin 6 < 0.4 V
  - U15 pin 8 < 0.4 V
- After this, the amp **stays off when the U14 5-6 or U15 7-8 shunt is
  removed** (before the rework it ran by default).

**P2. PVDD sense on IO4** (issue 8)

The same divider as V1.3 (R53 / R54 / C70), built off-board onto U7
(XH 6-pin: pin 1 = GND, pin 2 = 3.3 V, pin 3 = IO4 = ADC1_CH3):

```text
PVDD (TP1) ──[100 kΩ]──┬── U7 pin 3 (IO4)
                       ├──[6.8 kΩ]── U7 pin 1 (GND)
                       └──[100 nF]── U7 pin 1 (GND)
```

- Solder the **100 kΩ right at TP1**, so the long wire carries only the
  divided voltage. If that wire chafes and shorts to something, the current
  is limited to < 0.4 mA.
- Put the 6.8 kΩ and the 100 nF at the U7 end (on an XH plug or on the
  header's back side).
- **Check**: with 36 V on CN1, U7 pin 3 reads about **2.29 V**
  (PVDD × 6.8 / 106.8).
- No zener or clamp is needed, see review P0-7.
- Firmware: `TAS_PIN_PVDD_SENSE` = **GPIO_NUM_4** (ADC1_CH3) on reworked
  V1.0/V1.1, GPIO_NUM_8 (ADC1_CH7) on V1.3. See the TODO in
  [tas_pins.h](main/tas_pins.h).

**P3. F1 → time-lag fuse** (issue 5, optional)

Replace F1 (Littelfuse 0451005.MRL, fast-acting) with **0452005.MRL**
(LCSC C66503, NANO² Slo-Blo 5 A, same 2410 footprint) as in V1.3. With this
fuse, switching the PSU on at the mains with the board already connected is
safe without a current-limited bench supply.

**P4. Switching off** (until P2 and the firmware PVDD monitor are in place)

Without PVDD sense the firmware can't react to the mains going off. To
avoid the switch-off thump:

1. Mute first: volume down / I²C soft-mute, or (once implemented) a long
   press on SW2 or the `off` console command, which mutes, pulls RESET_AMP
   low and turns GVDD off.
2. Then switch off the mains / PSU.

These clicks and thumps are **not dangerous** for normal speakers: they're
short, small-energy transients, like those of many consumer amps. During
development, use cheap test speakers or a dummy load anyway, keep the volume
low, and never connect a tweeter without its crossover capacitor.

#### B. Shunts / jumpers

| Header | Pins | Connects | Needed for |
|--------|------|----------|------------|
| U14 | 1-2 | IO1 ↔ TAS_MUTE | DAC_MUTE control |
| U14 | 3-4 | IO2 ↔ TAS_CLIP | /CLIP_OTW sense |
| U14 | 5-6 | IO42 ↔ TAS_RESET | RESET_AMP control |
| U14 | 7-8 | IO41 ↔ TAS_FAULT | /FAULT sense |
| U15 | 3-4 | IO40 ↔ ENABLE_3.3V | 3.3 V analog rail enable |
| U15 | 5-6 | IO39 ↔ GOOD_13.2V | 13.2 V good sense |
| U15 | 7-8 | IO38 ↔ ENABLE_12V | 12 V GVDD enable |
| H2 | 13-14 | TAS_ADR ↔ IO12 | I2C address strap read |
| U13 | 3-4 (exactly one pair) | FREQ_ADJ → 10 kΩ | 768 kHz PWM (default, see top-level README) |

#### C. Flash the firmware first, without 36 V

6. **Rebuild with Octal PSRAM.** Delete the old `sdkconfig` and run
   `idf.py reconfigure build`. Check that `grep SPIRAM_MODE sdkconfig` shows
   `CONFIG_SPIRAM_MODE_OCT=y`.
7. **Power the digital side only.** Connect a 5 V bench supply with a
   ~300 mA current limit: + to **H2 pin 1** (+5V), − to H2 pin 15/17/19/21-24
   (GND).
   - +5V feeds the AP63203 3.3 V buck directly, and D5 blocks back-feed into
     the 36 V buck.
   - This is the same state as the intended USB-C programming mode, so the
     TAS3251 output stage stays unpowered.
   - Alternative: power from the main 36 V input as before, but only after
     sections A and B are done.
8. **Wire a 3.3 V-logic UART adapter:**
   - adapter TXD → H2 pin 5 (RXD0)
   - adapter RXD → H2 pin 3 (TXD0)
   - adapter GND → any H2 GND pin

   Do not connect the adapter's 3.3 V/5 V output.
9. **Enter the ROM bootloader:**
   1. Jumper U10 pin 4 to U10 pin 1 (IO0 → GND).
   2. Press and release SW1 (EN/reset).
   3. Wait ~200 ms, then remove the IO0 jumper.

   The chip now waits in the UART download bootloader on UART0.
10. **Flash:**

    ```sh
    idf.py -p /dev/tty.usbserial-XXXX flash monitor
    ```

    - To find the port, run `ls /dev/tty.*` before and after plugging in
      the adapter.
    - esptool's DTR/RTS reset pulses fail silently because nothing is wired
      to them. That's fine, since the chip is already in the bootloader.
    - In VS Code, set `idf.port` to this device and `idf.flashType` to
      `"UART"` in `.vscode/settings.json`.
11. **Boot and check the log.** Press SW1 again (IO0 not grounded) and check
    the monitor output at 115200:
    - You should see `esp_psram: Found 8MB PSRAM device`.
    - The status LED (if reworked) goes blue, then amber, because
      GOOD_13.2V is absent without 36 V. That is expected.
    - If PSRAM init fails or the chip reboots in a loop, recheck step 6 and
      section A.

    11a. **Check the VDD_SPI strap override** (issue 4). With the chip in the
    bootloader (step 9), run:

    ```sh
    espefuse.py -p /dev/tty.usbserial-XXXX summary | grep -i -E "VDD_SPI|FLASH_TPUW"
    ```

    `VDD_SPI_FORCE` must be set with `VDD_SPI_TIEH = 1` (3.3 V). If it isn't,
    note the board: SCL's pull-up on IO45 selects 1.8 V for flash/PSRAM at
    reset. If step 11 boots fine, the board is OK as it is.

#### D. First 36 V power-up

12. Remove the 5 V bench supply from H2 pin 1 and keep the UART monitor
    connected.

    12a. **Check the input polarity at CN1 with a meter before connecting**
    (issue 6): pin 1 = **+36 V**, pin 2 = **GND**. On V1.0/V1.1 a reversed
    supply is not blocked by Q1.
13. Apply 36 V from a **current-limited** bench supply (e.g. 1–2 A limit)
    and turn the output on with the board already connected. The supply's
    current limit then charges the 6600 µF PVDD bulk capacitance gently
    (issue 5). Do not hot-plug a stiff, unlimited 36 V supply until F1 is
    replaced by a time-lag type. Expected result:
    - LED 0 goes blue → green.
    - The red D_FAULT LED stays off.
    - The log walks through the startup states to `READY`.
14. **Measure the rails** (GND = CN1 pin 2):

    | Test point | Rail | Expected |
    |------------|------|----------|
    | TP1 | PVDD | supply voltage minus a few mV (Q1 fully on) |
    | TP30 | PVDDLMQ | ≈ PVDD |
    | TP2 | +13.2V | 13.2 V |
    | TP3 | 12V_GVDD | 12.0 V, once the firmware drives ENABLE_12V (review P0-5) |

    If TP1 is ~0.7–1.4 V below the input, Q1 isn't turning on and the load
    runs through its body diode. Switch off and check D1/R2/R5.

One limit remains on V1.0: live JTAG debugging (the gdbtarget launch config)
goes over the broken USB-C native-USB-JTAG peripheral, so it is unavailable
on V1.0 boards.

#### Reworked V1.0/V1.1 vs V1.2

After sections A–C, a reworked board runs the same firmware as V1.2 (same
`tas_pins.h`, same `sdkconfig`). The PCB outline, connectors and heatsink
area are the same on all revisions. These differences remain:

| Item | Reworked V1.0/V1.1 | V1.2 | Can rework fix it? |
|------|--------------------|------|--------------------|
| USB-C (V1.0 only) | Rotated 180°: no USB power, no USB flashing, no JTAG | Works | **No.** Use UART flashing (section C) |
| SW2 user button | Removed or unused | IO10 with R51 10 kΩ pull-up | Yes, see [SW2 on IO10](#optional-sw2-on-io10-v12-equivalent) |
| Reverse-polarity protection (Q1) | Not effective (Q1 mounted source-to-input) | Same in the EasyEDA V1.2 design. Fixed in the KiCad 10 redraw (next revision) | **No.** Check polarity before connecting (step 12a) |
| ESP32 EN pull-up | 10 kΩ bodge on TP9 (step A6) | Missing in V1.2 too. To be added in the next revision | Yes, step A6 |
| H2 pins 7 / 8 | Carry the status LED bus (IO8/IO9) because of the bodge | Not connected | No. Don't use them for anything else |
| H2 pin 10 | Still IO10 (or SW2, if you reworked it) | Not connected | No. Don't use it for anything else |
| C51, R17, R18 | Removed (C51 optional on IO10) | Fitted, on the new nets | — |
| RESET_AMP / ENABLE_12V default | Pulled **up** (amp on during ESP32 boot) | Pulled down in V1.3 (R45, R7 → GND) | Yes, step P1 |
| PVDD sense | None | V1.3: R53 / R54 / C70 on **IO8** (ADC1_CH7) | Yes, step P2, on **IO4** (ADC1_CH3) via U7 |
| F1 | 0451005 fast-acting | V1.3: 0452005 Slo-Blo | Yes, step P3 |
| U7 pin 3 (IO4) | PVDD sense, if P2 is done | Spare | — |

Anything plugged into H2 must leave pins 7, 8 and 10 alone, so the same
add-on board works on every revision.
