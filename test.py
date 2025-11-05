import os

try:
    from dotenv import load_dotenv  # type: ignore
    # Load from .env then keys.env if present
    load_dotenv()
    if os.path.exists("keys.env"):
        load_dotenv("keys.env", override=True)
except Exception:
    pass

import google.generativeai as genai  # type: ignore


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip().strip("'")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in keys.env or environment.")

    # Pick a model you have access to (from your listed models)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    prompt = "Say hi in one word."
    out = model.generate_content(prompt)
    # Prefer .text; fallback for SDK variations
    text = getattr(out, "text", None)
    if not text and getattr(out, "candidates", None):
        parts = out.candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    print(text or out)


if __name__ == "__main__":
    main()