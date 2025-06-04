/*
  Mouse.cpp

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

#include "Mouse.h"

#if defined(_USING_HID)

static const uint8_t _hidReportDescriptor[] PROGMEM = {
    // Based on the provided HID descriptor
    0x05, 0x01,        // Usage Page (Generic Desktop)
    0x09, 0x02,        // Usage (Mouse)
    0xA1, 0x01,        // Collection (Application)
    0x85, 0x01,        // Report ID (1)
    0x09, 0x01,        // Usage (Pointer)
    0xA1, 0x00,        // Collection (Physical)
    
    // Button report
    0x05, 0x09,        // Usage Page (Button)
    0x19, 0x01,        // Usage Minimum (Button 1)
    0x29, 0x05,        // Usage Maximum (Button 5)
    0x15, 0x00,        // Logical Minimum (0)
    0x25, 0x01,        // Logical Maximum (1)
    0x95, 0x05,        // Report Count (5)
    0x75, 0x01,        // Report Size (1)
    0x81, 0x02,        // Input (Data,Var,Abs)
    0x95, 0x01,        // Report Count (1)
    0x75, 0x03,        // Report Size (3)
    0x81, 0x01,        // Input (Cnst,Ary,Abs)

    // X/Y movement
    0x05, 0x01,        // Usage Page (Generic Desktop)
    0x09, 0x30,        // Usage (X)
    0x09, 0x31,        // Usage (Y)
    0x16, 0x00, 0xF8,  // Logical Minimum (-2048)
    0x26, 0xFF, 0x07,  // Logical Maximum (2047)
    0x75, 0x10,        // Report Size (16)
    0x95, 0x02,        // Report Count (2)
    0x81, 0x06,        // Input (Data,Var,Rel)

    // Wheel movement
    0x09, 0x38,        // Usage (Wheel)
    0x15, 0x81,        // Logical Minimum (-127)
    0x25, 0x7F,        // Logical Maximum (127)
    0x75, 0x08,        // Report Size (8)
    0x95, 0x01,        // Report Count (1)
    0x81, 0x06,        // Input (Data,Var,Rel)

    0xC0,              // End Collection (Physical)
    0xC0               // End Collection (Application)
};

Mouse_::Mouse_(void) : _buttons(0)
{
    static HIDSubDescriptor node(_hidReportDescriptor, sizeof(_hidReportDescriptor));
    HID().AppendDescriptor(&node);
    memset(&_report, 0, sizeof(_report));
}

void Mouse_::begin(void)
{
}

void Mouse_::end(void)
{
}

void Mouse_::click(uint8_t b)
{
    _buttons = b;
    move(0, 0, 0);
    _buttons = 0;
    move(0, 0, 0);
}

void Mouse_::move(int16_t x, int16_t y, signed char wheel)
{
    _report.buttons = _buttons;
    _report.xAxis = x;
    _report.yAxis = y;
    _report.wheel = wheel;
    HID().SendReport(1, _report.raw, sizeof(_report));
}

void Mouse_::buttons(uint8_t b)
{
    if (b != _buttons)
    {
        _buttons = b;
        move(0, 0, 0);
    }
}

void Mouse_::press(uint8_t b)
{
    buttons(_buttons | b);
}

void Mouse_::release(uint8_t b)
{
    buttons(_buttons & ~b);
}

bool Mouse_::isPressed(uint8_t b)
{
    if ((b & _buttons) > 0)
        return true;
    return false;
}

void Mouse_::pan(signed char pan)
{
    uint8_t m[2];
    m[0] = pan;
    HID().SendReport(2, m, 2);
}

Mouse_ Mouse;

#endif
