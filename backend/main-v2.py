import os
import json
import time
import threading
import cv2
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

MONITORS_FILE = 'monitors.json'
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def load_monitors():
    if not os.path.exists(MONITORS_FILE):
        return []
    with open(MONITORS_FILE, 'r') as f:
        return json.load(f)

def save_monitors(monitors):
    with open(MONITORS_FILE, 'w') as f:
        json.dump(monitors, f, indent=2)

def send_notification(integrations, message):
    """
    Sends alerts based on user selection.
    For Hackathon: Print to console allows judges to see it works.
    """
    if not integrations: return

    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if "WhatsApp" in integrations:
        # Real impl: Use Twilio API
        print(f"\n[WHATSAPP ALERT {timestamp}] 📲 Sending to User: {message}")
        
    if "Email" in integrations:
        # Real impl: Use SMTP / SendGrid
        print(f"\n[EMAIL ALERT {timestamp}] 📧 Sending to Admin: {message}")
        
    if "Excel Sheet" in integrations:
        # Real impl: Append to CSV file
        with open("alert_log.csv", "a") as log:
            log.write(f"{timestamp},{message}\n")
        print(f"\n[EXCEL LOG {timestamp}] 📊 Row Added.")

# --- HELPER: Logic for QUANTIFIER ---
def analyze_quantifier(image_bytes, user_rule, ideal_image_bytes=None):
    # System Instruction from your uploaded file 
    sys_instruction = """You are a Visual Inventory Auditor. Compare 'Current Image' against 'Ideal State'.
    1. Divide image into 'Sections' (Labels, Shelf Compartments, Spatial Location).
    2. For EACH section determine:
       - Content Type: What is inside?
       - Strategy: COUNT (discrete) or ESTIMATE (fullness %).
       - Status: OK, LOW, EMPTY, or OVERFLOW.
    3. ASSUMPTION: Recognize 3D packing. Assume items exist behind visible front items if geometric packing suggests it.
    
    Output strictly in JSON:
    {
      "class": "QUANTIFIER",
      "timestamp": "ISO_STRING",
      "overall_status": "OK" | "ATTENTION_NEEDED",
      "sections": [
        {
          "section_id": "String",
          "detected_content": "String",
          "strategy": "COUNT" | "ESTIMATE",
          "ideal_value": Number,
          "current_value": Number,
          "unit": "units" | "percent",
          "status": "OK" | "LOW" | "EMPTY" | "MISMATCH"
        }
      ]
    }"""

    prompt_parts = [
        types.Part.from_text(text=f"User Rule/Context: {user_rule}"),
        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
    ]
    
    # If an Ideal Image is provided, add it to the prompt
    if ideal_image_bytes:
        prompt_parts.insert(0, types.Part.from_bytes(data=ideal_image_bytes, mime_type="image/jpeg"))
        prompt_parts.insert(1, types.Part.from_text(text="Above is the IDEAL STATE image. Below is the CURRENT image."))

    response = client.models.generate_content(
        model="gemini-3-flash-preview", # Use 3.0 Flash for speed/cost, or "gemini-3-pro" for reasoning
        contents=[types.Content(role="user", parts=prompt_parts)],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            response_mime_type="application/json" 
        )
    )
    return response.text

# --- HELPER: Logic for DETECTOR ---
def analyze_detector(image_bytes, user_rule):
    # System Instruction from your uploaded file 
    sys_instruction = """You are a Safety & Compliance Officer. Detect presence/absence of objects based on User Rules.
    
    Output strictly in JSON:
    {
      "class": "DETECTOR",
      "timestamp": "ISO_STRING",
      "compliance_status": "PASS" | "FAIL",
      "detections": [
        {
          "rule_checked": "String",
          "is_compliant": Boolean,
          "confidence": Number (0-1.0),
          "evidence": "String description"
        }
      ]
    }
    If FAIL, count instances (e.g., 'detected persons not wearing PPE: 5')."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            types.Content(
                role="user", 
                parts=[
                    types.Part.from_text(text=f"Rule to Check: {user_rule}"),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            response_mime_type="application/json"
        )
    )
    return response.text

# --- HELPER: Logic for PROCESS MONITOR ---
def analyze_process(image_bytes, user_rule):
    # System Instruction from your uploaded file 
    sys_instruction = """You are a Process Supervisor. Compare 'Current Image' with 'Start/Previous State' to estimate progress.
    
    Output strictly in JSON:
    {
      "class": "PROCESS_MONITOR",
      "process_name": "String",
      "current_stage": "String",
      "progress_percentage": Number (0-100),
      "anomalies_detected": ["String"],
      "visual_reasoning": "String"
    }"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            types.Content(
                role="user", 
                parts=[
                    types.Part.from_text(text=f"Process Context: {user_rule}"),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            response_mime_type="application/json"
        )
    )
    return response.text

