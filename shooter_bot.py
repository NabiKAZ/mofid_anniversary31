"""
Shooter Bot - Auto-click red boxes in Mofid Anniversary 31 shooter game
Uses computer vision to detect and click on small red boxes

Author: x.com/NabiKAZ
GitHub: https://github.com/NabiKAZ/mofid_anniversary31
Play the game: https://landing.emofid.com/anniversary40/login?invite_code=NV4NI3

Usage: python shooter_bot.py --calibrate --debug
"""

import cv2
import numpy as np
import pyautogui
import mss
import time
import argparse
from pynput import keyboard

# Global flag for emergency stop
emergency_stop = False

# Configuration constants
CLICK_DELAY = 0.5  # Delay between clicks in seconds
CLICK_HOLD_TIME = 0.1  # How long to hold mouse button down
DEBUG_SLEEP = 0.001  # Sleep time in debug mode
FPS_UPDATE_INTERVAL = 1.0  # How often to update FPS


def on_press(key):
    """Handle keyboard events for emergency stop"""
    global emergency_stop
    try:
        if key == keyboard.Key.esc:
            print("\n🛑 Emergency stop activated!")
            emergency_stop = True
            return False  # Stop listener
    except:
        pass


def start_keyboard_listener():
    """Start keyboard listener in background"""
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    return listener


def calibrate_region():
    """Calibrate game region by getting mouse positions"""
    print("\n=== Region Calibration ===")
    print("Move your mouse to the TOP-LEFT corner of the game window and press Enter...")
    input()
    top_left = pyautogui.position()
    print(f"Top-left position: {top_left}")
    
    print("\nMove your mouse to the BOTTOM-RIGHT corner of the game window and press Enter...")
    input()
    bottom_right = pyautogui.position()
    print(f"Bottom-right position: {bottom_right}")
    
    region = {
        'left': top_left[0],
        'top': top_left[1],
        'width': bottom_right[0] - top_left[0],
        'height': bottom_right[1] - top_left[1]
    }
    
    print(f"\n✓ Calibration complete!")
    print(f"Region: left={region['left']}, top={region['top']}, "
          f"width={region['width']}, height={region['height']}")
    
    return region


def find_red_boxes(frame, debug=False):
    """
    Find small red boxes in the frame
    Returns list of (x, y, w, h) tuples
    """
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Red color range in HSV (red wraps around in HSV)
    # Lower red range
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    
    # Upper red range
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    # Create masks for both red ranges
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    # Combine masks
    red_mask = cv2.bitwise_or(mask1, mask2)
    
    # Apply morphological operations to reduce noise
    kernel = np.ones((3, 3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    red_boxes = []
    for contour in contours:
        # Filter by area (small to medium sized boxes)
        area = cv2.contourArea(contour)
        if 100 < area < 5000:  # Adjust these values based on box size
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio (should be roughly square)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.8 < aspect_ratio < 1.2:
                # Check if it's approximately a quadrilateral (square/rectangle)
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                if len(approx) == 4:
                    red_boxes.append((x, y, w, h))
    
    return red_boxes, red_mask if debug else None


def click_box(box_x, box_y, region):
    """Click on a detected box"""
    # Calculate screen coordinates
    screen_x = region['left'] + box_x
    screen_y = region['top'] + box_y
    
    # Move and click with hold
    pyautogui.mouseDown(screen_x, screen_y)
    time.sleep(CLICK_HOLD_TIME)  # Hold for specified time
    pyautogui.mouseUp()
    print(f"  Clicked at ({screen_x}, {screen_y})")


def run_bot(region, debug=False, click_delay=CLICK_DELAY):
    """Main bot loop"""
    global emergency_stop
    
    print("\n=== Starting Shooter Bot ===")
    print(f"Region: {region}")
    print(f"Debug mode: {debug}")
    print(f"Click delay: {click_delay}s")
    print("\nPress ESC to stop")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    # Initialize screen capture
    sct = mss.mss()
    
    # FPS tracking
    fps_counter = 0
    fps_start_time = time.time()
    current_fps = 0
    
    # Statistics
    total_clicks = 0
    
    # Debug window
    if debug:
        cv2.namedWindow('Shooter Bot Debug', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Shooter Bot Debug', region['width'], region['height'])
        try:
            cv2.setWindowProperty('Shooter Bot Debug', cv2.WND_PROP_TOPMOST, 1)
        except:
            pass
    
    last_click_time = 0
    
    try:
        while not emergency_stop:
            # Capture screen
            screenshot = sct.grab(region)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Find red boxes
            red_boxes, debug_mask = find_red_boxes(frame, debug)
            
            # Click on boxes if enough time passed since last click
            current_time = time.time()
            if red_boxes and (current_time - last_click_time) >= click_delay:
                # Sort by y-position (top to bottom) then x-position (left to right)
                red_boxes.sort(key=lambda box: (box[1], box[0]))
                
                # Click the first box
                box = red_boxes[0]
                x, y, w, h = box
                click_x = x + w // 2
                click_y = y + h // 2
                
                click_box(click_x, click_y, region)
                total_clicks += 1
                last_click_time = current_time
            
            # Debug visualization
            if debug:
                debug_frame = frame.copy()
                
                # Draw detected boxes
                for x, y, w, h in red_boxes:
                    cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(debug_frame, (x + w // 2, y + h // 2), 5, (0, 255, 255), -1)
                
                # Add status text
                status_y = 30
                cv2.putText(debug_frame, f"FPS: {current_fps:.1f}", (10, status_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                status_y += 30
                cv2.putText(debug_frame, f"Red boxes: {len(red_boxes)}", (10, status_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                status_y += 30
                cv2.putText(debug_frame, f"Total clicks: {total_clicks}", (10, status_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                status_y += 30
                cv2.putText(debug_frame, "Press ESC for emergency stop", 
                           (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Show frames
                cv2.imshow('Shooter Bot Debug', debug_frame)
                if debug_mask is not None:
                    cv2.imshow('Red Mask', debug_mask)
                
                # Handle key press
                cv2.waitKey(1)
            else:
                time.sleep(DEBUG_SLEEP)  # Small delay when not in debug mode
            
            # Update FPS
            fps_counter += 1
            if time.time() - fps_start_time >= FPS_UPDATE_INTERVAL:
                current_fps = fps_counter / (time.time() - fps_start_time)
                fps_counter = 0
                fps_start_time = time.time()
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        print("\n=== Bot Stopped ===")
        print(f"Total clicks: {total_clicks}")
        
        if debug:
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Shooter Bot - Auto-click red boxes')
    parser.add_argument('--calibrate', '-c', action='store_true',
                       help='Calibrate game region interactively')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Show debug visualization window')
    parser.add_argument('--region', nargs=4, type=int, metavar=('LEFT', 'TOP', 'WIDTH', 'HEIGHT'),
                       help='Set game region manually')
    parser.add_argument('--delay', type=float, default=CLICK_DELAY,
                       help=f'Delay between clicks in seconds (default: {CLICK_DELAY})')
    
    args = parser.parse_args()
    
    # Start keyboard listener for emergency stop
    listener = start_keyboard_listener()
    
    # Get region
    if args.calibrate:
        region = calibrate_region()
    elif args.region:
        region = {
            'left': args.region[0],
            'top': args.region[1],
            'width': args.region[2],
            'height': args.region[3]
        }
        print(f"Using manual region: {region}")
    else:
        print("Error: Please specify --calibrate or --region")
        parser.print_help()
        return
    
    # Run bot
    run_bot(region, debug=args.debug, click_delay=args.delay)


if __name__ == "__main__":
    main()
