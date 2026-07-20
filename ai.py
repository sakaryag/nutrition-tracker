"""
AI integration layer.
Uses Claude if ANTHROPIC_API_KEY is set, otherwise falls back to parser.py.
"""
import os
import json
from parser import parse as fallback_parse

_SYSTEM_PROMPT = """\
You are a nutrition tracking assistant. Your job is to parse food entries from user messages.

When the user mentions eating food, respond ONLY with valid JSON matching this schema:
{
  "action": "add_food",
  "name": "<food name>",
  "quantity": <number>,
  "unit": "<g|ml|piece|slice|cup|tbsp|tsp|serving>",
  "calories": <estimated kcal as number, or null>,
  "protein_g": <estimated grams as number, or null>,
  "carbs_g": <estimated grams as number, or null>,
  "fat_g": <estimated grams as number, or null>,
  "meal": "<Breakfast|Lunch|Dinner|Snack>",
  "note": "<optional short note, or null>"
}

If the user is asking a question (e.g. "how much did I eat today?"), respond with:
{"action": "query", "message": "<friendly reply>"}

If you cannot parse a food entry, respond with:
{"action": "clarify", "message": "<short clarifying question>"}

Rules:
- Respond ONLY with JSON — no prose, no markdown fences.
- Use your nutritional knowledge to estimate macros when not provided.
- If quantity is ambiguous (e.g. "a bowl of rice"), use a sensible default and add a note.
- Meal defaults to "Snack" when unspecified.
- Never invent a food that wasn't mentioned; set macros to null if unknown.
"""


def _call_claude(user_message: str) -> dict:
    """Call the Anthropic API and return parsed JSON dict."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError('anthropic package not installed. Run: pip install anthropic')

    api_key = os.getenv('ANTHROPIC_API_KEY')
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_message}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if Claude wraps anyway
    if raw.startswith('```'):
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = raw.rstrip('`').strip()

    return json.loads(raw)


def process_message(user_message: str) -> dict:
    """
    Main entry point. Uses Claude if API key is present, else falls back to
    the rule-based parser. Always returns a dict with at least 'action'.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()

    if api_key:
        try:
            return _call_claude(user_message)
        except Exception as e:
            # Log but don't crash — fall back to rule parser
            import logging
            logging.getLogger(__name__).warning('Claude call failed: %s — using fallback parser', e)

    return fallback_parse(user_message)
