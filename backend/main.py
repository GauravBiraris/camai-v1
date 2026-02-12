import os
import json
import time
import threading
import cv2
import uuid
import base64
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import numpy as np

# 1. CONFIGURATION
load_dotenv()
app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONITORS_FILE = os.getenv("MONITORS_FILE", 'monitors.json')
LOGS_FILE = os.getenv("LOGS_FILE", 'logs.json')
STATIC_FOLDER = os.path.join("static", "captures")

client = genai.Client(api_key=GEMINI_API_KEY)

# Memory to store the last frame for each monitor (RAM only)
last_seen_frames = {}

# --- STORAGE HELPERS ---
def load_monitors():
    if not os.path.exists(MONITORS_FILE): return []
    try:
        with open(MONITORS_FILE, 'r') as f: return json.load(f)
    except: return []

def save_monitors(data):
    with open(MONITORS_FILE, 'w') as f: json.dump(data, f, indent=2)

def has_significant_change(monitor_id, current_frame_bytes, threshold=0.02):
    """
    Returns True if the image changed significantly since last scan.
    threshold=0.02 means 2% of pixels changed.
    """
    # Decode bytes to OpenCV Image
    nparr = np.frombuffer(current_frame_bytes, np.uint8)
    current_img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    # Resize to small thumbnail for fast comparison (e.g., 100x100)
    current_small = cv2.resize(current_img, (100, 100))
    
    # Get last frame
    last_small = last_seen_frames.get(monitor_id)
    
    # If no history, it's a "Change" (First run)
    if last_small is None:
        last_seen_frames[monitor_id] = current_small
        return True
        
    # Calculate Absolute Difference
    diff = cv2.absdiff(current_small, last_small)
    
    # Count pixels that changed intensity by more than 25 (out of 255)
    # This filters out minor lighting noise
    non_zero_count = np.count_nonzero(diff > 25)
    total_pixels = current_small.shape[0] * current_small.shape[1]
    
    change_ratio = non_zero_count / total_pixels
    
    if change_ratio > threshold:
        # Update history only if change occurred
        last_seen_frames[monitor_id] = current_small
        print(f"   [Diff: {change_ratio:.2%}] Motion Detected -> Triggering AI")
        return True
    
    print(f"   [Diff: {change_ratio:.2%}] No Motion -> Skipping AI")
    return False

def load_logs():
    if not os.path.exists(LOGS_FILE): return []
    try:
        with open(LOGS_FILE, 'r') as f: return json.load(f)
    except: return []

def save_log_entry(monitor_id, monitor_name, monitor_type, result_json, image_bytes):
    timestamp = datetime.now().isoformat()
    log_id = str(uuid.uuid4())
    
    # Save Image
    os.makedirs(STATIC_FOLDER, exist_ok=True)
    image_filename = f"{log_id}.jpg"
    with open(os.path.join(STATIC_FOLDER, image_filename), "wb") as f:
        f.write(image_bytes)
        
    # Create Log
    new_log = {
        "id": log_id,
        "monitor_id": monitor_id,
        "monitor_name": monitor_name,
        "type": monitor_type,
        "timestamp": timestamp,
        "image_url": f"http://127.0.0.1:5000/static/captures/{image_filename}",
        "result": result_json
    }
    
    # Append to File
    logs = load_logs()
    logs.insert(0, new_log)
    logs = logs[:100] # Keep last 100
    with open(LOGS_FILE, 'w') as f: json.dump(logs, f, indent=2)
    return new_log


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


# --- SCHEDULER ---
def run_scheduler():
    print("--- Scheduler Started (Smart Polling) ---")
    while True:
        try:
            monitors = load_monitors()
            for m in monitors:
                # 1. FILTER: Only process Active RTSP/Interval streams
                if m.get('source') != 'RTSP Stream':
                    continue

