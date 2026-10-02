# MindCare AI Chatbot

MindCare is an AI-powered clinic assistant prototype designed to help users with clinic information, appointment booking, cancellation, and rescheduling.

The project combines Retrieval-Augmented Generation (RAG), workflow automation, persistent session management, and external integrations to demonstrate how an AI chatbot can be deployed as a practical healthcare-support application.

> **Demo Prototype — For testing purposes only**  
> MindCare is not a medical diagnosis or treatment system. It is designed for clinic information and appointment-support workflows.

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
  +---------------------------+
  |                           |
  v                           v
Intent Routing             RAG
  |                           |
  |                      ChromaDB
  |                           |
  |                        OpenAI
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
