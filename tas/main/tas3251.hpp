/**
 * @file tas3251.hpp
 * @brief Driver for the TI TAS3251 Class-D amplifier: the four GPIO
 *        control/status lines (RESET_AMP, DAC_MUTE, /FAULT, /CLIP_OTW), the
 *        ADR address strap, and the I2C book/page register interface.
 */
#ifndef TAS_TAS3251_HPP
#define TAS_TAS3251_HPP

#include <cstdint>
#include "driver/i2c_master.h"
#include "esp_attr.h"
#include "esp_err.h"
#include "i2c_bus.hpp"

namespace tas {

/** @brief Audio channel selector for per-channel registers (B0-P0-R61/R62). */
enum class Channel : uint8_t {
    Left = 0,
    Right = 1,
};

/**
 * @brief Raw latched fault bytes read back from B0-P0-R94/R95.
 * @warning Bit-level meaning (OC/UV/OTE/clock-error position) is documented
 *          in the TAS3251 datasheet register map and is NOT decoded here —
 *          only the raw bytes are captured. Decode against the datasheet
 *          before acting on individual bits.
 */
struct FaultStatus {
    uint8_t reg94 = 0;
    uint8_t reg95 = 0;
};

/**
 * @brief Controls one TAS3251 amplifier: GPIO lines plus I2C registers.
 *
 * Register addressing follows TI's book/page convention referenced in the
 * hardware README (e.g. "B0-P0-R2" = Book 0, Page 0, Register 2):
 * selectBookPage() must be called (directly, or implicitly by the
 * convenience setters below) before writeRegister()/readRegister() target a
 * register outside the currently selected book/page.
 */
class Tas3251 {
public:
    /**
     * @name TAS3251 B0-P0 registers used by this driver
     * Register numbers per the hardware README register map / TI book-page
     * addressing (e.g. "B0-P0-R2" = Book 0, Page 0, Register 2). Exposed here
     * (rather than kept file-local in tas3251.cpp) so callers/tests can refer
     * to them by name instead of a bare hex literal.
     */
    ///@{
    static constexpr uint8_t kRegPageSelect = 0x00;      ///< PAGE — selects the page within the current book.
    static constexpr uint8_t kRegBookSelect = 0x7F;      ///< BOOK — selects the book (always issued from page 0).
    static constexpr uint8_t kRegDeviceCtrl2 = 0x02;     ///< DEVICE_CTRL_2 — bit7 is DSPR (see kDeviceCtrl2DspStandbyBit).
    static constexpr uint8_t kRegDacMute = 0x03;         ///< DAC mute control — bit0 (left) / bit4 (right), see kMuteBothChannelsMask.
    static constexpr uint8_t kRegVolumeLeft = 61;        ///< Left channel digital volume, 0.5 dB/step.
    static constexpr uint8_t kRegVolumeRight = 62;       ///< Right channel digital volume, 0.5 dB/step.
    static constexpr uint8_t kRegVolumeRampSpeed = 64;   ///< Volume ramp speed code (startup/shutdown pop control).
    static constexpr uint8_t kRegFaultStatus1 = 94;      ///< Latched fault status byte 1.
    static constexpr uint8_t kRegFaultStatus2 = 95;      ///< Latched fault status byte 2.
    ///@}

    /**
     * @name DEVICE_CTRL_2 (B0-P0-R2) bits used by this driver
     * Only bit7 (DSPR) is used/confirmed; the remaining bits of this register
     * are not written by this driver.
     */
    ///@{
    static constexpr uint8_t kDeviceCtrl2DspStandbyBit = 0x80; ///< Bit7 DSPR: 1 = DSP out of standby, 0 = DSP held in standby.
    ///@}

    /**
     * @name B0-P0-R3 (DAC mute) bits used by this driver
     * Per hardware bring-up spec: both the left (bit0) and right (bit4) mute
     * bits are set together — there is no independent per-channel I2C mute
     * in this firmware's sequencing.
     */
    ///@{
    static constexpr uint8_t kMuteBothChannelsMask = 0x11; ///< bit0 (left) | bit4 (right).
    ///@}

    Tas3251() = default;

    /**
     * @brief Configure the GPIO lines (including the /FAULT and /CLIP_OTW
     *        falling-edge interrupts), resolve the I2C address from the ADR
     *        strap (AMP ADDRESS pin), and attach the device on @p bus.
     * @note Calls assertSafeState() as part of GPIO configuration, so
     *       RESET_AMP/DAC_MUTE end up asserted regardless of whether the
     *       caller already called assertSafeState() earlier.
     * @param bus Already-initialized shared I2C bus (see I2cBus::init()).
     * @return ESP_OK on success.
     */
    esp_err_t init(const I2cBus &bus);