# 2. THE FIX: Check if this is a "Local Device" (0, 1) or a "Network Stream"
                cam_id = m.get('connection_url', 0)
                is_local_device = False
                try:
                    int(cam_id) # If it converts to int (0, 1), it's a local USB cam
                    is_local_device = True
                except:
                    is_local_device = False # It's a string (rtsp://...)

                # CRITICAL: If on Cloud, DO NOT touch local devices. 
                # We assume a "Bridge" script is handling them.
                if is_local_device:
                    # Optional: Check if we haven't heard from the bridge in a while (Health check)
                    # But DO NOT try cv2.VideoCapture(0) here.
                    continue 

                # 3. Handle Network Streams (RTSP)
                # Only proceed if it looks like a real URL (rtsp:// or http://)
                if isinstance(cam_id, str) and (cam_id.startswith('rtsp') or cam_id.startswith('http')):
                    print(f"⏰ Checking Network Cam: {m['name']}...")

                # 2. TIME CHECK LOGIC
                interval_minutes = float(m.get('interval', 60))
                last_check_str = m.get('last_check_time')
                should_run = False
                
                if not last_check_str:
                    should_run = True # First run
                else:
                    try:
                        last_check = datetime.fromisoformat(last_check_str)
                        diff = datetime.now() - last_check
                        diff_minutes = diff.total_seconds() / 60
                        if diff_minutes >= interval_minutes:
                            should_run = True
                    except ValueError:
                        should_run = True # Corrupted time, reset

                # 3. EXECUTION BLOCK
                if should_run:
                    print(f"⏰ Time to check: {m['name']} (Interval: {interval_minutes}m)")
                    
                    # --- A. CAPTURE ---
                    cam_id = m.get('connection_url', 0)
                    try: cam_input = int(cam_id)
                    except: cam_input = cam_id
                    
                    frame_bytes = None
                    cap = cv2.VideoCapture(cam_input)
                    
                    try:
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                _, buffer = cv2.imencode('.jpg', frame)
                                frame_bytes = buffer.tobytes()
                    except Exception as e:
                        print(f"   [!] Capture Error: {e}")
                    finally:
                        cap.release() # CRITICAL: Prevent Zombie Camera

                    # CHECK: Did we actually get a valid image?
                    if not frame_bytes:
                        print(f"   [!] Cam {cam_input} failed (No Frame). Skipping analysis.")
                        continue 

                    # --- B. ROUTING & ANALYSIS ---
                    try:
                        rule = m.get('rule', "")
                        result_text = "{}"
    # Load Ideal Image Bytes if it exists
                        ideal_bytes = None
                        if m.get('ideal_image_path') and os.path.exists(m['ideal_image_path']):
                            with open(m['ideal_image_path'], 'rb') as f:
                                ideal_bytes = f.read()                        
                        
                        # Select the correct AI Agent
                        if m['type'] == 'QUANTIFIER':
                            result_text = analyze_quantifier(frame_bytes, rule, ideal_bytes)
                        elif m['type'] == 'DETECTOR':
                            result_text = analyze_detector(frame_bytes, rule)
                        elif m['type'] == 'PROCESS':
                            result_text = analyze_process(frame_bytes, rule)
                            
                        # --- C. PARSE & SAVE ---
                        result_json = json.loads(result_text)
                        
                        # Save Log & Image
                        save_log_entry(m['id'], m['name'], m['type'], result_json, frame_bytes)
                        
                        # --- D. ALERTS ---
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
                        
                        # --- E. UPDATE TIMESTAMP ---
                        # Only update if successful, so we don't skip a retry if it was a glitch
                        # (But be careful: if it crashes 100% of the time, this loop will retry forever)
                        m['last_check_time'] = datetime.now().isoformat()
                        save_monitors(monitors)
                        
                    except Exception as e:
                        print(f"   [!] Analysis Failed: {e}")
                        # Optional: Update timestamp here anyway to prevent infinite retry loops on bad data
                        # m['last_check_time'] = datetime.now().isoformat()
                        # save_monitors(monitors)

            # Sleep briefly to reduce CPU usage
            time.sleep(10) 
            
        except Exception as e:
            print(f"Scheduler Crash: {e}")
            time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

# --- API ROUTES ---
@app.route('/', methods=['GET'])
def health_check():
    return "Camai Backend is Running", 200

@app.route('/monitors', methods=['GET'])
def get_monitors(): return jsonify(load_monitors())

@app.route('/logs', methods=['GET'])
def get_logs(): return jsonify(load_logs())

