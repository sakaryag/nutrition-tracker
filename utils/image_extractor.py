"""
image_extractor.py — Claude Vision extraction for printed diet sheets.

Reads an image file, sends it to Anthropic Claude with a structured-output
prompt, and returns a dict matching the ProgramDay/MealSlot/SlotItem schema.

Returns:
  {
    "plan_name": str | None,
    "duration_days": int,
    "days": [
      {
        "day_offset": int,          # 0-based
        "label": str | None,        # e.g. "Monday" or "Day 1"
        "label_tr": str | None,
        "notes": str | None,
        "slots": [
          {
            "slot_name": str,        # e.g. "Breakfast"
            "slot_name_tr": str | None,
            "content_pattern": str | None,  # A-F
            "is_optional": bool,
            "items": [
              {
                "food_name": str,
                "food_name_tr": str | None,
                "quantity": float | None,
                "unit": str | None,   # g/ml/piece/slice/serving
                "notes": str | None
              }
            ]
          }
        ]
      }
    ]
  }

Raises RuntimeError on any unrecoverable failure.
"""
import base64
import json
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """\
You are a clinical dietitian assistant. You will be given an image of a printed or handwritten diet / meal plan sheet.

Your task is to extract the complete meal plan structure from the image and return ONLY a JSON object — no prose, no markdown fences, no extra keys.

JSON schema (strictly follow this):
{
  "plan_name": "<name of the plan, or null>",
  "duration_days": <total number of days as integer>,
  "days": [
    {
      "day_offset": <0-based index>,
      "label": "<human label e.g. Monday / Day 1 / Gün 1, or null>",
      "label_tr": "<Turkish label if present, or null>",
      "notes": "<any day-level note, or null>",
      "slots": [
        {
          "slot_name": "<meal name e.g. Breakfast / Lunch / Snack 1>",
          "slot_name_tr": "<Turkish meal name if present, or null>",
          "content_pattern": "<A if fixed foods, B if exchange group, null otherwise>",
          "is_optional": false,
          "items": [
            {
              "food_name": "<exact food name from sheet>",
              "food_name_tr": "<Turkish food name if present, or null>",
              "quantity": <number or null>,
              "unit": "<g or ml or piece or slice or serving or null>",
              "notes": "<preparation note, or null>"
            }
          ]
        }
      ]
    }
  ]
}

Rules:
- Keep food names exactly as printed (Turkish or English).
- If quantities are given per 100g, use 100 as quantity and "g" as unit.
- If a piece count is given (e.g. "2 eggs"), use quantity=2 and unit="piece".
- If the sheet is completely empty or unreadable, return {"plan_name":null,"duration_days":0,"days":[]}.
- IMPORTANT: Return ONLY the JSON object. No other text.
"""

SUPPORTED_MIME_TYPES = {
    'image/jpeg': 'image/jpeg',
    'image/jpg':  'image/jpeg',
    'image/png':  'image/png',
    'image/gif':  'image/gif',
    'image/webp': 'image/webp',
    'application/pdf': None,  # not directly supported as vision input
}


def extract_diet_plan(file_path: str, mime_type: str, model: str | None = None) -> dict:
    """
    Extract diet plan structure from an image using Claude Vision.

    Args:
        file_path: Absolute path to the saved image file.
        mime_type: MIME type of the file (e.g. 'image/jpeg').
        model: Claude model to use. Defaults to claude-haiku-4-5 for cost efficiency.

    Returns:
        Parsed dict matching the schema above.

    Raises:
        RuntimeError: if extraction fails or API key is missing.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('ANTHROPIC_API_KEY is not set — cannot run image extraction')

    try:
        import anthropic
    except ImportError:
        raise RuntimeError('anthropic package not installed. Run: pip install anthropic')

    # Normalise MIME
    media_type = SUPPORTED_MIME_TYPES.get(mime_type)
    if media_type is None:
        raise RuntimeError(f'Unsupported image type for Vision API: {mime_type}')

    # Read and base64-encode the file
    path = Path(file_path)
    if not path.exists():
        raise RuntimeError(f'Image file not found: {file_path}')

    raw_bytes = path.read_bytes()
    b64_data = base64.standard_b64encode(raw_bytes).decode('ascii')

    target_model = model or 'claude-haiku-4-5-20251001'
    client = anthropic.Anthropic(api_key=api_key)

    log.info('Starting diet sheet extraction with model=%s file=%s', target_model, path.name)

    message = client.messages.create(
        model=target_model,
        max_tokens=4096,
        messages=[
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': b64_data,
                        },
                    },
                    {
                        'type': 'text',
                        'text': _EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text.strip()
    log.info('Extraction raw response length: %d chars', len(raw_text))

    # Strip accidental markdown fences
    if raw_text.startswith('```'):
        import re
        raw_text = re.sub(r'^```[a-z]*\n?', '', raw_text, flags=re.MULTILINE)
        raw_text = raw_text.rstrip('`').strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'Claude returned non-JSON response: {exc}\nRaw: {raw_text[:500]}')

    _validate_structure(result)
    return result


def _validate_structure(data: dict) -> None:
    """Minimal validation — raise if the top-level shape is wrong."""
    if not isinstance(data, dict):
        raise RuntimeError('Extraction result is not a JSON object')
    if 'days' not in data:
        raise RuntimeError('Extraction result missing "days" key')
    if not isinstance(data['days'], list):
        raise RuntimeError('"days" must be a list')
    # Normalise optional fields
    data.setdefault('plan_name', None)
    data.setdefault('duration_days', len(data['days']))
    for i, day in enumerate(data['days']):
        if not isinstance(day, dict):
            continue
        day.setdefault('day_offset', i)
        day.setdefault('label', None)
        day.setdefault('label_tr', None)
        day.setdefault('notes', None)
        day.setdefault('slots', [])
        for slot in day['slots']:
            if not isinstance(slot, dict):
                continue
            slot.setdefault('slot_name', 'Slot')
            slot.setdefault('slot_name_tr', None)
            slot.setdefault('content_pattern', None)
            slot.setdefault('is_optional', False)
            slot.setdefault('items', [])
            for item in slot['items']:
                if not isinstance(item, dict):
                    continue
                item.setdefault('food_name', 'Unknown food')
                item.setdefault('food_name_tr', None)
                item.setdefault('quantity', None)
                item.setdefault('unit', 'g')
                item.setdefault('notes', None)
