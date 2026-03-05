import subprocess
import threading
import time
import re
import os
import shutil
import datetime


class MinecraftServer:
    def __init__(self, jar_name="server.jar"):
        self.jar_name = jar_name
        self.process = None
        self.is_running = False
        self._lock = threading.Lock()  # Protects shared state

        self.online_players = []
        self.player_health = {}
        self.player_inventory = {}
        self.console_logs = []
        self.chat_logs = []
        self.tps = 20.0
        self._last_overload = 0
        self.restart_time = None  # "HH:MM" e.g. "04:00"
        self._scheduler_thread = None

    # ─── Server Lifecycle ────────────────────────────────────────────────────

    def start_server(self):
        with self._lock:
            if self.is_running:
                return  # Prevent double-start

        with self._lock:
            self.online_players = []
            self.player_health = {}
            self.player_inventory = {}
            self.chat_logs = []
            self.console_logs = ["Starting Fabric server..."]
            self.tps = 20.0

        self.process = subprocess.Popen(
            ["java", "-Xmx2G", "-Xms2G", "-jar", self.jar_name, "nogui"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(self.jar_name)) or ".",
        )
        with self._lock:
            self.is_running = True

        threading.Thread(target=self._read_console, daemon=True).start()
        threading.Thread(target=self._status_poller, daemon=True).start()

        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            self._scheduler_thread = threading.Thread(
                target=self._auto_restart_scheduler, daemon=True
            )
            self._scheduler_thread.start()

    def stop_server(self):
        if not self.is_running or not self.process:
            return
        self.send_command("stop")
        # Wait up to 10 seconds for graceful shutdown
        for _ in range(20):
            time.sleep(0.5)
            if self.process.poll() is not None:
                break
        else:
            # Force kill if still alive
            try:
                self.process.kill()
            except Exception:
                pass
        with self._lock:
            self.is_running = False
            self.online_players = []

    def send_command(self, command):
        if self.is_running and self.process:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except OSError:
                pass

    # ─── Background Threads ──────────────────────────────────────────────────

    def _status_poller(self):
        """Polls player list, health and inventory every 5 seconds."""
        while self.is_running:
            time.sleep(5)
            if not self.is_running:
                break
            self.send_command("list")
            for p in list(self.online_players):
                self.send_command(f"data get entity {p} Health")
                self.send_command(f"data get entity {p} Inventory")

    def _read_console(self):
        """Reads server stdout line by line and dispatches events."""
        while self.is_running and self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:
                break

            clean = re.sub(r"§[0-9a-fk-or]", "", line.strip())

            with self._lock:
                self.console_logs.append(clean)
                if len(self.console_logs) > 100:
                    self.console_logs.pop(0)

            if "]: " not in clean:
                continue

            # TPS detection via overload warnings
            if "Can't keep up! Is the server overloaded?" in clean:
                try:
                    ms = int(re.search(r"Running (\d+)ms or", clean).group(1))
                    ticks = int(re.search(r"or (\d+) ticks behind", clean).group(1))
                    self.tps = max(0.0, round(20.0 - ticks / max(ms / 50.0, 1), 1))
                    self._last_overload = time.time()
                except (AttributeError, ValueError):
                    self.tps = 15.0
            elif time.time() - self._last_overload > 15:
                self.tps = 20.0

            msg = clean.split("]: ", 1)[1]

            # Player join / leave
            if " joined the game" in msg:
                name = msg.split(" joined the game")[0].split()[-1]
                with self._lock:
                    if name not in self.online_players:
                        self.online_players.append(name)

            elif " left the game" in msg:
                name = msg.split(" left the game")[0].split()[-1]
                with self._lock:
                    if name in self.online_players:
                        self.online_players.remove(name)

            # Active player list response
            elif " players online:" in msg:
                after = msg.split(" players online:", 1)[1].strip()
                with self._lock:
                    self.online_players = [
                        p.strip() for p in after.split(",") if p.strip()
                    ] if after else []

            # Chat message: <PlayerName> text
            elif re.match(r"^<\w+> .+", msg):
                entry = {
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "raw": msg,
                }
                with self._lock:
                    self.chat_logs.append(entry)
                    if len(self.chat_logs) > 100:
                        self.chat_logs.pop(0)

            # NBT entity data (health / inventory)
            elif "has the following entity data: " in msg:
                parts = msg.split(" has the following entity data: ", 1)
                if len(parts) < 2:
                    continue
                player_name = parts[0].split()[-1]
                data = parts[1]

                if "Health" in msg:
                    try:
                        self.player_health[player_name] = float(
                            re.sub(r"[fd]", "", data.strip())
                        )
                    except ValueError:
                        pass

                elif "Inventory" in msg or data.strip().startswith("["):
                    self._parse_inventory(player_name, data)

        with self._lock:
            self.is_running = False

    def _parse_inventory(self, player_name, data):
        """Parse NBT inventory data into slot-aware item dicts."""
        found = []
        for match in re.finditer(
            r'id:\s*["\']?(?:minecraft:)?([a-z0-9_]+)["\']?', data
        ):
            item_id = match.group(1)
            start = data.rfind("{", 0, match.start())
            if start == -1:
                continue
            chunk = data[start: min(len(data), match.end() + 120)]
            slot_m = re.search(r"Slot:\s*(-?\d+)b?", chunk)
            if not slot_m:
                continue
            count_m = re.search(r"Count:\s*(\d+)b?", chunk)
            found.append({
                "slot": int(slot_m.group(1)),
                "id": item_id,
                "count": int(count_m.group(1)) if count_m else 1,
            })

        unique = {}
        for item in found:
            if item["slot"] not in unique:
                unique[item["slot"]] = item

        if unique or data.strip() == "[]":
            with self._lock:
                self.player_inventory[player_name] = list(unique.values())

    # ─── Auto-Restart Scheduler ──────────────────────────────────────────────

    def _auto_restart_scheduler(self):
        """Restarts server daily at self.restart_time (HH:MM)."""
        while True:
            time.sleep(20)
            if not (self.restart_time and self.is_running):
                continue
            now = datetime.datetime.now().strftime("%H:%M")
            if now == self.restart_time:
                self.send_command("say [Auto-Restart] Server restarting in 30 seconds!")
                time.sleep(30)
                self.stop_server()
                time.sleep(5)
                self.start_server()
                time.sleep(65)  # Skip at least 1 full minute before checking again

    # ─── World Backup ────────────────────────────────────────────────────────

    def backup_world(self):
        """Create a timestamped zip backup of the world folder. Returns (path, error)."""
        if not os.path.isdir("world"):
            return None, "World folder not found."
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs("backups", exist_ok=True)
        backup_path = os.path.join("backups", f"world_backup_{ts}")
        try:
            if self.is_running:
                self.send_command("save-off")
                self.send_command("save-all")
                time.sleep(3)
            shutil.make_archive(backup_path, "zip", ".", "world")
        except Exception as e:
            return None, str(e)
        finally:
            if self.is_running:
                self.send_command("save-on")
        return f"{backup_path}.zip", None

    # ─── Server Properties ───────────────────────────────────────────────────

    def set_server_property(self, key, value):
        """Update a key=value line in server.properties."""
        props_file = "server.properties"
        try:
            with open(props_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines, found = [], False
            for line in lines:
                if line.startswith(key + "="):
                    new_lines.append(f"{key}={value}\n")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"{key}={value}\n")
            with open(props_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except OSError:
            pass

    def get_server_properties(self):
        """Return a dict of all key-value pairs from server.properties."""
        result = {}
        try:
            with open("server.properties", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        result[k.strip()] = v.strip()
        except OSError:
            pass
        return result
