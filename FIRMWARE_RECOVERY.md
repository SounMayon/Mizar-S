# Mizar S firmware: filament runout and power-loss recovery

This note documents the MKS/LVGL firmware paths used by the Mizar S source in this repository. The source identifies itself as Marlin 2.0.7; the GitHub repository does not identify this checkout as an exact source export of the vendor binary `MizarS_FM_V201A_230512`. Confirm the installed firmware and board before flashing a build from this branch.

## Filament runout

The MKS screen polls the custom filament sensor in `Marlin2.0.7/Marlin/src/lcd/extui/lib/mks_ui/printer_operation.cpp`. A missing-filament sample advances a debounce counter, and a present-filament sample reduces it. When the counter reaches 20, the UI pauses SD printing, stops the print timer, and shows the filament-change dialog.

The original poll routine applied each sensor sample twice, so the effective debounce time was half the configured count. The branch changes this to one sample per poll and saves the current feedrate when starting the pause.

After the pause motion completes, the dialog's Confirm button now resumes only when the machine is in `PAUSED` and every configured MKS filament sensor reports filament present. It then switches to `RESUMING`; `printer_state_polling()` returns the head to the saved position and issues `M24`. If the sensor still reports runout, Confirm leaves the dialog open. This supports loading filament and purging manually before confirming.

## M600 and hotbed PID autotune

The source included Marlin's generic `M600` implementation, but `ADVANCED_PAUSE_FEATURE` was commented out, so that command was not compiled into the firmware. Although Marlin includes a generic `M600` implementation, enabling `ADVANCED_PAUSE_FEATURE` on this MKS/LVGL port currently fails the GitHub build: the pause UI refers to menu response symbols that are not available in this screen configuration. The source also has no MKS `ExtUI::onUserConfirmRequired` handler to route the M600 user-confirmation prompts to the touchscreen. Enabling the feature without that UI integration would be incomplete, so it remains disabled pending a complete screen-side port and a successful build. This limitation is separate from the custom filament-runout dialog, which the user has tested successfully.

`PIDTEMPBED` remains enabled. The Marlin bed autotune command `M303 E-1` remains available; this branch intentionally does not apply Geeetech V1.9.8's change that disabled bed PID. That choice preserves hotbed autotune as requested. Temperature-alarm changes from Geeetech V2.0.1 are not inferred from the short changelog and are not represented as implemented here.

## Power-loss recovery

The source enables `POWER_LOSS_RECOVERY` by default in `Marlin2.0.7/Marlin/Configuration_adv.h`. The GTM32 LCD35 A10 board pin map assigns `POWER_LOSS_PIN` to PE3, and the configured loss state is LOW. Recovery data is stored through `POWER_LOSS_STORAGE_EEPROM`; the saved state includes the SD filename and offset, position, temperatures, fan state, feedrate, and other print settings. At startup, a valid recovery record queues `M1000 S`; recovery restores machine state and resumes the SD file at its saved offset.

A recovery prompt requires a valid saved record. With the MKS/LVGL board mapping, the PE3 outage input can trigger an immediate save, while regular position checkpoints also update the recovery state. A record may be unavailable if the outage signal is not detected, power does not remain stable long enough to finish the EEPROM write, the SD card or EEPROM data is unavailable, or the job has completed. The firmware can only resume SD-card jobs. These hardware and persistence paths need to be checked on the printer to explain intermittent recovery prompts.

## Build and SD-card package

The upstream Geeetech PlatformIO configuration sets `geeetech_lcd35` as its default environment. This branch compiles that environment, which builds for the STM32F103VE board and generates `firmware.bin`. For the GTM32 bootloader, the flashable file must be named exactly `GTM32Source.bin`. PlatformIO still generates `firmware.bin` internally; the GitHub workflow copies it to `GTM32Source.bin` for the release artifact. Put `GTM32Source.bin` and the `assets` folder at the root of the TF card.

The official package archive `MizarS_FM_V201A_230512.rar` committed to this branch contains the vendor's `GTM32Source.bin`, `readme.txt`, and complete `assets/` directory. Its 107 icon filenames match `Resource/list.txt`, and it includes the original `FontUNIGBK.bin`. GitHub Actions now extracts and validates that exact asset set after compilation, then replaces PlatformIO's generated display assets with the official Geeetech files. It does not rename substitute MKS artwork. The archive SHA-256 is `510d22e81fc175c608cf94fc6e75eee46bb431b462b078a154749351b96b7f85`.

The previous MKS icon/font substitution package was tested on the printer and caused clipped or missing icon artwork and absent UI text. That test confirmed the substitutions are incompatible with the Mizar S UI. Do not use assets from older artifacts produced by the MKS alias workflow.

The official archive is a precompiled firmware package plus display assets; it does not include Marlin C++ source. The vendor readme identifies the package as V2.0.1 (20230512), while this branch's Marlin source still sets `USER_FIRMWARE_VERSION` to `1.9.4`. A build from this branch therefore combines the current branch's firmware code with the correct official screen assets; it is not source-equivalent to the vendor's V2.0.1 firmware. Keep the displayed version honest until the missing Geeetech source changes are identified and ported.

### Reverse-exporting the display icons

The same workflow runs `export_mizar_asset_previews.py` and adds an `assets-preview/` directory to the GitHub Actions artifact. It contains one PNG per decoded icon plus `contact-sheet.png`, a labeled overview. The script reads LVGL v7 four-byte image headers and decodes the little-endian RGB565 pixels. The 480×320 RGB565 logo may be raw or include a four-byte header; the exporter handles both official Geeetech and raw MKS forms. It skips `FontUNIGBK.bin`, which is font data rather than an image. `FontUNIGBK.bin` is skipped because it is font data rather than an image.

The PNGs let you inspect and recover a viewable copy of the decoded icons. RGB565 stores fewer color levels than the original JPG or PNG, so this cannot reconstruct the exact original source pixels; exporting PNG avoids adding another lossy JPEG pass. Preview files are separate from the `assets/` folder that goes on the SD card. Use the packaged `GTM32Source.bin` basename for flashing; `firmware.bin` is only PlatformIO's intermediate output name.

## Verification checklist

1. Build this branch with the Mizar S / `BOARD_GTM32_LCD35_A10` configuration and the original MKS screen enabled.
2. Start an SD print, trigger runout, wait until the pause completes, insert filament, purge manually, and press Confirm. Check that the print resumes from the saved position.
3. While the sensor still reports no filament, press Confirm. Check that the printer stays paused.
4. Repeat the runout test with each configured sensor and verify the polarity on the actual sensor wiring.
5. Enable PLR, start an SD print, and test power interruption at multiple points after valid layer checkpoints. Confirm that the boot prompt appears and resumes the same file near the saved position.
6. Repeat the power interruption test during an active filament pause and verify the saved SD position and restored machine state.
7. On the Mizar S TFT, inspect every screen/icon that uses an aliased asset; confirm all official Geeetech icons and text render correctly before treating this test package as suitable for regular use.

The user reports successful printer-side tests of the filament-runout recovery (reinsert filament, manually purge, confirm, and resume) and power-loss recovery. M600/touchscreen integration and the remaining checklist items have not been reported as tested. GitHub Actions must pass on the current branch head before its artifact is treated as build-verified.
