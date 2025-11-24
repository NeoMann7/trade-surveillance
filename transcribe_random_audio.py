#!/usr/bin/env python3
"""
Script to transcribe the audio file in the random directory using the same
transcription system as the trade surveillance system.
"""

import os
import glob
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai

def split_audio_file(audio_path, segment_duration=600):
    """
    Split long audio files into smaller segments for transcription
    segment_duration: duration in seconds (default 10 minutes)
    """
    import subprocess
    import os
    
    # Get audio duration
    try:
        duration_cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
        ]
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
    except:
        print(f"Could not determine duration of {audio_path}")
        return [audio_path]
    
    # If duration is less than segment_duration, return original file
    if duration <= segment_duration:
        return [audio_path]
    
    # Create segments directory
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    segments_dir = os.path.join(os.path.dirname(audio_path), f"{base_name}_segments")
    os.makedirs(segments_dir, exist_ok=True)
    
    segments = []
    num_segments = int(duration // segment_duration) + 1
    
    for i in range(num_segments):
        start_time = i * segment_duration
        segment_path = os.path.join(segments_dir, f"{base_name}_segment_{i+1:03d}.mp3")
        
        # Skip if segment already exists
        if os.path.exists(segment_path):
            segments.append(segment_path)
            continue
            
        cmd = [
            'ffmpeg', '-i', audio_path,
            '-ss', str(start_time),
            '-t', str(segment_duration),
            '-c', 'copy',
            '-y',  # Overwrite
            segment_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            segments.append(segment_path)
            print(f"Created segment {i+1}/{num_segments}: {segment_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating segment {i+1}: {e}")
            break
    
    return segments

def transcribe_audio_file(audio_path, model):
    """
    Transcribe a single audio file using the existing transcription logic
    """
    def get_prompt():
        return (
            """
You are a transcription assistant. The following audio may contain discussions about various topics.

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
        
        # Determine MIME type based on file extension
        if audio_path.lower().endswith('.mp3'):
            mime_type = "audio/mpeg"
        elif audio_path.lower().endswith('.wav'):
            mime_type = "audio/wav"
        elif audio_path.lower().endswith('.m4a'):
            mime_type = "audio/mp4"
        else:
            mime_type = "audio/mpeg"  # Default to mp3
        
        audio_content = Part.from_data(data=audio_bytes, mime_type=mime_type)
        prompt = get_prompt()
        contents = [audio_content, prompt]
        
        # Generate content with increased output token limit
        generation_config = {
            "max_output_tokens": 65535,  # Set to maximum output tokens
            "temperature": 0.1,  # Lower temperature for more consistent transcription
        }
        
        response = model.generate_content(
            contents=contents,
            generation_config=generation_config
        )
        
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
    
    # Audio directory
    audio_dir = "random"
    transcripts_dir = "random"
    
    # Create transcripts directory if it doesn't exist
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Find all audio files in the random directory
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.flac']
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(glob.glob(os.path.join(audio_dir, ext)))
    
    if not audio_files:
        print(f"No audio files found in {audio_dir}")
        return
    
    print(f"Found {len(audio_files)} audio files to process")
    
    # Process each audio file
    for audio_path in audio_files:
        audio_name = os.path.basename(audio_path)
        print(f"\n{'='*50}")
        print(f"Processing: {audio_name}")
        print(f"{'='*50}")
        
        # Create transcript filename
        base_name = os.path.splitext(audio_name)[0]
        transcript_path = os.path.join(transcripts_dir, f"{base_name}_transcript.txt")
        
        if os.path.exists(transcript_path):
            print(f"Transcript already exists for {base_name}, skipping transcription...")
            continue
        
        # Split audio file into segments if it's too long
        print(f"Checking if {base_name} needs to be split...")
        segments = split_audio_file(audio_path, segment_duration=600)  # 10-minute segments
        
        if len(segments) > 1:
            print(f"Audio file split into {len(segments)} segments")
            all_transcripts = []
            
            for i, segment_path in enumerate(segments):
                segment_name = os.path.basename(segment_path)
                print(f"Transcribing segment {i+1}/{len(segments)}: {segment_name}")
                
                transcript = transcribe_audio_file(segment_path, model)
                if transcript:
                    all_transcripts.append(f"\n--- Segment {i+1} ---\n{transcript}")
                    print(f"Segment {i+1} transcribed successfully")
                else:
                    print(f"Failed to transcribe segment {i+1}")
            
            # Combine all transcripts
            if all_transcripts:
                combined_transcript = "\n".join(all_transcripts)
                with open(transcript_path, "w", encoding='utf-8') as f:
                    f.write(combined_transcript)
                print(f"Complete transcript saved: {transcript_path}")
            else:
                print(f"Failed to transcribe any segments of {base_name}")
        else:
            # Single file transcription
            print(f"Transcribing {base_name}...")
            transcript = transcribe_audio_file(audio_path, model)
            
            if transcript:
                with open(transcript_path, "w", encoding='utf-8') as f:
                    f.write(transcript)
                print(f"Transcript saved: {transcript_path}")
            else:
                print(f"Failed to transcribe {base_name}")
    
    print(f"\n{'='*50}")
    print("Transcription completed!")
    print(f"Transcripts saved to: {transcripts_dir}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
