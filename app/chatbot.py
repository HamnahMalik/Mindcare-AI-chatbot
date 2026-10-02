import re
from datetime import datetime

from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Literal

from appointments import (
    get_sheet,
    save_appointment,
    find_appointments,
    cancel_appointment_row,
    update_appointment_row,
)

from sessions import (
    get_session,
    save_session,
    delete_session,
)

from rag import ask_mindcare

client = OpenAI()


# --------------------------------------------------
# Intent model
# --------------------------------------------------

class MindCareIntent(BaseModel):
    intent: Literal[
        "clinic_question",
        "book_appointment",
        "confirm_appointment",
        "cancel_appointment",
        "reschedule_appointment",
        "greeting",
        "other",
    ]

    name: Optional[str] = None
    service: Optional[str] = None
    clinician: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    time_preference: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# --------------------------------------------------
# General helpers
# --------------------------------------------------

TIME_SLOTS = {
    "morning": [
        "9:00 AM",
        "10:00 AM",
        "11:00 AM",
    ],
    "afternoon": [
        "1:00 PM",
        "2:00 PM",
        "3:00 PM",
        "4:00 PM",
    ],
    "evening": [
        "5:00 PM",
        "6:00 PM",
    ],
}


def normalize_reply(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def is_yes(text):
    value = normalize_reply(text)

    return value in {
        "yes",
        "y",
        "yeah",
        "yep",
        "confirm",
        "confirmed",
        "yes confirm",
        "yes confirm it",
        "go ahead",
        "ok",
        "okay",
    }


def is_no(text):
    value = normalize_reply(text)

    return value in {
        "no",
        "n",
        "nope",
        "cancel",
        "stop",
        "dont",
        "do not",
    }


def normalize_service(service):
    if not service:
        return None

    value = service.lower().strip()

    aliases = {
        "psychologist": "Psychologist",
        "psychology": "Psychologist",
        "therapy": "Psychologist",
        "therapist": "Psychologist",

        "psychiatrist": "Psychiatrist",
        "psychiatry": "Psychiatrist",

        "counselor": "Counselor",
        "counsellor": "Counselor",
        "counseling": "Counselor",
        "counselling": "Counselor",
    }

    return aliases.get(value, service.title())


def normalize_booking_date(date_text):
    today = datetime.now().strftime("%Y-%m-%d")

    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
Today is {today}.

Convert the appointment date below into YYYY-MM-DD.

Date:
{date_text}

Return only the date.
"""
    )

    return response.output_text.strip()


# --------------------------------------------------
# Intent understanding
# --------------------------------------------------

def understand_message(message, session=None):
    context = ""

    if session:
        context = f"""
Current appointment session:
{session}
"""

    response = client.responses.parse(
        model="gpt-5-mini",

        input=[
            {
                "role": "system",
                "content": """
You are the intent parser for MindCare clinic.

MindCare only handles:
- clinic information
- appointment booking
- appointment cancellation
- appointment rescheduling

Extract information explicitly provided by the user.

Valid services include:
- Psychologist
- Psychiatrist
- Counselor

Do not provide medical diagnosis, treatment, or medication advice.
"""
            },

            {
                "role": "user",
                "content": f"""
{context}

User message:
{message}
"""
            }
        ],

        text_format=MindCareIntent
    )

    result = response.output_parsed

    if result.service:
        result.service = normalize_service(result.service)

    return result


# --------------------------------------------------
# Availability
# --------------------------------------------------

def get_available_slots(service, date, preference):
    preference = str(preference).lower().strip()

    candidate_slots = TIME_SLOTS.get(preference, [])

    if not candidate_slots:
        return []

    sheet = get_sheet()
    rows = sheet.get_all_records()

    booked_times = set()

    for row in rows:
        row_status = str(row.get("Status", "")).strip().lower()

        if row_status != "confirmed":
            continue

        row_service = normalize_service(
            str(row.get("Service", ""))
        )

        row_date = str(row.get("Date", "")).strip()
        row_time = str(row.get("Time", "")).strip()

        if row_service == service and row_date == date:
            booked_times.add(row_time)

    return [
        slot
        for slot in candidate_slots
        if slot not in booked_times
    ]


# --------------------------------------------------
# Booking
# --------------------------------------------------

def booking_missing_fields(session):
    missing = []

    if not session.get("name"):
        missing.append("name")

    if not session.get("service"):
        missing.append("service")

    if not session.get("date"):
        missing.append("date")

    if not session.get("time") and not session.get("time_preference"):
        missing.append("time")

    if not session.get("email") and not session.get("phone"):
        missing.append("contact")

    return missing


def ask_booking_field(field):
    questions = {
        "name":
            "What name should I use for the appointment?",

        "service":
            "Which service would you like: Psychologist, Psychiatrist, or Counselor?",

        "date":
            "What date would you prefer for the appointment?",

        "time":
            "What time would you prefer? You can also say morning, afternoon, or evening.",

        "contact":
            "Please provide your phone number or email address.",
    }

    return questions[field]


def handle_booking(user_id, message, understanding=None):

    session = get_session(user_id, "booking") or {}

    # Confirmation stage
    if session.get("awaiting_confirmation"):

        if is_yes(message):

            save_appointment(
                name=session["name"],
                service=session["service"],
                date=session["date"],
                time=session["time"],
                email=session.get("email"),
                phone=session.get("phone"),
            )

            delete_session(user_id, "booking")

            return (
                "Your MindCare appointment has been confirmed.\n\n"
                f"Service: {session['service']}\n"
                f"Date: {session['date']}\n"
                f"Time: {session['time']}"
            )

        if is_no(message):

            delete_session(user_id, "booking")

            return "Your appointment request has been cancelled."

        return "Please reply Yes to confirm the appointment or No to cancel."

    if understanding is None:
        understanding = understand_message(
            message,
            session=session
        )

    # Update collected fields
    fields = [
        "name",
        "service",
        "clinician",
        "date",
        "time",
        "time_preference",
        "email",
        "phone",
    ]

    for field in fields:

        value = getattr(
            understanding,
            field,
            None
        )

        if value:
            session[field] = value

    if session.get("service"):
        session["service"] = normalize_service(
            session["service"]
        )

    # Normalize date
    if session.get("date"):

        date_value = session["date"]

        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            str(date_value)
        ):
            session["date"] = normalize_booking_date(
                date_value
            )

    # User supplied preference instead of exact time
    if (
        session.get("date")
        and session.get("service")
        and session.get("time_preference")
        and not session.get("time")
    ):

        slots = get_available_slots(
            session["service"],
            session["date"],
            session["time_preference"]
        )

        save_session(
            user_id,
            "booking",
            session
        )

        if not slots:
            return (
                "There are no available slots for that "
                "time preference. Please choose another "
                "time or time of day."
            )

        return (
            f"Available {session['time_preference']} slots "
            f"for {session['date']}:\n\n"
            + "\n".join(slots)
            + "\n\nPlease choose one."
        )

    missing = booking_missing_fields(session)

    if missing:

        save_session(
            user_id,
            "booking",
            session
        )

        return ask_booking_field(
            missing[0]
        )

    # All fields collected
    session["awaiting_confirmation"] = True

    save_session(
        user_id,
        "booking",
        session
    )

    contact = (
        session.get("phone")
        or session.get("email")
    )

    return (
        "Please confirm your appointment:\n\n"
        f"Name: {session['name']}\n"
        f"Service: {session['service']}\n"
        f"Date: {session['date']}\n"
        f"Time: {session['time']}\n"
        f"Contact: {contact}\n\n"
        "Reply Yes to confirm or No to cancel."
    )


# --------------------------------------------------
# Cancellation
# --------------------------------------------------

def handle_cancellation(user_id, message):

    session = get_session(
        user_id,
        "cancellation"
    ) or {
        "stage": "waiting_for_contact"
    }

    stage = session["stage"]

    if stage == "waiting_for_contact":

        matches = find_appointments(message)

        if not matches:

            return (
                "I couldn't find a confirmed appointment "
                "using that phone number or email. "
                "Please check it and try again."
            )

        session["matches"] = matches

        if len(matches) == 1:

            session["selected"] = matches[0]
            session["stage"] = "waiting_for_confirmation"

            save_session(
                user_id,
                "cancellation",
                session
            )

            appointment = matches[0]

            return (
                "I found this appointment:\n\n"
                f"{appointment['service']} — "
                f"{appointment['date']} at "
                f"{appointment['time']}\n\n"
                "Would you like to cancel it?"
            )

        session["stage"] = "multiple_appointments"

        save_session(
            user_id,
            "cancellation",
            session
        )

        lines = []

        for index, appointment in enumerate(
            matches,
            start=1
        ):
            lines.append(
                f"{index}. "
                f"{appointment['service']} — "
                f"{appointment['date']} at "
                f"{appointment['time']}"
            )

        return (
            "I found multiple appointments:\n\n"
            + "\n".join(lines)
            + "\n\nReply with the appointment number."
        )

    if stage == "multiple_appointments":

        try:
            selection = int(message.strip()) - 1

            appointment = session["matches"][selection]

        except (ValueError, IndexError):
            return "Please reply with a valid appointment number."

        session["selected"] = appointment
        session["stage"] = "waiting_for_confirmation"

        save_session(
            user_id,
            "cancellation",
            session
        )

        return (
            f"Cancel {appointment['service']} on "
            f"{appointment['date']} at "
            f"{appointment['time']}?\n\n"
            "Reply Yes or No."
        )

    if stage == "waiting_for_confirmation":

        if is_yes(message):

            appointment = session["selected"]

            cancel_appointment_row(
                appointment["row_number"]
            )

            delete_session(
                user_id,
                "cancellation"
            )

            return "Your appointment has been cancelled."

        if is_no(message):

            delete_session(
                user_id,
                "cancellation"
            )

            return "Cancellation stopped. Your appointment remains confirmed."

        return "Please reply Yes or No."

    return "Please provide the phone number or email used for your appointment."


# --------------------------------------------------
# Rescheduling
# --------------------------------------------------

def handle_reschedule(user_id, message):

    session = get_session(
        user_id,
        "reschedule"
    ) or {
        "stage": "waiting_for_contact"
    }

    stage = session["stage"]

    if stage == "waiting_for_contact":

        matches = find_appointments(message)

        if not matches:

            return (
                "I couldn't find a confirmed appointment "
                "using that phone number or email."
            )

        session["matches"] = matches

        if len(matches) == 1:

            session["selected"] = matches[0]
            session["stage"] = "waiting_for_new_date"

            save_session(
                user_id,
                "reschedule",
                session
            )

            appointment = matches[0]

            return (
                f"I found your {appointment['service']} "
                f"appointment on {appointment['date']} at "
                f"{appointment['time']}.\n\n"
                "What new date would you like?"
            )

        session["stage"] = "multiple_appointments"

        save_session(
            user_id,
            "reschedule",
            session
        )

        lines = []

        for index, appointment in enumerate(
            matches,
            start=1
        ):
            lines.append(
                f"{index}. "
                f"{appointment['service']} — "
                f"{appointment['date']} at "
                f"{appointment['time']}"
            )

        return (
            "I found multiple appointments:\n\n"
            + "\n".join(lines)
            + "\n\nReply with the appointment number."
        )

    if stage == "multiple_appointments":

        try:
            selection = int(message.strip()) - 1
            appointment = session["matches"][selection]

        except (ValueError, IndexError):
            return "Please reply with a valid appointment number."

        session["selected"] = appointment
        session["stage"] = "waiting_for_new_date"

        save_session(
            user_id,
            "reschedule",
            session
        )

        return "What new date would you like?"

    if stage == "waiting_for_new_date":

        new_date = normalize_booking_date(
            message
        )

        session["new_date"] = new_date
        session["stage"] = "waiting_for_new_time"

        save_session(
            user_id,
            "reschedule",
            session
        )

        return (
            f"New date: {new_date}\n\n"
            "What time would you prefer? "
            "You can say morning, afternoon, evening, "
            "or provide an exact time."
        )

    if stage == "waiting_for_new_time":

        normalized = normalize_reply(message)

        if normalized in TIME_SLOTS:

            appointment = session["selected"]

            slots = get_available_slots(
                appointment["service"],
                session["new_date"],
                normalized
            )

            if not slots:
                return (
                    "There are no available slots for that "
                    "time period. Please choose another."
                )

            return (
                "Available slots:\n\n"
                + "\n".join(slots)
                + "\n\nPlease choose one."
            )

        session["new_time"] = message.strip()
        session["stage"] = "waiting_for_confirmation"

        save_session(
            user_id,
            "reschedule",
            session
        )

        appointment = session["selected"]

        return (
            "Please confirm the reschedule:\n\n"
            f"Current: {appointment['date']} at "
            f"{appointment['time']}\n"
            f"New: {session['new_date']} at "
            f"{session['new_time']}\n\n"
            "Reply Yes to confirm or No to cancel."
        )

    if stage == "waiting_for_confirmation":

        if is_yes(message):

            appointment = session["selected"]

            update_appointment_row(
                appointment["row_number"],
                session["new_date"],
                session["new_time"],
            )

            delete_session(
                user_id,
                "reschedule"
            )

            return (
                "Your appointment has been rescheduled.\n\n"
                f"Date: {session['new_date']}\n"
                f"Time: {session['new_time']}"
            )

        if is_no(message):

            delete_session(
                user_id,
                "reschedule"
            )

            return (
                "Rescheduling cancelled. "
                "Your original appointment remains unchanged."
            )

        return "Please reply Yes or No."

    return "I couldn't continue the rescheduling request."


# --------------------------------------------------
# Main chatbot router
# --------------------------------------------------

def mindcare_chat(user_id, message):

    # Continue active workflows first
    if get_session(user_id, "reschedule"):
        return handle_reschedule(
            user_id,
            message
        )

    if get_session(user_id, "cancellation"):
        return handle_cancellation(
            user_id,
            message
        )

    booking_session = get_session(
        user_id,
        "booking"
    )

    if booking_session is not None:

        understanding = understand_message(
            message,
            session=booking_session
        )

        return handle_booking(
            user_id,
            message,
            understanding
        )

    # No active workflow
    understanding = understand_message(
        message
    )

    if understanding.intent == "greeting":

        return (
            "Hello! I’m the MindCare assistant. "
            "I can help with clinic information, "
            "booking, cancellation, or rescheduling."
        )

    if understanding.intent == "book_appointment":

        save_session(
            user_id,
            "booking",
            {}
        )

        return handle_booking(
            user_id,
            message,
            understanding
        )

    if understanding.intent == "cancel_appointment":

        save_session(
            user_id,
            "cancellation",
            {
                "stage": "waiting_for_contact"
            }
        )

        return (
            "Please provide the phone number or email "
            "used for your appointment."
        )

    if understanding.intent == "reschedule_appointment":

        save_session(
            user_id,
            "reschedule",
            {
                "stage": "waiting_for_contact"
            }
        )

        return (
            "Please provide the phone number or email "
            "used for your appointment."
        )

    if understanding.intent == "clinic_question":
    	return ask_mindcare(message)

    return (
        "I can help with MindCare clinic information "
        "or appointment booking, cancellation, and rescheduling."
    )

