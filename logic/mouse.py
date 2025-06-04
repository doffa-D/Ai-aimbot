import time
import math
import supervision as sv

from logic.config_watcher import cfg
from logic.visual import visuals
from logic.shooting import shooting
from logic.buttons import Buttons
from logic.logger import logger

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino

# Constants for stickiness logic
STICKY_MAX_DIST_REACQUIRE = 50  # Max distance (pixels) to associate a new detection with a locked target
STICKY_LOST_FRAMES_THRESHOLD = 5  # Frames to wait before unlocking if target not seen

# Non-aimable class IDs (based on visual.py definitions)
# 0:player, 1:bot, 2:weapon, 3:outline, 4:dead_body, 5:hideout_target_human, 6:hideout_target_balls, 7:head, 8:smoke, 9:fire, 10:third_person
NON_AIMABLE_CLS = [1, 2, 3, 4, 5, 6, 8, 9, 10] # Excludes player (0) and head (7)

class MouseThread:
    def __init__(self):
        self.initialize_parameters()

    def initialize_parameters(self):
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.prev_x = 0
        self.prev_y = 0
        self.prev_time = None
        self.max_distance = math.sqrt(self.screen_width**2 + self.screen_height**2) / 2
        self.min_speed_multiplier = cfg.mouse_min_speed_multiplier
        self.max_speed_multiplier = cfg.mouse_max_speed_multiplier
        self.prev_distance = None
        self.speed_correction_factor = 0.1
        self.bScope = False
        self.arch = self.get_arch()
        self.section_size_x = self.screen_width / 100
        self.section_size_y = self.screen_height / 100
        
        # Attributes for target locking/stickiness
        self.locked_target_details = None  # Stores dict: {'x', 'y', 'w', 'h', 'cls', 'dist_to_crosshair'}
        self.frames_locked_target_unseen = 0

    def get_arch(self):
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        if 'cpu' in cfg.AI_device:
            return 'cpu'
        return f'cuda:{cfg.AI_device}'

    def process_data(self, data):
        all_current_detections = []
        if isinstance(data, sv.Detections):
            if hasattr(data, 'xyxy') and data.xyxy.size > 0:
                for i in range(len(data.xyxy)):
                    box = data.xyxy[i]
                    cls_id = data.class_id[i] if hasattr(data, 'class_id') and data.class_id is not None and i < len(data.class_id) else None
                    # confidence = data.confidence[i] if hasattr(data, 'confidence') and data.confidence is not None and i < len(data.confidence) else None # Optional

                    # Filter out non-aimable classes early
                    if cls_id in NON_AIMABLE_CLS:
                        continue

                    center_x = (box[0] + box[2]) / 2
                    center_y = (box[1] + box[3]) / 2
                    width = box[2] - box[0]
                    height = box[3] - box[1]
                    
                    dist_to_crosshair = math.sqrt((center_x - self.center_x)**2 + (center_y - self.center_y)**2)
                    
                    all_current_detections.append({
                        'x': center_x, 'y': center_y, 'w': width, 'h': height, 'cls': cls_id,
                        'dist_to_crosshair': dist_to_crosshair
                    })
        elif isinstance(data, tuple) and len(data) == 5: # Handle the alternative raw format
            raw_target_x, raw_target_y, raw_target_w, raw_target_h, raw_target_cls = data
            dist_to_crosshair = math.sqrt((raw_target_x - self.center_x)**2 + (raw_target_y - self.center_y)**2)
            
            # Filter out non-aimable class for tuple data as well
            if raw_target_cls not in NON_AIMABLE_CLS:
                all_current_detections.append({
                    'x': raw_target_x, 'y': raw_target_y, 'w': raw_target_w, 'h': raw_target_h, 'cls': raw_target_cls,
                    'dist_to_crosshair': dist_to_crosshair
                })

        selected_target_for_frame = None

        if not all_current_detections:
            if self.locked_target_details:
                self.frames_locked_target_unseen += 1
                if self.frames_locked_target_unseen > cfg.mouse_sticky_lost_frames_threshold: # Use cfg
                    logger.info(f"[Mouse] Locked target (Class {self.locked_target_details.get('cls')}) lost after {self.frames_locked_target_unseen} unseen frames.")
                    self.locked_target_details = None
            
            if not self.locked_target_details: # Effectively, if no target is being tracked
                if cfg.show_window or cfg.show_overlay:
                    visuals.draw_target_line(None, None, None) # Signal to clear target line
                    visuals.draw_predicted_position(None, None, None) # Signal to clear prediction line
                return # No detections and no active lock, so do nothing
        else: # Current detections are available
            reacquired_match = None
            if self.locked_target_details:
                for det in all_current_detections:
                    # Check distance to last known locked target position
                    dist_to_locked_pos = math.sqrt((det['x'] - self.locked_target_details['x'])**2 + (det['y'] - self.locked_target_details['y'])**2)
                    if dist_to_locked_pos < cfg.mouse_sticky_max_dist_reacquire: # Use cfg
                        # Potential match. If multiple, prefer the one closer to crosshair (or stick to first good match)
                        if reacquired_match is None or det['dist_to_crosshair'] < reacquired_match['dist_to_crosshair']:
                            reacquired_match = det
            
            if reacquired_match:
                selected_target_for_frame = reacquired_match
                self.locked_target_details = selected_target_for_frame # Update lock with new position/details
                self.frames_locked_target_unseen = 0
                # logger.debug(f"[Mouse] Reacquired locked target: Class {selected_target_for_frame['cls']} at ({selected_target_for_frame['x']:.2f}, {selected_target_for_frame['y']:.2f})")
            else:
                # No reacquisition, or no previously locked target
                if self.locked_target_details: # Was locked, but not found in current frame
                    self.frames_locked_target_unseen += 1
                    if self.frames_locked_target_unseen > cfg.mouse_sticky_lost_frames_threshold: # Use cfg
                        logger.info(f"[Mouse] Locked target (Class {self.locked_target_details.get('cls')}) lost. Selecting new target from current detections.")
                        self.locked_target_details = None # Force new target selection
                    else:
                        # Target temporarily unseen, don't select a new one yet to avoid jitter. Do nothing this frame.
                        # logger.debug(f"[Mouse] Locked target temporarily unseen ({self.frames_locked_target_unseen} frames). Holding off selection.")
                        if cfg.show_window or cfg.show_overlay:
                            visuals.draw_target_line(None, None, None)
                            visuals.draw_predicted_position(None, None, None)
                        return

                if not self.locked_target_details: # True if lock was lost or never existed
                    all_current_detections.sort(key=lambda d: d['dist_to_crosshair'])
                    if all_current_detections: # Should be true if we are in this outer else block
                        selected_target_for_frame = all_current_detections[0]
                        self.locked_target_details = selected_target_for_frame
                        self.frames_locked_target_unseen = 0
                        logger.info(f"[Mouse] New target locked: Class {selected_target_for_frame['cls']} at ({selected_target_for_frame['x']:.2f}, {selected_target_for_frame['y']:.2f})")

        if not selected_target_for_frame:
            # This case should ideally be covered by returns above if no target is to be processed
            # logger.debug("[Mouse] No target selected for this frame after all logic.")
            if cfg.show_window or cfg.show_overlay:
                visuals.draw_target_line(None, None, None)
                visuals.draw_predicted_position(None, None, None)
            return

        # --- Original processing logic starts here, using the selected_target_for_frame --- 
        target_x = selected_target_for_frame['x']
        target_y = selected_target_for_frame['y']
        target_w = selected_target_for_frame['w']
        target_h = selected_target_for_frame['h']
        target_cls = selected_target_for_frame['cls']

        # --- Aim Point Adjustment based on cfg.mouse_aim_part and target_cls ---
        if cfg.mouse_aim_part == 'head_preferred':
            if target_cls == 0: # Player/Body
                target_y -= target_h * 0.25 # Aim for upper 25% of body bounding box
            # If target_cls is 7 (head), it will aim at its center by default (no change needed here)
        elif cfg.mouse_aim_part == 'body_upper_only':
            if target_cls == 0: # Player/Body
                target_y -= target_h * 0.25 # Aim for upper 25% of body bounding box
            # If head, still aims at center of head bounding box.
        # Else (cfg.mouse_aim_part == 'center'), no adjustment, aims at the center of the selected box.

        self.visualize_target(target_x, target_y, target_cls)
        self.bScope = self.check_target_in_scope(target_x, target_y, target_w, target_h, self.bScope_multiplier) if cfg.auto_shoot or cfg.triggerbot else False
        self.bScope = cfg.force_click or self.bScope

        # Log which target is being aimed at (using the now stable selected target)
        if target_cls is not None:
            if target_cls == 0: # Assuming 0 is 'player' based on prior user edit
                 logger.info(f"[Mouse] Aiming at player {target_cls} at X: {target_x:.2f}, Y: {target_y:.2f}")
            # Add other specific class logging if needed, e.g., from self.cls_model_data in visuals.py
            # elif target_cls == 7: # head
            #     logger.info(f"[Mouse] Aiming at head ({target_cls}) at X: {target_x:.2f}, Y: {target_y:.2f}")
            else:
                 logger.info(f"[Mouse] Aiming at target class: {target_cls} at X: {target_x:.2f}, Y: {target_y:.2f}")
        else:
            logger.info(f"[Mouse] Aiming at target (no class ID) at X: {target_x:.2f}, Y: {target_y:.2f}")

        if not self.disable_prediction:
            current_time = time.time()
            # Prediction should use the selected target_x, target_y
            predicted_target_x, predicted_target_y = self.predict_target_position(target_x, target_y, current_time)
            self.visualize_prediction(predicted_target_x, predicted_target_y, target_cls)
            # Use predicted coordinates for movement calculation if prediction is on
            move_x, move_y = self.calc_movement(predicted_target_x, predicted_target_y, target_cls)
        else:
            move_x, move_y = self.calc_movement(target_x, target_y, target_cls)
        
        self.visualize_history(target_x, target_y) # History of raw selected target
        shooting.queue.put((self.bScope, self.get_shooting_key_state()))
        self.move_mouse(move_x, move_y)

    def predict_target_position(self, target_x, target_y, current_time):
        # First target
        if self.prev_time is None:
            self.prev_time = current_time
            self.prev_x = target_x
            self.prev_y = target_y
            self.prev_velocity_x = 0
            self.prev_velocity_y = 0
            return target_x, target_y
        
        # Next target?
        max_jump = max(self.screen_width, self.screen_height) * 0.3 # 30%
        if abs(target_x - self.prev_x) > max_jump or abs(target_y - self.prev_y) > max_jump:
            self.prev_x, self.prev_y = target_x, target_y
            self.prev_velocity_x = 0
            self.prev_velocity_y = 0
            self.prev_time = current_time
            return target_x, target_y

        delta_time = current_time - self.prev_time
        
        if delta_time == 0:
            delta_time = 1e-6
    
        velocity_x = (target_x - self.prev_x) / delta_time
        velocity_y = (target_y - self.prev_y) / delta_time
        acceleration_x = (velocity_x - self.prev_velocity_x) / delta_time
        acceleration_y = (velocity_y - self.prev_velocity_y) / delta_time

        prediction_interval = delta_time * self.prediction_interval
        current_distance = math.sqrt((target_x - self.prev_x)**2 + (target_y - self.prev_y)**2)
        proximity_factor = max(0.1, min(1, 1 / (current_distance + 1)))

        speed_correction = 1 + (abs(current_distance - (self.prev_distance or 0)) / self.max_distance) * self.speed_correction_factor if self.prev_distance is not None else .0001

        predicted_x = target_x + velocity_x * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_x * (prediction_interval ** 2) * proximity_factor * speed_correction
        predicted_y = target_y + velocity_y * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_y * (prediction_interval ** 2) * proximity_factor * speed_correction

        self.prev_x, self.prev_y = target_x, target_y
        self.prev_velocity_x, self.prev_velocity_y = velocity_x, velocity_y
        self.prev_time = current_time
        self.prev_distance = current_distance

        return predicted_x, predicted_y

    def calculate_speed_multiplier(self, target_x, target_y, distance):
        if any(map(math.isnan, (target_x, target_y))) or self.section_size_x == 0:
            return self.min_speed_multiplier
    
        normalized_distance = min(distance / self.max_distance, 1)
        base_speed = self.min_speed_multiplier + (self.max_speed_multiplier - self.min_speed_multiplier) * (1 - normalized_distance)
        
        if self.section_size_x == 0:
            return self.min_speed_multiplier

        target_x_section = int((target_x - self.center_x + self.screen_width / 2) / self.section_size_x)
        target_y_section = int((target_y - self.center_y + self.screen_height / 2) / self.section_size_y)
        
        distance_from_center = max(abs(50 - target_x_section), abs(50 - target_y_section))
        
        if distance_from_center == 0:
            return 1
        elif 5 <= distance_from_center <= 10:
            return self.max_speed_multiplier
        else:
            speed_reduction = min(distance_from_center - 10, 45) / 100.0
            speed_multiplier = base_speed * (1 - speed_reduction)

        if self.prev_distance is not None:
            speed_adjustment = 1 + (abs(distance - self.prev_distance) / self.max_distance) * self.speed_correction_factor
            return speed_multiplier * speed_adjustment
        
        return speed_multiplier

    def calc_movement(self, target_x, target_y, target_cls):
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, distance)

        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height

        mouse_move_x = offset_x * degrees_per_pixel_x
        mouse_move_y = offset_y * degrees_per_pixel_y

        # Apply smoothing
        alpha = 0.85
        if not hasattr(self, 'last_move_x'):
            self.last_move_x, self.last_move_y = 0, 0
        
        move_x = alpha * mouse_move_x + (1 - alpha) * self.last_move_x
        move_y = alpha * mouse_move_y + (1 - alpha) * self.last_move_y
        
        self.last_move_x, self.last_move_y = move_x, move_y

        move_x = (move_x / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier
        move_y = (move_y / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier

        return move_x, move_y

    def move_mouse(self, x, y):
        if x == 0 and y == 0:
            return

        primary_aim_active = self.get_shooting_key_state()

        button_2_pressed = False
        # Check Arduino button 2 state only if Arduino movement is configured,
        # as arduino object might not be available otherwise and movement relies on it.
        if cfg.arduino_move:
            try:
                # arduino.is_button_pressed(2) will check the state of button ID 2
                button_2_pressed = arduino.is_button_pressed(2)
            except NameError: # Should not happen if cfg.arduino_move is true due to conditional import
                logger.error("[Mouse] Arduino object not available for button 2 check, though cfg.arduino_move is true. This is unexpected.")
            except Exception as e:
                logger.error(f"[Mouse] Error checking Arduino button 2 state: {e}")
                # Keep button_2_pressed as False to prevent movement on error

        # Move if primary aim is active, or auto-aim is on, or Arduino button 2 is pressed
        should_move = primary_aim_active or cfg.mouse_auto_aim or button_2_pressed

        if should_move:
            if cfg.arduino_move:
                arduino.move(int(x), int(y))
            # If cfg.arduino_move is False, no movement occurs via Arduino.
            # If you had a non-Arduino way to move, it would go in an else here.
        else:
            pass # No conditions met for movement

    def get_shooting_key_state(self):
        if cfg.arduino_shoot: # Arduino shooting is enabled
            if hasattr(cfg, 'arduino_aim_button_id'):
                try:
                    aim_button_id = int(cfg.arduino_aim_button_id)
                    return arduino.is_button_pressed(aim_button_id)
                except ValueError:
                    logger.error(f'[Mouse] cfg.arduino_aim_button_id ("{cfg.arduino_aim_button_id}") is not a valid integer. Arduino aiming will not occur.')
                    return False
                except Exception as e:
                    logger.error(f'[Mouse] Error checking Arduino button state: {e}. Arduino aiming will not occur.')
                    return False
            else:
                logger.warning('[Mouse] arduino_shoot is True, but cfg.arduino_aim_button_id is not defined. Arduino aiming will not occur.')
                return False
        else:
            # arduino_shoot is False, and we are not using win32api for keyboard fallback.
            # Therefore, shooting state will be false.
            # logger.debug('[Mouse] arduino_shoot is False. No keyboard hotkey check implemented as per user request.') # Optional: for verbosity
            return False

    def check_target_in_scope(self, target_x, target_y, target_w, target_h, reduction_factor):
        reduced_w, reduced_h = target_w * reduction_factor / 2, target_h * reduction_factor / 2
        x1, x2, y1, y2 = target_x - reduced_w, target_x + reduced_w, target_y - reduced_h, target_y + reduced_h
        bScope = self.center_x > x1 and self.center_x < x2 and self.center_y > y1 and self.center_y < y2
        
        if cfg.show_window and cfg.show_bScope_box:
            visuals.draw_bScope(x1, x2, y1, y2, bScope)
        
        return bScope

    def update_settings(self):
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2

        # Reset stickiness state on settings update too, in case screen dimensions change
        self.locked_target_details = None
        self.frames_locked_target_unseen = 0

    def visualize_target(self, target_x, target_y, target_cls):
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, target_cls)

    def visualize_prediction(self, target_x, target_y, target_cls):
        if (cfg.show_window and cfg.show_target_prediction_line) or (cfg.show_overlay and cfg.show_target_prediction_line):
            visuals.draw_predicted_position(target_x, target_y, target_cls)

    def visualize_history(self, target_x, target_y):
        if (cfg.show_window and cfg.show_history_points) or (cfg.show_overlay and cfg.show_history_points):
            visuals.draw_history_point_add_point(target_x, target_y)

mouse = MouseThread()