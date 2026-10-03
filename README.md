# MindCare AI Chatbot

MindCare is an AI-powered clinic assistant prototype designed to help users with clinic information, appointment booking, cancellation, and rescheduling.

It combines Retrieval-Augmented Generation (RAG), persistent conversation sessions, Google Sheets integration, workflow automation, and cloud deployment to demonstrate how an AI chatbot can support clinic operations.

> **Demo Prototype — For testing purposes only**
>
> MindCare is not a medical diagnosis or treatment system. It is designed for clinic information and appointment-support workflows only.

---

## Features

- AI-powered conversational interface
- Clinic FAQ answering using RAG
- Appointment booking
- Appointment cancellation
- Appointment rescheduling
- Available time-slot suggestions
- Persistent conversation sessions
- Google Sheets appointment storage
- WhatsApp appointment-confirmation automation
- Browser-based chat interface
- Dockerized deployment
- HTTPS deployment through Caddy
- n8n workflow automation
- OpenAI-powered intent understanding
- ChromaDB vector search
- SQLite session persistence

---

## Architecture

```text
User
  |
  v
Browser Chat Interface
  |
  v
FastAPI
  |
  +------------------------------+
  |                              |
  v                              v
Intent Routing                  RAG
  |                              |
  |                           ChromaDB
  |                              |
  |                           OpenAI
  |
  +--> Booking
  +--> Cancellation
  +--> Rescheduling
  |
  v
Google Sheets
  |
  v
n8n
  |
  v
WhatsApp Business Cloud
```

---

## Tech Stack

### AI & Backend
- Python
- FastAPI
- OpenAI API
- GPT models
- LangChain
- ChromaDB
- OpenAI Embeddings

### Data & Persistence
- SQLite
- Google Sheets

### Automation
- n8n
- WhatsApp Business Cloud API

### Deployment
- Docker
- Docker Compose
- Hostinger VPS
- Caddy
- HTTPS / SSL

### Frontend
- HTML
- CSS
- JavaScript

---

## Project Structure

```text
mindcare/
├── app/
│   ├── main.py
│   ├── chatbot.py
│   ├── rag.py
│   ├── appointments.py
│   ├── sessions.py
│   ├── static/
│   │   └── index.html
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

Persistent and sensitive directories such as ChromaDB, SQLite data, n8n data, and service-account credentials are intentionally excluded from the repository.

---

## Core Workflows

### 1. Clinic Information

Users can ask questions such as:

```text
Are you open on Saturday?
```

MindCare retrieves relevant clinic information from the ChromaDB knowledge base and generates a grounded response using the retrieved context.

If the information is not available in the knowledge base, the assistant clearly indicates that the demo knowledge base does not currently contain that information.

### 2. Appointment Booking

MindCare collects:
- Name
- Service
- Preferred date
- Preferred time
- Email or phone number

The user reviews the appointment details before confirming.

```text
User
   ↓
Booking conversation
   ↓
Collect appointment details
   ↓
User confirmation
   ↓
Google Sheets
```

### 3. Appointment Cancellation

Users can identify an existing appointment using their email address or phone number.

MindCare:
1. Searches confirmed appointments
2. Displays matching appointments
3. Requests confirmation
4. Updates the appointment status to `Cancelled`

### 4. Appointment Rescheduling

MindCare allows users to:
1. Find an existing confirmed appointment
2. Select a new date
3. Choose a preferred time
4. View available slots
5. Confirm the new appointment

The existing Google Sheets appointment row is updated rather than creating a duplicate appointment.

---

## Persistent Sessions

MindCare uses SQLite to store conversation state.

Supported session types:

```text
booking
cancellation
reschedule
```

This allows active conversations to survive Docker, application, or VPS restarts.

---

## Google Sheets Integration

Appointments are stored in Google Sheets using fields such as:

```text
ID
Name
Service
Date
Time
Email
Phone
Status
WhatsApp_Status
```

Example appointment ID:

```text
2026-10-01|6:00 PM
```

The VPS uses a Google Cloud service account for Google Sheets access.

---

## WhatsApp Automation

n8n monitors confirmed appointments and sends appointment confirmations through WhatsApp Business Cloud.

```text
Google Sheets Trigger
        ↓
