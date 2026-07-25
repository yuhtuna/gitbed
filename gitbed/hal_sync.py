import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def generate_devicetree_overlay(diff_data: dict) -> str:
    """Generates Zephyr / Linux RTOS DeviceTree overlay snippet for pin reassignment."""
    signal = diff_data.get("signal_name", "STATUS_LED").lower()
    new_pin = diff_data.get("new_pin", "PB7")

    port = new_pin[1:2].lower() if len(new_pin) > 1 else "b"
    pin_num = new_pin[2:] if len(new_pin) > 2 else "7"

    dts_content = (
        "// Auto-generated Zephyr DeviceTree Overlay by GitBed\n"
        "/ {\n"
        "    leds {\n"
        "        compatible = \"gpio-leds\";\n"
        f"        {signal}_led: {signal} {{\n"
        f"            gpios = <&gpio{port} {pin_num} GPIO_ACTIVE_HIGH>;\n"
        "            label = \"System Status LED\";\n"
        "        };\n"
        "    };\n"
        "};\n"
    )
    return dts_content


def generate_gpio_driver_cpp(diff_data: dict, original_cpp: str = "") -> str:
    """Updates or generates C++ GPIO driver initialization code for hardware pin sync."""
    signal = diff_data.get("signal_name", "STATUS_LED")
    new_pin = diff_data.get("new_pin", "PB7")

    if original_cpp:
        pattern = r"(init_gpio_" + re.escape(signal.lower()) + r"\s*\([^)]*\)\s*\{[^}]*\})"
        if re.search(pattern, original_cpp):
            updated = re.sub(r"GPIO_PIN_\w+", f"GPIO_PIN_{new_pin}", original_cpp)
            return updated

    cpp_content = (
        "// Auto-generated GPIO Driver Initialization by GitBed\n"
        "#include \"pin_config.h\"\n\n"
        f"void init_gpio_{signal.lower()}() {{\n"
        "    GPIO_InitTypeDef gpio_init = {0};\n"
        f"    gpio_init.Pin = {signal}_PIN;\n"
        "    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;\n"
        "    gpio_init.Pull = GPIO_NOPULL;\n"
        "    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;\n"
        "    HAL_GPIO_Init(GPIOB, &gpio_init);\n"
        "}\n"
    )
    return cpp_content


def build_multi_file_patch_bundle(diff_data: dict, header_code: str) -> Dict[str, str]:
    """Assembles multi-file patch dictionary mapping file paths to file contents."""
    files_bundle = {
        "pin_config.h": header_code,
        "boards/app.overlay": generate_devicetree_overlay(diff_data),
        "src/gpio_driver.cpp": generate_gpio_driver_cpp(diff_data),
    }
    logger.info(f"Built multi-file HAL patch bundle with {len(files_bundle)} files")
    return files_bundle
