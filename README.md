Live Website - https://flight-amedus-8ucwqsyarylskvuapuddrt.streamlit.app/

## AI-Powered Travel Itinerary Planner

An AI travel assistant that generates personalized itineraries with Grok (xAI) via an OpenAI-compatible API and fetches live flight options from Amadeus. Delivered as an interactive Streamlit app.

### Features

- Personalized multi-day itineraries using Grok (xAI) with LangGraph
- Live flight search using Amadeus Flight Offers Search API
- Streamlit UI for fast, friendly trip planning

### Architecture

- `Streamlit UI` → collects trip preferences and shows results
- `LangGraph Planner` → orchestrates prompts/tools to produce itinerary JSON
- `Amadeus Client` → fetches real-time flight offers

### Requirements

- Python 3.10+
- API keys (choose what you use):
  - xAI Grok API key (OpenAI-compatible)
  - Hugging Face API token (for Gemma via HF Inference)
  - Google Gemini API key (optional)
  - Amadeus API key/secret

### Environment Variables

Copy `.env.example` to `.env` and fill values:

```
# Grok (xAI) - OpenAI compatible
GROK_API_KEY=your_xai_api_key
GROK_BASE_URL=https://api.x.ai/v1
GROK_MODEL=grok-2-latest

# Hugging Face (Gemma)
# Provided in the UI sidebar; you can also set:
# HF_API_TOKEN=your_hf_token

# Google Gemini (optional)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-pro

# Amadeus
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret
AMADEUS_ENV=production  # or test

DEFAULT_CURRENCY=USD
```

Notes:

- Grok exposes an OpenAI-compatible API; we use the official `openai` Python SDK with `base_url` set via `GROK_BASE_URL`.
- Set `AMADEUS_ENV` to `test` if your Amadeus account is sandbox-only.
- In the Streamlit sidebar, you can choose between Grok and Hugging Face (Gemma). For Gemma, enter your HF token and optionally change the `repo_id` (default `google/gemma-2-2b-it`).

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# edit .env with your keys
```

### Run Locally

```bash
streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit. In the sidebar:

- Choose provider: Grok, Hugging Face (Gemma), or Google Gemini
- For Gemma, paste your HF token and (optional) model repo

### Deploy to Streamlit Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

**Quick Steps:**

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect your GitHub repo
4. Set main file to: `streamlit_app.py`
5. Add your API keys as secrets in the Streamlit Cloud dashboard
6. Deploy!

Your app will be live at: `https://your-app-name.streamlit.app`

### Notes on Accuracy

- The planner returns structured itinerary JSON and targets high relevance by grounding with user preferences (budget, interests, pace) and dates.
- Flight data is always live from Amadeus, not static.

### Files

- `streamlit_app.py` — Streamlit UI
- `src/config.py` — environment & settings
- `src/amadeus_client.py` — Amadeus integration
- `src/itinerary_graph.py` — LangGraph planner powered by Grok
- `src/utils.py` — shared helpers

### Future Enhancements

- Hotel and activity APIs (e.g., Booking, Google Places)
- Caching layer for repeated searches
- Offline export (PDF) and shareable links
