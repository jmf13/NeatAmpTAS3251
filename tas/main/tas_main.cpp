/**
 * @file tas_main.cpp
 * @brief Application entry point: runs the amplifier startup sequence and,
 *        on success, the steady-state monitoring loop. See
 *        tas::SystemController and tas/README.md "Firmware Architecture".
 */
#include "esp_log.h"
#include "system_controller.hpp"

namespace {
constexpr char kTag[] = "app_main";
}

extern "C" void app_main(void)
{
    static tas::SystemController controller;

    const esp_err_t err = controller.startup();
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Startup sequence failed (%s) — amplifier held in reset and muted",
                 esp_err_to_name(err));
        return;
    }

    controller.runForever();
}
