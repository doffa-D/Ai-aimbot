import queue
import threading

from logic.config_watcher import cfg
from logic.logger import logger

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino
    
class Shooting(threading.Thread):
    def __init__(self):
        super(Shooting, self).__init__()
        self.queue = queue.Queue(maxsize=1)
        self.daemon = True
        self.name = 'Shooting'
        self.button_pressed = False
        self.lock = threading.Lock()
        
        self.start()
            
    def run(self):
        while True:
            try:
                bScope, shooting_state = self.queue.get()
                self.shoot(bScope, shooting_state)
            except Exception as e:
                logger.error("[Shooting] Shooting thread crashed: %s", e)
            
    def shoot(self, bScope, shooting_state):
        with self.lock:
            # By GetAsyncKeyState
            if cfg.auto_shoot and not cfg.triggerbot:
                if shooting_state and bScope or cfg.mouse_auto_aim and bScope:
                    if not self.button_pressed:
                        if cfg.arduino_shoot:  # arduino
                            arduino.press()

                        self.button_pressed = True

            if not shooting_state and self.button_pressed or not bScope and self.button_pressed:
                if cfg.arduino_shoot:  # arduino
                    arduino.release()

                self.button_pressed = False

            if shooting_state == False and self.button_pressed == True or bScope == False and self.button_pressed == True:
                if cfg.arduino_shoot: # arduino
                    arduino.release()
                
                self.button_pressed = False
        
        # By triggerbot
        if cfg.auto_shoot and cfg.triggerbot and bScope or cfg.mouse_auto_aim and bScope:
            if not self.button_pressed:
                if cfg.arduino_shoot:  # arduino
                    arduino.press()

                self.button_pressed = True

        if cfg.auto_shoot and cfg.triggerbot and not bScope:
            if self.button_pressed:
                if cfg.arduino_shoot:  # arduino
                    arduino.release()

                self.button_pressed = False
    
shooting = Shooting()