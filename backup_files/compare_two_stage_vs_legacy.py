import json
import os
from typing import Any, Dict, List

from two_stage_email_analysis import analyze_email_two_stage


INPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "email_surveillance_20250922.json"))
OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "email_surveillance_two_stage_20250922.json"))


def build_attachment_info(attachments: List[Dict[str, Any]]) -> str:
    if not attachments:
        return ""
    parts: List[str] = []
    for i, att in enumerate(attachments, start=1):
        name = att.get("name") or att.get("file_name") or "Unknown"
        parts.append(f"Attachment {i}: {name}")
        extracted = att.get("extracted_text")
        if extracted:
            parts.append(f"Content:\n{extracted}")
    return "\n".join(parts)


def main() -> None:
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    emails: List[Dict[str, Any]] = []
    if isinstance(data, list):
        emails = data
    else:
        # Newer structure: categories with nested emails arrays
        for key in ("trade_instructions", "trade_confirmations", "other"):
            section = data.get(key)
            if isinstance(section, dict):
                arr = section.get("emails")
                if isinstance(arr, list):
                    emails.extend(arr)
        # Fallbacks
        if not emails:
            top = data.get("emails") or data.get("results")
            if isinstance(top, list):
                emails = top
    if not isinstance(emails, list) or not emails:
        print("No emails found in legacy file; nothing to compare.")
        with open(OUTPUT_FILE, "w") as f:
            json.dump([], f)
        print(f"Two-stage results saved to: {OUTPUT_FILE}")
        return

    new_results: List[Dict[str, Any]] = []

    for idx, item in enumerate(emails, start=1):
        subject = item.get("subject", "")
        sender = item.get("sender", "")
        clean_text = item.get("clean_text", "")
        attachments = item.get("attachments", [])
        attachment_info = build_attachment_info(attachments)

        two_stage = analyze_email_two_stage(subject, sender, clean_text, attachment_info)

        new_results.append({
            "subject": subject,
            "sender": sender,
            "two_stage_analysis": two_stage,
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(new_results, f, ensure_ascii=False, indent=2)

    # Quick comparison summary vs legacy
    legacy_intents = { (item.get("subject", ""), item.get("sender", "")) : (item.get("ai_analysis") or {}).get("ai_email_intent") for item in emails }
    two_stage_intents = { (r["subject"], r["sender"]) : r["two_stage_analysis"].get("ai_email_intent") for r in new_results }

    changed = []
    for key, legacy_intent in legacy_intents.items():
        two_intent = two_stage_intents.get(key)
        if legacy_intent != two_intent:
            changed.append((key, legacy_intent, two_intent))

    print("\n=== Comparison Summary (Legacy vs Two-Stage) ===")
    print(f"Total emails compared: {len(emails)}")
    print(f"Intent changes: {len(changed)}")
    if changed:
        print("Changed intents (subject | sender | legacy -> two-stage):")
        for (subject, sender), old_i, new_i in changed[:20]:
            print(f"- {subject} | {sender} | {old_i} -> {new_i}")
        if len(changed) > 20:
            print(f"... and {len(changed) - 20} more")
    print(f"\nTwo-stage results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


