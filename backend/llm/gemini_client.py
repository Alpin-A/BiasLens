from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import requests

from backend.llm.prompts import (
    BIAS_COACHING_PROMPT,
    CHAT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    TICKER_NEWS_PROMPT,
    TRADE_INSIGHTS_PROMPT,
)
from backend.utils.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# ── Global rate-limiter ───────────────────────────────────────────
# Serialize Gemini calls with a minimum gap between requests to stay
# within free-tier RPM limits (~15 RPM → ~4 s between calls).
_api_lock = threading.Lock()
_last_call_time: float = 0.0
_MIN_CALL_GAP = 4.0  # seconds between Gemini API calls


class GeminiClient:
    """Gemini REST API client with rate limiting and retry."""

    MAX_RETRIES = 4
    INITIAL_BACKOFF = 5.0  # seconds

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set – Gemini calls will fail.")

    def _call_api(self, payload: dict) -> dict:
        """Low-level call to Gemini REST API with rate limiting and retry.

        - Acquires a global lock so only one request is in-flight at a time.
        - Enforces a minimum gap between successive calls.
        - Retries up to MAX_RETRIES times on 429 / 503 with exponential backoff.
        """
        global _last_call_time

        if not self.settings.gemini_api_key:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY in your .env file.")

        url = GEMINI_API_URL.format(model=self.settings.gemini_model)
        last_exc: Exception | None = None

        for attempt in range(self.MAX_RETRIES + 1):
            with _api_lock:
                elapsed = time.time() - _last_call_time
                if elapsed < _MIN_CALL_GAP:
                    wait = _MIN_CALL_GAP - elapsed
                    logger.debug("Rate-limiter: waiting %.1fs before Gemini call", wait)
                    time.sleep(wait)

                try:
                    response = requests.post(
                        url,
                        params={"key": self.settings.gemini_api_key},
                        json=payload,
                        timeout=90,
                    )
                    _last_call_time = time.time()
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as exc:
                    _last_call_time = time.time()
                    last_exc = exc

                    # Only retry on rate-limit (429) or server errors (5xx)
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    if status in (429, 500, 502, 503) and attempt < self.MAX_RETRIES:
                        backoff = self.INITIAL_BACKOFF * (2 ** attempt)
                        logger.warning(
                            "Gemini %s (attempt %d/%d) – retrying in %.0fs",
                            status, attempt + 1, self.MAX_RETRIES + 1, backoff,
                        )
                        time.sleep(backoff)
                        continue

                    logger.error("Gemini API error: %s", exc)
                    raise RuntimeError(f"Gemini API error: {exc}") from exc

        raise RuntimeError(f"Gemini API failed after {self.MAX_RETRIES + 1} attempts: {last_exc}")

    def generate(self, prompt: str) -> str:
        """Standard generation without grounding."""
        if not self.settings.gemini_api_key:
            return "_Gemini API key not configured. Set GEMINI_API_KEY in your .env file._"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}],
                }
            ]
        }
        try:
            data = self._call_api(payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected Gemini response format.") from exc

    def chat(
        self,
        messages: list[dict[str, str]],
        analysis_context: str,
    ) -> str:
        """Multi-turn chat with analysis context injected as system instruction.

        Args:
            messages: List of {"role": "user"|"model", "text": "..."} dicts.
            analysis_context: Serialized analysis data to inject into system prompt.

        Returns:
            The model's response text.
        """
        if not self.settings.gemini_api_key:
            return "_Gemini API key not configured. Set GEMINI_API_KEY in your .env file._"

        system_text = CHAT_SYSTEM_PROMPT.format(analysis_context=analysis_context)

        contents: list[dict] = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["text"]}],
            })

        payload = {
            "system_instruction": {
                "parts": [{"text": system_text}],
            },
            "contents": contents,
        }

        try:
            data = self._call_api(payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected Gemini response format.") from exc

    def generate_grounded(self, prompt: str) -> dict[str, Any]:
        """Generation with Google Search grounding enabled.

        Returns:
            {
                "text": str,  # Gemini's grounded response text
                "sources": [{"title": str, "url": str}, ...],
                "search_queries": [str, ...],
            }
        """
        if not self.settings.gemini_api_key:
            return {
                "text": "_Gemini API key not configured. Set GEMINI_API_KEY in your .env file._",
                "sources": [],
                "search_queries": [],
            }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}],
                }
            ],
            "tools": [{"google_search": {}}],
        }
        try:
            data = self._call_api(payload)
            candidate = data["candidates"][0]
            text = candidate["content"]["parts"][0]["text"]

            grounding = candidate.get("groundingMetadata", {})
            search_queries = grounding.get("webSearchQueries", [])

            sources: list[dict[str, str]] = []
            for chunk in grounding.get("groundingChunks", []):
                web = chunk.get("web", {})
                raw_url = web.get("uri", "")
                title = web.get("title", "")
                # Filter out Vertex AI redirect URLs and invalid URLs
                if raw_url and (
                    "vertexaisearch" in raw_url
                    or "localhost" in raw_url
                    or not raw_url.startswith("https://")
                ):
                    raw_url = ""
                if title or raw_url:
                    sources.append({"title": title, "url": raw_url})

            return {
                "text": text,
                "sources": sources,
                "search_queries": search_queries,
            }
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Gemini grounded response parse error: %s", exc)
            return {
                "text": "Unable to retrieve grounded response.",
                "sources": [],
                "search_queries": [],
            }


