#!/usr/bin/env python3
"""
File Discovery and Mapping Module for Trade Surveillance
Handles discovery of uploaded files and maps them to expected surveillance locations
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileDiscoveryMapper:
    """Handles file discovery and mapping for surveillance execution"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()
        self.uploads_dir = os.path.join(self.base_dir, "uploads")
        self.september_dir = os.path.join(self.base_dir, "September")
        # Note: destinations are computed dynamically per date (month-aware)
        
        logger.info(f"FileDiscoveryMapper initialized with base_dir: {self.base_dir}")
    
    def discover_uploaded_files(self, date_str: str) -> Dict[str, List[str]]:
        """
        Discover uploaded files for a given date
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with file types as keys and file paths as values
        """
        date_upload_dir = os.path.join(self.uploads_dir, date_str)
        
        if not os.path.exists(date_upload_dir):
            logger.warning(f"No upload directory found for date: {date_str}")
            return {'orders': [], 'ucc': [], 'audios': []}
        
        discovered_files = {'orders': [], 'ucc': [], 'audios': []}
        
        # Check each file type directory
        for file_type in ['orders', 'ucc', 'audios']:
            type_dir = os.path.join(date_upload_dir, file_type)
            if os.path.exists(type_dir):
                files = [os.path.join(type_dir, f) for f in os.listdir(type_dir) 
                        if os.path.isfile(os.path.join(type_dir, f))]
                discovered_files[file_type] = files
                logger.info(f"Found {len(files)} {file_type} files for {date_str}")
        
        return discovered_files
    
    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type based on content analysis
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type: 'orders', 'ucc', 'audios', or 'unknown'
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Audio files by extension (including G.729 codec files)
        if file_ext in ['.m4a', '.wav', '.mp3', '.mp4', '.aac', '.729']:
            return 'audios'
        
        # CSV files - need content analysis
        if file_ext == '.csv':
            try:
                # Read first few rows to detect content
                df = pd.read_csv(file_path, nrows=5, low_memory=False)
                columns = [col.lower() for col in df.columns]
                
                # Order file detection
                order_indicators = ['norenorderid', 'symbol', 'qty', 'price', 'buysell', 'status', 'clientid']
                if any(indicator in columns for indicator in order_indicators):
                    return 'orders'
                
                # UCC file detection (add UCC-specific indicators)
                ucc_indicators = ['ucc', 'client_code', 'refcode6', 'username']
                if any(indicator in columns for indicator in ucc_indicators):
                    return 'ucc'
                
                logger.warning(f"Could not determine file type for CSV: {file_path}")
                return 'unknown'
                
            except Exception as e:
                logger.error(f"Error reading CSV file {file_path}: {e}")
                return 'unknown'
        
        return 'unknown'
    
    def generate_expected_filename(self, file_type: str, date_str: str, original_filename: str = None) -> str:
        """
        Generate expected filename for surveillance system
        
        Args:
            file_type: Type of file ('orders', 'ucc', 'audios')
            date_str: Date in YYYY-MM-DD format
            original_filename: Original filename (optional)
            
        Returns:
            Expected filename for surveillance system
        """
        # Convert YYYY-MM-DD to DDMMYYYY
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        ddmmyyyy = date_obj.strftime('%d%m%Y')
        
        if file_type == 'orders':
            return f"OrderBook-Closed-{ddmmyyyy}.csv"
        elif file_type == 'ucc':
            return f"UCC_{ddmmyyyy}.csv"
        elif file_type == 'audios':
            # For audios, keep original filename but ensure proper extension
            if original_filename:
                return original_filename
            else:
                return f"audio_{ddmmyyyy}.m4a"
        
        return original_filename or f"file_{ddmmyyyy}.csv"
    
    def map_files_to_surveillance_locations(self, date_str: str, discovered_files: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Map discovered files to expected surveillance locations
        
        Args:
            date_str: Date in YYYY-MM-DD format
            discovered_files: Dictionary of discovered files by type
            
        Returns:
            Dictionary mapping original paths to surveillance paths
        """
        file_mappings = {}

        # Derive month name and DDMMYYYY for proper destination paths
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        month_num = date_obj.month
        ddmmyyyy = date_obj.strftime('%d%m%Y')
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names.get(month_num)
        
        for file_type, file_paths in discovered_files.items():
            if not file_paths:
                continue
                
            for file_path in file_paths:
                # Generate expected filename
                expected_filename = self.generate_expected_filename(
                    file_type, date_str, os.path.basename(file_path)
                )
                
                # Create full surveillance path
                if file_type == 'audios':
                    # Place under <Month>/Call Records/Call_DDMMYYYY/
                    expected_dir = os.path.join(self.base_dir, month_name, "Call Records", f"Call_{ddmmyyyy}")
                    os.makedirs(expected_dir, exist_ok=True)
                    surveillance_path = os.path.join(expected_dir, expected_filename)
                elif file_type == 'orders':
                    # Place under <Month>/Order Files/
                    expected_dir = os.path.join(self.base_dir, month_name, "Order Files")
                    os.makedirs(expected_dir, exist_ok=True)
                    surveillance_path = os.path.join(expected_dir, expected_filename)
                elif file_type == 'ucc':
                    # Place UCC under <Month>/UCC Files/ (keep folder), filename from generator
                    expected_dir = os.path.join(self.base_dir, month_name, "UCC Files")
                    os.makedirs(expected_dir, exist_ok=True)
                    surveillance_path = os.path.join(expected_dir, expected_filename)
                else:
                    # Default to base_dir
                    expected_dir = self.base_dir
                    os.makedirs(expected_dir, exist_ok=True)
                    surveillance_path = os.path.join(expected_dir, expected_filename)
                
                file_mappings[file_path] = surveillance_path
                logger.info(f"Mapped {file_path} -> {surveillance_path}")
        
        return file_mappings
    
    def copy_files_to_surveillance_locations(self, file_mappings: Dict[str, str], replace_existing: bool = True) -> Tuple[bool, int, int]:
        """
        Copy files to surveillance locations
        
        Args:
            file_mappings: Dictionary mapping original paths to surveillance paths
            replace_existing: Whether to replace existing files
            
        Returns:
            Tuple of (success, copied_count, failed_count)
            success is True if at least some files were copied, False only if ALL files failed
        """
        copied_count = 0
        failed_count = 0
        
        for original_path, surveillance_path in file_mappings.items():
            try:
                # Ensure target directory exists
                target_dir = os.path.dirname(surveillance_path)
                os.makedirs(target_dir, exist_ok=True)
                
                # Check if target exists
                if os.path.exists(surveillance_path) and not replace_existing:
                    logger.warning(f"File already exists, skipping: {surveillance_path}")
                    copied_count += 1
                    continue
                
                # Verify source file exists
                if not os.path.exists(original_path):
                    logger.error(f"Source file does not exist: {original_path}")
                    failed_count += 1
                    continue
                
                # Copy file
                shutil.copy2(original_path, surveillance_path)
                
                # Verify copy was successful
                if os.path.exists(surveillance_path):
                    logger.info(f"Successfully copied: {os.path.basename(original_path)} -> {os.path.basename(surveillance_path)}")
                    copied_count += 1
                else:
                    logger.error(f"Copy verification failed: {surveillance_path} does not exist after copy")
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to copy {original_path} to {surveillance_path}: {e}")
                failed_count += 1
        
        # Success if at least one file was copied (or all files already existed)
        success = copied_count > 0 or len(file_mappings) == 0
        return success, copied_count, failed_count
    
    def process_uploaded_files(self, date_str: str, replace_existing: bool = True) -> Tuple[bool, Dict[str, str]]:
        """
        Complete file discovery and mapping process
        
        Args:
            date_str: Date in YYYY-MM-DD format
            replace_existing: Whether to replace existing files
            
        Returns:
            Tuple of (success, file_mappings)
        """
        logger.info(f"Processing uploaded files for date: {date_str}")
        
        # Step 1: Discover uploaded files
        discovered_files = self.discover_uploaded_files(date_str)
        
        # Check if any files found
        total_files = sum(len(files) for files in discovered_files.values())
        if total_files == 0:
            logger.warning(f"No uploaded files found for {date_str}, falling back to existing files")
            # CRITICAL: Still ensure directories exist even if no files found
            # This prevents downstream steps from failing due to missing directories
            self._ensure_required_directories_exist(date_str)
            return True, {}
        
        logger.info(f"Found {total_files} uploaded files for {date_str}")
        
        # Step 2: Map files to surveillance locations
        file_mappings = self.map_files_to_surveillance_locations(date_str, discovered_files)
        
        # Step 3: Copy files to surveillance locations
        success, copied_count, failed_count = self.copy_files_to_surveillance_locations(file_mappings, replace_existing)
        
        if success:
            logger.info(f"Successfully processed {copied_count} files for {date_str}")
            if failed_count > 0:
                logger.warning(f"⚠️  {failed_count} files failed to copy, but continuing with {copied_count} successful copies")
        else:
            logger.error(f"All {len(file_mappings)} files failed to process for {date_str}")
        
        # CRITICAL: Ensure required directories exist even if file copying failed
        # This prevents downstream steps from failing due to missing directories
        self._ensure_required_directories_exist(date_str)
        
        return success, file_mappings
    
    def _ensure_required_directories_exist(self, date_str: str):
        """
        Ensure all required directories exist for the surveillance process.
        This prevents downstream steps from failing due to missing directories.
        
        Args:
            date_str: Date in YYYY-MM-DD format
        """
        try:
            # Derive month name and DDMMYYYY
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month_num = date_obj.month
            ddmmyyyy = date_obj.strftime('%d%m%Y')
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month_num)
            
            if not month_name:
                logger.warning(f"Invalid month number: {month_num}")
                return
            
            # Ensure Call Records directory exists (even if no audio files)
            call_records_dir = os.path.join(self.base_dir, month_name, "Call Records", f"Call_{ddmmyyyy}")
            os.makedirs(call_records_dir, exist_ok=True)
            logger.info(f"✅ Ensured Call Records directory exists: {call_records_dir}")
            
            # Ensure Order Files directory exists
            order_files_dir = os.path.join(self.base_dir, month_name, "Order Files")
            os.makedirs(order_files_dir, exist_ok=True)
            logger.info(f"✅ Ensured Order Files directory exists: {order_files_dir}")
            
            # Ensure Daily Reports directory exists
            daily_reports_dir = os.path.join(self.base_dir, month_name, "Daily_Reports", ddmmyyyy)
            os.makedirs(daily_reports_dir, exist_ok=True)
            logger.info(f"✅ Ensured Daily Reports directory exists: {daily_reports_dir}")
            
        except Exception as e:
            logger.error(f"Error ensuring required directories exist: {e}")

def main():
    """Test the file discovery and mapping functionality"""
    mapper = FileDiscoveryMapper()
    
    # Test with a sample date
    test_date = "2025-09-15"
    success, mappings = mapper.process_uploaded_files(test_date)
    
    if success:
        print(f"✅ File processing successful for {test_date}")
        print(f"📁 Mapped {len(mappings)} files")
        for original, target in mappings.items():
            print(f"   {original} -> {target}")
    else:
        print(f"❌ File processing failed for {test_date}")

if __name__ == "__main__":
    main()
