# Pro1020-ALAN
AI that Listens, Answers, and Narrates

ALAN is an intelligent email-based AI assistant that reads your emails, understands your requests, and replies with personalized, RAG-powered summaries or narrated insights — all through a simple Gmail inbox.

Alan doesn’t need a website, app, or database.
He just listens, thinks, and replies — directly over email.


✨ What Alan Does

📥 Listens to incoming emails — reads messages from your Gmail inbox via IMAP

💬 Understands requests — parses the subject and body

🧠 Finds relevant information — uses a Retrieval-Augmented Generation (RAG) pipeline to retrieve context from stored documents or recent blogs

🎙️ Generates responses — summarises or explains with an LLM

📤 Replies automatically — sends the result back via Gmail SMTP

Alan can:

Summarize the latest AI, tech, or data news

Answer questions about uploaded documents or articles

Create daily podcast scripts or briefings from your RAG index


🏗️ Architecture Overview
User email → alan@gmail.com
         ↓
 [IMAP Poller: FastAPI Background Task]
         ↓
 [RAG Engine: Retrieve + Generate Answer]
         ↓
 [SMTP: Send Alan’s Reply]

Tech Stack
Component	Tool
API / Scheduler	FastAPI
Email Receive	IMAP (Gmail)
Email Send	SMTP (Gmail)
AI Brain	RAG pipeline + LLM (GPT-4-turbo)
Storage	(Optional) Local FAISS index or Pinecone
Config	.env for credentials
Deployment	Fly.io / Railway / VPS
🚀 Getting Started
1️⃣ Prerequisites

Python 3.10+

Gmail account (for Alan, e.g. alan.ai.bot@gmail.com)

IMAP enabled in Gmail

2-Step Verification enabled

App Password generated for Gmail

Go to Google Account → Security → App passwords

Choose “Mail” → “Other (AlanBot)”

Copy the 16-character password

2️⃣ Install dependencies
pip install fastapi uvicorn python-dotenv imapclient pyzmail36 smtplib openai

3️⃣ Environment variables

Create a .env file:

GMAIL_USER=alan.ai.bot@gmail.com
GMAIL_APP_PASS=your-16-char-app-password
OPENAI_API_KEY=your-openai-key

4️⃣ Run the server
uvicorn main:app --reload


Alan will:

Check Gmail every 5 minutes for unread messages

Generate RAG-powered responses

Reply automatically via email

📁 Project Structure
email-alan/
│
├── main.py             # FastAPI server & background task
├── email_client.py     # IMAP/SMTP email handling
├── rag_engine.py       # Retrieval-Augmented Generation logic
├── templates/          # Optional email or HTML templates
├── .env                # Gmail + API credentials
└── users.json          # (Optional) lightweight personalization data

🧠 RAG Pipeline (Simplified)

Alan’s brain can be extended to:

Index daily blog articles (using FAISS or Pinecone)

Chunk and embed text with OpenAI embeddings

Retrieve relevant context based on email queries

Generate summaries or “daily briefings”

Example retrieval flow:

query = "Summarize today's AI startup news"
context = retriever.search(query, top_k=5)
response = llm.generate(context, query)

🔒 Security Notes

Use App Passwords, never your Gmail password

Gmail free accounts have ~100–150 email/day send limits

To prevent duplicate replies, store processed message IDs locally

Add a “STOP” keyword handler to let users unsubscribe

🧱 Roadmap
Phase	Description
✅ MVP	Email-based RAG assistant using Gmail IMAP/SMTP
🔜 Phase 2	Daily automated digests (Alan emails you each morning)
🔜 Phase 3	Host public “Listen” pages for generated audio summaries
🔜 Phase 4	Move from Gmail → Resend / Mailgun for scalability
💡 Example Interaction

You email:

Subject: "AI News Summary"
Body: "Hey Alan, can you summarise the most interesting AI stories from today?"

Alan replies:

Subject: "Alan’s reply: AI News Summary"
Body:
“Here’s your 3-minute AI digest: OpenAI releases a new model, Anthropic expands Claude context windows, and Hugging Face partners with AWS. [🎧 Listen here]”

🕒 Phase 2: Daily Digest Automation

Once Alan’s core email functionality works, you can make him proactive — emailing users each morning with a personalised daily briefing.

Example flow
[Daily cron or background task @ 07:00]
       ↓
[Load users.json with their interests]
       ↓
[RAG search: "Recent blogs about <topics>"]
       ↓
[Summarize and format digest]
       ↓
[Send via Gmail SMTP]

Implementation snippet (FastAPI)
import asyncio
from email_client import send_email
from rag_engine import generate_reply
import json
from datetime import datetime

async def daily_digest_task():
    while True:
        now = datetime.now()
        # Send at 07:00
        if now.hour == 7 and now.minute < 5:
            with open("users.json") as f:
                users = json.load(f)
            for user in users:
                query = f"Summarize yesterday’s news about {', '.join(user['interests'])}"
                summary = generate_reply(query)
                send_email(
                    to=user["email"],
                    subject="Alan’s Daily Briefing ☕",
                    body=summary
                )
        await asyncio.sleep(300)  # check every 5 min


Add this in your @app.on_event("startup") block to run alongside the IMAP poller.

🧩 Example user profile

users.json

[
  {
    "email": "anna@example.com",
    "interests": ["AI", "data science", "startups"]
  },
  {
    "email": "ben@example.com",
    "interests": ["finance", "crypto"]
  }
]

💬 Result

Each morning, Alan sends a personalised summary email:

Subject: “Alan’s Daily Briefing ☕”
Body: “Here’s what’s new in AI and startups today...”

⚙️ License

MIT License © 2025 — built with ❤️ by Anna van Wingerden, Rich Couzens and David Ogden