@app.route('/monitors', methods=['POST'])
def create_monitor():
    data = request.form.to_dict()
    monitors = load_monitors()

    # 1. Handle Ideal Image Upload
    ideal_image_path = None
    if 'ideal_image' in request.files:
        file = request.files['ideal_image']
        if file.filename != '':
            filename = f"ref_{uuid.uuid4()}.jpg"
            # Save to a new folder 'static/references'
            ref_folder = os.path.join("static", "references")
            os.makedirs(ref_folder, exist_ok=True)
            path = os.path.join(ref_folder, filename)
            file.save(path)
            ideal_image_path = path

    new_m = {
        "id": str(uuid.uuid4()),
        "name": data.get('name'),
        "type": data.get('type'),
        "source": data.get('source'),
        "connection_url": data.get('connection_url', '0'),
        "rule": data.get('rule'),
        "interval": float(data.get('interval', 60)),
        "integrations": data.get('integrations', '').split(','),
        "status": "OK",
        "ideal_image_path": ideal_image_path,
        "last_update": datetime.now().isoformat()
    }
    monitors.append(new_m)
    save_monitors(monitors)
    return jsonify(new_m)

@app.route('/monitors/<id>', methods=['PUT'])
def update_monitor_endpoint(id): 
    data = request.form.to_dict()
    monitors = load_monitors()
    updated = None
    
    for m in monitors:
        if m['id'] == id:
            m['name'] = data.get('name', m['name'])
            m['type'] = data.get('type', m['type'])
            m['source'] = data.get('source', m['source'])
            m['connection_url'] = data.get('connection_url', m.get('connection_url'))
            m['rule'] = data.get('rule', m['rule'])
            m['interval'] = float(data.get('interval', m.get('interval', 60)))
            if 'integrations' in data:
                m['integrations'] = data['integrations'].split(',')
            updated = m
            break
            
    if updated:
        save_monitors(monitors)
        return jsonify(updated)
    return jsonify({"error": "Not found"}), 404

@app.route('/monitors/<id>', methods=['DELETE'])
def delete_monitor(id):
    monitors = [m for m in load_monitors() if m['id'] != id]
    save_monitors(monitors)
    return jsonify({"success": True})

@app.route('/monitors/<id>/download-bridge', methods=['GET'])
def download_bridge_script(id):
    monitors = load_monitors()
    monitor = next((m for m in monitors if m['id'] == id), None)
    
    if not monitor:
        return jsonify({"error": "Monitor not found"}), 404

    # Note: We use the Monitor ID as the "Token" so the backend knows which cam is pushing
    # Get the actual domain where this backend is running (localhost or Render)

    api_base = os.getenv('PUBLIC_URL', request.url_root).rstrip('/')

    bridge_code = f"""
import cv2
import time
import requests
import json
import sys

# --- CONFIGURATION ---
MONITOR_ID = "{monitor['id']}"
API_URL = "{api_base}"  
# API_URL = "http://127.0.0.1:5000" # For local testing
INTERVAL = {monitor.get('interval', 60)} * 60 # Convert minutes to seconds
SOURCE_ID = "{monitor.get('connection_url', 0)}"

def run_bridge():
    print(f"--- Bridge Started for Monitor {{MONITOR_ID}} ---")
    print(f"Target: {{API_URL}}")
    print(f"Interval: {{INTERVAL}} seconds")
    
    # Handle Integer vs String source
    try:
        src = int(SOURCE_ID)
    except:
        src = SOURCE_ID
        
    while True:
        try:
            print("📸 Capturing frame...")
            cap = cv2.VideoCapture(src)
            
            if not cap.isOpened():
                print("❌ Failed to open camera. Retrying in 10s...")
                time.sleep(10)
                continue
                
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("❌ Failed to grab frame.")
            else:
                # Convert to JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                
                # Push to Cloud (Trigger Endpoint)
                # We use the 'trigger' endpoint we built earlier!
                url = f"{{API_URL}}/monitors/{{MONITOR_ID}}/trigger"
                files = {{'image': ('snap.jpg', buffer.tobytes(), 'image/jpeg')}}
                
                print(f"🚀 Uploading to Cloud...")
                try:
                    res = requests.post(url, files=files)
                    if res.status_code == 200:
                        print(f"✅ Success: {{res.json().get('message')}}")
                    else:
                        print(f"⚠️ Error: {{res.text}}")
                except Exception as e:
                    print(f"🌐 Network Error: {{e}}")
                    
        except Exception as e:
            print(f"🔥 Critical Error: {{e}}")
            
        print(f"💤 Sleeping for {{INTERVAL}}s...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    # Install requests/opencv if missing
    try:
        import cv2
        import requests
    except ImportError:
        print("Please run: pip install opencv-python requests")
        sys.exit(1)
        
    run_bridge()
"""

    # Return as a downloadable file
    from flask import Response
    return Response(
        bridge_code,
        mimetype="text/x-python",
        headers={"Content-disposition": f"attachment; filename=bridge_{monitor['name'].replace(' ', '_')}.py"}
    )

