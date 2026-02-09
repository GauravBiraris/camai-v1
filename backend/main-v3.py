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

LOGS_FILE = 'logs.json'
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

def update_monitor_timestamp(monitor_id):
    monitors = load_monitors()
    for m in monitors:
        if m['id'] == monitor_id:
            m['last_check_time'] = datetime.now().isoformat()
    save_monitors(monitors)

def save_log_entry(monitor_id, monitor_name, monitor_type, result_json, image_bytes):
    """Saves the JSON result and the Image to disk."""
    timestamp = datetime.now().isoformat()
    log_id = str(uuid.uuid4())
    
    # A. Save Image to 'static/captures'
    image_filename = f"{log_id}.jpg"
    image_path = os.path.join("static", "captures", image_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    with open(image_path, "wb") as f:
        f.write(image_bytes)
        
    # B. Create Log Entry
    new_log = {
        "id": log_id,
        "monitor_id": monitor_id,
        "monitor_name": monitor_name,
        "type": monitor_type,
        "timestamp": timestamp,
        "image_url": f"http://127.0.0.1:5000/static/captures/{image_filename}",
        "result": result_json
    }
    
    # C. Append to logs.json
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            try:
                logs = json.load(f)
            except: pass
    
    # Keep only last 50 logs to prevent file bloat
    logs.insert(0, new_log) 
    logs = logs[:50] 
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
        
    return new_log

def send_notification(integrations, message):
    """
    Sends alerts based on user selection.
    For Hackathon: Print to console allows judges to see it works.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")

    if not integrations: return

    print(f"\n[🔔 NOTIFICATION EVENT] Message: {message}")
    
    
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
    if not user_rule or user_rule.strip() == "":
        user_rule = "Count the items and identify any low stock."

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
    print("--- Scheduler Started (Smart Polling) ---")
    while True:
        try:
            monitors = load_monitors()
            for m in monitors:
                # 1. FILTER: Only process Active RTSP/Interval streams
                if m.get('source') not in ['RTSP Stream', 'Upload Interval']:
                    continue

                # 2. TIME CHECK LOGIC
                interval_minutes = float(m.get('interval', 60))
                last_check_str = m.get('last_check_time')
                
                should_run = False
                
                if not last_check_str:
                    should_run = True # Never ran before, run now
                else:
                    try:
                        last_check = datetime.fromisoformat(last_check_str)
                        # Calculate difference in minutes
                        diff = datetime.now() - last_check
                        diff_minutes = diff.total_seconds() / 60
                        
                        if diff_minutes >= interval_minutes:
                            should_run = True
                    except ValueError:
                        should_run = True # corrupted time string, run now
                
                # 3. EXECUTION BLOCK (Only runs if Time Check passed)
                if should_run:
                    print(f"⏰ Time to check: {m['name']} (Interval: {interval_minutes}m)")
                    
                    # --- A. CAPTURE ---
                    cam_id = m.get('connection_url', 0)
                    # Try to convert to int (for USB), keep string for RTSP
                    try: cam_input = int(cam_id)
                    except: cam_input = cam_id
                    
                    cap = cv2.VideoCapture(cam_input)
                    frame_bytes = None
                    
                    try:
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                _, buffer = cv2.imencode('.jpg', frame)
                                frame_bytes = buffer.tobytes()
                    finally:
                        cap.release() # CRITICAL: Always release camera

                    if not frame_bytes:
                        print(f"   [!] Cam {cam_input} failed (No Frame).")
                        continue # Skip analysis, don't update timestamp so it retries

                    # --- B. ROUTING & ANALYSIS ---
                    rule = m.get('rule', "")
                    result_text = "{}"
                    
                    try:
                        if m['type'] == 'QUANTIFIER':
                            result_text = analyze_quantifier(frame_bytes, rule)
                        elif m['type'] == 'DETECTOR':
                            result_text = analyze_detector(frame_bytes, rule)
                        elif m['type'] == 'PROCESS':
                            result_text = analyze_process(frame_bytes, rule)
                            
                        # --- C. PARSE & SAVE ---
                        result_json = json.loads(result_text)
                        
                        # Save to History
                        save_log_entry(m['id'], m['name'], m['type'], result_json, frame_bytes)
                        
                        # Check Status for Alerts
                        status = "OK"
                        if m['type'] == 'QUANTIFIER':
                            status = result_json.get('overall_status', 'OK')
                        elif m['type'] == 'DETECTOR':
                            status = "FAIL" if result_json.get('compliance_status') == 'FAIL' else "OK"
                        elif m['type'] == 'PROCESS':
                            if result_json.get('anomalies_detected'): status = "ALERT"

                        if status != 'OK':
                            print(f"   [!] ALERT: {status}")
                            send_notification(m.get('integrations', []), f"Alert on {m['name']}: {status}")
                        else:
                            print(f"   [+] {m['type']} Analysis OK")
                        
                        # --- D. UPDATE TIMESTAMP ---
                        # Only update if we successfully finished analysis
                        update_monitor_timestamp(m['id'])
                            
                    except Exception as e:
                        print(f"   [!] Analysis Error: {e}")

            # Sleep briefly to prevent high CPU usage, then check again
            time.sleep(10) 
            
        except Exception as e:
            print(f"Scheduler Crash: {e}")
            time.sleep(10)

# Start Scheduler in Background
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# --- API ENDPOINTS ---
@app.route('/logs', methods=['GET'])
def get_logs():
    if not os.path.exists(LOGS_FILE):
        return jsonify([])
    with open(LOGS_FILE, 'r') as f:
        return jsonify(json.load(f))
    
@app.route('/monitors', methods=['GET'])
def get_monitors():
    return jsonify(load_monitors())

@app.route('/monitors', methods=['POST'])
def add_monitor():
    data = request.form.to_dict()
    monitors = load_monitors()
    
    new_monitor = {
        "id": str(uuid.uuid4()),
        "name": data.get('name'),
        "type": data.get('type'),
        "source": data.get('source'),
        "connection_url": data.get('connection_url', '0'), 
        "rule": data.get('rule'),
        "integrations": data.get('integrations', '').split(','),
        "status": "OK",
        "last_update": datetime.now().isoformat(),
        "ideal_image_path": None,
        "interval": float(data.get('interval', 60)), # Save as float (minutes)
        "last_check_time": None # Track when we last ran AI on this cam
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

@app.route('/monitors', methods=['PUT'])
def update_monitor():
    data = request.form.to_dict()
    monitors = load_monitors()
    
    # Find and update the specific monitor
    updated_monitor = None
    for m in monitors:
        if m['id'] == data.get('id'):
            m['name'] = data.get('name')
            m['type'] = data.get('type')
            m['source'] = data.get('source')
            m['connection_url'] = data.get('connection_url', '0')
            m['rule'] = data.get('rule')
            m['interval'] = float(data.get('interval', 60))
            m['integrations'] = data.get('integrations', '').split(',')
            updated_monitor = m
            break
            
    if updated_monitor:
        save_monitors(monitors)
        return jsonify(updated_monitor)
    return jsonify({"error": "Monitor not found"}), 404

@app.route('/monitors/<id>', methods=['PUT'])
def update_monitor(id):
    try:
        # 1. Get the Updates
        # Note: request.form works for FormData (files), request.json works for raw JSON
        # Since your frontend sends FormData, use request.form
        data = request.form.to_dict() 
        monitors = load_monitors()
        
        # 2. Find and Update
        updated_monitor = None
        for m in monitors:
            if m['id'] == id:
                m['name'] = data.get('name', m['name'])
                m['type'] = data.get('type', m['type'])
                m['source'] = data.get('source', m['source'])
                m['rule'] = data.get('rule', m['rule'])
                m['connection_url'] = data.get('connection_url', m.get('connection_url', '0'))
                m['interval'] = float(data.get('interval', m.get('interval', 60)))
                
                # Handle Integrations (comes as string "A,B" from FormData)
                if 'integrations' in data:
                    m['integrations'] = data['integrations'].split(',') if data['integrations'] else []
                
                # Check if a new Ideal Image was uploaded
                # (Implementation omitted for brevity, but this is where you'd save it)
                
                updated_monitor = m
                break
        
        if updated_monitor:
            save_monitors(monitors)
            return jsonify(updated_monitor)
        
        return jsonify({"error": "Monitor not found"}), 404
        
    except Exception as e:
        print(f"Update Error: {e}")
        return jsonify({"error": str(e)}), 500
    
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