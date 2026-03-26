from groq import Groq
from config import _FALLBACK_KEY, GROQ_MODEL
import database as db


def _make_client(api_key):
    return Groq(api_key=api_key)


def get_response(messages: list[dict]) -> str:
    user_key = db.get_api_key()
    # try user key first, fallback to hidden key
    keys = [k for k in [user_key, _FALLBACK_KEY] if k]
    last_err = "No API key configured."
    for key in keys:
        try:
            client = _make_client(key)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_err = str(e)
    return f"Error: {last_err}"
