import serial
import time

class MouseController:
    def __init__(self, port='COM22', baudrate=115200):
        """Initialize the serial connection to Arduino."""
        self.serial = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset
        self.debug = True

    def click(self):
        """Send mouse click command."""
        if self.debug:
            print("Sending click command")
        self.serial.write(b'c\n')
        self.serial.flush()  # Ensure the command is sent immediately
        return self._read_response()

    def press(self):
        """Send mouse press command."""
        if self.debug:
            print("Sending press command")
        self.serial.write(b'p\n')
        self.serial.flush()
        return self._read_response()

    def release(self):
        """Send mouse release command."""
        if self.debug:
            print("Sending release command")
        self.serial.write(b'r\n')
        self.serial.flush()
        return self._read_response()

    def move(self, x, y):
        """Send mouse move command with x,y coordinates."""
        if self.debug:
            print(f"Moving mouse: x={x}, y={y}")
        command = f'm{x},{y}\n'
        self.serial.write(command.encode())
        self.serial.flush()
        return self._read_response()

    def _read_response(self):
        """Read and return the response from Arduino."""
        response = self.serial.readline().decode().strip()
        if self.debug and response:
            print(f"Arduino response: {response}")
        return response

    def close(self):
        """Close the serial connection."""
        self.serial.close()

def test_mouse_controls():
    """Test function to demonstrate various mouse controls."""
    try:
        mouse = MouseController()
        print("Connected to Arduino")

        # Test smooth mouse movement with minimal delay
        print("\nTesting mouse movement...")
        for i in range(4):  # Move in a square pattern
            mouse.move(50, 0)   # Right
            time.sleep(0.1)     # Reduced delay
            mouse.move(0, 50)   # Down
            time.sleep(0.1)
            mouse.move(-50, 0)  # Left
            time.sleep(0.1)
            mouse.move(0, -50)  # Up
            time.sleep(0.1)

        # Test click and move combination
        print("\nTesting click and move...")
        mouse.click()
        time.sleep(0.1)  # Minimal delay
        mouse.move(20, 20)
        time.sleep(0.1)
        
        # Test press, move, and release (drag operation)
        print("\nTesting drag operation...")
        mouse.press()
        time.sleep(0.1)
        mouse.move(30, 0)
        time.sleep(0.1)
        mouse.release()

        print("\nTest completed successfully!")

    except serial.SerialException as e:
        print(f"Error: {e}")
        print("Please check if the correct COM port is specified and Arduino is connected.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'mouse' in locals():
            mouse.close()

def interactive_test():
    """Interactive test function for debugging."""
    try:
        mouse = MouseController()
        print("Interactive Mouse Control Test")
        print("Commands:")
        print("  c - click")
        print("  p - press")
        print("  r - release")
        print("  m x,y - move (e.g., m 100,100)")
        print("  q - quit")

        while True:
            cmd = input("> ").strip().lower()
            if cmd == 'q':
                break
            elif cmd == 'c':
                mouse.click()
            elif cmd == 'p':
                mouse.press()
            elif cmd == 'r':
                mouse.release()
            elif cmd.startswith('m'):
                try:
                    _, coords = cmd.split(' ')
                    x, y = map(int, coords.split(','))
                    mouse.move(x, y)
                except:
                    print("Invalid move command. Format: m x,y")
            else:
                print("Unknown command")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'mouse' in locals():
            mouse.close()

if __name__ == "__main__":
    # Choose which test to run
    choice = input("Select test mode (1 for automatic, 2 for interactive): ")
    if choice == "1":
        test_mouse_controls()
    elif choice == "2":
        interactive_test()
    else:
        print("Invalid choice") 