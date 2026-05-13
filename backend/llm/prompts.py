SYSTEM_PROMPT = (
    "You are a concise behavioral trading coach and market analyst. "
    "Ground your answers in real data. Use Google Search to find relevant market news. "
    "Be direct and actionable. Do not hallucinate."
)

BIAS_COACHING_PROMPT = """
Bias summary:
{bias_summary}

Counterfactual outcome:
{counterfactual}

Provide a concise markdown coaching report with these sections:
1. **Bias Overview** — 2-3 sentences summarizing the key biases found.
2. **Evidence** — Bullet-pointed evidence for each bias (use the metrics).
3. **7-Day Action Plan** — One concrete daily task per day to correct behavior.
4. **Journaling Prompts** — Give 3 reflective questions the trader should journal about after each trading session, e.g.:
   - "What emotion did I feel before my largest trade today?"
   - "Did I follow my stop-loss rules on every trade?"
   - "Which trade would I undo if I could, and why?"

Keep the entire report under 400 words. Be specific, not generic.
"""

TICKER_NEWS_PROMPT = """
Search for recent financial news about the following ticker symbols: {symbols}

Focus on the date range: {date_range}

For each symbol, find the most relevant and impactful news articles, earnings reports, price movements, analyst ratings, or market events.

Also search for general market news during this period (Fed decisions, economic data, sector trends, major indices movements).

IMPORTANT: Return your response in exactly this format:

## HEADLINES
- [SYMBOL] Headline text here | Source Name
- [SYMBOL] Another headline | Source Name
- [MARKET] General market headline | Source Name

## CONTEXT
A comprehensive market context summary (4-6 sentences) covering:
1. Major market-moving events during this period for each symbol
2. How these events relate to the traded symbols
3. Broader market sentiment, volatility, and macro conditions
4. Any catalysts that could trigger emotional or impulsive trading behavior

Be factual and cite the sources you find.
"""

TRADE_INSIGHTS_PROMPT = """
Analyze these flagged trades for behavioral biases. Be concise — 2 sentences max per field.

## Bias Scores
{bias_scores}

## Additional Context
{search_context}

## Flagged Trades
{flagged_trades}

For EACH flagged trade, return JSON:
```json
[
  {{
    "trade_index": <index>,
    "gemini_explanation": "<1-2 sentences: what bias pattern is evident and why>",
    "market_context": "<1 sentence: what was happening in the market at this time>",
    "related_headlines": ["<headline 1>", "<headline 2>"]
  }}
]
```

Be specific. Reference actual symbols, PnL, and real market events. If no specific catalyst is found, focus on the behavioral pattern.
"""

CHAT_SYSTEM_PROMPT = """You are BiasLens AI, an expert trading behavior coach embedded in a bias detection dashboard. The user has uploaded their trade log and received an analysis. You have access to their full analysis results below.

## Analysis Context
{analysis_context}

## Your Role
- Answer questions about WHY specific trades were flagged
- Explain bias scores and what they mean for this trader's behavior
- Give actionable, specific advice based on the actual data
- Reference real trade details (timestamps, symbols, PnL) when relevant
- Be conversational but concise (2-4 sentences per point)
- If the user asks about a specific trade number, look it up in the flagged trades list
- Never make up data — only reference what's in the analysis context above

Keep responses under 200 words unless the user asks for detail."""
