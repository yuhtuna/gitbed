import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def generate_devicetree_overlay(diff_data: dict, original_dts: str = "") -> str:
    """Generates or updates Zephyr / Linux RTOS DeviceTree overlay snippet for pin reassignment."""
    signal = diff_data.get("signal_name", "STATUS_LED").lower()
    new_pin = diff_data.get("new_pin", "PB7")

    port = new_pin[1:2].lower() if len(new_pin) > 1 else "b"
    pin_num = new_pin[2:] if len(new_pin) > 2 else "7"

    new_node = (
        f"        {signal}_led: {signal} {{\n"
        f"            gpios = <&gpio{port} {pin_num} GPIO_ACTIVE_HIGH>;\n"
        "            label = \"System Status LED\";\n"
        "        };\n"
    )

    if original_dts and "leds {" in original_dts:
        pattern = rf"({signal}_led:\s*{signal}\s*\{{[^}}]*gpios = <&gpio)\w+\s+\d+"
        if re.search(pattern, original_dts):
            return re.sub(pattern, rf"\g<1>{port} {pin_num}", original_dts)
        else:
            return original_dts.replace("leds {", f"leds {{\n{new_node}")

    return (
        "// Auto-generated Zephyr DeviceTree Overlay by GitBed\n"
        "/ {\n"
        "    leds {\n"
        "        compatible = \"gpio-leds\";\n"
        f"{new_node}"
        "    };\n"
        "};\n"
    )


def generate_gpio_driver_cpp(diff_data: dict, original_cpp: str = "") -> str:
    """Updates or appends C++ GPIO driver initialization code for hardware pin sync."""
    signal = diff_data.get("signal_name", "STATUS_LED")
    new_pin = diff_data.get("new_pin", "PB7")

    new_func = (
        f"\nvoid init_gpio_{signal.lower()}() {{\n"
        "    GPIO_InitTypeDef gpio_init = {0};\n"
        f"    gpio_init.Pin = {signal}_PIN;\n"
        "    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;\n"
        "    gpio_init.Pull = GPIO_NOPULL;\n"
        "    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;\n"
        "    HAL_GPIO_Init(GPIOB, &gpio_init);\n"
        "}\n"
    )

    if original_cpp:
        pattern = r"(init_gpio_" + re.escape(signal.lower()) + r"\s*\([^)]*\)\s*\{[^}]*\})"
        if re.search(pattern, original_cpp):
            return original_cpp
        else:
            return original_cpp.rstrip() + "\n" + new_func

    return (
        "// Auto-generated GPIO Driver Initialization by GitBed\n"
        "#include \"pin_config.h\"\n" + new_func
    )


def build_multi_file_patch_bundle(diff_data: dict, header_code: str, existing_files: Dict[str, str] = None) -> Dict[str, str]:
    """Assembles multi-file patch dictionary mapping file paths to file contents."""
    if existing_files is None:
        existing_files = {}

    orig_overlay = existing_files.get("boards/app.overlay", "")
    orig_driver = existing_files.get("src/gpio_driver.cpp", "")

    files_bundle = {
        "pin_config.h": header_code,
        "boards/app.overlay": generate_devicetree_overlay(diff_data, orig_overlay),
        "src/gpio_driver.cpp": generate_gpio_driver_cpp(diff_data, orig_driver),
    }
    logger.info(f"Built multi-file HAL patch bundle with {len(files_bundle)} files")
    return files_bundle
