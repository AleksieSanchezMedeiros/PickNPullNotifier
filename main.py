import requests
import json
import time
import os
import smtplib

from email.message import EmailMessage
from email.mime.image import MIMEImage

# --------------------------
# CONFIG
# --------------------------

ZIP_CODE = "98011"
DISTANCE = 50

SEARCHES = [
    {
        "name": "Acura Integra",
        "makeId": 67,
        "modelId": 958,
        "minYear": 1994,
        "maxYear": 2001,
    },
    {
        "name": "Honda Civic",
        "makeId": 145,
        "modelId": 2413,
        "minYear": 1992,
        "maxYear": 1995,
    },
    {
        "name": "Honda Civic Del Sol",
        "makeId": 145,
        "modelId": 2414,
        "minYear": 1992,
        "maxYear": 1998,
    },
    {
        "name": "Honda Del Sol",
        "makeId": 145,
        "modelId": 2445,
        "minYear": 1992,
        "maxYear": 1998,
    },
    {
        "name": "Honda CRX",
        "makeId": 145,
        "modelId": 5165,
        "minYear": 1983,
        "maxYear": 1998,
    },
    {
        "name": "Honda CR-V",
        "makeId": 145,
        "modelId": 2440,
        "minYear": 1997,
        "maxYear": 2006,
    },
    {
        "name": "Mazda Miata",
        "makeId": 180,
        "modelId": 3577,
        "minYear": 1990,
        "maxYear": 2005,
    },
    {
        "name": "Subaru Impreza WRX",
        "makeId": 226,
        "modelId": 4155,
        "minYear": 2000,
        "maxYear": 2007,
    },
]

def get_vehicles(make_id, model_id):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/148.0 Safari/537.36"
        )
    }

    url = (
        "https://www.picknpull.com/api/vehicle/search"
        f"?makeId={make_id}"
        f"&modelId={model_id}"
        f"&distance={DISTANCE}"
        f"&zip={ZIP_CODE}"
        "&language=english"
    )

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()

def decode_vin(vin):
    if not vin:
        return {}

    try:
        url = (
            f"https://vpic.nhtsa.dot.gov/api/vehicles/"
            f"DecodeVinValuesExtended/{vin}?format=json"
        )

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        results = response.json()["Results"][0]

        return {
            "trim": results.get("Trim"),
            "series": results.get("Series"),
            "engine": results.get("EngineModel"),
            "displacement": results.get("DisplacementL"),
            "cylinders": results.get("EngineCylinders"),
            "transmission": results.get("TransmissionStyle"),
            "drive": results.get("DriveType"),
            "body": results.get("BodyClass"),
        }

    except Exception as e:
        print(f"VIN decode failed for {vin}: {e}")
        return {}

CHECK_INTERVAL = 24 * 60 * 60  # 24 hour

SEEN_FILE = "seen.txt"

# Email settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

EMAIL_TO = [
    "aleksiesanmed@gmail.com",
    "ayadabozed7@gmail.com"
]

# --------------------------
# EMAIL
# --------------------------

def send_email(subject, body, image_url=None):
    msg = EmailMessage()

    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    msg.set_content(body)

    if image_url:
        try:
            img_data = requests.get(image_url, timeout=30).content

            msg.add_alternative(
                f"""
                <html>
                    <body>
                        <pre>{body}</pre>
                        <br>
                        <img src="cid:vehicle_image">
                    </body>
                </html>
                """,
                subtype="html"
            )

            msg.get_payload()[1].add_related(
                img_data,
                maintype="image",
                subtype="jpeg",
                cid="vehicle_image"
            )

        except Exception as e:
            print("Failed to attach image:", e)

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
# PROCESS
# --------------------------

def check_inventory():

    searched = "\n".join(
    f"• {s['name']} ({s['minYear']}-{s['maxYear']})"
    for s in SEARCHES
)

    seen = load_seen()
    new_found = 0

    for search in SEARCHES:

        print(f"Checking {search['name']}...")

        try:
            data = get_vehicles(
                search["makeId"],
                search["modelId"]
            )
        except Exception as e:
            print(e)
            continue

        for location in data:

            for car in location.get("vehicles", []):

                year = car.get("year", 0)

                if not (
                    search["minYear"]
                    <= year
                    <= search["maxYear"]
                ):
                    continue

                vehicle_key = (
                    f"{search['name']}:{car['id']}"
                )

                if vehicle_key in seen:
                    continue

                image_url = car.get("largeImage")
                
                vin = car.get("vin")
                vin_info = decode_vin(vin)

                message = f"""
    🚗 NEW {search['name'].upper()} FOUND

    Year: {car.get('year')}
    Make: {car.get('make')}
    Model: {car.get('model')}

    Trim: {vin_info.get('trim')}
    Series: {vin_info.get('series')}
    Engine: {vin_info.get('engine')}
    Displacement: {vin_info.get('displacement')} L
    Cylinders: {vin_info.get('cylinders')}
    Transmission: {vin_info.get('transmission')}
    Drive: {vin_info.get('drive')}
    Body: {vin_info.get('body')}

    Location: {car.get('locationName')}
    City: {car.get('city')}, {car.get('state')}
    Row: {car.get('row')}

    Date Added: {car.get('dateAdded')}
    VIN: {car.get('vin')}
    Barcode: {car.get('barCodeNumber')}

    Image attached below.
    """

                print(
    f"Found {car.get('year')} "
    f"{car.get('make')} {car.get('model')} "
    f"at {car.get('locationName')}"
)

                try:
                    send_email(
                        f"🚗 New {search['name']} Found - {car.get('city')}",
                        message,
                        image_url
                    )
                    print("Notification sent.")
                except Exception as e:
                    print("Email failed:", e)

                seen.add(vehicle_key)
                new_found += 1
    
    save_seen(seen)
    print(f"Done. {new_found} new vehicle(s).")
    
    if new_found == 0:
        send_email(
    "Daily Pick-N-Pull Report",
    f"""No new vehicles were added today.

Searched:
{searched}

Notifier Status: OK
"""
)

# --------------------------
# MAIN LOOP
# --------------------------

def main():

    print("Pick-N-Pull Vehicle Notifier Started")

    check_inventory()

if __name__ == "__main__":
    check_inventory()