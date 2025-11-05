import os
import datetime as dt
import json
from typing import List, Dict, Any

import streamlit as st

from src.config import get_settings
from src.itinerary_graph import build_itinerary_graph, PlannerInput
from src.amadeus_client import AmadeusService
from src.utils import to_pretty_json
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint  # type: ignore
import google.generativeai as genai  # type: ignore


st.set_page_config(page_title="AI Travel Planner", page_icon="🗺️", layout="wide")


def parse_itinerary_json(text: str) -> Dict[str, Any]:
    """Parse itinerary JSON from text, handling various formats."""
    try:
        # Try parsing as JSON directly
        if isinstance(text, dict):
            return text
        if isinstance(text, str):
            # Remove markdown code blocks if present
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    return {}


def parse_flight_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Amadeus flight offer into a readable format."""
    price = offer.get("price", {})
    total_price = price.get("total", "N/A")
    currency = price.get("currency", "USD")
    
    itineraries = offer.get("itineraries", [])
    if not itineraries:
        return {"price": total_price, "currency": currency, "outbound": None, "return": None}
    
    outbound = None
    return_flight = None
    
    # Parse outbound flight
    if len(itineraries) > 0:
        outbound = parse_itinerary(itineraries[0])
    
    # Parse return flight if exists
    if len(itineraries) > 1:
        return_flight = parse_itinerary(itineraries[1])
    
    return {
        "price": total_price,
        "currency": currency,
        "outbound": outbound,
        "return": return_flight,
        "raw": offer
    }


def parse_itinerary(itinerary: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single itinerary (outbound or return)."""
    segments = itinerary.get("segments", [])
    if not segments:
        return {}
    
    first_seg = segments[0]
    last_seg = segments[-1]
    
    departure = first_seg.get("departure", {})
    arrival = last_seg.get("arrival", {})
    
    # Calculate total duration
    duration = itinerary.get("duration", "")
    
    # Count stops
    stops = len(segments) - 1
    
    # Get airlines
    carriers = set()
    for seg in segments:
        carrier = seg.get("carrierCode", "")
        if carrier:
            carriers.add(carrier)
    
    return {
        "departure_airport": departure.get("iataCode", ""),
        "departure_time": departure.get("at", ""),
        "arrival_airport": arrival.get("iataCode", ""),
        "arrival_time": arrival.get("at", ""),
        "duration": duration,
        "stops": stops,
        "carriers": list(carriers),
        "segments": segments
    }


def format_time(time_str: str) -> str:
    """Format ISO time string to readable format."""
    if not time_str:
        return "N/A"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.strftime("%I:%M %p")
    except:
        return time_str


def format_duration(duration_str: str) -> str:
    """Format duration string (PT2H30M) to readable format."""
    if not duration_str:
        return "N/A"
    try:
        import re
        hours_match = re.search(r'(\d+)H', duration_str)
        mins_match = re.search(r'(\d+)M', duration_str)
        hours = hours_match.group(1) if hours_match else "0"
        mins = mins_match.group(1) if mins_match else "0"
        return f"{hours}h {mins}m" if mins != "0" else f"{hours}h"
    except:
        return duration_str


