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
        body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 960px; margin: 40px auto; padding: 20px; background: var(--bg); color: #1e293b; }
        .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; margin-bottom: 24px; }
        h1 { color: var(--odoo-purple); margin-bottom: 30px; font-weight: 800; border-bottom: 3px solid var(--odoo-purple); display: inline-block; padding-bottom: 5px; }
        h3 { margin-bottom: 18px; color: #1e293b; font-weight: 700; }
        .section-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 16px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; font-weight: 600; margin-bottom: 8px; color: #475569; }
        input { width: 100%; padding: 12px 14px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 15px; transition: border-color 0.2s; box-sizing: border-box; }
        input:focus { border-color: var(--odoo-purple); outline: none; }
        .btn { color: white; padding: 14px 28px; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: 700; border: none; cursor: pointer; transition: all 0.3s; font-size: 15px; }
        .btn-purple { background: var(--odoo-purple); box-shadow: 0 4px 14px rgba(113, 75, 103, 0.4); }
        .btn-purple:hover { background: #5a3c52; transform: translateY(-2px); }
        .btn-teal { background: #0f766e; box-shadow: 0 4px 14px rgba(15, 118, 110, 0.4); }
        .btn-teal:hover { background: #0d6460; transform: translateY(-2px); }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 700px) { .grid-2 { grid-template-columns: 1fr; } }
        pre { background: #0f172a; color: #38bdf8; padding: 25px; border-radius: 12px; overflow-x: auto; font-size: 13px; border-left: 6px solid #22c55e; }
        .status-badge { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 700; }
        .config-info { background: #f1f5f9; padding: 20px; border-radius: 12px; margin-bottom: 30px; font-size: 14px; }
        .config-info code { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        .chip { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; }
        .chip-teal { background: #ccfbf1; color: #0f766e; }
    </style>
    <script>
        let currentUpdate = {{ last_update }};
        setInterval(async () => {
            try {
                const response = await fetch('/api/check-update');
                const data = await response.json();
                if (data.last_update > currentUpdate) { window.location.reload(); }
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

        <div class="grid-2">
            <!-- Labour Code Selection -->
            <div>
                <p class="section-title">🔧 Labour Code Selection</p>
                <form action="/generate-url" method="POST" target="_blank">
                    <div class="form-group">
                        <label>Chassis Number (6+ chars):</label>
                        <input type="text" name="chassis" value="WDD17604423456789" required>
                    </div>
                    <div class="form-group">
                        <label>Job Order ID:</label>
                        <input type="text" name="job_order" value="JO-{{ timestamp }}">
                    </div>
                    <button type="submit" class="btn btn-purple">🚀 Select Labour Codes in RTS</button>
                </form>
            </div>

            <!-- Service History Viewer -->
            <div>
                <p class="section-title">📋 Service History Viewer <span class="chip chip-teal">Read-Only</span></p>
                <form action="/view-service-history" method="POST" target="_blank">
                    <div class="form-group">
                        <label>Chassis Number (6+ chars):</label>
                        <input type="text" name="chassis" value="WDD17604423456789" required>
                    </div>
                    <div class="form-group">
                        <label style="visibility:hidden;">Spacer</label>
                        <input type="text" name="_spacer" placeholder="(no job order needed)" disabled style="opacity:0.4; cursor:not-allowed;">
                    </div>
                    <button type="submit" class="btn btn-teal">🕐 View Service History in RTS</button>
                </form>
            </div>
        </div>

        {% if received_data %}
        <div style="margin-top: 40px;">
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

@app.route("/view-service-history", methods=["POST"])
def view_service_history():
    """Generate a signed URL for the RTS service history viewer and redirect."""
    from flask import redirect
    chassis = request.form.get("chassis", "").upper().strip()
    
    params = {
        "chassis": chassis,
        "nonce": uuid.uuid4().hex,
        "exp": str(int(time.time()) + 3600),
    }
    
    # Sort and sign (same shared secret, fewer params)
    canonical = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    signature = hmac.new(SHARED_SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    
    target_url = f"{RTS_BASE_URL}/odoo/service-history?{canonical}&sig={signature}"
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
