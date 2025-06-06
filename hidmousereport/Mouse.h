/*
  Mouse.h

  Copyright (c) 2015, Arduino LLC
  Original code (pre-library): Copyright (c) 2011, Peter Barrett

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/

#ifndef MOUSE_h
#define MOUSE_h

#include "HID.h"

#if !defined(_USING_HID)

#warning "Using legacy HID core (non pluggable)"

#else

//================================================================================
//================================================================================
//  Mouse

#define MOUSE_LEFT 1
#define MOUSE_RIGHT 2
#define MOUSE_MIDDLE 4
#define MOUSE_PREV 8
#define MOUSE_NEXT 16
#define MOUSE_ALL (MOUSE_LEFT | MOUSE_RIGHT | MOUSE_MIDDLE | MOUSE_PREV | MOUSE_NEXT)

typedef union {
    struct {
        uint8_t buttons : 5;  // 5 buttons
        uint8_t padding : 3;  // 3 padding bits
        int16_t xAxis;       // X movement (-2048 to 2047)
        int16_t yAxis;       // Y movement (-2048 to 2047)
        int8_t wheel;        // Wheel movement (-127 to 127)
    };
    uint8_t raw[6];         // Raw report data
} HID_MouseReport_Data_t;

class Mouse_
{
private:
    uint8_t _buttons;
    void buttons(uint8_t b);
    HID_MouseReport_Data_t _report;

public:
    Mouse_(void);
    void begin(void);
    void end(void);
    void click(uint8_t b = MOUSE_LEFT);
    void move(int x, int y, signed char wheel = 0);
    void press(uint8_t b = MOUSE_LEFT);
    void release(uint8_t b = MOUSE_LEFT);
    bool isPressed(uint8_t b = MOUSE_LEFT);
    void pan(signed char pan);
};
extern Mouse_ Mouse;

#endif
#endif