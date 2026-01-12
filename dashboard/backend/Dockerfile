FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY dashboard/backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend API code
COPY dashboard/backend/surveillance_api.py .
COPY dashboard/backend/s3_utils.py .

# Copy all required Python scripts and modules from project root (preserving structure)
COPY file_discovery_mapper.py .
COPY audio_utils.py .
COPY email_processing/ ./email_processing/
COPY oms_surveillance/ ./oms_surveillance/
COPY extract_call_info_august_daily.py .
COPY comprehensive_audio_trading_validation_august_daily.py .
COPY transcribe_calls_august_daily.py .
COPY order_transcript_analysis_august_daily.py .
COPY email_order_validation_august_daily.py .
COPY add_required_columns_to_excel_august_daily.py .
COPY classify_discrepancies_august_daily.py .

# Copy Google Cloud credentials file (if it exists)
# Note: This file should be in the project root
COPY key2.json* ./

# Expose port
EXPOSE 5001

# Set environment variables (can be overridden)
ENV FLASK_APP=surveillance_api.py
ENV FLASK_DEBUG=False
ENV PORT=5001
ENV USE_S3=true

# Run the application
CMD ["python", "surveillance_api.py"]

