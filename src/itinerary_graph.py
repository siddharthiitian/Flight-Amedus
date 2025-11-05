from __future__ import annotations

from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph, START, END  # type: ignore
from langchain.schema import SystemMessage, HumanMessage  # type: ignore
from langchain.chat_models.base import BaseChatModel  # type: ignore
from langchain_core.output_parsers import JsonOutputParser  # type: ignore
from openai import OpenAI

from .config import get_settings
from .utils import clamp_days


class PlannerInput(TypedDict, total=False):
    origin: str
    destination: str
    start_date: str
    end_date: str
    budget: str
    interests: List[str]
    travelers: int
    pace: str
    currency: str


class PlannerState(TypedDict, total=False):
    request: PlannerInput
    itinerary: Dict[str, Any]


def _make_llm() -> OpenAI:
    settings = get_settings()
    if not settings.grok_api_key:
        raise RuntimeError("GROK_API_KEY is required")
    return OpenAI(api_key=settings.grok_api_key, base_url=settings.grok_base_url)


ITINERARY_SCHEMA_HINT = (
    "Return strict JSON with keys: destination, total_days, daily_plan (array of {day, summary, activities}), "
    "estimated_cost (object with currency and total), tips (array of strings)."
)


def planner_node(state: PlannerState) -> PlannerState:
    settings = get_settings()
    client = _make_llm()

    req = state.get("request", {})
    start_date = req.get("start_date", "")
    end_date = req.get("end_date", "")

    system = SystemMessage(
        content=(
            "You are an expert travel planner. Create practical, local-savvy itineraries. "
            "Use realistic travel times, cluster nearby activities, and balance mornings/afternoons/evenings. "
            f"Output currency: {req.get('currency') or settings.default_currency}. {ITINERARY_SCHEMA_HINT}"
        )
    )

    human = HumanMessage(
        content=(
            "Plan a trip with these details:\n" \
            f"- Origin: {req.get('origin')}\n" \
            f"- Destination: {req.get('destination')}\n" \
            f"- Dates: {start_date} to {end_date}\n" \
            f"- Travelers: {req.get('travelers', 1)}\n" \
            f"- Budget: {req.get('budget', 'moderate')}\n" \
            f"- Interests: {', '.join(req.get('interests', []))}\n" \
            f"- Preferred pace: {req.get('pace', 'balanced')}\n" \
            "Return only JSON."
        )
    )

    response = client.chat.completions.create(
        model=settings.grok_model,
        messages=[
            {"role": "system", "content": system.content},
            {"role": "user", "content": human.content},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    message = response.choices[0].message
    content = message.content or "{}"
    parser = JsonOutputParser()
    itinerary = parser.parse(content)

    # Clamp total_days if present
    if "total_days" in itinerary and isinstance(itinerary["total_days"], int):
        itinerary["total_days"] = clamp_days(itinerary["total_days"]) 

    return {"itinerary": itinerary}


def build_itinerary_graph():
    graph = StateGraph(PlannerState)
    graph.add_node("planner", planner_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", END)
    return graph.compile()

