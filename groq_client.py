from groq import Groq
from config import _FALLBACK_KEY, _FALLBACK_MODEL
import database as db

AVAILABLE_MODELS = [
    "llama-3.1-8b-instant",
"llama-3.3-70b-versatile",
"openai/gpt-oss-120b",
"openai/gpt-oss-20b",
"whisper-large-v3",
"whisper-large-v3-turbo",
"groq/compound",
"groq/compound-mini",
"canopylabs/orpheus-arabic-saudi",
"canopylabs/orpheus-v1-english",
"meta-llama/llama-4-scout-17b-16e-instruct",
"meta-llama/llama-prompt-guard-2-22m",
"meta-llama/llama-prompt-guard-2-86m",
"openai/gpt-oss-safeguard-20b",
"qwen/qwen3-32b",
]

def get_response(messages: list[dict]) -> str:
    user_keys = db.get_api_keys()
    selected_model = db.get_selected_model() or _FALLBACK_MODEL

    # build attempt list: all user keys with selected model, then fallback key+model
    attempts = [(k, selected_model) for k in user_keys]
    attempts.append((_FALLBACK_KEY, _FALLBACK_MODEL))

    last_err = "No API key configured."
    for key, model in attempts:
        try:
            response = Groq(api_key=key).chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_err = str(e)
    return f"Error: {last_err}"
