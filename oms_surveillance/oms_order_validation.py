#!/usr/bin/env python3
"""
OMS Order Validation
Validates OMS orders against order book and updates Excel files.
"""

import json
import pandas as pd
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the oms_surveillance directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from wealth_spectrum_api_client import WealthSpectrumAPIClient

# Initialize OpenAI client (same as email surveillance)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OMSOrderValidator:
    """Validates OMS orders against order book data."""
    
    def __init__(self):
        """Initialize the OMS order validator."""
        self.api_client = WealthSpectrumAPIClient()
        self.client_master_data = None
    
    def load_oms_surveillance_results(self, date: str) -> Optional[Dict]:
        """
        Load OMS surveillance results for a specific date.
        
        Args:
            date: Date in DDMMYYYY format (standardized format)
        
        Returns:
            Dictionary containing OMS surveillance results or None if failed
        """
        
        # STANDARDIZED FORMAT: File is in DDMMYYYY format
        file_path = os.path.join(os.path.dirname(__file__), f"oms_email_surveillance_{date}.json")
        
        if not os.path.exists(file_path):
            logger.error(f"OMS surveillance results file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded OMS surveillance results from {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading OMS surveillance results: {e}")
            return None
    
    def map_oms_client_codes(self, oms_data: Dict) -> Dict[str, str]:
        """
        Map OMS client codes to actual client codes using Wealth Spectrum API.
        
        Args:
            oms_data: OMS surveillance results data
        
        Returns:
            Dictionary mapping OMS client codes to actual client codes
        """
        
        # Extract unique client codes from OMS data
        client_codes = set()
        
        for alert in oms_data.get('oms_order_alerts', []):
            details = alert.get('ai_analysis', {}).get('ai_order_details', [])
            # Normalize to a list of dicts
            if isinstance(details, dict):
                details = [details]
            if not isinstance(details, list):
                continue
            for order in details:
                if not isinstance(order, dict):
                    continue
                client_code = order.get('client_code')
                if client_code:
                    client_codes.add(client_code)
        
        if not client_codes:
            logger.warning("No client codes found in OMS data")
            return {}
        
        logger.info(f"Found {len(client_codes)} unique client codes to map")
        
        # Fetch client master data if not already available
        if self.client_master_data is None:
            self.client_master_data = self.api_client.fetch_client_master_data()
        
        if not self.client_master_data:
            logger.error("Failed to fetch client master data")
            return {}
        
        # Map client codes
        mapping_results = self.api_client.batch_map_client_codes(list(client_codes))
        
        # Filter out None values
        successful_mappings = {k: v for k, v in mapping_results.items() if v is not None}
        
        logger.info(f"Successfully mapped {len(successful_mappings)} out of {len(client_codes)} client codes")
        
        return successful_mappings
    
    def load_kl_orders(self, date: str) -> Optional[pd.DataFrame]:
        """
        Load KL orders for a specific date from OrderBook files (same as email surveillance).
        
        Args:
            date: Date in DDMMYYYY format (standardized format)
        
        Returns:
            DataFrame containing KL orders or None if failed
        """
        
        # Date is already in DDMMYYYY format (e.g., 03102025)
        # Parse to determine month directory
        try:
            if len(date) == 8:
                day = int(date[:2])
                month_num = int(date[2:4])
                year = int(date[4:])
                orderbook_date = date  # Already in DDMMYYYY format
            else:
                logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
                return None
        except ValueError:
            logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
            return None
        
        # Map month number to month name
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names.get(month_num)
        if not month_name:
            logger.error(f"Invalid month number: {month_num}")
            return None
        
        # Use dynamic month path (absolute path to avoid CWD issues)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        order_file = os.path.join(base_dir, month_name, 'Order Files', f'OrderBook-Closed-{orderbook_date}.csv')
        logger.info(f"[KL LOAD] Looking for OrderBook file: {order_file}")
        print(f"[PRINT KL LOAD] path={order_file} exists={os.path.exists(order_file)}")
        if not os.path.exists(order_file):
            logger.error(f"OrderBook file not found: {order_file}")
            return None
        
        try:
            # Load all orders from OrderBook file
            # Use pandas defaults (works in direct test) with low_memory disabled
            df = pd.read_csv(order_file, low_memory=False)
            logger.info(f"[KL LOAD] Loaded {len(df)} total orders from {order_file}")
            logger.info(f"[KL LOAD] Columns: {list(df.columns)}")
            print(f"[PRINT KL LOAD] rows={len(df)} cols_sample={list(df.columns)[:6]}")
            
            # Filter for KL orders (User column starts with 'KL') - same as email surveillance
            if 'User' in df.columns:
                kl_orders = df[df['User'].astype(str).str.startswith('KL', na=False)]
                logger.info(f"[KL LOAD] Filtered to {len(kl_orders)} KL orders (User starts with 'KL')")
                print(f"[PRINT KL LOAD] KL rows={len(kl_orders)}")
                if len(kl_orders) == 0:
                    logger.warning("[KL LOAD] KL filter returned 0 rows; sample User values: %s", df['User'].astype(str).head(5).tolist())
                    print(f"[PRINT KL LOAD] KL sample users={df['User'].astype(str).head(5).tolist()}")
                return kl_orders
            else:
                logger.error(f"[KL LOAD] 'User' column not found in OrderBook file: {order_file}")
                return None
        except Exception as e:
            logger.error(f"[KL LOAD] Error loading OrderBook file: {e}")
            return None

    def _build_noren_to_exch_mapping(self, date: str) -> Dict[str, str]:
        """
        Build a mapping from NorenOrderID -> ExchOrderID from the OrderBook file for the date.
        Mirrors the email surveillance process so we can match Excel 'Order ID' reliably.
        """
        mapping: Dict[str, str] = {}
        # Date is already in DDMMYYYY format (e.g., 03102025)
        # Parse to determine month directory
        try:
            if len(date) == 8:
                day = int(date[:2])
                month_num = int(date[2:4])
                year = int(date[4:])
                orderbook_date = date  # Already in DDMMYYYY format
            else:
                logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
                return mapping
        except ValueError:
            logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
            return mapping

        # Map month number to month name
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names.get(month_num)
        if not month_name:
            logger.warning(f"Invalid month number: {month_num}")
            return mapping

        # Use dynamic month path (absolute path to avoid CWD issues)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        order_file = os.path.join(base_dir, month_name, 'Order Files', f'OrderBook-Closed-{orderbook_date}.csv')
        if not os.path.exists(order_file):
            logger.warning(f"OrderBook file not found for mapping: {order_file}")
            return mapping

        try:
            df = pd.read_csv(order_file, low_memory=False)
            if 'NorenOrderID' in df.columns and 'ExchOrderID' in df.columns:
                for _, row in df.iterrows():
                    n = str(row['NorenOrderID']) if pd.notna(row['NorenOrderID']) else ''
                    e = str(row['ExchOrderID']) if pd.notna(row['ExchOrderID']) else ''
                    # Normalize both sides to plain strings without trailing .0
                    if n.endswith('.0'):
                        n = n[:-2]
                    if e.endswith('.0'):
                        e = e[:-2]
                    if n and e:
                        mapping[n] = e
            else:
                logger.warning("Required columns not found in OrderBook for mapping: need 'NorenOrderID' and 'ExchOrderID'")
        except Exception as e:
            logger.error(f"Error building Noren->Exch mapping: {e}")
        return mapping

    @staticmethod
    def _normalize_order_id(order_id: Any) -> Optional[str]:
        """Normalize possibly scientific or float-like order IDs to string, same as email surveillance."""
        if pd.isna(order_id):
            return None
        try:
            normalized = str(int(float(order_id)))
            return normalized
        except (ValueError, TypeError):
            try:
                s = str(order_id)
                return s[:-2] if s.endswith('.0') else s
            except Exception:
                return None
    
    def match_oms_to_orders(self, oms_data: Dict, kl_orders: pd.DataFrame, client_mapping: Dict[str, str]) -> Dict[str, Dict]:
        """
        Match OMS orders to KL orders using AI-like matching logic.
        
        Args:
            oms_data: OMS surveillance results data
            kl_orders: DataFrame containing KL orders
            client_mapping: Dictionary mapping OMS client codes to actual client codes
        
        Returns:
            Dictionary mapping order IDs to OMS match data
        """
        
        oms_order_mapping = {}
        
        for alert in oms_data.get('oms_order_alerts', []):
            details = alert.get('ai_analysis', {}).get('ai_order_details', [])
            # Normalize to a list of dicts
            if isinstance(details, dict):
                details = [details]
            if not isinstance(details, list):
                continue
            for order in details:
                if not isinstance(order, dict):
                    continue
                oms_client_code = order.get('client_code')
                actual_client_code = client_mapping.get(oms_client_code)
                
                if not actual_client_code:
                    logger.warning(f"No mapping found for OMS client code: {oms_client_code}")
                    continue
                
                # Find matching KL orders for this client
                client_orders = kl_orders[kl_orders['ClientID'] == actual_client_code]
                
                if client_orders.empty:
                    logger.warning(f"No KL orders found for client code: {actual_client_code}")
                    continue
                
                # Use AI matching (EXACT same as email surveillance system)
                ai_result = self.match_oms_to_orders_with_ai(order, client_orders)
                
                # Process AI matching results (same as email surveillance)
                matched_order_ids = ai_result.get('matched_order_ids', [])
                confidence_score = ai_result.get('confidence_score', 0)
                match_type = ai_result.get('match_type', 'NO_MATCH')
                reasoning = ai_result.get('reasoning', '')
                discrepancies = ai_result.get('discrepancies', [])
                
                if matched_order_ids:
                    for order_id in matched_order_ids:
                        # PERMANENT FIX: Handle multiple OMS orders matching the same KL order
                        # If this KL order already has an OMS match, append the new OMS Order ID
                        if order_id in oms_order_mapping:
                            existing_oms_id = oms_order_mapping[order_id].get('OMS_Order_ID', '')
                            new_oms_id = order.get('order_id', '')
                            # Append new OMS Order ID if different
                            if new_oms_id and new_oms_id != existing_oms_id:
                                oms_order_mapping[order_id]['OMS_Order_ID'] = f"{existing_oms_id}, {new_oms_id}"
                                logger.info(f"📋 Multiple OMS orders match same KL order {order_id}: {existing_oms_id} and {new_oms_id}")
                        else:
                            # First match for this KL order
                            oms_order_mapping[order_id] = {
                                'OMS_Order_ID': order.get('order_id'),
                                'OMS_Symbol': order.get('symbol'),
                                'OMS_Quantity': order.get('quantity'),
                                'OMS_Price': order.get('price'),
                                'OMS_Side': order.get('buy_sell'),
                                'OMS_Client_Code': oms_client_code,
                                'OMS_Confidence_Score': f"{confidence_score}%",
                                'OMS_Match_Type': 'OMS_MATCH',
                                'OMS_AI_Reasoning': reasoning,
                                'OMS_Discrepancies': discrepancies,
                                'OMS_Review_Required': ai_result.get('review_required', False)
                            }
                    
                    logger.info(f"✅ AI matched OMS order {order.get('order_id')} to {len(matched_order_ids)} KL orders (confidence: {confidence_score}%)")
                    logger.info(f"   Reasoning: {reasoning}")
                else:
                    logger.warning(f"❌ AI found no matches for OMS order {order.get('order_id')}")
                    logger.warning(f"   Reasoning: {reasoning}")
        
        logger.info(f"Successfully matched {len(oms_order_mapping)} OMS orders to KL orders using AI")
        return oms_order_mapping
    
    def match_oms_to_orders_with_ai(self, oms_order: Dict, client_orders: pd.DataFrame) -> Dict:
        """
        Use AI to match OMS order to KL orders with intelligent symbol matching.
        EXACT copy from email surveillance system.
        
        Args:
            oms_order: OMS order data
            client_orders: DataFrame containing KL orders for the client
        
        Returns:
            Dictionary with matching results
        """
        
        if client_orders.empty:
            return {
                'matched_order_ids': [],
                'confidence_score': 0,
                'reasoning': 'No orders found for client',
                'match_type': 'NO_MATCH',
                'discrepancies': ['No orders found for client'],
                'review_required': False
            }
        
        # Convert client orders to list format for AI (using OrderBook column names)
        available_orders = []
        for _, order in client_orders.iterrows():
            available_orders.append({
                'order_id': str(order.get('NorenOrderID', '')),
                'symbol': str(order.get('Symbol', '')),
                'quantity': order.get('Qty', 0),
                'price': order.get('Price', 0),
                'side': str(order.get('BuySell', '')),
                'status': str(order.get('Status', '')),
                'client_code': str(order.get('ClientID', '')),
                'client_name': str(order.get('ClientName', ''))
            })
        
        # Create AI prompt for OMS order matching (adapted from email surveillance)
        prompt = f"""
        You are a trade surveillance expert. Match the OMS order to the available KL orders.

        **OMS ORDER:**
        {json.dumps(oms_order, indent=2)}

        **AVAILABLE KL ORDERS FOR CLIENT:**
        {json.dumps(available_orders, indent=2)}

        **CRITICAL MATCHING RULES:**

        1. **SYMBOL MATCHING** - Be intelligent about variations:
           - "MANAPPURAM FINANCE LTD" = "MANAPPURAM" or "MANAPPURAM-EQ"
           - "blue jet healthcare" = "BLUEJET"
           - "Energy INVIT" = "ENERGYINF"
           - Extract company name from full company names

        2. **BUY/SELL DIRECTION**: Must match exactly (BUY/SELL)

        3. **ORDER STATUS HANDLING**:
           - Match orders regardless of status (Complete, Active, Cancelled, Rejected)
           - All orders provide valuable surveillance data
           - Flag status discrepancies for review if needed

        4. **QUANTITY MATCHING**:
           - OMS orders may not have quantity specified
           - If quantity is specified, try to match or flag discrepancies
           - If no quantity in OMS, match based on symbol and side only

        5. **PRICE MATCHING**:
           - OMS orders may not have price specified
           - If price is specified, try to match or flag discrepancies
           - If no price in OMS, match based on symbol and side only

        **IMPORTANT:** 
        - OMS orders are system-generated alerts, so they may have limited information
        - Focus on symbol and side matching primarily
        - Flag any discrepancies for review

        **RETURN JSON:**
        {{
            "matched_order_ids": ["list of order IDs that match the OMS order"],
            "confidence_score": 0-100,
            "reasoning": "explanation of the match",
            "match_type": "EXACT_MATCH|PARTIAL_MATCH|NO_MATCH",
            "discrepancies": ["list of any discrepancies found"],
            "review_required": true/false
        }}
        """
        
        try:
            logger.info(f"🔍 Sending OMS order to AI for matching...")
            logger.info(f"🔍 OMS Order: {oms_order.get('symbol')} - {oms_order.get('buy_sell')}")
            logger.info(f"🔍 Available orders: {len(available_orders)}")
            
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a trade surveillance expert. Match OMS orders to KL orders accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"🔍 AI Response: {ai_response[:200]}...")
            
            # Parse AI response - handle markdown code blocks and extra content (same as email surveillance)
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            
            # Find the JSON part (between first { and last })
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_part = ai_response[start_idx:end_idx+1]
                ai_result = json.loads(json_part.strip())
            else:
                ai_result = json.loads(ai_response.strip())
            
            logger.info(f"🔍 Parsed AI result: {ai_result}")
            return ai_result
            
        except Exception as e:
            logger.error(f"❌ AI matching failed: {e}")
            return {
                'matched_order_ids': [],
                'confidence_score': 0,
                'reasoning': f'AI matching failed: {str(e)}',
                'match_type': 'NO_MATCH',
                'discrepancies': [f'AI matching error: {str(e)}'],
                'review_required': True
            }
    
    def _save_oms_matches_to_file(self, date: str, oms_order_mapping: Dict[str, Dict], client_mapping: Dict[str, str]) -> Optional[str]:
        """
        PERMANENT FIX: Save OMS matches to intermediate JSON file.
        This ensures matches are never lost, even if Excel doesn't exist yet.
        
        Args:
            date: Date in DDMMYYYY format
            oms_order_mapping: Dictionary mapping order IDs to OMS match data
            client_mapping: Dictionary mapping OMS client codes to actual client codes
        
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Save to oms_surveillance directory
            oms_dir = os.path.dirname(os.path.abspath(__file__))
            matches_file = os.path.join(oms_dir, f'oms_matches_{date}.json')
            
            # Create data structure for matches
            matches_data = {
                'date': date,
                'matches': oms_order_mapping,
                'client_mapping': client_mapping,
                'total_matches': len(oms_order_mapping),
                'created_at': datetime.now().isoformat()
            }
            
            # Save to JSON file
            with open(matches_file, 'w', encoding='utf-8') as f:
                json.dump(matches_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(oms_order_mapping)} OMS matches to {matches_file}")
            return matches_file
            
        except Exception as e:
            logger.error(f"Error saving OMS matches to file: {e}")
            return None
    
    def _load_oms_matches_from_file(self, date: str) -> Optional[Dict]:
        """
        Load OMS matches from intermediate JSON file.
        
        Args:
            date: Date in DDMMYYYY format
        
        Returns:
            Dictionary with matches data or None if not found
        """
        try:
            oms_dir = os.path.dirname(os.path.abspath(__file__))
            matches_file = os.path.join(oms_dir, f'oms_matches_{date}.json')
            
            if not os.path.exists(matches_file):
                return None
            
            with open(matches_file, 'r', encoding='utf-8') as f:
                matches_data = json.load(f)
            
            logger.info(f"Loaded {matches_data.get('total_matches', 0)} OMS matches from {matches_file}")
            return matches_data
            
        except Exception as e:
            logger.error(f"Error loading OMS matches from file: {e}")
            return None
    
    def update_excel_file(self, date: str, oms_order_mapping: Dict[str, Dict] = None, client_mapping: Dict[str, str] = None) -> bool:
        """
        PERMANENT FIX: Update Excel file with OMS match data.
        Can load matches from intermediate JSON file if oms_order_mapping is not provided.
        
        Args:
            date: Date in DDMMYYYY format (standardized format)
            oms_order_mapping: Dictionary mapping order IDs to OMS match data (optional, can load from file)
            client_mapping: Dictionary mapping OMS client codes to actual client codes (optional)
        
        Returns:
            True if successful, False otherwise
        """
        
        # PERMANENT FIX: If oms_order_mapping not provided, try to load from intermediate file
        if oms_order_mapping is None:
            matches_data = self._load_oms_matches_from_file(date)
            if matches_data:
                oms_order_mapping = matches_data.get('matches', {})
                if client_mapping is None:
                    client_mapping = matches_data.get('client_mapping', {})
                logger.info(f"Loaded {len(oms_order_mapping)} OMS matches from intermediate file")
            else:
                logger.warning(f"No OMS matches found (neither provided nor in intermediate file)")
                return False
        
        if not oms_order_mapping:
            logger.warning("No OMS matches to apply")
            return False
        
        # Date is already in DDMMYYYY format (e.g., 03102025)
        # Parse to determine month directory
        try:
            if len(date) == 8:
                day = int(date[:2])
                month_num = int(date[2:4])
                year = int(date[4:])
                excel_date = date  # Already in DDMMYYYY format
            else:
                logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
                return False
        except ValueError:
            logger.error(f"Invalid date format: {date}. Expected DDMMYYYY")
            return False
        
        # Map month number to month name
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names.get(month_num)
        if not month_name:
            logger.error(f"Invalid month number: {month_num}")
            return False
        
        # Look for the Final Trade Surveillance Report Excel file (dynamic month path)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        excel_file = os.path.join(base_dir, month_name, 'Daily_Reports', excel_date, f'Final_Trade_Surveillance_Report_{excel_date}_with_Email_and_Trade_Analysis.xlsx')
        
        if not os.path.exists(excel_file):
            # PERMANENT FIX: Excel file doesn't exist yet - this is expected if OMS runs before step 9
            # Matches are already saved to intermediate file, so return True
            logger.info(f"Excel file not found: {excel_file}")
            logger.info("This is expected if OMS surveillance runs before 'Final Required Columns Mapping' step.")
            logger.info(f"OMS matches ({len(oms_order_mapping)}) are saved to intermediate file and will be applied in Step 9.")
            return True  # Return True - matches are saved and will be applied later
        
        try:
            # Load Excel file with converters to preserve large numeric IDs as strings
            def _to_str_id(v):
                try:
                    if pd.isna(v):
                        return ''
                    # Handle strings directly
                    s = str(v)
                    if s.endswith('.0'):
                        s = s[:-2]
                    # If scientific or float-like, cast to int then str
                    if 'e+' in s.lower() or s.replace('.', '', 1).isdigit():
                        return str(int(float(s)))
                    return s
                except Exception:
                    return str(v)

            df = pd.read_excel(
                excel_file,
                converters={
                    'Order ID': _to_str_id,
                    'order_id': _to_str_id
                }
            )
            
            # Normalize Order ID for reliable matching (avoid float string like '...0')
            def normalize_order_id_value(v):
                try:
                    if pd.isna(v):
                        return ''
                    # If it's float-like, cast to int first
                    as_int = int(float(v))
                    return str(as_int)
                except Exception:
                    # Fallback to raw string without trailing .0
                    s = str(v)
                    return s[:-2] if s.endswith('.0') else s

            # Prefer the string-based 'order_id' column if present to avoid float precision issues
            has_lower_order_id = 'order_id' in df.columns
            # Normalize both columns to strings for comparison
            df_order_id_str = df['Order ID'].apply(normalize_order_id_value) if 'Order ID' in df.columns else pd.Series(['']*len(df))

            # Build Noren->Exch mapping for this date so we match against Excel's Order ID
            noren_to_exch = self._build_noren_to_exch_mapping(date)
            
            # Update existing email match columns with OMS data
            for order_id, oms_data in oms_order_mapping.items():
                # Convert NorenOrderID (from AI) to ExchOrderID used in Excel, then normalize
                exch_id = noren_to_exch.get(str(order_id), str(order_id))
                normalized_target = normalize_order_id_value(exch_id)
                mask_numeric = df_order_id_str == normalized_target
                if has_lower_order_id:
                    mask_text = df['order_id'].astype(str) == str(order_id)
                    mask = mask_numeric | mask_text
                else:
                    mask = mask_numeric
                if not mask.any():
                    # AI-only policy: do not apply non-ID fallback; log for audit
                    logger.warning("AI returned order id %s (normalized %s) but no Excel row matched; skipping non-ID fallback",
                                   order_id, normalized_target)
                if mask.any():
                    df.loc[mask, 'Email-Order Match Status'] = 'OMS_MATCH'
                    # Use correct Excel column names (spaces, not underscores)
                    df.loc[mask, 'Email Confidence Score'] = oms_data.get('OMS_Confidence_Score', '')
                    df.loc[mask, 'Email_Order_ID'] = oms_data.get('OMS_Order_ID', '')
                    df.loc[mask, 'Email_Symbol'] = oms_data.get('OMS_Symbol', '')
                    df.loc[mask, 'Email_Quantity'] = oms_data.get('OMS_Quantity', '')
                    df.loc[mask, 'Email_Price'] = oms_data.get('OMS_Price', '')
                    df.loc[mask, 'Email_Side'] = oms_data.get('OMS_Side', '')
                    # Store mapped client code if present
                    oms_client_code = oms_data.get('OMS_Client_Code', '')
                    df.loc[mask, 'Email_Client_Code'] = client_mapping.get(oms_client_code, oms_client_code)
            
            # Save updated Excel file
            df.to_excel(excel_file, index=False)
            
            # PERMANENT FIX: Verify Excel was actually updated
            verification_success = self._verify_excel_updated(excel_file, oms_order_mapping)
            if not verification_success:
                logger.warning("Excel file was updated but verification failed - matches may not have been applied correctly")
            
            logger.info(f"Updated Excel file {excel_file} with {len(oms_order_mapping)} OMS matches")
            if verification_success:
                logger.info(f"✅ Verified: Excel file contains OMS_MATCH status for matched orders")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating Excel file: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _verify_excel_updated(self, excel_file: str, oms_order_mapping: Dict[str, Dict]) -> bool:
        """
        PERMANENT FIX: Verify that Excel file was actually updated with OMS matches.
        
        Args:
            excel_file: Path to Excel file
            oms_order_mapping: Dictionary of OMS matches that should be in Excel
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Read Excel file back
            df = pd.read_excel(excel_file)
            
            if 'Email-Order Match Status' not in df.columns:
                logger.warning("Excel file does not have 'Email-Order Match Status' column")
                return False
            
            # Count OMS matches in Excel
            oms_matches_in_excel = df[df['Email-Order Match Status'] == 'OMS_MATCH']
            expected_count = len(oms_order_mapping)
            actual_count = len(oms_matches_in_excel)
            
            if actual_count == 0:
                logger.warning(f"Verification failed: Expected {expected_count} OMS matches but found 0 in Excel")
                return False
            
            if actual_count < expected_count:
                logger.warning(f"Verification warning: Expected {expected_count} OMS matches but found {actual_count} in Excel")
                # Still return True as partial success
                return True
            
            logger.info(f"✅ Verification successful: {actual_count} OMS matches found in Excel (expected {expected_count})")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Excel update: {e}")
            return False
    
    def validate_oms_orders(self, date: str) -> bool:
        """
        Complete OMS order validation process.
        
        Args:
            date: Date in DDMMYYYY format (standardized format)
        
        Returns:
            True if successful, False otherwise
        """
        
        print(f"🚀 Starting OMS Order Validation for {date}")
        print("=" * 60)
        logger.info(f"🔍 [VALIDATE] Starting OMS Order Validation for {date}")
        
        # Step 1: Load OMS surveillance results
        print("📋 Step 1: Loading OMS surveillance results...")
        logger.info(f"🔍 [VALIDATE] Step 1: Loading OMS surveillance results for {date}")
        try:
            oms_data = self.load_oms_surveillance_results(date)
            if not oms_data:
                logger.error(f"❌ [VALIDATE] Failed to load OMS surveillance results for {date}")
                print(f"❌ [VALIDATE] Failed to load OMS surveillance results for {date}")
                return False
            logger.info(f"✅ [VALIDATE] Step 1: Successfully loaded OMS surveillance results")
            print(f"✅ [VALIDATE] Step 1: Successfully loaded OMS surveillance results")
        except Exception as e:
            logger.error(f"❌ [VALIDATE] Error loading OMS surveillance results: {e}")
            import traceback
            logger.error(f"❌ [VALIDATE] Traceback: {traceback.format_exc()}")
            print(f"❌ [VALIDATE] Error: {e}")
            return False
        
        # Check if there are any OMS orders to process
        oms_alerts = oms_data.get('oms_order_alerts', [])
        if not oms_alerts:
            print("ℹ️  No OMS orders found for this date (this is normal)")
            print("✅ OMS Order Validation completed successfully (no orders to process)")
            return True
        
        # Step 2: Map OMS client codes to actual client codes
        print("🔗 Step 2: Mapping OMS client codes...")
        try:
            client_mapping = self.map_oms_client_codes(oms_data)
            if not client_mapping:
                logger.warning(f"No client code mappings found for {date}")
                print("⚠️ No client code mappings found")
                return False
        except Exception as e:
            logger.error(f"Error mapping client codes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        # Step 3: Load KL orders
        print("📊 Step 3: Loading KL orders...")
        print("[DEBUG] Calling load_kl_orders...")
        try:
            kl_orders = self.load_kl_orders(date)
            print(f"[DEBUG] load_kl_orders returned: {'None' if kl_orders is None else len(kl_orders)} rows")
            if kl_orders is None:
                logger.error(f"Failed to load KL orders for {date}")
                return False
            if len(kl_orders) == 0:
                logger.warning(f"No KL orders found for {date}")
                print("⚠️ No KL orders found for this date")
                return False
        except Exception as e:
            logger.error(f"Error loading KL orders: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        # Step 4: Match OMS orders to KL orders
        print("🎯 Step 4: Matching OMS orders to KL orders...")
        logger.info(f"🔍 [VALIDATE] Step 4: Starting OMS order matching for {date}")
        try:
            oms_order_mapping = self.match_oms_to_orders(oms_data, kl_orders, client_mapping)
            logger.info(f"🔍 [VALIDATE] Step 4: match_oms_to_orders returned {len(oms_order_mapping) if oms_order_mapping else 0} matches")
            if not oms_order_mapping:
                logger.warning(f"⚠️ [VALIDATE] No OMS orders matched to KL orders for {date}")
                print("⚠️ No OMS orders matched to KL orders")
                return False
            logger.info(f"✅ [VALIDATE] Step 4: Successfully matched {len(oms_order_mapping)} OMS orders")
            print(f"✅ [VALIDATE] Step 4: Successfully matched {len(oms_order_mapping)} OMS orders")
        except Exception as e:
            logger.error(f"❌ [VALIDATE] Error matching OMS orders: {e}")
            import traceback
            logger.error(f"❌ [VALIDATE] Traceback: {traceback.format_exc()}")
            print(f"❌ [VALIDATE] Error: {e}")
            return False
        
        # PERMANENT FIX: Always save matches to intermediate JSON file
        # This ensures matches are never lost, even if Excel doesn't exist yet
        print("💾 Step 5: Saving OMS matches to intermediate file...")
        logger.info(f"🔍 [VALIDATE] Step 5: Saving OMS matches to intermediate file for {date}")
        matches_file = self._save_oms_matches_to_file(date, oms_order_mapping, client_mapping)
        if not matches_file:
            logger.error(f"❌ [VALIDATE] Failed to save OMS matches to intermediate file for {date}")
            print(f"❌ [VALIDATE] Failed to save OMS matches to intermediate file")
            return False
        logger.info(f"✅ [VALIDATE] Step 5: Successfully saved matches to {matches_file}")
        print(f"✅ OMS matches saved to: {matches_file}")
        
        # Step 6: Try to update Excel file (if it exists)
        print("📝 Step 6: Attempting to update Excel file...")
        logger.info(f"🔍 [VALIDATE] Step 6: Attempting to update Excel file for {date}")
        excel_updated = self.update_excel_file(date, oms_order_mapping, client_mapping)
        logger.info(f"🔍 [VALIDATE] Step 6: update_excel_file returned: {excel_updated}")
        
        if excel_updated:
            # Check if Excel file actually exists (it might not if Step 8 runs before Step 9)
            month_num = int(date[2:4])
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month_num)
            excel_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                month_name,
                "Daily_Reports",
                date,
                f"Final_Trade_Surveillance_Report_{date}_with_Email_and_Trade_Analysis.xlsx"
            )
            
            if os.path.exists(excel_file):
                print(f"✅ Excel file updated successfully")
                logger.info(f"✅ [VALIDATE] Step 6: Excel file updated successfully")
                
                # VERIFICATION: Confirm matches were actually applied to Excel
                logger.info(f"🔍 [VALIDATE] Verifying matches were applied to Excel...")
                try:
                    import pandas as pd
                    df = pd.read_excel(excel_file)
                    oms_matched = df[df['Email-Order Match Status'] == 'OMS_MATCH']
                    match_count = len(oms_matched)
                    expected_count = len(oms_order_mapping)
                    
                    logger.info(f"🔍 [VALIDATE] Verification: Found {match_count} OMS matches in Excel (expected {expected_count})")
                    print(f"🔍 [VALIDATE] Verification: Found {match_count} OMS matches in Excel (expected {expected_count})")
                    
                    if match_count == 0:
                        logger.error(f"❌ [VALIDATE] VERIFICATION FAILED: No OMS matches found in Excel after update!")
                        print(f"❌ [VALIDATE] VERIFICATION FAILED: No OMS matches found in Excel after update!")
                        return False
                    elif match_count < expected_count:
                        logger.warning(f"⚠️ [VALIDATE] WARNING: Found {match_count} matches but expected {expected_count}")
                        print(f"⚠️ [VALIDATE] WARNING: Found {match_count} matches but expected {expected_count}")
                    else:
                        logger.info(f"✅ [VALIDATE] Verification passed: {match_count} matches found in Excel")
                        print(f"✅ [VALIDATE] Verification passed: {match_count} matches found in Excel")
                except Exception as verify_error:
                    logger.error(f"❌ [VALIDATE] Error during verification: {verify_error}")
                    import traceback
                    logger.error(f"❌ [VALIDATE] Traceback: {traceback.format_exc()}")
                    print(f"❌ [VALIDATE] Error during verification: {verify_error}")
            else:
                # Excel file doesn't exist - this is expected if Step 8 runs before Step 9
                # Matches are saved to intermediate file and will be applied in Step 9
                logger.info(f"ℹ️ [VALIDATE] Excel file not found: {excel_file}")
                logger.info(f"ℹ️ [VALIDATE] This is expected if Step 8 runs before Step 9")
                logger.info(f"ℹ️ [VALIDATE] Matches ({len(oms_order_mapping)}) saved to intermediate file, will be applied in Step 9")
                print(f"ℹ️ [VALIDATE] Excel file not found (expected if Step 8 runs before Step 9)")
                print(f"   Matches saved to intermediate file, will be applied in Step 9")
                # DON'T delete intermediate file - Step 9 needs it!
                return True  # Return early, matches saved to intermediate file
            
            # Delete intermediate file only if Excel was actually updated
            try:
                if os.path.exists(matches_file):
                    os.remove(matches_file)
                    logger.info(f"🗑️  Deleted intermediate file (matches applied to Excel)")
                    print(f"🗑️  Deleted intermediate file (matches applied to Excel)")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete intermediate file: {e}")
        else:
            logger.warning(f"⚠️ [VALIDATE] Excel file update failed or file doesn't exist yet")
            print(f"ℹ️  Excel file not found or not updated (matches saved to intermediate file)")
            print(f"   Matches will be applied in Step 9 when Excel is created")
        
        # Always print success message and summary
        print(f"\n✅ OMS Order Validation completed successfully!")
        print(f"📊 Summary:")
        print(f"   📋 OMS orders processed: {len(oms_data.get('oms_order_alerts', []))}")
        print(f"   🔗 Client codes mapped: {len(client_mapping)}")
        print(f"   🎯 Orders matched: {len(oms_order_mapping)}")
        print(f"   💾 Matches saved to: {matches_file}")
        print(f"   📝 Excel file updated: {excel_updated}")
        logger.info(f"✅ [VALIDATE] OMS Order Validation completed successfully for {date}")
        
        # Return True if matches were found and saved (even if Excel wasn't updated)
        return True

def main():
    """Main function for OMS order validation."""
    
    if len(sys.argv) != 2:
        print("Usage: python oms_order_validation.py <date>")
        print("Example: python oms_order_validation.py 03102025")
        print("Note: Date format is DDMMYYYY (standardized format)")
        sys.exit(1)
    
    date = sys.argv[1]
    
    # Validate date format (DDMMYYYY)
    try:
        datetime.strptime(date, '%d%m%Y')
    except ValueError:
        print("❌ Invalid date format. Please use DDMMYYYY format (e.g., 03102025).")
        sys.exit(1)
    
    # Initialize validator and run validation
    validator = OMSOrderValidator()
    success = validator.validate_oms_orders(date)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()