import os
import glob
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION")
CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Set Google credentials for Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

# Gemini model
model = GenerativeModel("gemini-2.5-flash")

# Directories
CALL_RECORDS_DIR = os.path.join("July", "Call Records")
TRANSCRIPTS_DIR = os.path.join("July", "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

# Prompt for transcription
def get_prompt():
    return (
        """
You are a transcription assistant. The following audio is a call recording between a client and a dealer discussing the Indian stock market. The client may be placing orders or discussing trades with the dealer.

Transcribe the conversation in a dialogue format, clearly mapping and labeling each speaker as either 'Client' or 'Dealer' for every utterance. If the speaker is unclear, make your best guess based on context. Do not summarize or omit any part of the conversation. Only output the transcript in the following format:

Client: <what the client says>
Dealer: <what the dealer says>
Client: <...>
Dealer: <...>
...and so on for the entire call.
"""
    )

# Find all .wav files in all subfolders
def find_audio_files():
    pattern = os.path.join(CALL_RECORDS_DIR, "Call_*", "*.wav")
    return glob.glob(pattern)

# Transcribe a single file
def transcribe_file(audio_path):
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    audio_content = Part.from_data(data=audio_bytes, mime_type="audio/wav")
    prompt = get_prompt()
    contents = [audio_content, prompt]
    response = model.generate_content(contents=contents)
    return response.text.strip()

# Main transcription loop
def main():
    audio_files = find_audio_files()
    for audio_path in audio_files:
        base = os.path.basename(audio_path)
        transcript_path = os.path.join(TRANSCRIPTS_DIR, base + ".txt")
        if os.path.exists(transcript_path):
            print(f"Transcript already exists for {base}, skipping.")
            continue
        print(f"Transcribing {base}...")
        try:
            transcript = transcribe_file(audio_path)
            with open(transcript_path, "w") as f:
                f.write(transcript)
            print(f"Saved transcript to {transcript_path}")
        except Exception as e:
            print(f"Failed to transcribe {base}: {e}")

if __name__ == "__main__":
    main()
