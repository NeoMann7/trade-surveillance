#!/usr/bin/env python3
"""
Script to extract audio from video files and transcribe them using existing transcription code.
"""

import os
import subprocess
import glob
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai

def extract_audio_from_video(video_path, output_dir="extracted_audio"):
    """
    Extract audio from video file using ffmpeg
    Returns the path to the extracted audio file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename without extension
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_output_path = os.path.join(output_dir, f"{base_name}.wav")
    
    # Check if audio already exists
    if os.path.exists(audio_output_path):
        print(f"Audio already extracted for {base_name}, skipping extraction...")
        return audio_output_path
    
    # FFmpeg command to extract audio
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # PCM 16-bit
        '-ar', '16000',  # Sample rate 16kHz
        '-ac', '1',  # Mono audio
        '-y',  # Overwrite output file
        audio_output_path
    ]
    
    try:
        print(f"Extracting audio from {os.path.basename(video_path)}...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Audio extracted successfully: {audio_output_path}")
        return audio_output_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio from {video_path}: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg first.")
        print("On macOS: brew install ffmpeg")
        print("On Ubuntu: sudo apt install ffmpeg")
        return None

def transcribe_audio_file(audio_path, model):
    """
    Transcribe a single audio file using the existing transcription logic
    """
    def get_prompt():
        return (
            """
You are a transcription assistant. The following audio is a video recording that may contain discussions about trading, investments, or financial topics.

Transcribe the conversation in a dialogue format, clearly mapping and labeling each speaker. If there are multiple speakers, label them as 'Speaker 1', 'Speaker 2', etc. If the speaker is unclear, make your best guess based on context. Do not summarize or omit any part of the conversation. Only output the transcript in the following format:

Speaker 1: <what the speaker says>
Speaker 2: <what the other speaker says>
Speaker 1: <...>
...and so on for the entire recording.

If there's only one speaker, label them as 'Speaker'.
"""
        )
    
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_content = Part.from_data(data=audio_bytes, mime_type="audio/wav")
        prompt = get_prompt()
        contents = [audio_content, prompt]
        response = model.generate_content(contents=contents)
        
        # Handle multiple content parts if they exist
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                # Get the first text part
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        return part.text.strip()
        
        # Fallback to the standard method
        return response.text.strip()
    except Exception as e:
        print(f"Error transcribing {audio_path}: {e}")
        return None

def main():
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
    
    # Video directory
    video_dir = "audios_to_transcribe"
    audio_output_dir = "extracted_audio"
    transcripts_dir = "video_transcripts"
    
    # Create directories
    os.makedirs(audio_output_dir, exist_ok=True)
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Find all video files
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.flv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(video_dir, ext)))
    
    if not video_files:
        print(f"No video files found in {video_dir}")
        return
    
    print(f"Found {len(video_files)} video files to process")
    
    # Process each video file
    for video_path in video_files:
        video_name = os.path.basename(video_path)
        print(f"\n{'='*50}")
        print(f"Processing: {video_name}")
        print(f"{'='*50}")
        
        # Step 1: Extract audio
        audio_path = extract_audio_from_video(video_path, audio_output_dir)
        if not audio_path:
            print(f"Skipping {video_name} due to extraction error")
            continue
        
        # Step 2: Transcribe audio
        base_name = os.path.splitext(video_name)[0]
        transcript_path = os.path.join(transcripts_dir, f"{base_name}_transcript.txt")
        
        if os.path.exists(transcript_path):
            print(f"Transcript already exists for {base_name}, skipping transcription...")
            continue
        
        print(f"Transcribing {base_name}...")
        transcript = transcribe_audio_file(audio_path, model)
        
        if transcript:
            with open(transcript_path, "w", encoding='utf-8') as f:
                f.write(transcript)
            print(f"Transcript saved: {transcript_path}")
        else:
            print(f"Failed to transcribe {base_name}")
    
    print(f"\n{'='*50}")
    print("Processing completed!")
    print(f"Audio files extracted to: {audio_output_dir}")
    print(f"Transcripts saved to: {transcripts_dir}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