def display_flight_offers(offers: List[Dict[str, Any]], request: PlannerInput) -> None:
    """Display flight offers in an interactive, user-friendly format."""
    if not offers:
        st.info("No flight offers found for these dates/route.")
        return
    
    st.markdown(f"### ✈️ Found {len(offers)} Flight Options")
    
    # Parse all offers
    parsed_offers = [parse_flight_offer(offer) for offer in offers]
    
    # Filter and sort options
    col_filter, col_sort = st.columns([1, 1])
    
    with col_filter:
        max_stops = st.selectbox("Max Stops", ["Any", "0", "1", "2+"], index=0)
    
    with col_sort:
        sort_by = st.selectbox("Sort By", ["Price (Low to High)", "Price (High to Low)", "Duration (Shortest)", "Departure Time"], index=0)
    
    # Filter offers
    filtered_offers = parsed_offers
    if max_stops != "Any":
        max_stops_int = int(max_stops) if max_stops != "2+" else 2
        filtered_offers = [
            offer for offer in parsed_offers
            if (offer.get("outbound", {}).get("stops", 999) <= max_stops_int) and
               (not offer.get("return") or offer.get("return", {}).get("stops", 999) <= max_stops_int)
        ]
    
    # Sort offers
    if sort_by == "Price (Low to High)":
        filtered_offers = sorted(filtered_offers, key=lambda x: float(str(x.get("price", 0)).replace(",", "")))
    elif sort_by == "Price (High to Low)":
        filtered_offers = sorted(filtered_offers, key=lambda x: float(str(x.get("price", 0)).replace(",", "")), reverse=True)
    elif sort_by == "Duration (Shortest)":
        # Sort by total duration (simplified)
        filtered_offers = sorted(filtered_offers, key=lambda x: x.get("outbound", {}).get("duration", ""))
    
    # Display offers
    for idx, offer in enumerate(filtered_offers, start=1):
        price = offer.get("price", "N/A")
        currency = offer.get("currency", "USD")
        outbound = offer.get("outbound", {})
        return_flight = offer.get("return")
        
        # Create card header
        st.markdown("---")
        st.markdown(f"### ✈️ Option {idx} - **{currency} {price}**")
        
        # Use tabs for detailed view
        tab1, tab2, tab3 = st.tabs(["📋 Overview", "🔍 Details", "🔧 Raw JSON"])
        
        with tab1:
            # Outbound flight
            if outbound:
                st.markdown("#### 🛫 Outbound Flight")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    dep_airport = outbound.get("departure_airport", "")
                    dep_time = format_time(outbound.get("departure_time", ""))
                    st.markdown(f"**From:** {dep_airport}")
                    st.markdown(f"**Departure:** {dep_time}")
                
                with col2:
                    arr_airport = outbound.get("arrival_airport", "")
                    arr_time = format_time(outbound.get("arrival_time", ""))
                    st.markdown(f"**To:** {arr_airport}")
                    st.markdown(f"**Arrival:** {arr_time}")
                
                with col3:
                    duration = format_duration(outbound.get("duration", ""))
                    stops = outbound.get("stops", 0)
                    carriers = ", ".join(outbound.get("carriers", []))
                    st.markdown(f"**Duration:** {duration}")
                    st.markdown(f"**Stops:** {stops} {'stop' if stops == 1 else 'stops'}")
                    st.markdown(f"**Airlines:** {carriers}")
            
            # Return flight
            if return_flight:
                st.divider()
                st.markdown("#### 🛬 Return Flight")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    dep_airport = return_flight.get("departure_airport", "")
                    dep_time = format_time(return_flight.get("departure_time", ""))
                    st.markdown(f"**From:** {dep_airport}")
                    st.markdown(f"**Departure:** {dep_time}")
                
                with col2:
                    arr_airport = return_flight.get("arrival_airport", "")
                    arr_time = format_time(return_flight.get("arrival_time", ""))
                    st.markdown(f"**To:** {arr_airport}")
                    st.markdown(f"**Arrival:** {arr_time}")
                
                with col3:
                    duration = format_duration(return_flight.get("duration", ""))
                    stops = return_flight.get("stops", 0)
                    carriers = ", ".join(return_flight.get("carriers", []))
                    st.markdown(f"**Duration:** {duration}")
                    st.markdown(f"**Stops:** {stops} {'stop' if stops == 1 else 'stops'}")
                    st.markdown(f"**Airlines:** {carriers}")
            else:
                st.info("One-way flight only")
        
        with tab2:
            # Detailed segment info
            if outbound:
                st.markdown("**🛫 Outbound Segments:**")
                for seg_idx, segment in enumerate(outbound.get("segments", []), start=1):
                    seg_dep = segment.get("departure", {})
                    seg_arr = segment.get("arrival", {})
                    seg_carrier = segment.get("carrierCode", "")
                    seg_number = segment.get("number", "")
                    st.markdown(f"{seg_idx}. {seg_dep.get('iataCode', '')} → {seg_arr.get('iataCode', '')} | {seg_carrier} {seg_number} | {format_time(seg_dep.get('at', ''))} - {format_time(seg_arr.get('at', ''))}")
            
            if return_flight:
                st.divider()
                st.markdown("**🛬 Return Segments:**")
                for seg_idx, segment in enumerate(return_flight.get("segments", []), start=1):
                    seg_dep = segment.get("departure", {})
                    seg_arr = segment.get("arrival", {})
                    seg_carrier = segment.get("carrierCode", "")
                    seg_number = segment.get("number", "")
                    st.markdown(f"{seg_idx}. {seg_dep.get('iataCode', '')} → {seg_arr.get('iataCode', '')} | {seg_carrier} {seg_number} | {format_time(seg_dep.get('at', ''))} - {format_time(seg_arr.get('at', ''))}")
        
        with tab3:
            # Raw JSON
            st.json(offer.get("raw", {}))


