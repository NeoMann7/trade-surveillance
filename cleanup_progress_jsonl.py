import json

input_file = "order_transcript_analysis_progress_all_dates.jsonl"
output_file = "order_transcript_analysis_progress_all_dates.cleaned.jsonl"

seen_no_audio = set()
with open(input_file, "r") as fin, open(output_file, "w") as fout:
    for line in fin:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue
        order_id = data.get("order_id")
        audio_mapped = data.get("audio_mapped")
        if audio_mapped == "yes":
            fout.write(json.dumps(data, ensure_ascii=False) + "\n")
        elif audio_mapped == "no":
            if order_id not in seen_no_audio:
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                seen_no_audio.add(order_id) 