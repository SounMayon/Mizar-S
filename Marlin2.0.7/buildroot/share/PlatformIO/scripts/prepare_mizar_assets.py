"""Prepare the Geeetech Mizar S TFT asset set from the pinned MKS archive.

The MKS archive does not provide all Mizar S names. Exact matches are retained;
the explicit aliases below duplicate the closest available MKS icon under the
filename expected by this firmware. This guarantees names/format, not visual
equivalence with Geeetech's official Mizar S package.
"""
from pathlib import Path
import re
import shutil

MKS_ALIASES = {
    "bmp_babystep.bin": "bmp_baby_move0_1.bin",
    "bmp_buzz_off.bin": "bmp_Light_close.bin",
    "bmp_buzz_on.bin": "bmp_Light_open.bin",
    "bmp_clear.bin": "bmp_zero.bin",
    "bmp_confirm.bin": "bmp_enable.bin",
    "bmp_confirm_dis.bin": "bmp_disable.bin",
    "bmp_cool.bin": "bmp_Light_close.bin",
    "bmp_disoperate.bin": "bmp_disable.bin",
    "bmp_espeed.bin": "bmp_speed_state.bin",
    "bmp_filament_off.bin": "bmp_disable.bin",
    "bmp_filament_on.bin": "bmp_enable.bin",
    "bmp_filamentchange_dis.bin": "bmp_filamentchange.bin",
    "bmp_gradient.bin": "bmp_twoInOneSet.bin",
    "bmp_heatbas.bin": "bmp_bed.bin",
    "bmp_heatpla.bin": "bmp_extru1.bin",
    "bmp_led_color.bin": "bmp_Light_open.bin",
    "bmp_led_off.bin": "bmp_Light_close.bin",
    "bmp_led_white.bin": "bmp_Light_open.bin",
    "bmp_level_set.bin": "bmp_leveling.bin",
    "bmp_leveling_auto.bin": "bmp_leveling1.bin",
    "bmp_leveling_manual.bin": "bmp_leveling2.bin",
    "bmp_machine_para_dis.bin": "bmp_machine_para.bin",
    "bmp_mixing_entry.bin": "bmp_twoInOneSet.bin",
    "bmp_mixing_icon.bin": "bmp_twoInOneSet.bin",
    "bmp_motor_off.bin": "bmp_disable.bin",
    "bmp_motor_off_cn.bin": "bmp_disable.bin",
    "bmp_move_clear.bin": "bmp_zero.bin",
    "bmp_move_xAdd.bin": "bmp_xAdd.bin",
    "bmp_move_xDec.bin": "bmp_xDec.bin",
    "bmp_move_yAdd.bin": "bmp_yAdd.bin",
    "bmp_move_yDec.bin": "bmp_yDec.bin",
    "bmp_move_zAdd.bin": "bmp_zAdd.bin",
    "bmp_move_zDec.bin": "bmp_zDec.bin",
    "bmp_mspeed.bin": "bmp_speed_state.bin",
    "bmp_mspeed_mms.bin": "bmp_speed.bin",
    "bmp_plog.bin": "bmp_Power.bin",
    "bmp_pre_cool.bin": "bmp_Light_close.bin",
    "bmp_return_dis.bin": "bmp_return.bin",
    "bmp_sensor_check.bin": "bmp_init_state.bin",
    "bmp_start.bin": "bmp_printing.bin",
    "bmp_start_dis.bin": "bmp_printing.bin",
    "bmp_switch_off.bin": "bmp_Light_close.bin",
    "bmp_switch_on.bin": "bmp_Light_open.bin",
    "bmp_toggle.bin": "bmp_enable.bin",
    "bmp_wait.bin": "bmp_init_state.bin",
}

def main():
    repo_root = Path(__file__).resolve().parents[5]
    assets_dir = repo_root / "Marlin2.0.7/.pio/build/geeetech_lcd35/assets"
    expected_file = repo_root / "Resource/list.txt"
    if not assets_dir.is_dir():
        raise SystemExit(f"PlatformIO assets directory not found: {assets_dir}")

    expected = re.findall(r'"([^"]+\.bin)"', expected_file.read_text(encoding="utf-8"))
    if len(expected) != 107 or len(set(expected)) != len(expected):
        raise SystemExit(f"Expected 107 unique Mizar S icon names, found {len(expected)}")

    by_lower = {path.name.lower(): path for path in assets_dir.iterdir() if path.is_file()}
    stage = assets_dir.with_name("assets.mizar-s")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()

    aliases_used = []
    for target_name in expected:
        source = by_lower.get(target_name.lower())
        if source is None:
            alias_name = MKS_ALIASES.get(target_name)
            source = by_lower.get(alias_name.lower()) if alias_name else None
            if source is None:
                raise SystemExit(f"No MKS icon or alias for expected asset: {target_name}")
            aliases_used.append((target_name, source.name))
        shutil.copy2(source, stage / target_name)

    font_name = "FontUNIGBK.bin"
    font = by_lower.get(font_name.lower())
    if font is None:
        raise SystemExit(f"Required MKS font is missing: {font_name}")
    shutil.copy2(font, stage / font_name)

    shutil.rmtree(assets_dir)
    stage.rename(assets_dir)

    print(f"Prepared {len(expected)} expected Mizar S icon filenames and {font_name}.")
    for target_name, source_name in aliases_used:
        print(f"Asset alias: {target_name} <- {source_name}")
    print("This is a test asset set based on MKS artwork; verify its appearance on the Mizar S TFT.")

if __name__ == "__main__":
    main()