def display_formatted_itinerary(itinerary: Dict[str, Any]) -> None:
    """Display itinerary in a beautiful, formatted way."""
    if not itinerary:
        st.warning("No itinerary data to display.")
        return
    
    # Header with destination
    destination = itinerary.get("destination", "Unknown Destination")
    total_days = itinerary.get("total_days", 0)
    
    st.markdown(f"## ✈️ {destination}")
    if total_days:
        st.markdown(f"**Duration:** {total_days} day{'s' if total_days > 1 else ''}")
    
    # Estimated cost
    estimated_cost = itinerary.get("estimated_cost", {})
    if estimated_cost:
        cost_currency = estimated_cost.get("currency", "USD")
        cost_total = estimated_cost.get("total", "N/A")
        st.markdown(f"**💰 Estimated Cost:** {cost_currency} {cost_total}")
    
    st.divider()
    
    # Daily plan
    daily_plan = itinerary.get("daily_plan", [])
    if daily_plan:
        st.markdown("### 📅 Daily Itinerary")
        for day_info in daily_plan:
            day_num = day_info.get("day", "Day ?")
            summary = day_info.get("summary", "")
            activities = day_info.get("activities", [])
            
            with st.expander(f"**Day {day_num}** - {summary}", expanded=False):
                if activities:
                    st.markdown("**Activities:**")
                    for activity in activities:
                        if isinstance(activity, str):
                            st.markdown(f"• {activity}")
                        elif isinstance(activity, dict):
                            activity_name = activity.get("name", activity.get("activity", "Activity"))
                            activity_time = activity.get("time", activity.get("duration", ""))
                            if activity_time:
                                st.markdown(f"• **{activity_name}** ({activity_time})")
                            else:
                                st.markdown(f"• **{activity_name}**")
                else:
                    st.info("No activities listed for this day.")
    else:
        st.info("No daily plan available.")
    
    # Tips
    tips = itinerary.get("tips", [])
    if tips:
        st.divider()
        st.markdown("### 💡 Travel Tips")
        for tip in tips:
            if isinstance(tip, str):
                st.markdown(f"• {tip}")
            else:
                st.markdown(f"• {str(tip)}")
    
    # Show raw JSON in expander for debugging
    with st.expander("📋 View Raw JSON"):
        st.json(itinerary)


