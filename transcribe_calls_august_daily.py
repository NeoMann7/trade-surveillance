import os
import glob
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai
from audio_utils import get_audio_file_for_processing, cleanup_converted_file

def transcribe_calls_for_date(date_str):
    """
    Transcribe audio calls for a specific date in August using Google Vertex AI
    date_str format: '01082025' for August 1st, 2025
    """
    
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
    
    # Determine month and set paths accordingly
    month = int(date_str[2:4])
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    if month not in month_names:
        print(f"❌ Invalid month: {month}")
        return None
    
    month_name = month_names[month]
    
    # Define paths based on month
    call_records_path = f"{month_name}/Call Records/Call_{date_str}"
    transcripts_path = f"{month_name}/Daily_Reports/{date_str}/transcripts_{date_str}"
    
    # Create transcripts directory if it doesn't exist
    os.makedirs(transcripts_path, exist_ok=True)
    
    # Check if call records directory exists
    if not os.path.exists(call_records_path):
        print(f"Call records directory not found: {call_records_path}")
        return None
    
    # Get all audio files for the specific date (including .729 files)
    audio_files = (
        glob.glob(os.path.join(call_records_path, "*.wav")) + 
        glob.glob(os.path.join(call_records_path, "*.mp3")) +
        glob.glob(os.path.join(call_records_path, "*.729"))
    )
    
    if not audio_files:
        print(f"No audio files found in {call_records_path}")
        return None
    
    print(f"Found {len(audio_files)} audio files for {date_str}")
    
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
    
    # Transcribe a single file
    def transcribe_file(audio_path):
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_content = Part.from_data(data=audio_bytes, mime_type="audio/wav")
        prompt = get_prompt()
        contents = [audio_content, prompt]
        response = model.generate_content(contents=contents)
        return response.text.strip()
    
    # Process each audio file
    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        transcript_file = os.path.join(transcripts_path, filename + ".txt")
        
        # Skip if transcript already exists
        if os.path.exists(transcript_file):
            print(f"Transcript already exists for {filename}, skipping...")
            continue
        
        print(f"Transcribing {filename}...")
        
        # Convert .729 files to WAV if needed
        converted_file = None
        try:
            processing_file = get_audio_file_for_processing(audio_file, convert_to_wav=True)
            if processing_file != audio_file:
                converted_file = processing_file
                print(f"  Converted .729 file to WAV: {os.path.basename(converted_file)}")
            
            transcript = transcribe_file(processing_file)
            with open(transcript_file, "w", encoding='utf-8') as f:
                f.write(transcript)
            print(f"  Transcript saved: {transcript_file}")
            
        except Exception as e:
            print(f"  Error transcribing {filename}: {e}")
            continue
        finally:
            # Clean up converted file if it was created
            if converted_file and converted_file != audio_file:
                cleanup_converted_file(converted_file)
    
    print(f"Transcription completed for {date_str}")
    return transcripts_path

if __name__ == "__main__":
    import sys
    
    # Get date from command line argument or use default
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        # Default date (August 7th, 2025)
        date_str = "07082025"
    
    result = transcribe_calls_for_date(date_str)
    if result:
        print(f"Successfully processed {date_str}")
    else:
        print(f"Failed to process {date_str}")
        sys.exit(1) 