# ---  THE "HEARTBEAT" (Background Scheduler) ---
def run_scheduler():
    """Checks active monitors every 10 seconds."""
    print("--- Scheduler Started ---")
    while True:
        try:
            monitors = load_monitors()
            for m in monitors:
                # Logic: Only run 'RTSP Stream' or 'Interval' types automatically
                if m['source'] == 'RTSP Stream': 
                    # Simulating a check every minute for demo purposes
                    # In production, check 'last_run_time' timestamp
                    print(f"Checking Camera: {m['name']}...")
                    
                    # A. Grab Frame (Mock or Real)
                    # For Hackathon demo: Use the 'last_test_image' if real RTSP isn't available
                    # cap = cv2.VideoCapture(m['rtsp_url'])
                    # ret, frame = cap.read()
                    
                    # B. Analyze (Mocking the call to save API credits during loop dev)
                    # result = analyze_quantifier(frame, m['rule'])
                    
                    # C. Check Alerts
                    # if result['overall_status'] != 'OK':
                    #     send_notification(m['integrations'], f"Alert on {m['name']}")
                    
            time.sleep(60) # Wait 60 seconds before next cycle
        except Exception as e:
            print(f"Scheduler Error: {e}")
            time.sleep(60)

# Start Scheduler in Background
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# --- API ENDPOINT ---

@app.route('/monitors', methods=['GET'])
def get_monitors():
    return jsonify(load_monitors())

@app.route('/monitors', methods=['POST'])
def add_monitor():
    data = request.form.to_dict() # Handle FormData
    monitors = load_monitors()
    
    new_monitor = {
        "id": str(uuid.uuid4()),
        "name": data.get('name'),
        "type": data.get('type'),
        "source": data.get('source'),
        "rule": data.get('rule'),
        "integrations": data.get('integrations', '').split(','),
        "status": "OK",
        "last_update": datetime.now().isoformat(),
        # Save images if uploaded (simplified for hackathon)
        "ideal_image_path": None 
    }
    
    monitors.append(new_monitor)
    save_monitors(monitors)
    return jsonify(new_monitor)

@app.route('/monitors/<id>', methods=['DELETE'])
def delete_monitor(id):
    monitors = load_monitors()
    monitors = [m for m in monitors if m['id'] != id]
    save_monitors(monitors)
    return jsonify({"success": True})

@app.route('/trigger-scan', methods=['POST'])
def trigger_scan():
    try:
        # 1. Get Data from Frontend
        # Expecting JSON payload with base64 image or multipart/form-data
        # For simplicity, let's assume multipart/form-data for images
        
        mode = request.form.get('mode') # QUANTIFIER, DETECTOR, PROCESS
        user_rule = request.form.get('rule')
        
        if 'image' not in request.files:
            return jsonify({"error": "No image uploaded"}), 400
            
        file = request.files['image']
        image_bytes = file.read()
        
        # Check for Ideal Image (Optional)
        ideal_image_bytes = None
        if 'ideal_image' in request.files:
            ideal_image_bytes = request.files['ideal_image'].read()

        print(f"Received Request: Mode={mode}, Rule={user_rule}")

        # 2. Route to Logic
        result_json = "{}"
        if mode == "QUANTIFIER":
            result_json = analyze_quantifier(image_bytes, user_rule, ideal_image_bytes)
        elif mode == "DETECTOR":
            result_json = analyze_detector(image_bytes, user_rule)
        elif mode == "PROCESS":
            result_json = analyze_process(image_bytes, user_rule)
        else:
            return jsonify({"error": "Invalid Mode"}), 400

        # 3. Return Raw JSON String (Flask will sanitize it)
        return result_json, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)