Check Status = Confirmed
        ↓
Format appointment data
        ↓
WhatsApp Business Cloud
        ↓
Send confirmation template
        ↓
Update WhatsApp_Status = Sent
```

Example confirmation template:

```text
Hello {{1}},

Your MindCare appointment has been confirmed.

Service: {{2}}
Date: {{3}}
Time: {{4}}

Thank you,
MindCare
```

---

## RAG Knowledge Base

MindCare uses ChromaDB as a vector database.

The knowledge base can contain:

```text
clinic_hours
services
pricing
appointment_policy
therapists
faq
```

Embeddings are generated with:

```text
text-embedding-3-small
```

Retrieval flow:

```text
User Question
      ↓
Similarity Search
      ↓
Relevant ChromaDB Chunks
      ↓
OpenAI Model
      ↓
Grounded Response
```

---

## Intent Handling

Supported intents include:

```text
clinic_question
book_appointment
confirm_appointment
cancel_appointment
reschedule_appointment
greeting
other
```

---

## Deployment Architecture

```text
Hostinger VPS
│
├── mindcare-api
│   ├── FastAPI
│   ├── OpenAI
│   ├── RAG
│   ├── SQLite
│   └── Google Sheets
│
├── n8n
│   └── WhatsApp automation
│
└── Caddy
    ├── HTTPS
    └── Reverse proxy
```

Caddy provides HTTPS and routes traffic to the appropriate Docker container.

---

## Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Never commit the real `.env` file to GitHub.

---

## Google Service Account

Place the Google service-account JSON file at:

```text
secrets/google-service-account.json
```

The service account must have access to the Google Sheet used by the application.

This file must never be committed to GitHub.

---

## Running the Project

### 1. Clone the repository

```bash
git clone https://github.com/HamnahMalik/Mindcare-AI-chatbot.git
cd Mindcare-AI-chatbot
```

### 2. Create the environment file

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Add Google credentials

Create `secrets/` and place the service-account file at:

```text
secrets/google-service-account.json
```

### 4. Add ChromaDB data

Place your vector database inside:

```text
chromadb/
```

### 5. Start the containers

```bash
docker compose up -d --build
```

### 6. Check running containers

```bash
docker ps
```

Expected containers:

```text
mindcare-api
n8n
caddy
```

### 7. Check application health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy"
}
```

---

## Security

Sensitive and persistent files should not be committed:

```text
.env
secrets/
google-service-account.json
data/
chromadb/
n8n_data/
caddy_data/
caddy_config/
```

API keys, OAuth credentials, service-account files, and production databases should remain outside version control.

---

## Demo Scope

This project is an MVP/prototype intended to demonstrate:

- conversational appointment automation
- RAG-based clinic information retrieval
- workflow orchestration
- persistent sessions
- Google Sheets integration
- cloud deployment
- third-party integrations
- WhatsApp automation

The clinic information used in this project is demo data, and the project is not connected to a real medical clinic.

---

## Safety Disclaimer

MindCare is designed only for:

- clinic information
- appointment booking
- appointment cancellation
- appointment rescheduling
- general scheduling support

MindCare does **not** provide:

- medical diagnosis
- prescriptions
- treatment recommendations
- medical decision-making
- emergency medical assistance

A real healthcare deployment would require additional privacy, security, compliance, clinical governance, and regulatory review.

---

## Future Improvements

- Production WhatsApp Business integration
- Human-agent handoff
- Appointment reminders
- Admin dashboard
- Google Calendar integration
- Clinician-specific availability
- Authentication
- Rate limiting
- PostgreSQL migration
- Analytics dashboard
- Reusable website chat widget
- Multi-clinic support
- CRM integration
- Email notifications
- Improved appointment conflict detection
- Automated follow-up workflows

---

## Use Case

MindCare demonstrates how AI automation can support clinic operations by reducing repetitive administrative work.

Potential use cases include:

- private clinics
- counseling centers
- therapy practices
- diagnostic centers
- healthcare consultation services
- appointment-based service businesses

---

## Author

Developed as part of an AI automation portfolio project.

### AI Forge

AI automation, AI agents, workflow automation, and intelligent business systems.

---

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.
