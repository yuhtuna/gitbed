// Auto-generated GPIO Driver Initialization by GitBed
#include "pin_config.h"

void init_gpio_status_led() {
    GPIO_InitTypeDef gpio_init = {0};
    gpio_init.Pin = STATUS_LED_PIN;
    gpio_init.Mode = GPIO_MODE_OUTPUT_PP;
    gpio_init.Pull = GPIO_NOPULL;
    gpio_init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &gpio_init);
}
