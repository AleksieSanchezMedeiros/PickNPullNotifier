import requests
import json
import time
import os
import smtplib

from email.message import EmailMessage

# --------------------------
# CONFIG
# --------------------------

ZIP_CODE = "98011"
DISTANCE = 50

API_URL = (
    f"https://www.picknpull.com/api/vehicle/search"
    f"?makeId=67"
    f"&modelId=958"
    f"&distance={DISTANCE}"
    f"&zip={ZIP_CODE}"
    f"&language=english"
)

CHECK_INTERVAL = 24 * 60 * 60  # 1 hour

SEEN_FILE = "seen.txt"

# Email settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

EMAIL_FROM = "cerezen0@gmail.com"
EMAIL_PASSWORD = "ulxo lcek jhsg ygzi"

EMAIL_TO = [
    "aleksiesanmed@gmail.com"
]

# --------------------------
# EMAIL
# --------------------------

def send_email(subject, body):
    msg = EmailMessage()

    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    msg.set_content(body)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --------------------------
# SEEN IDS
# --------------------------

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    with open(SEEN_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        for vehicle_id in seen:
            f.write(vehicle_id + "\n")

# --------------------------
# API
# --------------------------

def get_integras():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/148.0 Safari/537.36"
        )
    }

    response = requests.get(
        API_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()

# --------------------------
# PROCESS
# --------------------------

def check_inventory():

    print("Checking inventory...")

    seen = load_seen()

    try:
        data = get_integras()

    except Exception as e:
        print("API Error:", e)
        return

    new_found = 0

    for location in data:

        vehicles = location.get("vehicles", [])

        for car in vehicles:

            year = car.get("year", 0)

            # 3rd gen only
            if not (1994 <= year <= 2001):
                continue

            vehicle_id = str(car["id"])

            if vehicle_id in seen:
                continue

            message = f"""
NEW INTEGRA FOUND

Year: {car.get("year")}
Make: {car.get("make")}
Model: {car.get("model")}

Location: {car.get("locationName")}
City: {car.get("city")}, {car.get("state")}
Row: {car.get("row")}

Date Added: {car.get("dateAdded")}
VIN: {car.get("vin")}
Barcode: {car.get("barCodeNumber")}

Image:
{car.get("largeImage")}
"""

            print(message)

            try:
                send_email(
                    "🚗 New Acura Integra Found!",
                    message
                )

                print("Notification sent.")

            except Exception as e:
                print("Email failed:", e)

            seen.add(vehicle_id)
            new_found += 1

    save_seen(seen)

    print(f"Done. {new_found} new vehicle(s).")

    if new_found == 0:
        try:
            send_email(
                "Integra Daily Report",
                "No new 1994-2001 Acura Integras were added today.\n\nNotifier status: OK"
            )

            print("Daily report sent.")

        except Exception as e:
            print("Daily report email failed:", e)

# --------------------------
# MAIN LOOP
# --------------------------

def main():

    print("Pick-N-Pull Integra Notifier Started")

    # Initial run
    check_inventory()

    while True:

        print(
            f"Sleeping {CHECK_INTERVAL // 60} minutes..."
        )

        time.sleep(CHECK_INTERVAL)

        check_inventory()

if __name__ == "__main__":
    main()