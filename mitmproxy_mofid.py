"""
mitmproxy addon for Mofid Anniversary 31 game API interception
Intercepts game API endpoints to bypass validations and allow unlimited plays

Author: x.com/NabiKAZ
Usage: mitmweb --scripts mitmproxy_mofid.py

For more info: https://github.com/NabiKAZ/mofid_anniversary31
Play the game: https://landing.emofid.com/anniversary40/login?invite_code=NV4NI3
"""

from mitmproxy import http
import json


# Configuration flags
ENABLE_GAME_API_INTERCEPTION = True  # Controls can-start and finish-game interception
ENABLE_TEXTS_MODIFICATION = True     # Controls texts.json modification


class Anniversary40Interceptor:
    def __init__(self):
        print("[Anniversary40] Interceptor loaded!")
        print("[Anniversary40] Intercepting:")
        print("  - /api-service/anniversary40/can-start")
        print("  - /api-service/anniversary40/finish-game")
        print("  - /games/shooter/texts.json")
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept requests and return fake responses"""
        
        # Check if it's a request to can-start
        if ENABLE_GAME_API_INTERCEPTION and "landing.emofid.com" in flow.request.pretty_host and \
           "/api-service/anniversary40/can-start" in flow.request.path:
            
            # Create fake response
            fake_response = {
                "can_start": 1,
                "total_points": 0,
                "remaining_chances": 0
            }
            
            # Return fake response immediately
            flow.response = http.Response.make(
                200,  # Status code
                json.dumps(fake_response),  # Body
                {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
            
            print(f"[✓] Intercepted can-start for game: {flow.request.query.get('game', 'unknown')}")
            return
        
        # Check if it's a request to finish-game
        if ENABLE_GAME_API_INTERCEPTION and "landing.emofid.com" in flow.request.pretty_host and \
           "/api-service/anniversary40/finish-game" in flow.request.path:
            
            # Parse the original request to show what was sent
            try:
                request_body = json.loads(flow.request.content.decode('utf-8'))
                mission = request_body.get('mission_name', 'unknown')
                points = request_body.get('points_earned', 'unknown')
                print(f"[INFO] Game finished - Mission: {mission}, Points: {points[:20]}...")
            except:
                pass
            
            # Create fake response
            fake_response = {
                "success": True,
                "message": "Action recorded successfully"
            }
            
            # Return fake response immediately
            flow.response = http.Response.make(
                200,  # Status code
                json.dumps(fake_response),  # Body
                {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
            
            print(f"[✓] Intercepted finish-game - Fake success returned!")
            return
        
        # Check if it's a request to texts.json (shooter game questions)
        if ENABLE_TEXTS_MODIFICATION and "landing.emofid.com" in flow.request.pretty_host and \
           "/games/shooter/texts.json" in flow.request.path:
            print(f"[INFO] Intercepted texts.json request - will modify response")
    
    def response(self, flow: http.HTTPFlow) -> None:
        """Modify responses after they're received"""
        
        # Check if it's a response for texts.json
        if ENABLE_TEXTS_MODIFICATION and "landing.emofid.com" in flow.request.pretty_host and \
           "/games/shooter/texts.json" in flow.request.path:
            
            try:
                # Parse the original response
                texts_data = json.loads(flow.response.content.decode('utf-8'))
                
                # Modify each question: append type to text
                modified_count = 0
                for key, question in texts_data.items():
                    if isinstance(question, dict) and 'text' in question and 'type' in question:
                        # Append type to text in Persian
                        question_type = question['type']
                        type_label = " (✓ درست)🟩" if question_type == "true" else " (✗ غلط)🟥"
                        question['text'] = question['text'] + type_label
                        modified_count += 1
                
                # Update response with modified data
                flow.response.content = json.dumps(texts_data, ensure_ascii=False).encode('utf-8')
                
                print(f"[✓] Modified texts.json - {modified_count} questions updated with type labels")
                
            except Exception as e:
                print(f"[ERROR] Failed to modify texts.json: {e}")


# Create the addon instance
addons = [Anniversary40Interceptor()]
