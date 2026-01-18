import os
import sqlite3
import shutil
import requests
from collections import Counter
from urllib.parse import urlparse
from datetime import datetime, timezone

# Your webhook (the one for top sites)
WEBHOOK_URL = "YOUR DISCORD WEBHOOK HERE"

HISTORY_PATHS = [
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\History"),
    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History"),
]


def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else ""
    except:
        return ""


def read_recent_history(db_path):
    if not os.path.exists(db_path):
        return []

    temp_db = "temp_hist.db"
    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Chromium visit_time = microseconds since 1601-01-01 00:00:00 UTC
        now_webkit = int(datetime.now(timezone.utc).timestamp() * 1000000)
        # 30 days in microseconds
        THIRTY_DAYS_MICRO = 30 * 24 * 60 * 60 * 1000000
        threshold = now_webkit - THIRTY_DAYS_MICRO

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
            except:
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


def send_to_webhook():
    top5 = get_top_5_last_month()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not top5:
        message = f"**Top 5 Domains (Last 30 Days)**\n{now_str}\nNo recent history could be read"
    else:
        lines = [
            f"**Top 5 Most Visited Domains (Last 30 Days)**",
            f"{now_str}"
        ]
        for i, (domain, visits) in enumerate(top5, 1):
            lines.append(f"{i}. {domain}  —  ≈{visits:,} visits")
        message = "\n".join(lines)

    try:
        requests.post(
            WEBHOOK_URL,
            json={"content": message},
            timeout=7
        )
    except:
        pass


if __name__ == "__main__":
    send_to_webhook()
