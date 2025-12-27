from flask import Flask, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'UPI Bot is running',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'password': '6203'})

def keep_alive():
    from threading import Thread
    import os
    
    port = int(os.getenv('PORT', 10000))
    
    def run():
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    
    t = Thread(target=run, daemon=True)
    t.start()
    print(f"✅ Keep-alive server started on port {port}")
