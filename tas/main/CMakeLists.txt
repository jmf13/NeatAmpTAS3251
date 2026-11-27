idf_component_register(SRCS "tas_main.cpp"
                             "system_controller.cpp"
                             "power_supplies.cpp"
                             "tas3251.cpp"
                             "dsp_adau1466.cpp"
                             "i2c_bus.cpp"
                             "i2s_bus.cpp"
                             "status_led.cpp"
                       PRIV_REQUIRES esp_driver_gpio esp_driver_i2c esp_driver_i2s esp_app_format spi_flash esp_psram
                       INCLUDE_DIRS "")
