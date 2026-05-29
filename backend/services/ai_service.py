# services/ai_service.py

from google import genai
import os
import json
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# Load Environment Variables
# ─────────────────────────────────────────────────────────────

load_dotenv()

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

# ─────────────────────────────────────────────────────────────
# Gemini Client
# ─────────────────────────────────────────────────────────────

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"  # or "gemini-2.5-pro" for more power (with longer response times)

# ─────────────────────────────────────────────────────────────
# Safe Gemini Request
# ─────────────────────────────────────────────────────────────

def generate_text(prompt: str) -> str:
    """
    Send prompt to Gemini and return clean text response
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        if hasattr(response, "text") and response.text:
            return response.text.strip()

        return "No response generated."

    except Exception as e:
        print("❌ Gemini Error:", str(e))
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Safe JSON Parser
# ─────────────────────────────────────────────────────────────

def parse_json_response(raw: str) -> dict:
    """
    Safely parse Gemini JSON response
    """

    try:
        raw = raw.strip()

        # Remove markdown json block
        if raw.startswith("```"):
            raw = raw.replace("```json", "")
            raw = raw.replace("```", "")
            raw = raw.strip()

        # Extract JSON object only
        start = raw.find("{")
        end = raw.rfind("}") + 1

        if start != -1 and end != -1:
            raw = raw[start:end]

        return json.loads(raw)

    except Exception as e:
        print("❌ JSON Parse Error:", str(e))

        return {
            "reply": raw,
            "score": 0,
            "name": "",
            "email": "",
            "phone": "",
            "budget": "",
            "intent": "",
            "category": "cold",
            "is_qualified": False
        }


# ─────────────────────────────────────────────────────────────
# Lead Qualification
# ─────────────────────────────────────────────────────────────

def qualify_lead(conversation_history: list, user_message: str) -> dict:

    system_prompt = """
You are an AI lead qualification agent for a digital marketing agency.

Your job:
- Talk naturally like a human sales executive
- Ask one question at a time
- Collect:
    1. Name
    2. Business type
    3. Goal
    4. Marketing budget
    5. Timeline
    6. Email

Scoring Rules:
- Budget:
    - $5000+ → +40
    - $2000-5000 → +30
    - $500-2000 → +20
    - <$500 → +5

- Timeline:
    - Immediate → +30
    - 1-3 months → +20

- Clear business goal → +20
- Valid email → +10

Lead Categories:
- 70-100 → hot
- 40-69 → warm
- 0-39 → cold

IMPORTANT:
Return ONLY valid JSON.
Do not add markdown.
Do not add explanation.

JSON Format:
{
  "reply": "",
  "score": 0,
  "name": "",
  "email": "",
  "phone": "",
  "budget": "",
  "intent": "",
  "category": "cold",
  "is_qualified": false
}
"""

    # Build conversation history
    messages_text = ""

    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        messages_text += f"{role}: {content}\n"

    messages_text += f"user: {user_message}"

    full_prompt = f"""
{system_prompt}

Conversation:
{messages_text}
"""

    raw_response = generate_text(full_prompt)

    return parse_json_response(raw_response)


# ─────────────────────────────────────────────────────────────
# Follow-Up Generator
# ─────────────────────────────────────────────────────────────

def generate_followup(
    lead_name: str,
    lead_intent: str,
    days_since_contact: int
) -> str:

    prompt = f"""
Write a professional WhatsApp follow-up message.

Lead Name: {lead_name}
Interest: {lead_intent}
Days Since Contact: {days_since_contact}

Rules:
- Keep it short
- Friendly tone
- Maximum 3 sentences
- Include call to action
"""

    return generate_text(prompt)


# ─────────────────────────────────────────────────────────────
# Campaign Summary
# ─────────────────────────────────────────────────────────────

def generate_campaign_summary(campaign_data: dict) -> str:

    prompt = f"""
Analyze the following campaign data and summarize performance.

Provide:
- 3 bullet points
- Key wins
- Areas to improve

Campaign Data:
{json.dumps(campaign_data, indent=2)}
"""

    return generate_text(prompt)


# ─────────────────────────────────────────────────────────────
# Analytics Insight
# ─────────────────────────────────────────────────────────────

def generate_analytics_insight(analytics_data: dict) -> str:

    prompt = f"""
Analyze this lead analytics data.

Provide:
1. Top insight
2. Biggest problem
3. Recommended action

Keep response concise.

Analytics Data:
{json.dumps(analytics_data, indent=2)}
"""

    return generate_text(prompt)