import hashlib
import hmac
import json
import time
import uuid
import os
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Config from Environment Variables
RTS_BASE_URL = os.getenv("RTS_BASE_URL", "https://hrm-data.hartonomotor-group.com")
SHARED_SECRET = os.getenv("ODOO_SHARED_SECRET", "")
WEBHOOK_SECRET = os.getenv("ODOO_WEBHOOK_SECRET", "")
MOCK_PUBLIC_URL = os.getenv("MOCK_PUBLIC_URL", "")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mock Odoo ERP Bridge Test</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --odoo-purple: #714B67; --bg: #f8fafc; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: var(--bg); color: #1e293b; }
        .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; }
        h1 { color: var(--odoo-purple); margin-bottom: 30px; font-weight: 800; border-bottom: 3px solid var(--odoo-purple); display: inline-block; padding-bottom: 5px; }
        .form-group { margin-bottom: 25px; }
        label { display: block; font-weight: 600; margin-bottom: 10px; color: #475569; }
        input { width: 100%; padding: 14px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; transition: border-color 0.2s; }
        input:focus { border-color: var(--odoo-purple); outline: none; }
        .btn { background: var(--odoo-purple); color: white; padding: 16px 32px; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: 700; border: none; cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 14px rgba(113, 75, 103, 0.4); }
        .btn:hover { background: #5a3c52; transform: translateY(-2px); }
        pre { background: #0f172a; color: #38bdf8; padding: 25px; border-radius: 12px; overflow-x: auto; font-size: 14px; border-left: 6px solid #22c55e; }
        .status-badge { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 700; }
        .config-info { background: #f1f5f9; padding: 20px; border-radius: 12px; margin-bottom: 30px; font-size: 14px; }
        .config-info code { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; }
    </style>
    <script>
        // Background Polling for Updates
        let currentUpdate = {{ last_update }};
        setInterval(async () => {
            try {
                const response = await fetch('/api/check-update');
                const data = await response.json();
                if (data.last_update > currentUpdate) {
                    window.location.reload();
                }
            } catch (e) {}
        }, 2000);
    </script>
</head>
<body>
    <div class="card">
        <h1>Odoo ERP Mock</h1>
        
        <div class="config-info">
            <strong>Configuration:</strong><br>
            RTS Target: <code>{{ rts_url }}</code><br>
            Public Callback: <code>{{ callback_url }}</code>
        </div>

        <form action="/generate-url" method="POST" target="_blank">
            <div class="form-group">
                <label>Test Chassis Number (6+ chars):</label>
                <input type="text" name="chassis" value="WDD17604423456789" required>
            </div>
            <div class="form-group">
                <label>Job Order ID (Ref):</label>
                <input type="text" name="job_order" value="JO-{{ timestamp }}">
            </div>
            <button type="submit" class="btn">🚀 Select Labour Codes in RTS</button>
        </form>
        
        {% if received_data %}
        <div style="margin-top: 50px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">Latest Webhook Result</h3>
                <div style="display: flex; gap: 8px;">
                    <span class="status-badge" style="background: #e0f2fe; color: #0369a1;">Live Polling Active</span>
                    <span class="status-badge">Signature Verified</span>
                </div>
            </div>
            <pre>{{ received_data | tojson(indent=2) }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

last_received_data = None
last_update_time = 0

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE, 
        rts_url=RTS_BASE_URL, 
        callback_url=MOCK_PUBLIC_URL,
        timestamp=int(time.time()),
        received_data=last_received_data,
        last_update=last_update_time
    )

@app.route("/api/check-update")
def check_update():
    return jsonify({"last_update": last_update_time})

@app.route("/generate-url", methods=["POST"])
def generate_url():
    chassis = request.form.get("chassis", "")
    job_order = request.form.get("job_order", "")
    
    params = {
        "job_order_id": job_order,
        "job_number": job_order,
        "chassis": chassis,
        "customer_name": "Test Customer",
        "callback_url": f"{MOCK_PUBLIC_URL}/rts/labour-callback",
        "nonce": uuid.uuid4().hex,
        "exp": str(int(time.time()) + 3600)
    }
    
    # Sort and sign
    canonical = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    signature = hmac.new(SHARED_SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    
    target_url = f"{RTS_BASE_URL}/odoo/select-labour?{canonical}&sig={signature}"
    
    from flask import redirect
    return redirect(target_url)

@app.route("/rts/labour-callback", methods=["POST"])
def webhook():
    global last_received_data, last_update_time
    signature = request.headers.get("X-RTS-Signature")
    if not signature:
        return jsonify({"status": "error", "message": "Missing signature"}), 401
    
    expected_sig = hmac.new(WEBHOOK_SECRET.encode(), request.data, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected_sig):
        return jsonify({"status": "error", "message": "Invalid signature"}), 403

    last_received_data = request.json
    last_update_time = time.time()
    print(f"\\n[MOCK ODOO] Webhook received for JO: {last_received_data.get('job_order_id')}")
    
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
