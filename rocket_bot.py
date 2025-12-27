#!/usr/bin/env python3
"""
Rocket Game Bot - Automated player for Mofid Anniversary 31 game
Uses computer vision to detect and collect items while avoiding obstacles

Author: x.com/NabiKAZ
GitHub: https://github.com/NabiKAZ/mofid_anniversary31
Play the game: https://landing.emofid.com/anniversary40/login?invite_code=NV4NI3

Uses screen capture and image processing to:
1. Run: python rocket_bot.py --calibrate --debug
2. Detect the rocket position
3. Find white/colored item boxes to collect
4. Avoid fireballs
5. Control mouse to move the rocket
"""

import cv2
import numpy as np
import pyautogui
import time
import mss
from PIL import Image
import threading
from pynput import keyboard
import threading
from pynput import keyboard

# Disable pyautogui fail-safe for smoother control
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

# Configuration constants
ROCKET_MOVE_DURATION = 0.15  # Duration for rocket movement
TARGET_MOVE_DURATION = 0.1   # Duration for target movement
POST_MOVE_SLEEP = 0.1        # Sleep after movement
GAME_REGISTER_SLEEP = 0.2    # Wait for game to register action
FPS_SLEEP = 0.016            # Sleep for ~60 FPS
FPS_UPDATE_INTERVAL = 1.0    # How often to update FPS

