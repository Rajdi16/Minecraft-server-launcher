import http.server
import socketserver
import threading
import urllib.parse
import os
import json
import datetime
import zipfile
import shutil
import tempfile
import cgi

NAV = """<a href='/'>📊 Dashboard</a><a href='/map'>🗺️ Map</a><a href='/chat'>💬 Chat</a><a href='/inventory'>🎒 Inventories</a><a href='/backups'>💾 Backups</a><a href='/world_upload'>🌍 World Upload</a><a href='/server_props'>⚙️ Server Props</a><a href='/gamerules'>🎮 Game Rules</a><a href='/stats'>📊 Stats</a><a href='/mods'>🔧 Mods</a><a href='/logs'>📜 Logs</a><a href='/commands'>💻 Commands</a><a href='/scheduler'>⏰ Scheduler</a><a href='/settings'>🛡️ Settings</a>"""


class DashboardServer:
    def __init__(self, minecraft_server, port=8080):
        self.mc_server = minecraft_server
        self.port = port

    def start(self):
        mc = self.mc_server

        class DashboardHandler(http.server.BaseHTTPRequestHandler):
            def _read_form(self):
                """Parse regular application/x-www-form-urlencoded POST body."""
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                return urllib.parse.parse_qs(body)

            def do_POST(self):
                ct = self.headers.get("Content-Type", "")

                # ── World upload (multipart) ────────────────────────────────
                if self.path == "/world_upload":
                    if "multipart" not in ct:
                        self.send_response(400); self.end_headers(); return
                    environ = {"REQUEST_METHOD": "POST"}
                    form = cgi.FieldStorage(
                        fp=self.rfile,
                        headers=self.headers,
                        environ=environ,
                    )
                    file_item = form.get("world_zip")
                    if file_item and file_item.filename:
                        threading.Thread(
                            target=self._install_world,
                            args=(file_item.file.read(),),
                            daemon=True
                        ).start()
                    self.send_response(303)
                    self.send_header("Location", "/world_upload")
                    self.end_headers()
                    return

                # ── Standard form-encoded routes ───────────────────────────
                parsed_data = self._read_form()

                if self.path == "/start":
                    mc.start_server()
                elif self.path == "/stop":
                    mc.stop_server()
                elif self.path == "/command":
                    if "cmd" in parsed_data:
                        mc.send_command(parsed_data["cmd"][0])
                elif self.path == "/chat":
                    if "msg" in parsed_data:
                        mc.send_command(f"say [Admin] {parsed_data['msg'][0]}")
                elif self.path == "/backup":
                    threading.Thread(target=mc.backup_world, daemon=True).start()
                elif self.path == "/scheduler":
                    t = parsed_data.get("restart_time", [None])[0]
                    mc.restart_time = t if t and t.strip() else None
                elif self.path == "/server_props":
                    for key, vals in parsed_data.items():
                        mc.set_server_property(key, vals[0])
                elif self.path == "/gamerule":
                    rule = parsed_data.get("rule", [None])[0]
                    value = parsed_data.get("value", [None])[0]
                    if rule and value:
                        mc.send_command(f"gamerule {rule} {value}")

                self.send_response(303)
                self.send_header("Location", self.headers.get("Referer", "/"))
                self.end_headers()

            def _install_world(self, zip_bytes):
                """Stop server, replace world folder, restart."""
                was_running = mc.is_running
                if was_running:
                    mc.send_command("say [Admin] Server stopping to install new world...")
                    mc.stop_server()
                try:
                    with tempfile.TemporaryDirectory() as tmp:
                        zip_path = os.path.join(tmp, "upload.zip")
                        with open(zip_path, "wb") as f:
                            f.write(zip_bytes)
                        with zipfile.ZipFile(zip_path, "r") as z:
                            z.extractall(tmp)
                        # Find the world folder inside the zip
                        world_src = None
                        for item in os.listdir(tmp):
                            full = os.path.join(tmp, item)
                            if os.path.isdir(full) and item != "__MACOSX":
                                world_src = full
                                break
                        if world_src:
                            if os.path.exists("world"):
                                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                shutil.move("world", f"world_old_{ts}")
                            shutil.copytree(world_src, "world")
                except Exception as e:
                    mc.console_logs.append(f"[Upload Error] {e}")
                    return
                if was_running:
                    mc.start_server()


            def do_GET(self):
                css = """
                    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
                    @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
                    @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
                    @keyframes glow { 0%, 100% { box-shadow: 0 0 5px rgba(129, 140, 248, 0.5); } 50% { box-shadow: 0 0 20px rgba(129, 140, 248, 0.8), 0 0 30px rgba(129, 140, 248, 0.6); } }
                    @keyframes slideIn { from { transform: translateX(-100%); } to { transform: translateX(0); } }
                    :root {
                    --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
                    --text-color: #f8fafc;
                    --glass-bg: rgba(30, 41, 59, 0.8);
                    --border-color: rgba(255, 255, 255, 0.12);
                    --shadow: rgba(0, 0, 0, 0.4);
                    --accent1: #818cf8;
                    --accent2: #c084fc;
                    --accent3: #f472b6;
                    --success: #10b981;
                    --danger: #ef4444;
                    --console-bg: rgba(0, 0, 0, 0.7);
                    --console-color: #a7f3d0;
                    --input-bg: rgba(0, 0, 0, 0.5);
                    --input-border: rgba(255,255,255,0.1);
                    --sidebar-hover: rgba(255, 255, 255, 0.08);
                    --card-bg: rgba(30,41,59,0.95);
                    --slot-bg: rgba(15,23,42,0.9);
                    --slot-border: rgba(255,255,255,0.08);
                    --player-item-bg: rgba(255,255,255,0.04);
                    --player-item-border: rgba(255,255,255,0.08);
                    --btn-bg: linear-gradient(135deg, #6366f1, #4f46e5);
                    --scrollbar-track: rgba(255,255,255,0.05);
                    --scrollbar-thumb: linear-gradient(to bottom, rgba(129,140,248,0.5), rgba(192,132,252,0.5));
                    }
                    .theme-light {
                    --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
                    --text-color: #0f172a;
                    --glass-bg: rgba(255, 255, 255, 0.9);
                    --border-color: rgba(0, 0, 0, 0.1);
                    --shadow: rgba(0, 0, 0, 0.2);
                    --accent1: #3b82f6;
                    --accent2: #8b5cf6;
                    --accent3: #ec4899;
                    --success: #10b981;
                    --danger: #ef4444;
                    --console-bg: rgba(255, 255, 255, 0.9);
                    --console-color: #065f46;
                    --input-bg: rgba(255, 255, 255, 0.8);
                    --input-border: rgba(0,0,0,0.2);
                    --sidebar-hover: rgba(0, 0, 0, 0.05);
                    --card-bg: rgba(255,255,255,0.95);
                    --slot-bg: rgba(241,245,249,0.9);
                    --slot-border: rgba(0,0,0,0.1);
                    --player-item-bg: rgba(0,0,0,0.04);
                    --player-item-border: rgba(0,0,0,0.08);
                    --btn-bg: linear-gradient(135deg, #3b82f6, #2563eb);
                    --scrollbar-track: rgba(0,0,0,0.05);
                    --scrollbar-thumb: linear-gradient(to bottom, rgba(59,130,246,0.5), rgba(139,92,246,0.5));
                    }
                    .theme-dark {
                    --bg-gradient: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2a2a2a 100%);
                    --text-color: #f5f5f5;
                    --glass-bg: rgba(20, 20, 20, 0.8);
                    --border-color: rgba(255, 255, 255, 0.1);
                    --shadow: rgba(0, 0, 0, 0.6);
                    --accent1: #60a5fa;
                    --accent2: #a78bfa;
                    --accent3: #f472b6;
                    --success: #34d399;
                    --danger: #f87171;
                    --console-bg: rgba(0, 0, 0, 0.9);
                    --console-color: #6ee7b7;
                    --input-bg: rgba(0, 0, 0, 0.7);
                    --input-border: rgba(255,255,255,0.15);
                    --sidebar-hover: rgba(255, 255, 255, 0.1);
                    --card-bg: rgba(30,30,30,0.95);
                    --slot-bg: rgba(10,10,10,0.9);
                    --slot-border: rgba(255,255,255,0.1);
                    --player-item-bg: rgba(255,255,255,0.05);
                    --player-item-border: rgba(255,255,255,0.1);
                    --btn-bg: linear-gradient(135deg, #60a5fa, #3b82f6);
                    --scrollbar-track: rgba(255,255,255,0.05);
                    --scrollbar-thumb: linear-gradient(to bottom, rgba(96,165,250,0.5), rgba(167,139,250,0.5));
                    }
                    .theme-blue {
                    --bg-gradient: linear-gradient(135deg, #0f1419 0%, #1e293b 50%, #334155 100%);
                    --text-color: #f1f5f9;
                    --glass-bg: rgba(30, 41, 59, 0.8);
                    --border-color: rgba(255, 255, 255, 0.12);
                    --shadow: rgba(0, 0, 0, 0.4);
                    --accent1: #3b82f6;
                    --accent2: #60a5fa;
                    --accent3: #93c5fd;
                    --success: #10b981;
                    --danger: #ef4444;
                    --console-bg: rgba(0, 0, 0, 0.7);
                    --console-color: #a7f3d0;
                    --input-bg: rgba(0, 0, 0, 0.5);
                    --input-border: rgba(255,255,255,0.1);
                    --sidebar-hover: rgba(255, 255, 255, 0.08);
                    --card-bg: rgba(30,41,59,0.95);
                    --slot-bg: rgba(15,23,42,0.9);
                    --slot-border: rgba(255,255,255,0.08);
                    --player-item-bg: rgba(255,255,255,0.04);
                    --player-item-border: rgba(255,255,255,0.08);
                    --btn-bg: linear-gradient(135deg, #3b82f6, #1d4ed8);
                    --scrollbar-track: rgba(255,255,255,0.05);
                    --scrollbar-thumb: linear-gradient(to bottom, rgba(59,130,246,0.5), rgba(96,165,250,0.5));
                    }
                    .theme-purple {
                    --bg-gradient: linear-gradient(135deg, #1a0b2e 0%, #2d1b69 50%, #4c1d95 100%);
                    --text-color: #f3e8ff;
                    --glass-bg: rgba(45, 27, 105, 0.8);
                    --border-color: rgba(255, 255, 255, 0.12);
                    --shadow: rgba(0, 0, 0, 0.4);
                    --accent1: #a855f7;
                    --accent2: #c084fc;
                    --accent3: #d8b4fe;
                    --success: #10b981;
                    --danger: #ef4444;
                    --console-bg: rgba(0, 0, 0, 0.7);
                    --console-color: #a7f3d0;
                    --input-bg: rgba(0, 0, 0, 0.5);
                    --input-border: rgba(255,255,255,0.1);
                    --sidebar-hover: rgba(255, 255, 255, 0.08);
                    --card-bg: rgba(45,27,105,0.95);
                    --slot-bg: rgba(26,11,46,0.9);
                    --slot-border: rgba(255,255,255,0.08);
                    --player-item-bg: rgba(255,255,255,0.04);
                    --player-item-border: rgba(255,255,255,0.08);
                    --btn-bg: linear-gradient(135deg, #a855f7, #7c3aed);
                    --scrollbar-track: rgba(255,255,255,0.05);
                    --scrollbar-thumb: linear-gradient(to bottom, rgba(168,85,247,0.5), rgba(192,132,252,0.5));
                    }
                    body { margin: 0; font-family: 'Outfit', sans-serif; background: var(--bg-gradient); color: var(--text-color); min-height: 100vh; overflow-x: hidden; animation: fadeIn 0.8s ease-out; }
                    body::before { content:''; position:fixed; top:-50%; left:-50%; width:200%; height:200%; background: radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.1) 50%, transparent 70%); z-index:-1; pointer-events:none; animation: pulse 4s ease-in-out infinite; }
                    body::after { content:''; position:fixed; top:0; left:0; width:100%; height:100%; background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="1" fill="rgba(255,255,255,0.03)"/></svg>'); z-index:-1; pointer-events:none; }
                    .glass { background: var(--glass-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid var(--border-color); box-shadow: 0 12px 40px var(--shadow), inset 0 1px 0 rgba(255, 255, 255, 0.1); animation: fadeIn 0.6s ease-out; }
                    .topbar { position: fixed; top: 0; left: 0; width: 100%; height: 70px; display: flex; align-items: center; padding: 0 30px; z-index: 100; border-bottom: 1px solid var(--border-color); box-sizing: border-box; animation: slideIn 0.5s ease-out; }
                    .topbar h2 { font-weight: 800; background: linear-gradient(to right, var(--accent1), var(--accent2), var(--accent3)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px; text-shadow: 0 0 20px rgba(129, 140, 248, 0.3); }
                    .sidebar { position: fixed; top: 70px; width: 260px; height: calc(100% - 70px); padding: 30px 0; border-right: 1px solid var(--border-color); animation: slideIn 0.7s ease-out; }
                    .sidebar a { display: flex; align-items: center; padding: 16px 30px; color: #94a3b8; text-decoration: none; font-weight: 600; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); border-left: 3px solid transparent; margin-bottom: 8px; border-radius: 0 8px 8px 0; position: relative; overflow: hidden; }
                    .sidebar a::before { content:''; position:absolute; top:0; left:-100%; width:100%; height:100%; background: linear-gradient(90deg, transparent, rgba(129, 140, 248, 0.1), transparent); transition: left 0.5s; }
                    .sidebar a:hover::before { left: 100%; }
                    .sidebar a:hover { color: var(--text-color); background: var(--sidebar-hover); padding-left: 35px; transform: translateX(5px); }
                    .sidebar a.active { color: #fff; background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.1)); border-left-color: var(--accent1); text-shadow: 0 0 15px rgba(129, 140, 248, 0.7); animation: glow 2s ease-in-out infinite; }
                    .main { margin-left: 260px; margin-top: 70px; padding: 40px; width: calc(100% - 260px); box-sizing: border-box; min-height: calc(100vh - 70px); display: grid; gap: 30px; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); align-content: start; }
                    .card { border-radius: 24px; padding: 35px; text-align: left; position: relative; overflow: hidden; animation: fadeIn 0.8s ease-out; transition: transform 0.3s ease, box-shadow 0.3s ease; }
                    .card:hover { transform: translateY(-5px); box-shadow: 0 20px 60px var(--shadow); }
                    .card::before { content:''; position:absolute; top:0; left:0; right:0; height:6px; background: linear-gradient(to right, rgba(99, 102, 241, 0.9), rgba(192, 132, 252, 0.9), rgba(244, 114, 182, 0.9)); opacity: 0.7; }
                    .card::after { content:''; position:absolute; bottom:0; left:0; right:0; height:1px; background: linear-gradient(to right, transparent, rgba(255,255,255,0.1), transparent); }
                    .card h1 { margin-top: 0; font-weight: 800; letter-spacing: -1px; background: linear-gradient(to right, var(--text-color), #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                    .card h3 { color: #cbd5e1; font-weight: 600; margin-top: 0; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }
                    .console-box { background: var(--console-bg); color: var(--console-color); font-family: 'JetBrains Mono', monospace; padding: 20px; border-radius: 16px; height: 350px; overflow-y: auto; font-size: 13px; border: 1px inset rgba(255, 255, 255, 0.15); line-height: 1.5; box-shadow: inset 0 6px 25px rgba(0,0,0,0.6), 0 4px 15px rgba(0,0,0,0.3); scroll-behavior: smooth; }
                    .console-box::-webkit-scrollbar { width: 10px; border-radius: 5px; }
                    .console-box::-webkit-scrollbar-track { background: var(--scrollbar-track); border-radius: 5px; }
                    .console-box::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 5px; transition: 0.3s; }
                    .console-box::-webkit-scrollbar-thumb:hover { background: linear-gradient(to bottom, rgba(129,140,248,0.8), rgba(192,132,252,0.8)); }
                    .cmd-input { width: calc(100% - 100px); padding: 14px 20px; background: var(--input-bg); border: 2px solid var(--input-border); color: white; border-radius: 12px 0 0 12px; font-family: 'JetBrains Mono', monospace; outline: none; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }
                    .cmd-input:focus { border-color: var(--accent1); background: rgba(0,0,0,0.7); box-shadow: 0 0 0 3px rgba(129,140,248,0.2), inset 0 2px 4px rgba(0,0,0,0.3); transform: scale(1.02); }
                    .cmd-btn { width: 100px; padding: 14px; background: var(--btn-bg); border: none; color: white; font-weight: 700; border-radius: 0 12px 12px 0; cursor: pointer; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 15px rgba(99,102,241,0.3); }
                    .cmd-btn:hover { background: linear-gradient(135deg, #4f46e5, #3730a3); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(99,102,241,0.5); }
                    .inv-grid { display: grid; grid-template-columns: repeat(9, 54px); gap: 4px; background: var(--card-bg); padding: 16px; border: 2px solid var(--input-border); border-radius: 16px; margin: 20px auto; width: fit-content; box-shadow: inset 0 6px 20px rgba(0,0,0,0.6), 0 8px 25px rgba(0,0,0,0.4); animation: fadeIn 1s ease-out; }
                    .slot { width: 54px; height: 54px; background: var(--slot-bg); border: 2px solid var(--slot-border); border-radius: 8px; display: flex; align-items: center; justify-content: center; position: relative; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; }
                    .slot:hover { background: rgba(30,41,59,1); border-color: rgba(129,140,248,0.5); transform: scale(1.1) rotate(2deg); z-index: 30; box-shadow: 0 8px 20px rgba(129,140,248,0.3); }
                    .slot img { width: 34px; height: 34px; image-rendering: pixelated; z-index: 10; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.6)); transition: 0.3s; }
                    .slot:hover img { transform: scale(1.2); }
                    .hotbar-separator { grid-column: span 9; height: 12px; background: linear-gradient(to right, transparent, rgba(255,255,255,0.1), transparent); border-radius: 2px; }
                    .player-item { display: flex; align-items: center; background: var(--player-item-bg); margin: 12px 0; padding: 15px; border-radius: 16px; border: 1px solid var(--player-item-border); transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
                    .player-item::before { content:''; position:absolute; top:0; left:-100%; width:100%; height:100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent); transition: left 0.6s; }
                    .player-item:hover::before { left: 100%; }
                    .player-item:hover { background: rgba(255,255,255,0.1); transform: translateY(-3px) scale(1.02); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
                    .btn-action { padding: 10px 16px; border: none; color: white; border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 12px; margin-left: 8px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-transform: uppercase; letter-spacing: 0.5px; position: relative; overflow: hidden; }
                    .btn-action::before { content:''; position:absolute; top:50%; left:50%; width:0; height:0; background: rgba(255,255,255,0.2); border-radius: 50%; transition: width 0.6s, height 0.6s; transform: translate(-50%, -50%); }
                    .btn-action:hover::before { width: 300px; height: 300px; }
                    .btn-action:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.4); }
                    .btn-start { padding: 18px; background: linear-gradient(135deg, var(--success), #059669); border: none; color: white; border-radius: 14px; font-weight: 800; cursor: pointer; width: 100%; font-size: 16px; text-shadow: 0 2px 4px rgba(0,0,0,0.4); box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5); transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); animation: pulse 3s ease-in-out infinite; }
                    .btn-start:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 10px 30px rgba(16, 185, 129, 0.7); }
                    .btn-stop { padding: 18px; background: linear-gradient(135deg, var(--danger), #dc2626); border: none; color: white; border-radius: 14px; font-weight: 800; cursor: pointer; width: 100%; font-size: 16px; text-shadow: 0 2px 4px rgba(0,0,0,0.4); box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5); transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
                    .btn-stop:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 10px 30px rgba(239, 68, 68, 0.7); }
                    .badge { position:absolute; bottom:2px; right:4px; font-size:14px; font-weight:800; color:white; font-family:'Outfit', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,1), 0 -1px 3px rgba(0,0,0,0.9); z-index:20; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px; }
                    select { background: var(--input-bg); color: white; border: 2px solid var(--input-border); border-radius: 8px; padding: 10px; transition: 0.3s; }
                    select:focus { border-color: var(--accent1); box-shadow: 0 0 0 3px rgba(129,140,248,0.2); }
                    input[type="text"], input[type="number"], input[type="time"] { background: var(--input-bg); color: white; border: 2px solid var(--input-border); border-radius: 8px; padding: 10px; transition: 0.3s; }
                    input:focus { border-color: var(--accent1); box-shadow: 0 0 0 3px rgba(129,140,248,0.2); }
                """

                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                theme = query.get('theme', ['default'])[0]
                body_class = f"theme-{theme}"
                # build theme selector dropdown (kept in nav header)
                theme_options = ['default','light','dark','blue','purple']
                theme_dropdown = '<select onchange="window.location.search = \'?theme=\' + this.value" style="background:rgba(0,0,0,0.5);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px;margin-left:20px;">'
                for t in theme_options:
                    sel = ' selected' if t == theme else ''
                    theme_dropdown += f"<option value=\"{t}\"{sel}>{t.capitalize()}</option>"
                theme_dropdown += '</select>'

                if self.path == "/map":
                    self.send_response(200)
                    self.send_header("Content-type","text/html")
                    self.end_headers()
                    if mc.is_running:
                        content = "<iframe src='http://localhost:8081' style='width:100%; height:100%; border:none; border-radius:12px;'></iframe>"
                    else:
                        content = """
                            <div style='display:flex; justify-content:center; align-items:center; height:100%;'>
                                <div class='glass card' style='max-width:400px; text-align:center;'>
                                    <h2 style='color:#ef4444;'>🗺️ Map is Offline</h2>
                                    <p style='color:#cbd5e1; margin-bottom:20px;'>The Live Map requires the Minecraft server to be running.</p>
                                    <form method='POST' action='/start'>
                                        <button class='btn-start'>🚀 START SERVER</button>
                                    </form>
                                </div>
                            </div>
                            """
                    nav = NAV.replace("href='/map'", "href='/map' class='active'")
                    self.wfile.write(
                        f"<html><head><title>Live Map</title><meta charset='UTF-8'><style>{css}</style></head><body class=\"{body_class}\"><div class='glass topbar'><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div><div class='glass sidebar'>{nav}</div><div class='main' style='padding:40px; display:block; height:calc(100vh - 70px);'>{content}</div></body></html>".encode()
                    )

                # PAGE: SETTINGS (WHITELIST & BANS)
                elif self.path == "/settings":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()

                    whitelist, bans = [], []
                    try:
                        if os.path.exists("whitelist.json"):
                            with open("whitelist.json", "r") as f:
                                whitelist = json.load(f)
                    except:
                        pass
                    try:
                        if os.path.exists("banned-players.json"):
                            with open("banned-players.json", "r") as f:
                                bans = json.load(f)
                    except:
                        pass

                    wl_html = (
                        "".join(
                            [
                                f"<div class='player-item'><b>{p.get('name', 'Unknown')}</b><form method='POST' action='/command' style='margin:0 0 0 auto;'><input type='hidden' name='cmd' value='whitelist remove {p.get('name')}'><button class='btn-action' style='background:#ef4444;'>❌ Remove</button></form></div>"
                                for p in whitelist
                            ]
                        )
                        if whitelist
                        else "<p style='color:#64748b;'>Whitelist is currently empty.</p>"
                    )
                    ban_html = (
                        "".join(
                            [
                                f"<div class='player-item'><b>{p.get('name', 'Unknown')}</b><span style='color:#94a3b8; font-size:12px; margin-left:10px;'>Reason: {p.get('reason', 'None')}</span><form method='POST' action='/command' style='margin:0 0 0 auto;'><input type='hidden' name='cmd' value='pardon {p.get('name')}'><button class='btn-action' style='background:#10b981;'>✔️ Pardon</button></form></div>"
                                for p in bans
                            ]
                        )
                        if bans
                        else "<p style='color:#64748b;'>No banned players.</p>"
                    )

                    nav = NAV.replace("href='/settings'", "href='/settings' class='active'")
                    self.wfile.write(
                        f"<html><head><title>Server Settings</title><meta charset='UTF-8'><style>{css}</style><meta http-equiv='refresh' content='10'></head><body class=\"{body_class}\"><div class='glass topbar'><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div><div class='glass sidebar'>{nav}</div><div class='main'><div class='glass card'><h3>🛡️ Whitelist Manager</h3><form method='POST' action='/command' style='display:flex; margin-bottom:20px;'><input type='text' name='cmd' class='cmd-input' style='background:rgba(0,0,0,0.2);' placeholder='Enter username to whitelist...' onchange=\"this.value='whitelist add '+this.value.replace('whitelist add ', '')\"><button class='cmd-btn' style='background:#10b981;'>ADD</button></form><div style='max-height: 250px; overflow-y: auto;'>{wl_html}</div></div><div class='glass card'><h3>🔨 Banned Players</h3><form method='POST' action='/command' style='display:flex; margin-bottom:20px; gap:10px;'><input type='text' name='cmd' class='cmd-input' style='background:rgba(0,0,0,0.2); flex:1;' placeholder='Username...' onchange=\"this.form.elements[1].name='cmd'; this.form.elements[1].value='ban '+this.value+' '+this.form.elements[2].value\"><select name='reason' style='background:rgba(0,0,0,0.4);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px;'><option value='Griefing'>Griefing</option><option value='Spamming'>Spamming</option><option value='Cheating'>Cheating</option><option value='Harassment'>Harassment</option><option value='Other'>Other</option></select><button class='cmd-btn' style='background:#ef4444;' onclick=\"this.form.elements[1].value='ban '+this.form.elements[0].value+' '+this.form.elements[2].value\">BAN</button></form><div style='max-height: 250px; overflow-y: auto;'>{ban_html}</div></div></div></body></html>".encode()
                    )

                # PAGE: INVENTORY
                elif self.path.startswith("/inventory"):
                    query = urllib.parse.urlparse(self.path).query
                    player_name = urllib.parse.parse_qs(query).get("name", [None])[0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    if not player_name:
                        # Show player selector
                        usercache = []
                        try:
                            with open("usercache.json") as f:
                                usercache = json.load(f)
                        except: pass
                        online_names = list(mc.online_players)
                        all_players = list(set([p['name'] for p in usercache] + online_names))
                        options = "".join([f"<option value='{p}'>{p} {'(Online)' if p in online_names else ''}</option>" for p in sorted(all_players)])
                        nav = NAV.replace("href='/inventory'", "href='/inventory' class='active'")
                        self.wfile.write(f"""<html><head><title>Inventory Viewer</title><meta charset='UTF-8'><style>{css}</style></head><body class="{body_class}">
                            <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                            <div class="glass sidebar">{nav}</div>
                            <div class="main"><div class="glass card" style="text-align:center;">
                                <h2>🎒 Select Player Inventory</h2>
                                <form method="GET" action="/inventory" style="margin:20px 0;">
                                    <select name="name" style="background:rgba(0,0,0,0.4);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:10px;margin-right:10px;">
                                        <option value="">Choose a player...</option>{options}
                                    </select>
                                    <button class="btn-action" style="background:#6366f1;">View Inventory</button>
                                </form>
                                <a href='/' style='color: #818cf8; text-decoration: none; font-weight:600;'>← Back to Dashboard</a>
                            </div></div>
                        </body></html>""".encode())
                        return
                    items = mc.player_inventory.get(player_name, [])
                    slot_map = {}
                    for item in items:
                        if isinstance(item, dict) and 0 <= item.get("slot", -1) <= 35:
                            slot_map[item["slot"]] = item

                    ordered_slots = list(range(9, 36)) + ["SEP"] + list(range(0, 9))
                    inv_slots = ""
                    for s in ordered_slots:
                        if s == "SEP":
                            inv_slots += "<div class='hotbar-separator'></div>"
                        else:
                            item = slot_map.get(s)
                            if item:
                                img_url = f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.1/items/{item['id']}.png"
                                count_div = (
                                    f"<div class='badge'>{item['count']}</div>"
                                    if item.get("count", 1) > 1
                                    else ""
                                )
                                inv_slots += f"<div class='slot'><img src='{img_url}' onerror=\"this.style.display='none'\">{count_div}</div>"
                            else:
                                inv_slots += "<div class='slot'></div>"
                    nav = NAV.replace("href='/inventory'", "href='/inventory' class='active'")
                    self.wfile.write(
                        f"<html><head><title>Inventory Viewer</title><meta charset='UTF-8'><style>{css}</style><meta http-equiv='refresh' content='5'></head><body class=\"{body_class}\"><div class='glass topbar'><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div><div class='glass sidebar'>{nav}</div><div class='main'><div class='glass card' style='text-align:center;'><h2><img src='https://mc-heads.net/avatar/{player_name}/32' style='vertical-align:middle;border-radius:6px;margin-right:12px;'>{player_name}'s Items</h2><div class='inv-grid'>{inv_slots}</div><a href='/inventory' style='color: #818cf8; text-decoration: none; font-weight:600;'>← Select Another Player</a></div></div></body></html>".encode()
                    )

                # PAGE: DASHBOARD
                elif self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    status = "ONLINE 🟢" if mc.is_running else "OFFLINE 🔴"
                    color = "#10b981" if mc.is_running else "#ef4444"
                    btn = (
                        '<form method="POST" action="/stop"><button class="btn-stop">🛑 STOP SERVER</button></form>'
                        if mc.is_running
                        else '<form method="POST" action="/start"><button class="btn-start">🚀 START SERVER</button></form>'
                    )
                    p_list = "".join(
                        [
                            f"<div class='player-item'><img src='https://mc-heads.net/avatar/{p}/32' style='margin-right:15px; border-radius:6px; box-shadow:0 2px 5px rgba(0,0,0,0.5);'><div style='text-align:left;flex-grow:1'><a href='/inventory?name={p}' style='color:white;text-decoration:none;font-size:16px;'><b>{p}</b></a></div>"
                            f"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='op {p}'><button class='btn-action' style='background:#f59e0b;'>⭐ OP</button></form>"
                            f"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='kick {p}'><button class='btn-action' style='background:#f97316;'>👢 Kick</button></form>"
                            f"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='ban {p}'><button class='btn-action' style='background:#ef4444;'>🔨 Ban</button></form>"
                            f"<a href='/inventory?name={p}' class='btn-action' style='background:#3b82f6; text-decoration:none;'>🎒 INV</a></div>"
                            for p in mc.online_players
                        ]
                    )
                    logs_html = "".join(
                        [
                            f"<div>{line.replace('<','&lt;').replace('>','&gt;')}</div>"
                            for line in mc.console_logs
                        ]
                    )
                    cmd_box = f"""
                        <form method="POST" action="/command" style="display:flex; margin-top:15px;">
                            <input type="text" name="cmd" class="cmd-input" placeholder="Enter server command (e.g. time set day)..." required {'disabled' if not mc.is_running else ''} autocomplete="off">
                            <button type="submit" class="cmd-btn" {'disabled' if not mc.is_running else ''}>SEND</button>
                        </form>
                    """
                    tps = mc.tps
                    tps_color = (
                        "#10b981"
                        if tps > 18
                        else ("#f59e0b" if tps > 13 else "#ef4444")
                    )
                    self.wfile.write(
                        f"""<html><head><title>Admin Dashboard</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar">{NAV.replace("href='/'", "href='/' class='active'")}</div>
                        <div class="main">
                            <div class="glass card" style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; padding: 25px 40px;">
                                <div style="display:flex; gap: 40px;">
                                    <div><h3 style="margin:0; color:#94a3b8;">Server Status</h3><h1 style="color:{color}; margin: 5px 0 0 0; font-size: 32px;" id="srv-status">{status}</h1></div>
                                    <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 40px;"><h3 style="margin:0; color:#94a3b8;">Performance</h3><h1 style="color:{tps_color}; margin: 5px 0 0 0; font-size: 32px;" id="srv-tps">{tps:.1f} TPS</h1></div>
                                </div>
                                <div style="width: 250px;">{btn}</div>
                            </div>
                            <div class="glass card">
                                <h3>👥 Online Players (<span id=\"player-count\">{len(mc.online_players)}</span>)</h3>
                                <div style="margin-top:20px;">{p_list or "<p style='color:#64748b; font-style:italic;'>No one is currently online.</p>"}</div>
                            </div>
                            <div class="glass card" style="display:flex; flex-direction:column;">
                                <h3>💻 Live Console</h3>
                                <div class="console-box" id="console">{logs_html}</div>
                                {cmd_box}
                            </div>
                        </div>
                        <script>
                             var cons = document.getElementById('console');
                             cons.scrollTop = cons.scrollHeight;
                             var _lastLog = cons.innerHTML;
                             function mkBtn(p) {{
                                 return "<div class='player-item'><img src='https://mc-heads.net/avatar/"+p+"/32' style='margin-right:15px;border-radius:6px;'><div style='text-align:left;flex-grow:1'><a href='/inventory?name="+p+"' style='color:white;text-decoration:none;font-size:16px;'><b>"+p+"</b></a></div>"
                                   +"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='op "+p+"'><button class='btn-action' style='background:#f59e0b;'>&#x2B50; OP</button></form>"
                                   +"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='kick "+p+"'><button class='btn-action' style='background:#f97316;'>&#x1F462; Kick</button></form>"
                                   +"<form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='ban "+p+"'><button class='btn-action' style='background:#ef4444;'>&#x1F528; Ban</button></form>"
                                   +"<a href='/inventory?name="+p+"' class='btn-action' style='background:#3b82f6;text-decoration:none;'>&#x1F392; INV</a></div>";
                             }}
                             function poll() {{
                                 fetch('/api/status').then(r => r.json()).then(d => {{
                                     document.getElementById('srv-status').style.color = d.running ? '#10b981' : '#ef4444';
                                     document.getElementById('srv-status').textContent = d.running ? 'ONLINE 🟢' : 'OFFLINE 🔴';
                                     var tc = d.tps > 18 ? '#10b981' : (d.tps > 13 ? '#f59e0b' : '#ef4444');
                                     document.getElementById('srv-tps').style.color = tc;
                                     document.getElementById('srv-tps').textContent = d.tps.toFixed(1) + ' TPS';
                                     document.getElementById('srv-btn').innerHTML = d.running
                                         ? "<form method='POST' action='/stop'><button class='btn-stop'>&#x1F6D1; STOP SERVER</button></form>"
                                         : "<form method='POST' action='/start'><button class='btn-start'>&#x1F680; START SERVER</button></form>";
                                     document.getElementById('player-count').textContent = d.players.length;
                                     document.getElementById('player-list').innerHTML = d.players.length
                                         ? d.players.map(mkBtn).join('')
                                         : "<p style='color:#64748b;font-style:italic;'>No one is currently online.</p>";
                                     var newLog = d.logs.map(l => "<div>"+l.replace(/</g,'&lt;').replace(/>/g,'&gt;')+"</div>").join('');
                                     if (newLog !== _lastLog) {{
                                         var atBottom = (cons.scrollHeight - cons.clientHeight - cons.scrollTop) < 60;
                                         cons.innerHTML = newLog;
                                         _lastLog = newLog;
                                         if (atBottom) cons.scrollTop = cons.scrollHeight;
                                     }}
                                 }}).catch(() => {{}});
                                 setTimeout(poll, 2500);
                             }}
                             setTimeout(poll, 2500);
                         </script>
                    </body></html>""".encode()
                    )

                elif self.path == "/api/status":
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    import json as _json
                    self.wfile.write(_json.dumps({
                        "running": mc.is_running,
                        "tps": round(mc.tps, 1),
                        "players": list(mc.online_players),
                        "logs": list(mc.console_logs[-60:]),
                        "chat": list(mc.chat_logs[-50:]),
                    }).encode())

                elif self.path.startswith("/image/"):
                    filepath = self.path[1:]
                    if os.path.exists(filepath):
                        self.send_response(200)
                        self.send_header("Content-type", "image/png")
                        self.end_headers()
                        with open(filepath, "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(404)
                        self.end_headers()

                # PAGE: WORLD UPLOAD
                elif self.path == "/world_upload":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    world_size = "Not found"
                    if os.path.isdir("world"):
                        total = sum(
                            os.path.getsize(os.path.join(dp, f))
                            for dp, _, files in os.walk("world")
                            for f in files
                        )
                        world_size = f"{total / (1024*1024):.1f} MB"
                    old_worlds = [d for d in os.listdir(".") if d.startswith("world_old_")] if os.path.isdir(".") else []
                    old_html = "".join(
                        f"<div class='player-item'><span style='flex-grow:1; font-size:13px; color:#94a3b8;'>📁 {d}</span></div>"
                        for d in sorted(old_worlds, reverse=True)[:5]
                    ) or "<p style='color:#64748b; font-size:13px;'>No old worlds.</p>"
                    warn = ""
                    if mc.is_running:
                        warn = "<div style='padding:12px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:8px; color:#f59e0b; margin-bottom:20px;'>⚠️ Server is running. It will be stopped automatically during the upload and restarted when done.</div>"
                    nav = NAV.replace("href='/world_upload'", "href='/world_upload' class='active'")
                    self.wfile.write(f"""<html><head><title>World Upload</title><meta charset="UTF-8"><style>{css}
                        .upload-zone {{ border: 2px dashed rgba(129,140,248,0.4); border-radius: 16px; padding: 60px 40px; text-align: center; background: rgba(99,102,241,0.05); transition: 0.3s; cursor: pointer; }}
                        .upload-zone:hover {{ border-color: #818cf8; background: rgba(99,102,241,0.1); }}
                        .upload-zone input[type=file] {{ display: none; }}
                        #upload-progress {{ display:none; margin-top:20px; height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden; }}
                        #upload-bar {{ height:100%; background: linear-gradient(to right, #818cf8, #c084fc); width:0; transition: width 0.3s; border-radius:3px; }}
                    </style></head><body class="{body_class}">
                    <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                    <div class="glass sidebar">{nav}</div>
                    <div class="main">
                        <div class="glass card">
                            <h3>🌍 Upload New World</h3>
                            {warn}
                            <form method="POST" action="/world_upload" enctype="multipart/form-data" id="uploadForm">
                                <div class="upload-zone" onclick="document.getElementById('wzip').click()" id="dropzone">
                                    <div style="font-size:48px; margin-bottom:15px;">📦</div>
                                    <h3 style="margin:0 0 8px 0;">Drop World ZIP here</h3>
                                    <p style="color:#64748b; margin:0; font-size:14px;">or click to browse — zip must contain a <b>world folder</b> inside</p>
                                    <input type="file" name="world_zip" id="wzip" accept=".zip" onchange="document.getElementById('fname').textContent=this.files[0].name; document.getElementById('uploadForm').submit();">
                                    <p id="fname" style="color:#818cf8; margin-top:15px; font-weight:600;"></p>
                                </div>
                                <div id="upload-progress"><div id="upload-bar"></div></div>
                            </form>
                        </div>
                        <div class="glass card">
                            <h3>📊 Current World</h3>
                            <div class="player-item"><span style="flex-grow:1;">📁 world/</span><b>{world_size}</b></div>
                            <h3 style="margin-top:25px;">🗃️ Previous Worlds</h3>
                            {old_html}
                        </div>
                    </div>
                    <script>
                        var dz = document.getElementById('dropzone');
                        dz.addEventListener('dragover', e => {{ e.preventDefault(); dz.style.borderColor='#818cf8'; }});
                        dz.addEventListener('dragleave', () => dz.style.borderColor='');
                        dz.addEventListener('drop', e => {{
                            e.preventDefault();
                            var f = e.dataTransfer.files[0];
                            if (f) {{
                                document.getElementById('fname').textContent = f.name;
                                var dt = new DataTransfer(); dt.items.add(f);
                                document.getElementById('wzip').files = dt.files;
                                document.getElementById('uploadForm').submit();
                            }}
                        }});
                    </script>
                    </body></html>""".encode())

                # PAGE: GAME RULES
                elif self.path == "/gamerules":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    BOOL_RULES = [
                        ("doDaylightCycle", "☀️ Daylight Cycle", "Enables day/night cycle"),
                        ("doWeatherCycle", "🌧️ Weather Cycle", "Enables weather changes"),
                        ("doFireTick", "🔥 Fire Spread", "Allows fire to spread"),
                        ("keepInventory", "💼 Keep Inventory", "Players keep items on death"),
                        ("doMobSpawning", "🐛 Mob Spawning", "Allows hostile/passive mobs to spawn"),
                        ("doMobLoot", "💎 Mob Loot", "Mobs drop items on death"),
                        ("doTileDrops", "📦 Block Drops", "Blocks drop items when broken"),
                        ("pvp", "⚔️ PVP", "Players can damage each other"),
                        ("mobGriefing", "💣 Mob Griefing", "Mobs can break/modify blocks"),
                        ("naturalRegeneration", "❤️ Natural Regen", "Players regenerate health naturally"),
                        ("showDeathMessages", "💀 Death Messages", "Shows death messages in chat"),
                        ("announceAdvancements", "🏆 Advancements", "Announces advancements in chat"),
                        ("commandBlockOutput", "📣 Command Output", "Commands broadcast to admins"),
                        ("sendCommandFeedback", "💬 Command Feedback", "Commands send feedback to sender"),
                        ("doInsomnia", "😴 Insomnia", "Allows phantoms to spawn from lack of sleep"),
                        ("forgiveDeadPlayers", "🕊️ Forgive Dead", "Mobs stop attacking after death"),
                        ("universalAnger", "😡 Universal Anger", "Neutral mobs attack any player who provokes"),
                    ]
                    INT_RULES = [
                        ("randomTickSpeed", "⚡ Random Tick Speed", 0, 4096, 3),
                        ("spawnRadius", "🏠 Spawn Radius", 0, 64, 10),
                        ("playerIdleTimeout", "⏱️ Idle Timeout (min)", 0, 240, 0),
                        ("maxEntityCramming", "🐄 Entity Cramming", 0, 128, 24),
                    ]
                    disabled_attr = "disabled" if not mc.is_running else ""
                    bool_html = ""
                    for rule, label, desc in BOOL_RULES:
                        bool_html += f"""
                        <div class='player-item' style='flex-wrap:wrap; gap:10px;'>
                            <div style='flex-grow:1;'>
                                <b>{label}</b>
                                <p style='margin:4px 0 0 0; color:#64748b; font-size:12px;'>{desc}</p>
                            </div>
                            <form method='POST' action='/gamerule' style='display:flex; gap:8px;'>
                                <input type='hidden' name='rule' value='{rule}'>
                                <button name='value' value='true' class='btn-action' style='background:#10b981; padding:10px 18px;' {disabled_attr}>✅ ON</button>
                                <button name='value' value='false' class='btn-action' style='background:#ef4444; padding:10px 18px;' {disabled_attr}>❌ OFF</button>
                            </form>
                        </div>"""
                    int_html = ""
                    for rule, label, mn, mx, default in INT_RULES:
                        int_html += f"""
                        <div class='player-item'>
                            <div style='flex-grow:1;'>
                                <b>{label}</b>
                                <p style='margin:4px 0 0 0; color:#64748b; font-size:12px;'>Range: {mn}–{mx} &nbsp;(default: {default})</p>
                            </div>
                            <form method='POST' action='/gamerule' style='display:flex; gap:8px; align-items:center;'>
                                <input type='hidden' name='rule' value='{rule}'>
                                <input type='number' name='value' min='{mn}' max='{mx}' value='{default}' style='width:90px; padding:10px; background:rgba(0,0,0,0.4); color:white; border:1px solid rgba(255,255,255,0.2); border-radius:8px; text-align:center;' {disabled_attr}>
                                <button class='btn-action' style='background:#6366f1; padding:10px 18px;' {disabled_attr}>SET</button>
                            </form>
                        </div>"""
                    offline_warn = "" if mc.is_running else "<div style='padding:12px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; color:#ef4444; margin-bottom:20px;'>🔴 Server is offline — start the server to apply game rules.</div>"
                    nav = NAV.replace("href='/gamerules'", "href='/gamerules' class='active'")
                    self.wfile.write(f"""<html><head><title>Game Rules</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                    <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                    <div class="glass sidebar">{nav}</div>
                    <div class="main">
                        <div class="glass card" style="grid-column:1/-1;">
                            <h3>🎮 Boolean Game Rules</h3>
                            {offline_warn}
                            {bool_html}
                        </div>
                        <div class="glass card" style="grid-column:1/-1;">
                            <h3>🔢 Numeric Game Rules</h3>
                            {int_html}
                        </div>
                    </div></body></html>""".encode())


                elif self.path == "/chat":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    chat_html = "".join([
                        f"<div style='padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05);'><span style='color:#818cf8; font-family:JetBrains Mono,monospace; font-size:12px;'>[{c['time']}]</span> <span style='color:#f8fafc;'>{c['raw'].replace('<','&lt;').replace('>','&gt;')}</span></div>"
                        for c in mc.chat_logs
                    ]) or "<p style='color:#64748b; font-style:italic;'>No chat messages yet.</p>"
                    self.wfile.write(f"""<html><head><title>Chat Relay</title><meta charset="UTF-8"><style>{css}</style><meta http-equiv="refresh" content="3"></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar"><a href="/">📊 Dashboard</a><a href="/map">🗺️ Map</a><a href="/chat" class="active">💬 Chat</a><a href="/inventory">🎒 Inventories</a><a href="/backups">💾 Backups</a><a href="/server_props">⚙️ Server Props</a><a href="/gamerules">🎮 Game Rules</a><a href="/stats">📊 Stats</a><a href="/mods">🔧 Mods</a><a href="/logs">📜 Logs</a><a href="/scheduler">⏰ Scheduler</a><a href="/settings">🛡️ Settings</a></div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1; display:flex; flex-direction:column;">
                            <h3>💬 Live Chat Relay</h3>
                            <div class="console-box" style="height:400px;" id="chat">{chat_html}</div>
                            <form method="POST" action="/chat" style="display:flex; margin-top:15px;">
                                <input type="text" name="msg" class="cmd-input" placeholder="Send a message to players as [Admin]..." required {'disabled' if not mc.is_running else ''} autocomplete="off">
                                <button class="cmd-btn" {'disabled' if not mc.is_running else ''}>SEND</button>
                            </form>
                        </div></div>
                        <script>var c=document.getElementById('chat');c.scrollTop=c.scrollHeight;</script>
                    </body></html>""".encode())

                # PAGE: BACKUPS
                elif self.path == "/backups":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    backup_files = []
                    if os.path.isdir("backups"):
                        for f in sorted(os.listdir("backups"), reverse=True):
                            if f.endswith(".zip"):
                                fpath = os.path.join("backups", f)
                                size_mb = os.path.getsize(fpath) / (1024*1024)
                                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
                                backup_files.append(f"<div class='player-item'><div style='flex-grow:1'><b>{f}</b><br><span style='color:#94a3b8; font-size:12px;'>{size_mb:.1f} MB &bull; {mod_time}</span></div><a href='/dl_backup?f={urllib.parse.quote(f)}' class='btn-action' style='background:#6366f1; text-decoration:none;'>⬇️ Download</a></div>")
                    backup_html = "".join(backup_files) if backup_files else "<p style='color:#64748b; font-style:italic;'>No backups yet. Create your first one!</p>"
                    self.wfile.write(f"""<html><head><title>World Backups</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar"><a href="/">📊 Dashboard</a><a href="/map">🗺️ Map</a><a href="/chat">💬 Chat</a><a href="/inventory">🎒 Inventories</a><a href="/backups" class="active">💾 Backups</a><a href="/server_props">⚙️ Server Props</a><a href="/gamerules">🎮 Game Rules</a><a href="/stats">📊 Stats</a><a href="/mods">🔧 Mods</a><a href="/logs">📜 Logs</a><a href="/scheduler">⏰ Scheduler</a><a href="/settings">🛡️ Settings</a></div>
                        <div class="main"><div class="glass card">
                            <h3>💾 World Backups</h3>
                            <form method="POST" action="/backup" style="margin-bottom:25px;">
                                <button class="btn-start" style="width:auto; padding:14px 30px;">🗜️ Create Backup Now</button>
                            </form>
                            <div>{backup_html}</div>
                        </div></div>
                    </body></html>""".encode())

                # PAGE: DOWNLOAD BACKUP
                elif self.path.startswith("/dl_backup"):
                    query = urllib.parse.urlparse(self.path).query
                    fname = urllib.parse.parse_qs(query).get("f", [None])[0]
                    fpath = os.path.join("backups", fname) if fname else None
                    if fpath and os.path.isfile(fpath):
                        self.send_response(200)
                        self.send_header("Content-type", "application/zip")
                        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                        self.end_headers()
                        with open(fpath, "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(404)
                        self.end_headers()

                # PAGE: SERVER PROPERTIES EDITOR
                elif self.path == "/server_props":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    props = mc.get_server_properties()
                    EDITABLE = [
                        ("pvp", "Enable PVP", "bool"),
                        ("difficulty", "Difficulty", "select", ["peaceful","easy","normal","hard"]),
                        ("hardcore", "Hardcore Mode", "bool"),
                        ("max-players", "Max Players", "number"),
                        ("gamemode", "Default Gamemode", "select", ["survival","creative","adventure","spectator"]),
                        ("allow-flight", "Allow Flight", "bool"),
                        ("enable-command-block", "Enable Command Blocks", "bool"),
                        ("motd", "Server MOTD", "text"),
                    ]
                    prop_html = ""
                    for item in EDITABLE:
                        key, label = item[0], item[1]
                        ftype = item[2]
                        cur = props.get(key, "")
                        if ftype == "bool":
                            checked_true = "checked" if cur == "true" else ""
                            checked_false = "checked" if cur == "false" else ""
                            prop_html += f"<div class='player-item'><span style='flex-grow:1; font-weight:600;'>{label}</span><label style='margin-right:15px; cursor:pointer;'><input type='radio' name='{key}' value='true' form='propsform' {checked_true} onchange='this.form.submit()'> On</label><label style='cursor:pointer;'><input type='radio' name='{key}' value='false' form='propsform' {checked_false} onchange='this.form.submit()'> Off</label></div>"
                        elif ftype == "select":
                            opts = "".join([f"<option value='{o}' {'selected' if cur==o else ''}>{o.title()}</option>" for o in item[3]])
                            prop_html += f"<div class='player-item'><span style='flex-grow:1; font-weight:600;'>{label}</span><select name='{key}' form='propsform' onchange='this.form.submit()' style='background:rgba(0,0,0,0.4);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px;'>{opts}</select></div>"
                        else:
                            prop_html += f"<div class='player-item'><span style='flex-grow:1; font-weight:600;'>{label}</span><input type='{ftype}' name='{key}' form='propsform' value='{cur}' style='width:200px; background:rgba(0,0,0,0.4);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px; text-align:right;' onblur='this.form.submit()'></div>"
                    restart_note = "<div style='margin-top:15px; padding:12px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:8px; color:#f59e0b; font-size:13px;'>⚠️ Changes take effect after the server restarts.</div>"
                    self.wfile.write(f"""<html><head><title>Server Properties</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar"><a href="/">📊 Dashboard</a><a href="/map">🗺️ Map</a><a href="/chat">💬 Chat</a><a href="/inventory">🎒 Inventories</a><a href="/backups">💾 Backups</a><a href="/server_props" class="active">⚙️ Server Props</a><a href="/gamerules">🎮 Game Rules</a><a href="/stats">📊 Stats</a><a href="/mods">🔧 Mods</a><a href="/logs">📜 Logs</a><a href="/scheduler">⏰ Scheduler</a><a href="/settings">🛡️ Settings</a></div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1;">
                            <h3>⚙️ Server Properties</h3>
                            <form id="propsform" method="POST" action="/server_props"></form>
                            {prop_html}
                            {restart_note}
                        </div></div>
                    </body></html>""".encode())

                # PAGE: PLAYER STATS
                elif self.path.startswith("/stats"):
                    query = urllib.parse.urlparse(self.path).query
                    player_uuid = urllib.parse.parse_qs(query).get("uuid", [None])[0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    stats_html = ""
                    if player_uuid:
                        try:
                            stats_file = os.path.join("world", "stats", f"{player_uuid}.json")
                            with open(stats_file) as f:
                                raw = json.load(f).get("stats", {})
                            mined = raw.get("minecraft:mined", {})
                            killed = raw.get("minecraft:killed", {})
                            custom = raw.get("minecraft:custom", {})
                            top_mined = sorted(mined.items(), key=lambda x: x[1], reverse=True)[:10]
                            top_killed = sorted(killed.items(), key=lambda x: x[1], reverse=True)[:10]
                            dist = custom.get("minecraft:walk_one_cm", 0) / 100
                            play_ticks = custom.get("minecraft:play_time", 0)
                            play_hrs = play_ticks // 72000
                            jumps = custom.get("minecraft:jump", 0)
                            mined_html = "".join([f"<div class='player-item'><span style='flex-grow:1;'>{k.replace('minecraft:','').replace('_',' ').title()}</span><b>{v:,}</b></div>" for k, v in top_mined]) or "<p style='color:#64748b'>None yet</p>"
                            killed_html = "".join([f"<div class='player-item'><span style='flex-grow:1;'>{k.replace('minecraft:','').replace('_',' ').title()}</span><b>{v:,}</b></div>" for k, v in top_killed]) or "<p style='color:#64748b'>None yet</p>"
                            stats_html = f"""<div style='display:grid; grid-template-columns:repeat(3,1fr); gap:15px; margin-bottom:25px;'>
                                <div class='glass card' style='text-align:center; padding:20px;'><h3>🚶 Distance Walked</h3><h2>{dist:,.0f}m</h2></div>
                                <div class='glass card' style='text-align:center; padding:20px;'><h3>🕐 Play Time</h3><h2>{play_hrs:,} hrs</h2></div>
                                <div class='glass card' style='text-align:center; padding:20px;'><h3>🐸 Jumps</h3><h2>{jumps:,}</h2></div>
                            </div>
                            <div style='display:grid; grid-template-columns:1fr 1fr; gap:20px;'>
                                <div><h3>⛏️ Top Blocks Mined</h3>{mined_html}</div>
                                <div><h3>⚔️ Mobs Killed</h3>{killed_html}</div>
                            </div>"""
                        except Exception as e:
                            stats_html = f"<p style='color:#ef4444;'>Could not load stats: {e}</p>"
                    else:
                        # Show list with links to individual player stats
                        usercache = []
                        try:
                            with open("usercache.json") as f:
                                usercache = json.load(f)
                        except: pass
                        rows = "".join([
                            f"<div class='player-item'><img src='https://mc-heads.net/avatar/{p['name']}/32' style='margin-right:15px; border-radius:6px;'><b style='flex-grow:1;'>{p['name']}</b><a href='/stats?uuid={p.get('uuid','')}' class='btn-action' style='background:#6366f1; text-decoration:none;'>📊 View Stats</a></div>"
                            for p in usercache
                        ])
                        stats_html = rows or "<p style='color:#64748b; font-style:italic;'>No player cache found.</p>"
                    self.wfile.write(f"""<html><head><title>Player Stats</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar"><a href="/">📊 Dashboard</a><a href="/map">🗺️ Map</a><a href="/chat">💬 Chat</a><a href="/inventory">🎒 Inventories</a><a href="/backups">💾 Backups</a><a href="/server_props">⚙️ Server Props</a><a href="/gamerules">🎮 Game Rules</a><a href="/stats">📊 Stats</a><a href="/mods">🔧 Mods</a><a href="/logs">📜 Logs</a><a href="/scheduler">⏰ Scheduler</a><a href="/settings">🛡️ Settings</a></div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1;">
                            <h3>📊 Player Statistics</h3><a href="/stats" style='color:#818cf8; text-decoration:none; font-size:13px;'>← All Players</a>
                            <div style="margin-top:20px;">{stats_html}</div>
                        </div></div>
                    </body></html>""".encode())

                # PAGE: MODS
                elif self.path == "/mods":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    mods_list = []
                    if os.path.isdir("mods"):
                        for f in sorted(os.listdir("mods")):
                            if f.endswith(".jar"):
                                fpath = os.path.join("mods", f)
                                size_mb = os.path.getsize(fpath) / (1024*1024)
                                mod_name = f.replace(".jar", "").replace("-", " ").title()
                                mods_list.append(f"<div class='player-item'><div style='flex-grow:1'><b>{mod_name}</b><br><span style='color:#94a3b8; font-size:12px;'>{f} &bull; {size_mb:.1f} MB</span></div></div>")
                    mods_html = "".join(mods_list) if mods_list else "<p style='color:#64748b; font-style:italic;'>No mods found.</p>"
                    nav = NAV.replace("href='/mods'", "href='/mods' class='active'")
                    self.wfile.write(f"""<html><head><title>Mods</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar">{nav}</div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1;">
                            <h3>🔧 Installed Mods</h3>
                            <div style="margin-top:20px;">{mods_html}</div>
                        </div></div>
                    </body></html>""".encode())

                # PAGE: LOGS
                elif self.path.startswith("/logs"):
                    query = urllib.parse.urlparse(self.path).query
                    log_file = urllib.parse.parse_qs(query).get("file", ["latest.log"])[0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    log_options = ["latest.log"]
                    if os.path.isdir("logs"):
                        log_options += sorted([f for f in os.listdir("logs") if f.endswith(".log.gz") or f.endswith(".log")], reverse=True)
                    select_html = "".join([f"<option value='{f}' {'selected' if f == log_file else ''}>{f}</option>" for f in log_options])
                    log_content = ""
                    try:
                        if log_file.endswith(".gz"):
                            import gzip
                            with gzip.open(os.path.join("logs", log_file), "rt", encoding="utf-8") as f:
                                lines = f.readlines()[-100:]  # Last 100 lines
                        else:
                            with open(os.path.join("logs", log_file), "r", encoding="utf-8") as f:
                                lines = f.readlines()[-100:]
                        log_content = "".join([f"<div>{line.strip()}</div>" for line in lines])
                    except Exception as e:
                        log_content = f"<p style='color:#ef4444;'>Error loading log: {e}</p>"
                    nav = NAV.replace("href='/logs'", "href='/logs' class='active'")
                    self.wfile.write(f"""<html><head><title>Logs</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar">{nav}</div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1;">
                            <h3>📜 Server Logs</h3>
                            <form method="GET" action="/logs" style="margin-bottom:20px;">
                                <label style="color:#94a3b8; font-size:14px;">Select Log File:</label>
                                <select name="file" onchange="this.form.submit()" style="background:rgba(0,0,0,0.4);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px;margin-left:10px;">{select_html}</select>
                            </form>
                            <div class="console-box" style="height:500px;">{log_content}</div>
                        </div></div>
                    </body></html>""".encode())

                # PAGE: COMMANDS
                elif self.path == "/commands":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    common_commands = [
                        ("time set day", "☀️ Set time to day"),
                        ("time set night", "🌙 Set time to night"),
                        ("weather clear", "☀️ Clear weather"),
                        ("weather rain", "🌧️ Start rain"),
                        ("weather thunder", "⛈️ Start thunderstorm"),
                        ("gamerule keepInventory true", "💼 Enable keep inventory"),
                        ("gamerule keepInventory false", "💀 Disable keep inventory"),
                        ("difficulty peaceful", "🕊️ Set difficulty to peaceful"),
                        ("difficulty easy", "🐔 Set difficulty to easy"),
                        ("difficulty normal", "⚖️ Set difficulty to normal"),
                        ("difficulty hard", "💀 Set difficulty to hard"),
                        ("save-all", "💾 Save the world"),
                        ("stop", "🛑 Stop the server"),
                    ]
                    cmd_html = "".join([
                        f"<div class='player-item'><span style='flex-grow:1; font-weight:600;'>{desc}</span><form method='POST' action='/command' style='margin:0;'><input type='hidden' name='cmd' value='{cmd}'><button class='btn-action' style='background:#6366f1;'>Execute</button></form></div>"
                        for cmd, desc in common_commands
                    ])
                    nav = NAV.replace("href='/commands'", "href='/commands' class='active'")
                    self.wfile.write(f"""<html><head><title>Commands</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar">{nav}</div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1;">
                            <h3>💻 Common Commands</h3>
                            <div style="margin-top:20px;">{cmd_html}</div>
                        </div></div>
                    </body></html>""".encode())

                # PAGE: AUTO RESTART SCHEDULER
                elif self.path == "/scheduler":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    cur_time = mc.restart_time or ""
                    status_html = f"<div style='padding:12px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; color:#10b981; margin-bottom:20px;'>✅ Auto-restart scheduled daily at <b>{cur_time}</b></div>" if cur_time else "<div style='padding:12px; background:rgba(100,116,139,0.1); border:1px solid rgba(100,116,139,0.3); border-radius:8px; color:#64748b; margin-bottom:20px;'>⏸️ Auto-restart is currently disabled.</div>"
                    self.wfile.write(f"""<html><head><title>Auto-Restart Scheduler</title><meta charset="UTF-8"><style>{css}</style></head><body class="{body_class}">
                        <div class="glass topbar"><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>
                        <div class="glass sidebar"><a href="/">📊 Dashboard</a><a href="/map">🗺️ Map</a><a href="/chat">💬 Chat</a><a href="/inventory">🎒 Inventories</a><a href="/backups">💾 Backups</a><a href="/server_props">⚙️ Server Props</a><a href="/gamerules">🎮 Game Rules</a><a href="/stats">📊 Stats</a><a href="/mods">🔧 Mods</a><a href="/logs">📜 Logs</a><a href="/scheduler" class="active">⏰ Scheduler</a><a href="/settings">🛡️ Settings</a></div>
                        <div class="main"><div class="glass card" style="grid-column:1/-1; max-width:600px;">
                            <h3>⏰ Auto-Restart Scheduler</h3>
                            {status_html}
                            <form method="POST" action="/scheduler">
                                <label style="color:#94a3b8; font-size:14px; font-weight:600;">Daily Restart Time (24h format):</label><br><br>
                                <div style="display:flex; gap:10px; align-items:center;">
                                    <input type="time" name="restart_time" value="{cur_time}" class="cmd-input" style="width:180px; border-radius:8px;">
                                    <button class="cmd-btn" style="border-radius:8px; width:auto; padding:14px 20px;">Set</button>
                                    <button class="cmd-btn" style="border-radius:8px; width:auto; padding:14px 20px; background:#ef4444;" name="restart_time" value="">Disable</button>
                                </div>
                            </form>
                            <p style="color:#64748b; font-size:13px; margin-top:20px;">When triggered, the server will warn players 30 seconds before restarting and automatically come back online.</p>
                        </div></div>
                    </body></html>""".encode())

                # 404 Fallback
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        f"<html><head><title>404</title><style>{css}</style></head><body class="{body_class}">"
                        f"<div class='glass topbar'><h2>🪐 Antigravity Panel</h2>{theme_dropdown}</div>"
                        f"<div class='glass sidebar'>{NAV}</div>"
                        f"<div class='main'><div class='glass card' style='text-align:center; grid-column:1/-1;'>"
                        f"<h1 style='font-size:80px; margin:0;'>404</h1>"
                        f"<p style='color:#94a3b8;'>Page not found.</p>"
                        f"<a href='/' style='color:#818cf8; text-decoration:none; font-weight:600;'>← Back to Dashboard</a>"
                        f"</div></div></body></html>".encode()
                    )

            def log_message(self, format, *args):
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("", self.port), DashboardHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
