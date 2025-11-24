#!/usr/bin/env python3
"""
Audio utility functions for handling various audio formats
Supports conversion of G.729 files to WAV format for processing
"""
import os
import subprocess
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_729_to_wav(input_path: str, output_path: str = None) -> str:
    """
    Convert G.729 (.729) audio file to WAV format using ffmpeg.
    
    Args:
        input_path: Path to the .729 audio file
        output_path: Optional output path. If not provided, creates a temporary WAV file.
    
    Returns:
        Path to the converted WAV file
    
    Raises:
        FileNotFoundError: If ffmpeg is not installed
        subprocess.CalledProcessError: If conversion fails
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Check if file is actually .729 format
    if not input_path.lower().endswith('.729'):
        raise ValueError(f"File is not a .729 file: {input_path}")
    
    # Determine output path
    if output_path is None:
        # Create temporary WAV file in same directory as input
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_converted.wav"
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise FileNotFoundError(
            "ffmpeg is not installed. Please install ffmpeg to convert .729 files.\n"
            "Install: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
        )
    
    logger.info(f"Converting .729 file to WAV: {input_path} -> {output_path}")
    
    # Convert using ffmpeg
    # G.729 files are typically 8kHz, mono, 8-bit
    # We'll let ffmpeg auto-detect and convert to standard WAV format
    try:
        subprocess.run([
            'ffmpeg',
            '-i', input_path,
            '-ar', '8000',  # Sample rate (G.729 is typically 8kHz)
            '-ac', '1',     # Mono channel
            '-sample_fmt', 's16',  # 16-bit signed PCM
            '-y',           # Overwrite output file if it exists
            output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        
        logger.info(f"Successfully converted to: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"ffmpeg conversion failed: {error_msg}")
        raise RuntimeError(f"Failed to convert .729 file: {error_msg}")


def get_audio_file_for_processing(file_path: str, convert_to_wav: bool = True) -> str:
    """
    Get the path to an audio file ready for processing.
    If the file is .729 format, converts it to WAV first.
    
    Args:
        file_path: Path to the audio file (can be .wav, .mp3, .729, etc.)
        convert_to_wav: If True, convert .729 files to WAV. If False, return original.
    
    Returns:
        Path to the audio file ready for processing (may be converted file)
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.729' and convert_to_wav:
        # Convert .729 to WAV
        converted_path = convert_729_to_wav(file_path)
        return converted_path
    
    # For other formats, return as-is
    return file_path


def cleanup_converted_file(converted_path: str):
    """
    Clean up a temporarily converted audio file.
    
    Args:
        converted_path: Path to the converted file to delete
    """
    if os.path.exists(converted_path) and '_converted.wav' in converted_path:
        try:
            os.remove(converted_path)
            logger.info(f"Cleaned up converted file: {converted_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup converted file {converted_path}: {e}")

