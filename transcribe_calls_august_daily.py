import os
import glob
import warnings
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Part
import vertexai
from audio_utils import get_audio_file_for_processing, cleanup_converted_file

# Import S3 utilities if available
try:
    import sys
    sys.path.insert(0, '/app')
    from s3_utils import (
        list_s3_objects, s3_file_exists, read_text_from_s3,
        upload_file_to_s3, get_s3_key
    )
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

# Suppress deprecation warnings from Vertex AI SDK
warnings.filterwarnings('ignore', category=UserWarning, module='vertexai')

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
    
    # Set Google credentials for Vertex AI (only if provided)
    if CREDENTIALS:
        # Check if it's a file path or already set
        if os.path.exists(CREDENTIALS):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS
            print(f"✅ Using Google credentials from: {CREDENTIALS}")
        else:
            print(f"⚠️ Credentials file not found: {CREDENTIALS}")
    elif not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        # Try default location in Docker
        default_key = "/app/key2.json"
        if os.path.exists(default_key):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key
            print(f"✅ Using default credentials file: {default_key}")
        else:
            print("⚠️ GOOGLE_APPLICATION_CREDENTIALS not set, using Application Default Credentials")
    
    # Validate required environment variables
    if not PROJECT_ID:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
    if not REGION:
        raise ValueError("GOOGLE_CLOUD_LOCATION environment variable is required")
    
    # Initialize Vertex AI
    try:
        vertexai.init(project=PROJECT_ID, location=REGION)
        print(f"✅ Vertex AI initialized with project: {PROJECT_ID}, location: {REGION}")
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        raise
    
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
    
    # Check if using S3
    USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')
    
    # Define paths based on month
    call_records_path = f"{month_name}/Call Records/Call_{date_str}"
    transcripts_path = f"{month_name}/Daily_Reports/{date_str}/transcripts_{date_str}"
    
    # Get audio files from S3 or local filesystem
    audio_files = []
    temp_files = []  # Track downloaded files for cleanup
    
    if USE_S3 and S3_AVAILABLE and S3_BUCKET_NAME:
        print(f"📦 Using S3 for audio files: {S3_BUCKET_NAME}")
        # List audio files from S3
        s3_prefix = f"{S3_BASE_PREFIX}/{call_records_path}/"
        print(f"🔍 Searching S3: s3://{S3_BUCKET_NAME}/{s3_prefix}")
        
        try:
            import boto3
            s3_client = boto3.client('s3', 
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'ap-south-1'))
            
            # List objects in S3
            response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=s3_prefix)
            if 'Contents' in response:
                # Filter for audio files
                audio_extensions = ['.wav', '.mp3', '.729']
                for obj in response['Contents']:
                    key = obj['Key']
                    if any(key.lower().endswith(ext) for ext in audio_extensions):
                        # Download to temp file for processing
                        temp_dir = tempfile.mkdtemp()
                        filename = os.path.basename(key)
                        temp_path = os.path.join(temp_dir, filename)
                        
                        # Download from S3
                        s3_client.download_file(S3_BUCKET_NAME, key, temp_path)
                        audio_files.append(temp_path)
                        temp_files.append((temp_path, temp_dir))
                        print(f"  ✅ Downloaded: {filename}")
            
            if not audio_files:
                print(f"⚠️ No audio files found in S3: {s3_prefix}")
                print(f"ℹ️ This date may not have any call recordings, or files may not be uploaded yet")
                # Return success but with no files processed (don't fail the step)
                return transcripts_path if not USE_S3 else None
        except Exception as e:
            print(f"❌ Error accessing S3: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        # Local filesystem
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
            print(f"⚠️ No audio files found in {call_records_path}")
            print(f"ℹ️ This date may not have any call recordings")
            # Return success but with no files processed (don't fail the step)
            return transcripts_path
    
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
    
    # Process a single audio file (worker function for parallel processing)
    def process_audio_file(audio_file):
        filename = os.path.basename(audio_file)
        
        # Determine transcript file path (local or S3)
        if USE_S3 and S3_AVAILABLE and S3_BUCKET_NAME:
            transcript_s3_key = f"{S3_BASE_PREFIX}/{transcripts_path}/{filename}.txt"
            # Check if transcript already exists in S3
            try:
                import boto3
                s3_client = boto3.client('s3', 
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'ap-south-1'))
                s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=transcript_s3_key)
                print(f"Transcript already exists in S3 for {filename}, skipping...")
                return
            except:
                pass  # File doesn't exist, continue
            transcript_file = os.path.join(tempfile.gettempdir(), f"{filename}.txt")
        else:
            transcript_file = os.path.join(transcripts_path, filename + ".txt")
            # Skip if transcript already exists
            if os.path.exists(transcript_file):
                print(f"Transcript already exists for {filename}, skipping...")
                return
        
        print(f"Transcribing {filename}...")
        
        # Convert .729 files to WAV if needed
        converted_file = None
        try:
            processing_file = get_audio_file_for_processing(audio_file, convert_to_wav=True)
            if processing_file != audio_file:
                converted_file = processing_file
                print(f"  Converted .729 file to WAV: {os.path.basename(converted_file)}")
            
            transcript = transcribe_file(processing_file)
            
            # Save transcript locally first
            with open(transcript_file, "w", encoding='utf-8') as f:
                f.write(transcript)
            
            # Upload to S3 if using S3
            if USE_S3 and S3_AVAILABLE and S3_BUCKET_NAME:
                try:
                    import boto3
                    s3_client = boto3.client('s3', 
                        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                        region_name=os.getenv('AWS_REGION', 'ap-south-1'))
                    s3_client.upload_file(transcript_file, S3_BUCKET_NAME, transcript_s3_key)
                    print(f"  Transcript uploaded to S3: {transcript_s3_key}")
                    # Clean up local temp file
                    os.remove(transcript_file)
                except Exception as e:
                    print(f"  ⚠️ Failed to upload transcript to S3: {e}")
            else:
                print(f"  Transcript saved: {transcript_file}")
            
        except Exception as e:
            print(f"  Error transcribing {filename}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up converted file if it was created
            if converted_file and converted_file != audio_file:
                cleanup_converted_file(converted_file)
    
    # Process audio files in parallel
    max_workers = 5  # Process 5 files concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_audio_file, audio_file): audio_file for audio_file in audio_files}
        
        for future in as_completed(futures):
            audio_file = futures[future]
            try:
                future.result()  # This will raise any exceptions that occurred
            except Exception as e:
                filename = os.path.basename(audio_file)
                print(f"  Error processing {filename}: {e}")
    
    # Clean up temporary downloaded files
    for temp_path, temp_dir in temp_files:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass
    
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