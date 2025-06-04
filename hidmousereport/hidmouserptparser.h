#if !defined(__HIDMOUSERPTPARSER_H__)

#define __HIDMOUSERPTPARSER_H__

#include <usbhid.h>

// Movement smoothing configuration -- REMOVING THESE AS THEY ARE NO LONGER USED IN THE PARSER
// #define MOVEMENT_HISTORY_SIZE 3
// #define MOVEMENT_THRESHOLD 5

// Button definitions
#define BUTTON_LEFT    0x01  // Bit 0 (1)
#define BUTTON_RIGHT   0x02  // Bit 1 (2)
#define BUTTON_MIDDLE  0x04  // Bit 2 (4)
#define BUTTON_BACK    0x08  // Bit 3 (8)
#define BUTTON_FORWARD 0x10  // Bit 4 (16)

void onButtonUp(uint16_t buttonId) __attribute__((weak));
void onButtonDown(uint16_t buttonId) __attribute__((weak));
void onTiltPress(int8_t tiltValue) __attribute__((weak));
void onMouseMove(int16_t xMovement, int16_t yMovement, int8_t scrollValue) __attribute__((weak));
void onScroll(int8_t scrollValue) __attribute__((weak));

// Process button state changes
inline void ProcessButton(bool prevPressed, bool newPressed, uint8_t buttonBit, uint8_t reportButton);

class HIDMouseReportParser : public HIDReportParser
{
private:
	uint8_t prevButtonsRaw;  // Changed from previousButtonsState to match your code
	
public:
	HIDMouseReportParser(void *);
	virtual void Parse(USBHID *hid, bool is_rpt_id, uint8_t len, uint8_t *buf);
};

#endif//__HIDMOUSERPTPARSER_H__