class RocketBot:
    def __init__(self):
        self.sct = mss.mss()
        self.game_region = None
        self.rocket_pos = None
        self.running = False
        self.mouse_pressed = False
        self.emergency_stop = False
        self.last_mouse_x = None
        self.last_mouse_x = None
        
    def find_game_window(self):
        """Find the game region on screen by looking for the game UI elements"""
        # Take a screenshot
        screenshot = np.array(self.sct.grab(self.sct.monitors[1]))
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        
        # Look for the teal/dark cyan header color (approximate)
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Teal color range for the header
        lower_teal = np.array([80, 50, 50])
        upper_teal = np.array([100, 255, 255])
        mask = cv2.inRange(hsv, lower_teal, upper_teal)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find the largest teal region (likely the game header)
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            
            # Estimate game region based on header
            # Game is typically below the header
            self.game_region = {
                'left': x,
                'top': y,
                'width': w,
                'height': int(w * 1.8)  # Approximate aspect ratio
            }
            print(f"[INFO] Game region found: {self.game_region}")
            return True
        
        print("[WARN] Could not find game window automatically")
        return False
    
    def set_game_region(self, left, top, width, height):
        """Manually set the game region"""
        self.game_region = {
            'left': left,
            'top': top,
            'width': width,
            'height': height
        }
        print(f"[INFO] Game region set: {self.game_region}")
    
    def capture_game(self):
        """Capture the game screen"""
        if not self.game_region:
            return None
        
        screenshot = np.array(self.sct.grab(self.game_region))
        return cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
    
    def find_rocket(self, frame):
        """Find the rocket position in the frame"""
        # The rocket has a distinctive purple/magenta color
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Purple/Magenta color range for the rocket
        lower_purple = np.array([130, 50, 50])
        upper_purple = np.array([160, 255, 255])
        mask = cv2.inRange(hsv, lower_purple, upper_purple)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find the rocket (should be a reasonably sized object)
            for contour in sorted(contours, key=cv2.contourArea, reverse=True):
                area = cv2.contourArea(contour)
                if 500 < area < 10000:  # Reasonable size for rocket
                    M = cv2.moments(contour)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        self.rocket_pos = (cx, cy)
                        return (cx, cy)
        
        return self.rocket_pos  # Return last known position
    
    def find_items(self, frame):
        """Find collectible items (white/light colored boxes)"""
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # White/light color range for items
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        items = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 1000 < area < 20000:  # Item size range
                x, y, w, h = cv2.boundingRect(contour)
                # Check if it's roughly square (item boxes)
                aspect_ratio = w / h if h > 0 else 0
                if 0.5 < aspect_ratio < 2.0:
                    cx = x + w // 2
                    cy = y + h // 2
                    items.append((cx, cy, area))
        
        return items
    
    def find_fireballs(self, frame):
        """Find fireballs to avoid (orange/red colored)"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Orange/Red color range for fireballs
        lower_orange = np.array([5, 100, 100])
        upper_orange = np.array([25, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        
        # Also detect bright yellow/orange flames
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([35, 255, 255])
        mask2 = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        mask = cv2.bitwise_or(mask, mask2)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fireballs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 2000:  # Fireball size threshold
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2
                # Add a danger zone around the fireball
                fireballs.append({
                    'center': (cx, cy),
                    'bounds': (x, y, w, h),
                    'danger_radius': max(w, h)
                })
        
        return fireballs
    
    def calculate_safe_move(self, rocket_pos, items, fireballs, frame_width):
        """Calculate the best move to collect items while avoiding fireballs"""
        if not rocket_pos:
            return None
        
        rx, ry = rocket_pos
        
        # Calculate danger zones from fireballs
        danger_zones = []
        for fb in fireballs:
            fcx, fcy = fb['center']
            radius = fb['danger_radius'] * 1.5  # Add safety margin
            danger_zones.append((fcx, fcy, radius))
        
        # Check if position is safe
        def is_safe(x, y):
            for dx, dy, radius in danger_zones:
                dist = np.sqrt((x - dx)**2 + (y - dy)**2)
                if dist < radius:
                    return False
            return True
        
        # Find the best target (closest safe item)
        best_target = None
        best_score = float('inf')
        
        for item in items:
            ix, iy, area = item
            
            # Check if path to item is relatively safe
            path_safe = True
            for t in np.linspace(0, 1, 5):
                px = int(rx + t * (ix - rx))
                py = int(ry + t * (iy - ry))
                if not is_safe(px, py):
                    path_safe = False
                    break
            
            if path_safe:
                dist = np.sqrt((ix - rx)**2 + (iy - ry)**2)
                if dist < best_score:
                    best_score = dist
                    best_target = (ix, iy)
        
        # If no safe item, try to avoid fireballs
        if not best_target:
            # Find safest horizontal position
            safe_x = rx
            min_danger = float('inf')
            
            for test_x in range(50, frame_width - 50, 20):
                danger_score = 0
                for dx, dy, radius in danger_zones:
                    dist = np.sqrt((test_x - dx)**2 + (ry - dy)**2)
                    if dist < radius * 2:
                        danger_score += (radius * 2 - dist)
                
                if danger_score < min_danger:
                    min_danger = danger_score
                    safe_x = test_x
            
            best_target = (safe_x, ry)
        
        return best_target
    
    def move_rocket(self, target_x, rocket_pos):
        """Move the rocket by dragging the mouse"""
        if not self.game_region or not rocket_pos:
            return
        
        # Calculate absolute screen positions
        rocket_screen_x = self.game_region['left'] + rocket_pos[0]
        rocket_screen_y = self.game_region['top'] + rocket_pos[1]
        
        target_screen_x = self.game_region['left'] + target_x
        target_screen_y = rocket_screen_y  # Keep same Y position as rocket
        
        # First time: move to rocket and press mouse
        if not self.mouse_pressed:
            print(f"[DEBUG] Moving to rocket at screen: ({rocket_screen_x}, {rocket_screen_y})")
            print(f"[DEBUG] Rocket in frame: {rocket_pos}")
            # Move cursor to rocket
            pyautogui.moveTo(rocket_screen_x, rocket_screen_y, duration=ROCKET_MOVE_DURATION)
            time.sleep(POST_MOVE_SLEEP)
            # Press and hold mouse button
            pyautogui.mouseDown(button='left')
            self.mouse_pressed = True
            print("[INFO] ✓ Mouse button pressed on rocket!")
            time.sleep(GAME_REGISTER_SLEEP)  # Wait for game to register
            return  # Don't move on first grab
        
        # Continuously drag to follow target
        current_x, current_y = pyautogui.position()
        print(f"[DEBUG] Current mouse: ({current_x}, {current_y}) -> Target: ({target_screen_x}, {target_screen_y})")
        
        # Smooth drag to target position
        pyautogui.moveTo(target_screen_x, target_screen_y, duration=TARGET_MOVE_DURATION)
    
    def on_press(self, key):
        """Handle keyboard press for emergency stop"""
        try:
            if key == keyboard.Key.esc or key == keyboard.Key.f12:
                print("\n[INFO] Emergency stop triggered!")
                self.emergency_stop = True
                self.running = False
        except AttributeError:
            pass
    
    def start_keyboard_listener(self):
        """Start keyboard listener in background thread"""
        listener = keyboard.Listener(on_press=self.on_press)
        listener.daemon = True
        listener.start()
    
    def run(self, debug=False):
        """Main bot loop"""
        print("[INFO] Starting Rocket Bot...")
        print("[INFO] Press ESC or F12 to stop the bot")
        print("[INFO] Bot will hold mouse button and drag rocket")
        
        # Start keyboard listener
        self.start_keyboard_listener()
        
        self.running = True
        
        # Create debug window if needed (will be sized properly on first frame)
        if debug:
            print("[INFO] Debug window will open - Press Q in debug window to quit")
        
        try:
            while self.running and not self.emergency_stop:
                # Capture game screen
                frame = self.capture_game()
                if frame is None:
                    time.sleep(POST_MOVE_SLEEP)
                    continue
                
                # Find game elements
                rocket_pos = self.find_rocket(frame)
                items = self.find_items(frame)
                fireballs = self.find_fireballs(frame)
                
                # Calculate and execute move
                if rocket_pos:
                    target = self.calculate_safe_move(
                        rocket_pos, items, fireballs, frame.shape[1]
                    )
                    
                    if target:
                        self.move_rocket(target[0], rocket_pos)
                # Debug visualization
                if debug:
                    debug_frame = frame.copy()
                    
                    # Draw rocket with MAGENTA (بنفش) box
                    if rocket_pos:
                        cv2.rectangle(debug_frame, 
                                    (rocket_pos[0]-30, rocket_pos[1]-40), 
                                    (rocket_pos[0]+30, rocket_pos[1]+40), 
                                    (255, 0, 255), 3)  # Magenta/Purple
                        cv2.putText(debug_frame, "ROCKET", (rocket_pos[0]-30, rocket_pos[1]-45),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    # Draw items with GREEN (سبز) boxes
                    for item in items:
                        cv2.rectangle(debug_frame, 
                                    (item[0]-25, item[1]-25), 
                                    (item[0]+25, item[1]+25), 
                                    (0, 255, 0), 3)  # Green
                        cv2.putText(debug_frame, "ITEM", (item[0]-20, item[1]-35),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Draw fireballs with RED (قرمز) boxes
                    for fb in fireballs:
                        x, y, w, h = fb['bounds']
                        cv2.rectangle(debug_frame, (x, y), (x+w, y+h), (0, 0, 255), 3)  # Red
                        cv2.putText(debug_frame, "DANGER!", (x, y-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        # Draw danger zone circle
                        cx, cy = fb['center']
                        danger_radius = int(fb['danger_radius'] * 1.5)
                        cv2.circle(debug_frame, (cx, cy), danger_radius, (0, 0, 255), 1)
                    
                    # Draw target with YELLOW (زرد) marker
                    if target:
                        cv2.circle(debug_frame, target, 15, (0, 255, 255), 3)
                        cv2.line(debug_frame, (target[0]-20, target[1]), (target[0]+20, target[1]), (0, 255, 255), 2)
                        cv2.line(debug_frame, (target[0], target[1]-20), (target[0], target[1]+20), (0, 255, 255), 2)
                    
                    # Add legend
                    legend_y = 30
                    cv2.rectangle(debug_frame, (10, legend_y-20), (200, legend_y+80), (0, 0, 0), -1)
                    cv2.rectangle(debug_frame, (10, legend_y-20), (200, legend_y+80), (255, 255, 255), 1)
                    cv2.putText(debug_frame, "ROCKET (Magenta)", (20, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                    cv2.putText(debug_frame, "ITEMS (Green)", (20, legend_y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.putText(debug_frame, "DANGER (Red)", (20, legend_y+50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    cv2.putText(debug_frame, "TARGET (Yellow)", (20, legend_y+75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    # Add status info
                    status_text = f"Rocket: {'Found' if rocket_pos else 'Lost'} | Items: {len(items)} | Dangers: {len(fireballs)}"
                    cv2.putText(debug_frame, status_text, (10, debug_frame.shape[0]-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Show debug window with original size (no stretching)
                    cv2.namedWindow("Rocket Bot Debug", cv2.WINDOW_AUTOSIZE)
                    cv2.setWindowProperty("Rocket Bot Debug", cv2.WND_PROP_TOPMOST, 1)
                    cv2.imshow("Rocket Bot Debug", debug_frame)
                    
                    key = cv2.waitKey(10) & 0xFF
                    if key == ord('q') or key == 27:  # q or ESC
                        print("[INFO] Debug window closed")
                        break
                
                # Small delay to prevent CPU overload
                time.sleep(FPS_SLEEP)  # ~60 FPS
                
        except KeyboardInterrupt:
            print("\n[INFO] Bot stopped by user")
        finally:
            self.running = False
            # Release mouse button if it was pressed
            if self.mouse_pressed:
                pyautogui.mouseUp()
                print("[INFO] Mouse button released")
            if debug:
                cv2.destroyAllWindows()
            print("[INFO] Bot stopped successfully")


def calibrate_region():
    """Interactive calibration to select game region"""
    print("\n=== Game Region Calibration ===")
    print("Move your mouse to the TOP-LEFT corner of the game and press Enter...")
    input()
    x1, y1 = pyautogui.position()
    print(f"Top-left: ({x1}, {y1})")
    
    print("Now move your mouse to the BOTTOM-RIGHT corner of the game and press Enter...")
    input()
    x2, y2 = pyautogui.position()
    print(f"Bottom-right: ({x2}, {y2})")
    
    return x1, y1, x2 - x1, y2 - y1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rocket Game Bot")
    parser.add_argument("--debug", "-d", action="store_true", help="Show debug visualization")
    parser.add_argument("--calibrate", "-c", action="store_true", help="Calibrate game region")
    parser.add_argument("--region", "-r", type=int, nargs=4, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
                       help="Set game region manually")
    args = parser.parse_args()
    
    bot = RocketBot()
    
    # Set or calibrate game region
    if args.calibrate:
        left, top, width, height = calibrate_region()
        bot.set_game_region(left, top, width, height)
    elif args.region:
        bot.set_game_region(*args.region)
    else:
        # Try auto-detection or use default
        if not bot.find_game_window():
            print("\n[INFO] Auto-detection failed. Running calibration...")
            left, top, width, height = calibrate_region()
            bot.set_game_region(left, top, width, height)
    
    print("\n[INFO] Starting in 3 seconds... Focus on the game!")
    time.sleep(3)
    
    bot.run(debug=args.debug)
