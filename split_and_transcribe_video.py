#!/usr/bin/env python3
"""
Script to split a video into 3 equal parts and transcribe each part, then combine the transcripts.
"""

import os
import subprocess
import glob
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai

def get_video_duration(video_path):
    """
    Get the duration of a video file using ffprobe
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0',
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting video duration: {e}")
        return None

def split_video_into_three_parts(video_path, output_dir="video_segments"):
    """
    Split video into 3 equal parts using ffmpeg
    Returns list of paths to the split video files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video duration
    duration = get_video_duration(video_path)
    if duration is None:
        print("Could not determine video duration")
        return None
    
    print(f"Video duration: {duration:.2f} seconds")
    
    # Calculate split points
    part_duration = duration / 3
    print(f"Each part will be approximately {part_duration:.2f} seconds")
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    split_files = []
    
    for i in range(3):
        start_time = i * part_duration
        output_path = os.path.join(output_dir, f"{base_name}_part_{i+1}.mp4")
        
        # Check if file already exists
        if os.path.exists(output_path):
            print(f"Part {i+1} already exists, skipping...")
            split_files.append(output_path)
            continue
        
        # FFmpeg command to split video
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(part_duration),
            '-c', 'copy',  # Copy without re-encoding for speed
            '-y',  # Overwrite output file
            output_path
        ]
        
        try:
            print(f"Splitting part {i+1} (from {start_time:.2f}s to {start_time + part_duration:.2f}s)...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Part {i+1} saved: {output_path}")
            split_files.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"Error splitting part {i+1}: {e}")
            print(f"FFmpeg stderr: {e.stderr}")
            return None
    
    return split_files

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

def transcribe_audio_file(audio_path, model, part_number=None):
    """
    Transcribe a single audio file using the existing transcription logic
    """
    def get_prompt():
        part_info = f" (Part {part_number})" if part_number else ""
        return (
            f"""
You are a transcription assistant. The following audio is a video recording{part_info} that may contain discussions about trading, investments, or financial topics.

Transcribe the conversation in a dialogue format, clearly mapping and labeling each speaker. If there are multiple speakers, label them as 'Speaker 1', 'Speaker 2', etc. If the speaker is unclear, make your best guess based on context. Do not summarize or omit any part of the conversation. Only output the transcript in the following format:

Speaker 1: <what the speaker says>
Speaker 2: <what the other speaker says>
Speaker 1: <...>
...and so on for the entire recording.

If there's only one speaker, label them as 'Speaker'.

Note: This is part {part_number} of a longer video, so the conversation may start or end mid-sentence.
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

def combine_transcripts(transcripts, output_path):
    """
    Combine multiple transcripts into one file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("COMBINED VIDEO TRANSCRIPT\n")
        f.write("=" * 80 + "\n\n")
        
        for i, transcript in enumerate(transcripts, 1):
            f.write(f"PART {i}:\n")
            f.write("-" * 40 + "\n")
            f.write(transcript)
            f.write("\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF COMBINED TRANSCRIPT\n")
        f.write("=" * 80 + "\n")

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
    video_segments_dir = "video_segments"
    audio_output_dir = "extracted_audio"
    transcripts_dir = "video_transcripts"
    
    # Create directories
    os.makedirs(video_segments_dir, exist_ok=True)
    os.makedirs(audio_output_dir, exist_ok=True)
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Find video files
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.flv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(video_dir, ext)))
    
    if not video_files:
        print(f"No video files found in {video_dir}")
        return
    
    # Process each video file
    for video_path in video_files:
        video_name = os.path.basename(video_path)
        base_name = os.path.splitext(video_name)[0]
        
        print(f"\n{'='*60}")
        print(f"Processing: {video_name}")
        print(f"{'='*60}")
        
        # Step 1: Split video into 3 parts
        print("\n1. Splitting video into 3 parts...")
        split_files = split_video_into_three_parts(video_path, video_segments_dir)
        if not split_files:
            print(f"Failed to split {video_name}")
            continue
        
        # Step 2: Extract audio from each part and transcribe
        print("\n2. Extracting audio and transcribing each part...")
        transcripts = []
        
        for i, part_video_path in enumerate(split_files, 1):
            print(f"\n--- Processing Part {i} ---")
            
            # Extract audio
            audio_path = extract_audio_from_video(part_video_path, audio_output_dir)
            if not audio_path:
                print(f"Failed to extract audio from part {i}")
                continue
            
            # Transcribe audio
            print(f"Transcribing part {i}...")
            transcript = transcribe_audio_file(audio_path, model, part_number=i)
            
            if transcript:
                transcripts.append(transcript)
                print(f"Part {i} transcribed successfully")
            else:
                print(f"Failed to transcribe part {i}")
        
        # Step 3: Combine transcripts
        if transcripts:
            print(f"\n3. Combining {len(transcripts)} transcripts...")
            combined_transcript_path = os.path.join(transcripts_dir, f"{base_name}_combined_transcript.txt")
            combine_transcripts(transcripts, combined_transcript_path)
            print(f"Combined transcript saved: {combined_transcript_path}")
            
            # Also save individual part transcripts
            for i, transcript in enumerate(transcripts, 1):
                part_transcript_path = os.path.join(transcripts_dir, f"{base_name}_part_{i}_transcript.txt")
                with open(part_transcript_path, 'w', encoding='utf-8') as f:
                    f.write(f"PART {i} TRANSCRIPT\n")
                    f.write("-" * 40 + "\n")
                    f.write(transcript)
                print(f"Part {i} transcript saved: {part_transcript_path}")
        else:
            print("No transcripts were generated")
    
    print(f"\n{'='*60}")
    print("Processing completed!")
    print(f"Video segments saved to: {video_segments_dir}")
    print(f"Audio files extracted to: {audio_output_dir}")
    print(f"Transcripts saved to: {transcripts_dir}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()