# ── Coaching ──────────────────────────────────────────────────────


def generate_coaching_report(
    analysis: dict[str, Any],
    counterfactual: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Return (markdown_report, coaching_plan_steps)."""
    client = GeminiClient()
    bias_summary = json.dumps(analysis.get("bias_scores", {}), indent=2)
    cf_text = json.dumps(counterfactual, indent=2) if counterfactual else "Not available."
    prompt = BIAS_COACHING_PROMPT.format(bias_summary=bias_summary, counterfactual=cf_text)
    report = client.generate(prompt)

    plan: list[str] = []
    for line in report.split("\n"):
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and "." in stripped[:4]:
            plan.append(stripped)

    if not plan:
        plan = [
            "Day 1–2: Review flagged trades and journal observations.",
            "Day 3–4: Set max trade limits and cooldown timers.",
            "Day 5–6: Practice mindful entry criteria before each trade.",
            "Day 7: Evaluate progress and adjust rules.",
        ]

    return report, plan


# ── News (Gemini + Google Search grounding) ───────────────────────


def search_ticker_news(
    symbols: list[str],
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    """Use Gemini with Google Search grounding to find news for traded symbols.

    Returns:
        {
            "headlines": [{"title": str, "source": str, "url": str, "symbol": str, "published_at": str}],
            "context": str,
            "symbols": [str],
            "search_queries": [str],
        }
    """
    client = GeminiClient()
    prompt = TICKER_NEWS_PROMPT.format(
        symbols=", ".join(symbols[:10]),
        date_range=f"{date_from} to {date_to}",
    )
    result = client.generate_grounded(prompt)
    text = result["text"]

    source_urls: dict[str, str] = {}
    for src in result.get("sources", []):
        domain = src.get("title", "").lower().replace("www.", "")
        if domain and src.get("url"):
            source_urls[domain] = src["url"]

    # Parse structured headlines from Gemini's text response
    headlines: list[dict[str, str]] = []
    context = ""

    headlines_section = ""
    if "## HEADLINES" in text:
        parts = text.split("## CONTEXT", 1)
        headlines_section = parts[0].split("## HEADLINES", 1)[1] if "## HEADLINES" in parts[0] else ""
        context = parts[1].strip() if len(parts) > 1 else text
    elif "## CONTEXT" in text:
        context = text.split("## CONTEXT", 1)[1].strip()
    else:
        # Fallback: use entire text as context
        context = text

    # Parse headline lines: "- [SYMBOL] Title | Source"
    import re
    for line in headlines_section.split("\n"):
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        line = line.lstrip("- ").strip()

        sym_match = re.match(r"\[([A-Z0-9]+)\]\s*(.*)", line)
        if sym_match:
            symbol = sym_match.group(1)
            rest = sym_match.group(2)
        else:
            symbol = "MARKET"
            rest = line

        if "|" in rest:
            title, source = rest.rsplit("|", 1)
            title = title.strip()
            source = source.strip()
        else:
            title = rest.strip()
            source = "Web"

        url = ""
        source_lower = source.lower().replace(" ", "")
        for domain, domain_url in source_urls.items():
            if source_lower in domain or domain in source_lower:
                url = domain_url
                break

        if symbol not in symbols and symbol != "MARKET":
            for sym in symbols:
                clean = sym.replace("USD", "").replace("USDT", "").replace("PERP", "").upper()
                if clean == symbol:
                    symbol = sym
                    break

        headlines.append({
            "title": title,
            "source": source,
            "url": url,
            "symbol": symbol,
            "published_at": f"{date_from}T00:00:00Z",
        })

    # If no headlines were parsed from structured format, extract from text
    if not headlines:
        headlines = _extract_headlines_from_text(text, symbols, result.get("sources", []), date_from)

    return {
        "headlines": headlines,
        "context": context,
        "symbols": symbols,
        "search_queries": result["search_queries"],
    }


def _extract_headlines_from_text(
    text: str,
    symbols: list[str],
    sources: list[dict[str, str]],
    date_from: str,
) -> list[dict[str, str]]:
    """Fallback: extract headline-like content from Gemini's free-form text."""
    import re
    headlines: list[dict[str, str]] = []

    # Look for bold items (**Title**) or bullet points
    for line in text.split("\n"):
        line = line.strip()
        # Match "**Title:**" or "* **Title:**" patterns
        bold_match = re.search(r"\*\*([^*]{10,80})\*\*", line)
        if bold_match and not line.startswith("##"):
            title = bold_match.group(1).rstrip(":").strip()

            # Try to match to a symbol
            matched_symbol = "MARKET"
            title_lower = title.lower()
            for sym in symbols:
                clean = sym.replace("USD", "").replace("USDT", "").replace("PERP", "").lower()
                if clean and clean in title_lower:
                    matched_symbol = sym
                    break

            # Use a grounding source if available
            source_name = "Web"
            url = ""
            if sources:
                src = sources[len(headlines) % len(sources)]
                source_name = src.get("title", "Web")
                url = src.get("url", "")

            headlines.append({
                "title": title,
                "source": source_name,
                "url": url,
                "symbol": matched_symbol,
                "published_at": f"{date_from}T00:00:00Z",
            })

    return headlines[:15]  # Cap at 15


def search_general_news(date: str, bias: str = "") -> dict[str, Any]:
    """Use Gemini with Google Search grounding for general market news on a date.

    Returns same structure as search_ticker_news.
    """
    client = GeminiClient()
    bias_context = f" Focus on events related to {bias} behavior patterns." if bias else ""
    prompt = (
        f"Search for the most important financial market news and events on {date}.{bias_context} "
        f"Include stock market, crypto, economic data releases, and central bank actions. "
        f"\n\nIMPORTANT: Format your response as:\n\n"
        f"## HEADLINES\n"
        f"- [MARKET] Headline text here | Source Name\n"
        f"- [MARKET] Another headline | Source Name\n\n"
        f"## CONTEXT\n"
        f"A summary of the key events and how they may have affected trader sentiment."
    )
    result = client.generate_grounded(prompt)
    text = result["text"]

    # Parse structured headlines (same logic as ticker news)
    headlines: list[dict[str, str]] = []
    context = ""

    if "## HEADLINES" in text:
        parts = text.split("## CONTEXT", 1)
        headlines_section = parts[0].split("## HEADLINES", 1)[1] if "## HEADLINES" in parts[0] else ""
        context = parts[1].strip() if len(parts) > 1 else text
    else:
        headlines_section = ""
        context = text

    import re
    for line in headlines_section.split("\n"):
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        line = line.lstrip("- ").strip()

        sym_match = re.match(r"\[([A-Z0-9]+)\]\s*(.*)", line)
        rest = sym_match.group(2) if sym_match else line

        if "|" in rest:
            title, source = rest.rsplit("|", 1)
            title = title.strip()
            source = source.strip()
        else:
            title = rest.strip()
            source = "Web"

        headlines.append({
            "title": title,
            "source": source,
            "url": "",
            "symbol": "MARKET",
            "published_at": f"{date}T00:00:00Z",
        })

    if not headlines:
        headlines = _extract_headlines_from_text(text, [], result.get("sources", []), date)

    return {
        "headlines": headlines,
        "context": context,
        "symbols": [],
        "search_queries": result["search_queries"],
    }


# ── Trade Insights ────────────────────────────────────────────────


def generate_trade_insights(
    flagged_trades: list[dict[str, Any]],
    bias_scores: dict[str, Any],
    search_context: str = "",
) -> list[dict[str, Any]]:
    """Generate per-trade Gemini explanations linking biases to market context.

    Uses google_search grounding so Gemini can look up real market events
    around each trade's timestamp.
    """
    client = GeminiClient()

    trades_text = ""
    for t in flagged_trades[:20]:  # cap to avoid huge prompts
        trades_text += (
            f"- Trade #{t.get('trade_index', '?')}: {t.get('symbol', '?')} "
            f"{t.get('side', '?')} | PnL: {t.get('pnl', 0):.2f} | "
            f"Time: {t.get('timestamp', '?')} | "
            f"Bias tags: {', '.join(t.get('tags', []))} | "
            f"Reason: {t.get('reason', 'N/A')}\n"
        )

    bias_text = json.dumps(bias_scores, indent=2, default=str)

    prompt = TRADE_INSIGHTS_PROMPT.format(
        bias_scores=bias_text,
        flagged_trades=trades_text,
        search_context=search_context,
    )

    result = client.generate_grounded(prompt)
    raw = result["text"]

    source_titles = [s["title"] for s in result.get("sources", [])]

    # Parse JSON from Gemini response
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            # Inject grounding sources as related_headlines if not already present
            for item in parsed:
                if not item.get("related_headlines"):
                    item["related_headlines"] = source_titles[:3]
            return parsed
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to parse Gemini trade insights JSON: %s", exc)

    # Fallback: return generic insights for each trade
    return [
        {
            "trade_index": t.get("trade_index", i),
            "gemini_explanation": "AI analysis unavailable. Review the bias flags and market conditions manually.",
            "market_context": "Market context could not be generated.",
            "related_headlines": source_titles[:3] if source_titles else [],
        }
        for i, t in enumerate(flagged_trades)
    ]


# ── Helpers ───────────────────────────────────────────────────────


def _extract_domain(url: str) -> str:
    """Extract domain name from URL for display as source."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or "Web"
    except Exception:
        return "Web"
