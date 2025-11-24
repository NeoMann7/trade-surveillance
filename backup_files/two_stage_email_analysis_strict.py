import json
from typing import Any, Dict, Optional

import openai
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def _parse_json_response(text: str) -> Dict[str, Any]:
    if text is None:
        raise ValueError("Empty AI response")
    text_stripped = text.strip()
    if not text_stripped:
        raise ValueError("Empty AI response")
    try:
        return json.loads(text_stripped)
    except Exception:
        start = text_stripped.find("{")
        end = text_stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text_stripped[start : end + 1]
            return json.loads(candidate)
        raise


def classify_email_gpt41_strict(subject: str, sender: str, clean_text: str, attachment_info: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Strict classifier (duplicate) with:
    - Subject gate: Only allow trade_confirmation if subject contains 'Trade Confirmation' (case-insensitive)
    - Instruction precedence: If ANY new instructions exist anywhere in thread, classify as trade_instruction
    - Instruction cues and table handling
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

CLASSIFICATION POLICY (STRICT)
1) SUBJECT GATE for confirmations:
   • Only classify as trade_confirmation if the Subject contains 'Trade Confirmation' (case-insensitive).
   • Otherwise, do NOT return trade_confirmation even if the body includes executed trade details.

2) INSTRUCTION PRECEDENCE:
   • If ANY part of the thread (body or attachments) contains NEW instructions, classify as trade_instruction.
   • NEW instructions include any of: buy/sell requests; approvals to execute; RM forwards to dealing desk asking to execute; structured order tables to be executed.

3) INSTRUCTION CUES:
   • Strong signals: phrases like 'please execute', 'kindly execute', 'approve/approval to execute', 'as per client instruction', 'kindly process';
     RM forwarding to dealing desk; presence of a structured table with columns such as client/script/qty/price/side/date/expiry.

4) TABLE HANDLING:
   • If a table with prospective orders (client/script/qty/price/side, price bands, GTC/Open-until-filled) is present, treat as trade_instruction.

5) FALLBACK:
   • If the subject does NOT contain 'Trade Confirmation' and no NEW instructions are detected, classify as 'other'.

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
    raise RuntimeError(f"Strict classification failed: {last_error}")


def analyze_email_two_stage_strict(subject: str, sender: str, clean_text: str, attachment_info: str) -> Dict[str, Any]:
    """
    Two-stage analysis using the strict classifier and the existing extractor (o3).
    """
    # Import extractor from the original two_stage module to avoid duplication
    from two_stage_email_analysis import extract_instructions_o3  # type: ignore

    classification = classify_email_gpt41_strict(subject, sender, clean_text, attachment_info)

    final: Dict[str, Any] = {
        "ai_email_intent": classification.get("ai_email_intent"),
        "ai_confidence_score": classification.get("ai_confidence_score"),
        "ai_reasoning": classification.get("ai_reasoning"),
        "ai_order_details": None,
        "ai_instruction_type": None,
    }

    if final["ai_email_intent"] == "trade_instruction":
        extraction = extract_instructions_o3(subject, sender, clean_text, attachment_info)
        final["ai_order_details"] = extraction.get("ai_order_details")
        final["ai_instruction_type"] = extraction.get("ai_instruction_type")

    return final