def sidebar_inputs() -> PlannerInput:
    st.sidebar.header("Trip Details")
    origin = st.sidebar.text_input("Origin (IATA)", value="SFO")
    destination = st.sidebar.text_input("Destination (IATA)", value="CDG")
    start = st.sidebar.date_input("Start date", value=dt.date.today() + dt.timedelta(days=30))
    end = st.sidebar.date_input("End date", value=dt.date.today() + dt.timedelta(days=37))
    travelers = st.sidebar.number_input("Travelers", min_value=1, max_value=10, value=2, step=1)
    budget = st.sidebar.selectbox("Budget", ["budget", "moderate", "premium", "luxury"], index=1)
    pace = st.sidebar.selectbox("Pace", ["relaxed", "balanced", "intense"], index=1)
    interests: List[str] = st.sidebar.multiselect(
        "Interests",
        ["food", "museums", "nature", "nightlife", "shopping", "adventure", "history"],
        default=["food", "history"],
    )
    settings = get_settings()
    currency = st.sidebar.text_input("Currency", value=settings.default_currency)

    return {
        "origin": origin.strip(),
        "destination": destination.strip(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "travelers": int(travelers),
        "budget": budget,
        "pace": pace,
        "interests": interests,
        "currency": currency.strip() or settings.default_currency,
    }


def main() -> None:
    st.title("🗺️ AI-Powered Travel Itinerary Planner")
    st.caption("Personalized plans with Grok, Hugging Face (Gemma) + live flights via Amadeus")

    request = sidebar_inputs()

    st.sidebar.divider()
    provider = st.sidebar.radio(
        "Planner model provider",
        ["Grok (xAI)", "Hugging Face (Gemma)", "Google Gemini"],
        index=0,
    )
    hf_token = ""
    hf_repo = "google/gemma-2-2b-it"
    if provider == "Hugging Face (Gemma)":
        hf_token = st.sidebar.text_input("HF API Token", type="password")
        hf_repo = st.sidebar.text_input("HF Model repo_id", value="google/gemma-2-2b-it")
    gemini_key = ""
    gemini_model = ""
    if provider == "Google Gemini":
        settings = get_settings()
        # Default to values from keys.env if available
        default_key = settings.gemini_api_key if settings.gemini_api_key else ""
        default_model = settings.gemini_model if settings.gemini_model else "gemini-2.5-flash"
        gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=default_key)
        gemini_model = st.sidebar.text_input("Gemini Model", value=default_model)

    # Section 1: Generate Itinerary
    with st.container():
        st.markdown("---")
        st.markdown("## 📅 Generate Your Travel Itinerary")
        st.caption("Create a personalized travel plan powered by AI")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            generate_btn = st.button("✨ Generate Itinerary", type="primary", use_container_width=True)
        with col_btn2:
            st.write("")  # Spacing
        
        if generate_btn:
            try:
                with st.spinner("🤖 Generating your personalized itinerary..."):
                    if provider == "Grok (xAI)":
                        graph = build_itinerary_graph()
                        result = graph.invoke({"request": request})
                        itinerary = result.get("itinerary", {})
                        display_formatted_itinerary(itinerary)
                    elif provider == "Hugging Face (Gemma)":
                        if not hf_token:
                            st.error("Please provide your Hugging Face API token.")
                        else:
                            prompt = (
                                "Return only JSON with keys: destination, total_days, daily_plan (array of {day, summary, activities}), "
                                "estimated_cost (object with currency and total), tips (array of strings). "
                                f"Destination: {request['destination']}. Dates: {request['start_date']} to {request['end_date']}. "
                                f"Travelers: {request['travelers']}. Budget: {request['budget']}. Interests: {', '.join(request['interests'])}. "
                                f"Preferred pace: {request['pace']}. Output currency: {request['currency']}."
                            )
                            llm = HuggingFaceEndpoint(
                                repo_id=hf_repo,
                                task="text-generation",
                                huggingfacehub_api_token=hf_token,
                                max_new_tokens=1024,
                                temperature=0.7,
                            )
                            chat = ChatHuggingFace(llm=llm)
                            res = chat.invoke(prompt)
                            itinerary = parse_itinerary_json(str(res.content))
                            display_formatted_itinerary(itinerary)
                    else:  # Google Gemini
                        # Use API key from sidebar if provided, otherwise from config
                        api_key = ""
                        if gemini_key and gemini_key.strip():
                            api_key = gemini_key.strip().strip("'\"")
                        else:
                            settings = get_settings()
                            api_key = settings.gemini_api_key.strip().strip("'\"") if settings.gemini_api_key else ""
                        
                        if not api_key:
                            st.error("Please provide your Gemini API key in the sidebar or set GEMINI_API_KEY in keys.env.")
                        else:
                            # Use model from sidebar if provided, otherwise from config, otherwise fallback
                            model_name = gemini_model.strip() if gemini_model and gemini_model.strip() else get_settings().gemini_model
                            if not model_name or not model_name.strip():
                                model_name = "gemini-2.5-flash"  # fallback to working model
                            
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel(model_name)
                            prompt = (
                                "Return only JSON with keys: destination, total_days, daily_plan (array of {day, summary, activities}), "
                                "estimated_cost (object with currency and total), tips (array of strings). "
                                f"Destination: {request['destination']}. Dates: {request['start_date']} to {request['end_date']}. "
                                f"Travelers: {request['travelers']}. Budget: {request['budget']}. Interests: {', '.join(request['interests'])}. "
                                f"Preferred pace: {request['pace']}. Output currency: {request['currency']}."
                            )
                            out = model.generate_content(prompt)
                            # Use the same robust text extraction as test.py
                            text = getattr(out, "text", None)
                            if not text and getattr(out, "candidates", None):
                                parts = out.candidates[0].content.parts
                                text = "".join(getattr(p, "text", "") for p in parts)
                            if text:
                                itinerary = parse_itinerary_json(text)
                                display_formatted_itinerary(itinerary)
                            else:
                                st.error(f"No text in response. Response: {out}")
            except Exception as e:
                st.error(f"❌ Planner error: {e}")
    
    # Section 2: Live Flight Options
    st.markdown("---")
    with st.container():
        st.markdown("## ✈️ Live Flight Options")
        st.caption("Search for real-time flight prices and schedules from Amadeus")
        
        # Flight search options
        col_search1, col_search2, col_search3 = st.columns([2, 2, 3])
        with col_search1:
            non_stop_only = st.checkbox("Non-stop flights only", value=False)
        with col_search2:
            max_results = st.number_input("Max Results", min_value=5, max_value=50, value=10, step=5)
        with col_search3:
            st.write("")  # Spacing
        
        search_btn = st.button("🔍 Search Flights", type="primary", use_container_width=True)
        
        if search_btn:
            try:
                with st.spinner("🔍 Searching for flights..."):
                    settings = get_settings()
                    ama = AmadeusService()
                    offers = ama.search_flights(
                        origin=request["origin"],
                        destination=request["destination"],
                        departure_date=request["start_date"],
                        return_date=request["end_date"],
                        adults=request["travelers"],
                        currency=request["currency"] or settings.default_currency,
                        non_stop=non_stop_only if non_stop_only else None,
                        max_results=max_results,
                    )
                    display_flight_offers(offers, request)
            except Exception as e:
                st.error(f"❌ Flight search error: {e}")
                st.info("💡 Make sure your Amadeus API credentials are set correctly in keys.env")

    with st.expander("Environment diagnostics"):
        settings = get_settings()
        st.write({
            "GROK_BASE_URL": settings.grok_base_url,
            "GROK_MODEL": settings.grok_model,
            "GEMINI_MODEL": settings.gemini_model,
            "AMADEUS_ENV": settings.amadeus_env,
            "DEFAULT_CURRENCY": settings.default_currency,
            "Has GROK_API_KEY": bool(settings.grok_api_key),
            "Has GEMINI_API_KEY": bool(settings.gemini_api_key),
            "Has AMADEUS_API_KEY": bool(settings.amadeus_api_key),
        })


if __name__ == "__main__":
    main()