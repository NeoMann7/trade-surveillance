import json
from typing import Any, Dict, Optional

import openai
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # dotenv is optional; if not present, assume OPENAI_API_KEY is already set in env
    pass


def _parse_json_response(text: str) -> Dict[str, Any]:
    """
    Best-effort JSON parsing for model responses that are supposed to be JSON-only.
    Raises ValueError if parsing fails.
    """
    if text is None:
        raise ValueError("Empty AI response")
    text_stripped = text.strip()
    if not text_stripped:
        raise ValueError("Empty AI response")
    # Direct parse first
    try:
        return json.loads(text_stripped)
    except Exception:
        # Fallback: try to locate first JSON object
        start = text_stripped.find("{")
        end = text_stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text_stripped[start : end + 1]
            return json.loads(candidate)
        raise


def classify_email_gpt41(subject: str, sender: str, clean_text: str, attachment_info: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Stage 1: Classification using gpt-4.1 (per user request).
    Returns a dict: { ai_email_intent, ai_confidence_score, ai_reasoning }
    """
    client = openai.OpenAI()

    prompt = f"""
ROLE
You are an expert financial email analyst. Classify whether the email contains NEW trade instructions. Output JSON only.

INPUT
Subject: {subject}
Sender: {sender}
Body: {clean_text}
Attachments: {attachment_info}

DEFINITIONS
Trade instruction = any NEW request to execute a trade (buy/sell), including:
• Direct requests ("please/ kindly execute", "place & execute", "buy/sell …")
• Requests including client codes (patterns like NEOWM/NEOC/NEO + digits/letters)
• Requests specifying symbol/script, quantity, price, side
• Approval/authorization to execute
• Forwarded (FW/Fwd) or reply (RE/Re) threads that contain such requests
• Instructions inside attachments (tables, order lists)

NOT trade instructions:
• Confirmations or contract notes of already executed trades
• Admin/ops notices, settlements, debit lists, market commentary, general queries

CLASSIFICATION (exactly one)
ai_email_intent ∈ {"trade_instruction","trade_confirmation","other"}

OUTPUT (JSON ONLY)
{{
  "ai_email_intent": "trade_instruction" | "trade_confirmation" | "other",
  "ai_confidence_score": "0-100 integer as string",
  "ai_reasoning": "≤30 words"
}}

REQUIRED CONSTRAINTS
• Return valid JSON ONLY. No markdown, no additional fields.
"""

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert financial compliance analyst."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            return _parse_json_response(content)
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                raise
    # Should not reach here
    raise RuntimeError(f"Classification failed: {last_error}")


def extract_instructions_o3(subject: str, sender: str, clean_text: str, attachment_info: str, max_retries: int = 1) -> Dict[str, Any]:
    """
    Stage 2: Extraction using o3 (per user request), with the user's updated prompt.
    Returns a dict following the specified OUTPUT FORMAT.
    """
    client = openai.OpenAI()

    prompt = f"""
ROLE
You are an expert financial email analyst. Extract every trade instruction found in the email body and any provided attachment text. Output JSON only (no prose, no markdown).

INPUT
Subject: {subject}
Sender: {sender}
Body: {clean_text}
Attachments: {attachment_info}

ASSUMPTION
The email has already been classified as "trade_instruction". Do not re-classify.

EXTRACTION RULES
1) Parse body and attachments. If table(s) exist, treat each data row as a separate instruction.
2) Column/term synonyms:
   • Client Code → Account / Client / Code (patterns like NEOWM\\d+, NEOC\\d+, NEO[A-Z0-9]+)
   • Symbol → Script / Scrip / Ticker / Instrument
   • Quantity → Qty / QTY / Quantity
   • Price → Price / LTP / Market Price / Limit Price
   • Side → Buy/Sell / B/S / Action / Side
3) Normalize values:
   • BUY/SELL uppercase
   • Remove thousand separators: "74,000" → "74000"
   • Keep decimals as-is (e.g., "548.85")
   • Extract only explicit order_time strings if clearly stated (do not infer)
4) Ignore any section that looks like a trade confirmation/contract note (executed trades).
5) Same client/symbol appearing in distinct rows (different qty/price/side) = multiple instructions.
6) If attachments exist but no parsable instruction text was provided, do not guess.

INSTRUCTION TYPE HEURISTICS
ai_instruction_type ∈ {"rm_forwarded","client_direct","unknown"}

OUTPUT FORMAT (JSON ONLY)
{{
  "ai_email_intent": "trade_instruction",
  "ai_confidence_score": "0-100 integer as string",
  "ai_reasoning": "≤30 words explaining the extraction basis.",
  "ai_order_details": [
    {{
      "client_code": "string or null",
      "symbol": "string or null",
      "quantity": "string or null",
      "price": "string or null",
      "buy_sell": "BUY" | "SELL" | null,
      "order_time": "string or null"
    }}
  ],
  "ai_instruction_type": "rm_forwarded" | "client_direct" | "unknown"
}}

REQUIRED CONSTRAINTS
• ai_order_details MUST be a non-empty array (one object per instruction).
• Return valid JSON ONLY. No markdown, no comments, no additional fields.
• Use ONLY values present in the provided inputs; do not infer missing data.
"""

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "system", "content": "You are an expert financial compliance analyst."},
                    {"role": "user", "content": prompt},
                ]
            )
            content = response.choices[0].message.content
            data = _parse_json_response(content)

            # Guardrails: enforce array for ai_order_details only when intent == trade_instruction
            intent = (data.get("ai_email_intent") or "").strip()
            if intent == "trade_instruction":
                ai_order_details = data.get("ai_order_details")
                if isinstance(ai_order_details, dict):
                    data["ai_order_details"] = [ai_order_details]
                elif not isinstance(ai_order_details, list) or len(ai_order_details) == 0:
                    data["ai_order_details"] = []
            else:
                data["ai_order_details"] = None
                data["ai_instruction_type"] = None

            return data
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                raise
    # Should not reach here
    raise RuntimeError(f"Extraction failed: {last_error}")


def analyze_email_two_stage(subject: str, sender: str, clean_text: str, attachment_info: str) -> Dict[str, Any]:
    """
    Public entrypoint: two-stage analysis where classification uses gpt-4.1 and
    extraction uses o3. The final merged structure mirrors the extraction schema.
    """
    classification = classify_email_gpt41(subject, sender, clean_text, attachment_info)

    final: Dict[str, Any] = {
        "ai_email_intent": classification.get("ai_email_intent"),
        "ai_confidence_score": classification.get("ai_confidence_score"),
        "ai_reasoning": classification.get("ai_reasoning"),
        "ai_order_details": None,
        "ai_instruction_type": None,
    }

    if final["ai_email_intent"] == "trade_instruction":
        extraction = extract_instructions_o3(subject, sender, clean_text, attachment_info)
        # Merge, preferring extraction fields for orders and instruction type, but
        # keeping classification confidence/reasoning.
        final["ai_order_details"] = extraction.get("ai_order_details")
        final["ai_instruction_type"] = extraction.get("ai_instruction_type")
        # Optionally reconcile intent if extractor disagrees; we keep classifier's.

    return final


