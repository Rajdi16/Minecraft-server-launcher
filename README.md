# 🟢 Minecraft Fabric Server — Python Admin Dashboard

A Python-powered management system for a **Fabric Minecraft server**, featuring a browser-based admin dashboard for real-time monitoring and control.

---

## 📋 Requirements

- **Python 3.8+**
- **Java** (JDK 17+ recommended for modern Minecraft versions)
- A valid **Fabric `server.jar`** in the project root

---

## 🚀 Getting Started

1. **Accept the EULA** — Edit `eula.txt` and set `eula=true`.

2. **Run the server:**
   ```bash
   python app.py
   ```

3. **Open the dashboard** in your browser:
   ```
   http://localhost:8080
   ```

---

## 📁 Project Structure

```
minecraft server fabric/
├── app.py               # Entry point — starts server + dashboard
├── server_engine.py     # Minecraft server process manager
├── web_dashboard.py     # HTTP web dashboard server
├── server.jar           # Fabric server JAR
├── server.properties    # Minecraft server configuration
├── mods/                # Fabric mods folder
├── world/               # World save data
├── backups/             # Timestamped world backups
├── logs/                # Server logs
└── eula.txt             # Minecraft EULA acceptance
```

---

## 🖥️ Dashboard Features

| Feature | Description |
|---|---|
| **Live Console** | View and send server commands in real time |
| **Player Monitor** | See online players, health, and inventory |
| **TPS Tracking** | Monitors server performance (ticks per second) |
| **Chat Log** | View in-game chat history |
| **World Backup** | One-click timestamped `.zip` backups of the world |
| **Server Properties** | Edit `server.properties` from the browser |
| **Auto-Restart** | Schedule daily automatic restarts at a set time |

---

## ⚙️ Configuration

### Server Memory
The server launches with **2GB RAM** by default. To change this, edit the Java flags in `server_engine.py`:
```python
["java", "-Xmx2G", "-Xms2G", "-jar", self.jar_name, "nogui"]
```

### Auto-Restart
Set a daily restart time (24h format) from the dashboard, or programmatically:
```python
mc_server.restart_time = "04:00"  # Restarts every day at 4:00 AM
```

### Dashboard Port
Change the port in `app.py`:
```python
dashboard = DashboardServer(mc_server, port=8080)
```

---

## 🗺️ Mods Included

- **[Squaremap](https://modrinth.com/plugin/squaremap)** — Live web map of your world

---

## 🛑 Stopping the Server

Press `Ctrl+C` in the terminal. The server will shut down gracefully before exiting.

---

## 💾 Backups

World backups are stored in the `backups/` folder as `.zip` files named:
```
world_backup_YYYY-MM-DD_HH-MM-SS.zip
```
Backups pause saving (`save-off`) before archiving and resume it (`save-on`) after, ensuring data integrity.
