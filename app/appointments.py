import gspread
from google.oauth2.service_account import Credentials


SERVICE_ACCOUNT_FILE = "/app/secrets/google-service-account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open("MindCare_Appointments")

    return spreadsheet.sheet1


def normalize_phone(phone):
    if phone is None:
        return ""

    phone = str(phone).strip()
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("+92", "0")

    if len(phone) == 10 and phone.startswith("3"):
        phone = "0" + phone

    return phone


def make_appointment_id(date, time):
    return f"{date}|{time}"


def save_appointment(
    name,
    service,
    date,
    time,
    email=None,
    phone=None,
    status="Confirmed"
):
    sheet = get_sheet()

    appointment_id = make_appointment_id(
        date,
        time
    )

    appointment = [
        appointment_id,          # A - ID
        name or "",              # B - Name
        service or "",           # C - Service
        date or "",              # D - Date
        time or "",              # E - Time
        email or "",             # F - Email
        normalize_phone(phone),  # G - Phone
        status,                  # H - Status
        ""                       # I - WhatsApp_Status
    ]

    sheet.append_row(
        appointment,
        value_input_option="USER_ENTERED"
    )

    return True


def find_appointments(contact):
    sheet = get_sheet()
    rows = sheet.get_all_records()

    contact = str(contact).strip()
    contact_phone = normalize_phone(contact)
    contact_email = contact.lower()

    matches = []

    for index, row in enumerate(rows, start=2):

        row_phone = normalize_phone(
            row.get("Phone", "")
        )

        row_email = str(
            row.get("Email", "")
        ).strip().lower()

        row_status = str(
            row.get("Status", "")
        ).strip().lower()

        if row_status != "confirmed":
            continue

        phone_match = (
            contact_phone
            and row_phone == contact_phone
        )

        email_match = (
            contact_email
            and row_email == contact_email
        )

        if phone_match or email_match:
            matches.append({
                "row_number": index,
                "id": row.get("ID", ""),
                "name": row.get("Name", ""),
                "service": row.get("Service", ""),
                "date": row.get("Date", ""),
                "time": row.get("Time", ""),
                "email": row.get("Email", ""),
                "phone": row.get("Phone", ""),
                "status": row.get("Status", "")
            })

    return matches


def cancel_appointment_row(row_number):
    sheet = get_sheet()

    # H = Status
    sheet.update_cell(
        row_number,
        8,
        "Cancelled"
    )

    return True


def update_appointment_row(
    row_number,
    new_date,
    new_time
):
    sheet = get_sheet()

    new_id = make_appointment_id(
        new_date,
        new_time
    )

    # A = ID
    sheet.update_cell(
        row_number,
        1,
        new_id
    )

    # D = Date
    sheet.update_cell(
        row_number,
        4,
        new_date
    )

    # E = Time
    sheet.update_cell(
        row_number,
        5,
        new_time
    )

    # H = Status
    sheet.update_cell(
        row_number,
        8,
        "Confirmed"
    )

    # Reset WhatsApp_Status so n8n can send
    # another confirmation after rescheduling.
    sheet.update_cell(
        row_number,
        9,
        ""
    )

    return True
