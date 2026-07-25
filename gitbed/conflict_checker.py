import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Sample MCU Peripheral Multiplexing Matrix (STM32/ESP32 common pin functions)
MCU_PERIPHERAL_MAP: Dict[str, List[str]] = {
    "PA9": ["UART1_TX", "TIM1_CH2"],
    "PA10": ["UART1_RX", "TIM1_CH3"],
    "PB6": ["I2C1_SCL", "TIM4_CH1", "UART1_TX"],
    "PB7": ["I2C1_SDA", "TIM4_CH2", "USART1_RX"],
    "PB8": ["I2C1_SCL", "CAN1_RX", "TIM10_CH1"],
    "PB9": ["I2C1_SDA", "CAN1_TX", "TIM11_CH1"],
    "PA5": ["SPI1_SCK", "ADC1_IN5", "DAC1_OUT"],
    "PA6": ["SPI1_MISO", "ADC1_IN6", "TIM3_CH1"],
    "PA7": ["SPI1_MOSI", "ADC1_IN7", "TIM3_CH2"],
}


class PinConflictChecker:
    """Detects peripheral collisions and double-assignment errors in pin definitions."""

    def __init__(self, mcu_map: Optional[Dict[str, List[str]]] = None):
        self.mcu_map = mcu_map or MCU_PERIPHERAL_MAP

    def check_code_conflicts(self, code: str, target_pin: str, signal_name: str) -> Tuple[bool, List[str]]:
        errors = []

        # 1. Check for duplicate pin definitions in code
        macro_matches = re.findall(r"#define\s+(\w+)\s+(" + re.escape(target_pin) + r")\b", code)
        assigned_signals = [sig for sig, pin in macro_matches if sig != f"{signal_name}_PIN" and sig != signal_name]

        if len(assigned_signals) > 0:
            err = (
                f"Hardware Collision: Pin '{target_pin}' is already assigned to signal(s) "
                f"[{', '.join(assigned_signals)}] in code."
            )
            logger.warning(err)
            errors.append(err)

        # 2. Check for reserved peripheral bus conflicts (e.g. if code uses I2C1 and pin is assigned to I2C1_SCL)
        reserved_peripherals = self.mcu_map.get(target_pin, [])
        for periph in reserved_peripherals:
            bus_prefix = periph.split("_")[0]  # e.g., I2C1, SPI1, UART1
            if f"#define ENABLE_{bus_prefix}" in code or f"#define USE_{bus_prefix}" in code:
                err = (
                    f"Peripheral Conflict: Pin '{target_pin}' conflicts with active hardware peripheral "
                    f"'{periph}' enabled in code."
                )
                logger.warning(err)
                errors.append(err)

        is_clean = len(errors) == 0
        return is_clean, errors