    /**
     * @brief Configure RESET_AMP and DAC_MUTE as GPIO outputs and drive both
     *        low (asserted) immediately.
     * @note Per hardware bring-up spec, both lines are negative logic and
     *       must go down together as early as possible — call this as the
     *       very first action of SystemController::startup(), before any
     *       other peripheral (I2C bus, power rails, status LED) is touched,
     *       since it needs nothing but GPIO. init() also calls this, so
     *       calling it twice is harmless (it does not change an
     *       already-asserted level).
     */
    esp_err_t assertSafeState();

    /**
     * @brief Drive RESET_AMP (active low).
     * @param assertReset true = hold the amplifier in reset (drive low),
     *        false = release it (drive high).
     */
    esp_err_t reset(bool assertReset);

    /**
     * @brief Drive DAC_MUTE (active low, hardware mute independent of the
     *        I2C soft-mute register).
     * @param muteOn true = mute (drive low), false = unmute (drive high).
     */
    esp_err_t mute(bool muteOn);

    /**
     * @brief Set the I2C soft-mute bits (B0-P0-R3, kMuteBothChannelsMask —
     *        bit0 left + bit4 right), independent of the DAC_MUTE GPIO line.
     * @param muteOn true = set both mute bits, false = clear both.
     */
    esp_err_t setSoftMuteRegister(bool muteOn);

    /**
     * @brief Bring the DSP out of standby, or put it back into standby
     *        (B0-P0-R2 / DEVICE_CTRL_2, bit7 DSPR — kDeviceCtrl2DspStandbyBit).
     * @note Writes the whole register byte with only bit7 set/clear, on the
     *       assumption the register is still at its post-hardware-reset
     *       default (0x00) elsewhere — this driver does not use any other
     *       DEVICE_CTRL_2 bits.
     * @param exitStandby true = DSPR = 1 (out of standby), false = DSPR = 0
     *        (standby).
     */
    esp_err_t setDspStandby(bool exitStandby);

    /**
     * @brief Set per-channel digital volume (B0-P0-R61/R62), 0.5 dB/step,
     *        -103 dB to +24 dB per the hardware README register map.
     * @warning The dB-to-register-code formula here is UNVERIFIED against
     *          the TAS3251 datasheet (sign/zero-point of the encoding).
     *          SystemController deliberately starts at a conservative low
     *          volume regardless of this formula's correctness, but confirm
     *          the encoding before trusting absolute dB values in the field.
     */
    esp_err_t setVolumeDb(Channel channel, float db);

    /** @brief Set the volume ramp speed code (B0-P0-R64), raw register value. */
    esp_err_t setVolumeRampSpeed(uint8_t code);

    /** @brief Read the latched fault status (B0-P0-R94/R95). */
    esp_err_t readFaultStatus(FaultStatus &status);

    /** @brief True if the /FAULT ISR has fired since the last clearFaultLatch(). */
    bool isFaultLatched() const { return faultLatched_; }

    /** @brief True if the /CLIP_OTW ISR has fired since the last clearClipOtwLatch(). */
    bool isClipOtwLatched() const { return clipOtwLatched_; }

    /** @brief Acknowledge and clear the /FAULT latch tracked by this driver. */
    void clearFaultLatch() { faultLatched_ = false; }

    /** @brief Acknowledge and clear the /CLIP_OTW latch tracked by this driver. */
    void clearClipOtwLatch() { clipOtwLatched_ = false; }

    /**
     * @brief Select a book and page, per TI's book/page register addressing:
     *        selecting a new book always goes through page 0 first
     *        (register 0x7F selects the book while on page 0 of the current
     *        book, register 0x00 selects the page within a book).
     */
    esp_err_t selectBookPage(uint8_t book, uint8_t page);

    /** @brief Write one raw register byte in the currently selected book/page. */
    esp_err_t writeRegister(uint8_t reg, uint8_t value);

    /** @brief Read one raw register byte from the currently selected book/page. */
    esp_err_t readRegister(uint8_t reg, uint8_t &value);

private:
    static void IRAM_ATTR faultIsrThunk(void *arg);
    static void IRAM_ATTR clipOtwIsrThunk(void *arg);
    uint8_t resolveI2cAddress() const;

    i2c_master_dev_handle_t dev_ = nullptr;
    uint8_t currentBook_ = 0;
    /** 0xFF forces the first selectBookPage()/writeRegister(0,...) call to
     *  actually write the page register instead of assuming it is already
     *  correct. */
    uint8_t currentPage_ = 0xFF;
    volatile bool faultLatched_ = false;
    volatile bool clipOtwLatched_ = false;
};

} // namespace tas

#endif
