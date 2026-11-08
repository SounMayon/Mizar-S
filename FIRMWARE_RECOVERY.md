# Mizar S firmware: filament runout and power-loss recovery

This note documents the MKS/LVGL firmware paths used by the Mizar S source in this repository. The source identifies itself as Marlin 2.0.7; the GitHub repository does not identify this checkout as an exact source export of the vendor binary `MizarS_FM_V201A_230512`. Confirm the installed firmware and board before flashing a build from this branch.

## Filament runout

The MKS screen polls the custom filament sensor in `Marlin/src/lcd/extui/lib/mks_ui/printer_operation.cpp`. A missing-filament sample advances a debounce counter, and a present-filament sample reduces it. When the counter reaches 20, the UI pauses SD printing, stops the print timer, and shows the filament-change dialog.

The original poll routine applied each sensor sample twice, so the effective debounce time was half the configured count. The branch changes this to one sample per poll and saves the current feedrate when starting the pause.

After the pause motion completes, the dialog's Confirm button now resumes only when the machine is in `PAUSED` and every configured MKS filament sensor reports filament present. It then switches to `RESUMING`; `printer_state_polling()` returns the head to the saved position and issues `M24`. If the sensor still reports runout, Confirm leaves the dialog open. This supports loading filament and purging manually before confirming.

## Power-loss recovery

The source enables `POWER_LOSS_RECOVERY` by default in `Marlin/Configuration_adv.h`. The GTM32 LCD35 A10 board pin map assigns `POWER_LOSS_PIN` to PE3, and the configured loss state is LOW. Recovery data is stored through `POWER_LOSS_STORAGE_EEPROM`; the saved state includes the SD filename and offset, position, temperatures, fan state, feedrate, and other print settings. At startup, a valid recovery record queues `M1000 S`; recovery restores machine state and resumes the SD file at its saved offset.

A recovery prompt requires a valid saved record. With the MKS/LVGL board mapping, the PE3 outage input can trigger an immediate save, while regular position checkpoints also update the recovery state. A record may be unavailable if the outage signal is not detected, power does not remain stable long enough to finish the EEPROM write, the SD card or EEPROM data is unavailable, or the job has completed. The firmware can only resume SD-card jobs. These hardware and persistence paths need to be checked on the printer to explain intermittent recovery prompts.

## Build and SD-card package

The upstream Geeetech PlatformIO configuration sets `geeetech_lcd35` as its default environment. This branch compiles that environment, which builds for the STM32F103VE board and generates `firmware.bin`. Geeetech's published update instructions say to put a `.bin` file and the `assets` folder at the root of the TF card; they do not specify a required basename. The Mizar S LVGL configuration also documents copying the build's `assets` folder alongside the firmware.

The GitHub Actions build now pins the MKS asset archive to commit `af5eb011d08f2a2e19809e38470f678958530b29` and runs `prepare_mizar_assets.py` after compilation. It keeps exact filename matches, maps the 45 absent names to selected MKS icons, removes surplus icons, and verifies the 107 expected names plus `FontUNIGBK.bin`. The mapping is an **experimental visual substitution set**, not the official Geeetech Mizar S artwork; review the alias list in the preparation script and test every screen on the printer before deciding whether to keep it. The repository's `Resource/icon/` still contains the original 107 JPG sources, not the converted MKS-format `.bin` files. I found no Geeetech instruction requiring the firmware binary to be renamed to `MizarS_FM_V201A_230512.bin`; PlatformIO generates `firmware.bin`.

## Verification checklist

1. Build this branch with the Mizar S / `BOARD_GTM32_LCD35_A10` configuration and the original MKS screen enabled.
2. Start an SD print, trigger runout, wait until the pause completes, insert filament, purge manually, and press Confirm. Check that the print resumes from the saved position.
3. While the sensor still reports no filament, press Confirm. Check that the printer stays paused.
4. Repeat the runout test with each configured sensor and verify the polarity on the actual sensor wiring.
5. Enable PLR, start an SD print, and test power interruption at multiple points after valid layer checkpoints. Confirm that the boot prompt appears and resumes the same file near the saved position.
6. Repeat the power interruption test during an active filament pause and verify the saved SD position and restored machine state.
7. On the Mizar S TFT, inspect every screen/icon that uses an aliased asset; confirm icons remain understandable and correctly placed before treating this test package as suitable for regular use.

These are hardware validation steps, not results claimed by this source review. GitHub Actions successfully compiled the Geeetech LCD35 firmware for this branch; the printer-side tests above are still pending.