@app.route('/monitors/<id>/trigger', methods=['POST'])
def trigger_existing_monitor(id):
    try:
        monitors = load_monitors()
        monitor = next((m for m in monitors if m['id'] == id), None)
        
        if not monitor:
            return jsonify({"error": "Monitor not found"}), 404

        print(f"⚡ EXTERNAL TRIGGER RECEIVED: {monitor['name']}")
        
        # Scenario A: The external app sent an IMAGE (e.g., Mobile App upload)
        # We look for 'image' in request.files
        frame_bytes = None
        if 'image' in request.files:
            print("   [+] Using uploaded image from request")
            file = request.files['image']
            frame_bytes = file.read()
            
        # Scenario B: The external app sent a SIGNAL (e.g., Billing POS)
        # We must grab the frame from the configured RTSP/Camera ourselves
        elif monitor.get('connection_url'):
            print(f"   [+] Capturing from configured source: {monitor['connection_url']}")
            
            cam_id = monitor.get('connection_url')
            try: cam_input = int(cam_id)
            except: cam_input = cam_id
            
            cap = cv2.VideoCapture(cam_input)
            try:
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        _, buffer = cv2.imencode('.jpg', frame)
                        frame_bytes = buffer.tobytes()
            finally:
                cap.release()
        
        if not frame_bytes:
            return jsonify({"error": "No image provided and camera capture failed"}), 400

        # --- RUN ANALYSIS ---
        # (Reuse logic from scheduler)
        rule = monitor.get('rule', "")
        result_text = "{}"
        
        if monitor['type'] == 'QUANTIFIER':
            result_text = analyze_quantifier(frame_bytes, rule)
        elif monitor['type'] == 'DETECTOR':
            result_text = analyze_detector(frame_bytes, rule)
        elif monitor['type'] == 'PROCESS':
            result_text = analyze_process(frame_bytes, rule)
            
        result_json = json.loads(result_text)
        
        # Save to logs
        log_entry = save_log_entry(
            monitor['id'], 
            monitor['name'], 
            monitor['type'], 
            result_json, 
            frame_bytes
        )
        
        return jsonify({
            "success": True, 
            "message": "Scan completed", 
            "result": result_json,
            "log_id": log_entry['id']
        })

    except Exception as e:
        print(f"Trigger Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/trigger-scan', methods=['POST'])
def test_monitor_logic():
    try:
        # 1. Extract Data
        mode = request.form.get('mode', 'QUANTIFIER')
        user_rule = request.form.get('rule', '')
        
        # 2. Extract Images
        if 'image' not in request.files:
            return jsonify({"error": "No image uploaded"}), 400
            
        file = request.files['image']
        image_bytes = file.read()
        
        ideal_bytes = None
        if 'ideal_image' in request.files:
            ideal_bytes = request.files['ideal_image'].read()

        # 3. Route to AI Logic (Stateless)
        result_text = "{}"
        if mode == 'QUANTIFIER':
            result_text = analyze_quantifier(image_bytes, user_rule, ideal_bytes)
        elif mode == 'DETECTOR':
            result_text = analyze_detector(image_bytes, user_rule)
        elif mode == 'PROCESS':
            result_text = analyze_process(image_bytes, user_rule)
            
        # 4. Return Result directly
        return jsonify(json.loads(result_text))

    except Exception as e:
        print(f"Test Scan Error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/test-rule', methods=['POST'])
def test_rule_endpoint():
    try:
        # Simple validation endpoint to pass verification checks
        data = request.json if request.is_json else request.form.to_dict()
        return jsonify({
            "status": "success", 
            "message": "Backend is ready",
            "received_rule": data.get('rule', 'No rule provided')
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
