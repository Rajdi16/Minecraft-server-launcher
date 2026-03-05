import time
from server_engine import MinecraftServer
from web_dashboard import DashboardServer

print("🚀 Launching Hidden Admin Panel...")
mc_server = MinecraftServer("server.jar")

dashboard = DashboardServer(mc_server, port=8080)
dashboard.start()

print("✅ Dashboard Ready: http://localhost:8080")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    mc_server.stop_server()
