#!/usr/bin/env python3
"""
Wealth Spectrum API Client
Client for interacting with the Wealth Spectrum API to map client codes.
"""

import requests
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WealthSpectrumAPIClient:
    """Client for Wealth Spectrum API operations."""
    
    def __init__(self, base_url: str = "https://ws.neo-wealth.com/wealthspectrum/app/api/boQueries/execute", 
                 auth_token: str = "79117bffV2e07h49f40Kbf30Wu4c4c21f9c6d56a"):
        """
        Initialize the Wealth Spectrum API client.
        
        Args:
            base_url: Base URL for the Wealth Spectrum API
            auth_token: Authorization token for API access
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    
    def fetch_client_master_data(self, from_date: str = None, to_date: str = None) -> Optional[Dict]:
        """
        Fetch client master data from Wealth Spectrum API.
        
        Args:
            from_date: Start date in YYYY-MM-DD format (defaults to 6 months ago)
            to_date: End date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            Dictionary containing client master data or None if failed
        """
        
        # Set default dates if not provided
        if not from_date:
            from_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Prepare request payload
        payload = {
            "fDate": from_date,
            "tDate": to_date,
            "queryFile": "ClientMaster.xml",
            "scope": "",
            "scopeId": "",
            "queryCriteria": [
                {"field": "output", "type": "", "defaultValue": "JSON"},
                {"field": "txtField1", "type": "", "defaultValue": ""}
            ]
        }
        
        try:
            logger.info(f"Fetching client master data from {from_date} to {to_date}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched client master data: {len(data.get('data', []))} records")
                return data
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def map_wealth_spectrum_to_actual_client_code(self, wealth_spectrum_code: str, client_master_data: Dict = None) -> Optional[str]:
        """
        Map Wealth Spectrum client code to actual client code (REFCODE6).
        
        Args:
            wealth_spectrum_code: The client code from Wealth Spectrum (USERNAME or CLIENTCODE)
            client_master_data: Pre-fetched client master data (optional)
        
        Returns:
            Actual client code (REFCODE6) or None if not found
        """
        
        # Fetch client master data if not provided
        if client_master_data is None:
            client_master_data = self.fetch_client_master_data()
            if not client_master_data:
                logger.error("Failed to fetch client master data")
                return None
        
        try:
            # Search for the client code in the data
            if "data" in client_master_data:
                for client in client_master_data["data"]:
                    username = str(client.get("USERNAME", ""))
                    clientcode = str(client.get("CLIENTCODE", ""))
                    
                    # Check if either USERNAME or CLIENTCODE matches
                    if username == str(wealth_spectrum_code) or clientcode == str(wealth_spectrum_code):
                        actual_client_code = client.get("REFCODE6", "")
                        if actual_client_code and actual_client_code != "-":
                            logger.info(f"Mapped Wealth Spectrum code {wealth_spectrum_code} to actual client code {actual_client_code}")
                            return actual_client_code
                        else:
                            logger.warning(f"Found matching client but REFCODE6 is empty or invalid: {actual_client_code}")
                            continue
            
            logger.warning(f"No mapping found for Wealth Spectrum code: {wealth_spectrum_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error mapping client code {wealth_spectrum_code}: {e}")
            return None
    
    def batch_map_client_codes(self, wealth_spectrum_codes: List[str]) -> Dict[str, Optional[str]]:
        """
        Map multiple Wealth Spectrum client codes to actual client codes.
        
        Args:
            wealth_spectrum_codes: List of Wealth Spectrum client codes
        
        Returns:
            Dictionary mapping Wealth Spectrum codes to actual client codes
        """
        
        # Fetch client master data once
        client_master_data = self.fetch_client_master_data()
        if not client_master_data:
            logger.error("Failed to fetch client master data for batch mapping")
            return {code: None for code in wealth_spectrum_codes}
        
        # Map each code
        results = {}
        for code in wealth_spectrum_codes:
            actual_code = self.map_wealth_spectrum_to_actual_client_code(code, client_master_data)
            results[code] = actual_code
        
        logger.info(f"Batch mapping completed: {len([v for v in results.values() if v])} successful mappings out of {len(wealth_spectrum_codes)} codes")
        return results

def main():
    """Test the Wealth Spectrum API client."""
    
    print("🚀 Wealth Spectrum API Client Test")
    print("=" * 50)
    
    # Initialize client
    client = WealthSpectrumAPIClient()
    
    # Test fetching client master data
    print("📊 Fetching client master data...")
    client_data = client.fetch_client_master_data()
    
    if client_data:
        print(f"✅ Successfully fetched {len(client_data.get('data', []))} client records")
        
        # Test mapping a sample client code
        print("\n🔍 Testing client code mapping...")
        sample_code = "105897"  # Example from OMS email
        
        actual_code = client.map_wealth_spectrum_to_actual_client_code(sample_code, client_data)
        if actual_code:
            print(f"✅ Mapped {sample_code} to {actual_code}")
        else:
            print(f"❌ No mapping found for {sample_code}")
        
        # Show sample data structure
        if client_data.get("data"):
            print(f"\n📋 Sample client record:")
            sample_record = client_data["data"][0]
            for key, value in sample_record.items():
                print(f"   {key}: {value}")
    
    else:
        print("❌ Failed to fetch client master data")

if __name__ == "__main__":
    main()
