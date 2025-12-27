from flask import Flask, render_template_string
import logging

app = Flask(__name__)

# Disable Flask logging
log = logging.getLogger('werkzeug')
log.disabled = True

@app.route('/')
def home():
    """Health check endpoint"""
    return {
        "status": "online",
        "bot": "UPI Discord Bot v3.0",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": "Bot is running 24/7"
    }, 200

@app.route('/health')
def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "UPI-Bot",
        "version": "3.0",
        "checks": {
            "web_server": "pass",
            "bot_process": "running"
        }
    }, 200

@app.route('/uptime')
def uptime():
    """Uptime monitoring endpoint"""
    return {
        "status": "up",
        "uptime": "24/7",
        "provider": "Render.com"
    }, 200

def keep_alive():
    """Start web server for uptime monitoring"""
    try:
        from threading import Thread
        port = int(os.environ.get('PORT', 10000))
        Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False), daemon=True).start()
        print("✅ Keep-alive server started on port", port)
    except Exception as e:
        print("❌ Keep-alive failed:", e)
      
