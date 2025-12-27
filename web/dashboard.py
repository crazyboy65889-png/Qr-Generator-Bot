from flask import Flask, render_template_string, request, jsonify
import os
from threading import Thread
import asyncio
import datetime

class Dashboard:
    """Web dashboard for bot monitoring"""
    
    def __init__(self, bot):
        self.bot = bot
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.urandom(32)
        self.password = os.getenv('DASHBOARD_PASSWORD', 'admin')
        
        self._setup_routes()
        
        # Start in thread
        Thread(target=self._run_server, daemon=True).start()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            if not self._check_auth():
                return self._login_page()
            return self._dashboard_page()
        
        @self.app.route('/api/stats')
        def api_stats():
            if not self._check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            return jsonify(self.bot.get_bot_stats())
        
        @self.app.route('/api/temp-channels')
        def api_temp_channels():
            if not self._check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            return jsonify({
                'channels': list(self.bot.temp_channels.keys()),
                'count': len(self.bot.temp_channels)
            })
        
        @self.app.route('/login', methods=['POST'])
        def login():
            password = request.form.get('password')
            if password == self.password:
                return jsonify({'success': True})
            return jsonify({'error': 'Invalid password'}), 401
    
    def _check_auth(self):
        """Check if user is authenticated"""
        # Simple auth for now
        return request.args.get('token') == self.password
    
    def _login_page(self):
        """Login page HTML"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>UPI Bot - Login</title>
            <style>
                body { font-family: Arial; background: #2c3e50; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .login-box { background: #34495e; padding: 30px; border-radius: 10px; text-align: center; }
                input { padding: 10px; margin: 10px; width: 200px; }
                button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>🔐 Login Required</h2>
                <input type="password" id="password" placeholder="Enter password">
                <br>
                <button onclick="login()">Login</button>
            </div>
            <script>
                function login() {
                    const password = document.getElementById('password').value;
                    fetch('/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: 'password=' + password
                    }).then(r => {
                        if (r.ok) window.location.href = '/?token=' + password;
                        else alert('Invalid password!');
                    });
                }
            </script>
        </body>
        </html>
        '''
    
    def _dashboard_page(self):
        """Dashboard HTML"""
        stats = self.bot.get_bot_stats()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>UPI Bot Dashboard</title>
            <style>
                body {{ font-family: Arial; background: #1a1a2e; color: white; margin: 0; padding: 20px; }}
                .header {{ background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
                .stat-card {{ background: #0f3460; padding: 20px; border-radius: 10px; text-align: center; }}
                .stat-value {{ font-size: 2em; color: #00ff88; }}
                .label {{ color: #aaa; }}
                .temp-channels {{ margin-top: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; border-bottom: 1px solid #444; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 UPI Bot Dashboard</h1>
                <p>Real-time bot monitoring</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="label">Uptime</div>
                    <div class="stat-value">{self._format_uptime(stats["uptime_seconds"])}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Guilds</div>
                    <div class="stat-value">{stats["guilds"]}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Memory</div>
                    <div class="stat-value">{stats["memory_mb"]:.1f} MB</div>
                </div>
                <div class="stat-card">
                    <div class="label">QR Generated</div>
                    <div class="stat-value">{stats["qr_generated"]}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Commands</div>
                    <div class="stat-value">{stats["commands_processed"]}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Temp Channels</div>
                    <div class="stat-value">{stats["temp_channels"]}</div>
                </div>
            </div>
            
            <div class="temp-channels">
                <h2>🎤 Active Temp Channels</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Channel</th>
                            <th>Owner</th>
                            <th>Guild</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody id="channels-table"></tbody>
                </table>
            </div>
            
            <script>
                // Auto-refresh stats
                setInterval(() => {
                    fetch('/api/stats?token={self.password}').then(r => r.json()).then(data => {
                        document.querySelector('.stat-card:nth-child(2) .stat-value').textContent = data.guilds;
                        document.querySelector('.stat-card:nth-child(4) .stat-value').textContent = data.qr_generated;
                    });
                }, 5000);
            </script>
        </body>
        </html>
        '''
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"
    
    def _run_server(self):
        """Run Flask server"""
        try:
            port = int(os.getenv('PORT', 10000))
            self.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Dashboard server failed: {e}")
          
