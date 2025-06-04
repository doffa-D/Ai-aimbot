#include "hidmouserptparser.h"
#include "Mouse.h"

HIDMouseReportParser::HIDMouseReportParser(void *) : prevButtonsRaw(0) {
    // Initialize movement history to zero
    // moveHistory.index = 0;
    // for (int i = 0; i < MOVEMENT_HISTORY_SIZE; ++i) {
    //     moveHistory.x[i] = 0;
    //     moveHistory.y[i] = 0;
    // }
}

void HIDMouseReportParser::Parse(USBHID *hid, bool is_rpt_id, uint8_t len, uint8_t *buf)
{
    if (len < 6) return;
    
    // Get button byte directly (second byte of report)
    uint8_t btn = buf[1];

    // Process buttons using raw button byte
    ProcessButton((prevButtonsRaw & BUTTON_LEFT) != 0,  (btn & BUTTON_LEFT) != 0,  BUTTON_LEFT,   MOUSE_LEFT);
    ProcessButton((prevButtonsRaw & BUTTON_RIGHT) != 0, (btn & BUTTON_RIGHT) != 0, BUTTON_RIGHT,  MOUSE_RIGHT);
    ProcessButton((prevButtonsRaw & BUTTON_MIDDLE) != 0,(btn & BUTTON_MIDDLE) != 0,BUTTON_MIDDLE, MOUSE_MIDDLE);
    ProcessButton((prevButtonsRaw & BUTTON_BACK) != 0,  (btn & BUTTON_BACK) != 0,  BUTTON_BACK,   MOUSE_PREV);
    ProcessButton((prevButtonsRaw & BUTTON_FORWARD) != 0,(btn & BUTTON_FORWARD) != 0,BUTTON_FORWARD,MOUSE_NEXT);
    // Save current buttons for next comparison
    prevButtonsRaw = btn;

    // Branchless sign-extend for 12-bit values using XOR-sub trick
    uint16_t rawX = buf[2] | ((uint16_t)(buf[3] & 0x0F) << 8);
    int16_t deltaX = (int16_t)((rawX ^ 0x800) - 0x800);
    uint16_t rawY = ((uint16_t)(buf[3] >> 4)) | ((uint16_t)buf[4] << 4);
    int16_t deltaY = (int16_t)((rawY ^ 0x800) - 0x800);

    if (deltaX != 0 || deltaY != 0) {
        // Call onMouseMove callback with raw delta values
        if (::onMouseMove) 
        {
            ::onMouseMove(deltaX, deltaY, 0);
        }
    }

    // Handle wheel movement directly
    int8_t wheelVal = (int8_t)buf[5];
    if (wheelVal != 0) {
        // Call onScroll callback
        if (::onScroll)
        {
            ::onScroll(wheelVal);
        }
    }
}

// Process button state changes
inline void ProcessButton(bool prevPressed, bool newPressed, uint8_t buttonBit, uint8_t reportButton)
{
    if (prevPressed != newPressed)
    {
        if (newPressed) {
            // Call onButtonDown callback
            if (::onButtonDown)
            {
                ::onButtonDown(reportButton);
            }
        } else {
            // Call onButtonUp callback
            if (::onButtonUp)
            {
                ::onButtonUp(reportButton);
            }
        }
    }
}
