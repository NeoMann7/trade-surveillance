#!/usr/bin/env python3
"""
Test OMS Components
Test individual OMS components with sample data from September 2nd, 2025.
"""

import json
import os
import sys
from datetime import datetime

# Add the oms_surveillance directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oms_order_alert_processor import process_oms_emails_from_file, analyze_oms_order_alert_email
from wealth_spectrum_api_client import WealthSpectrumAPIClient

def create_test_oms_data():
    """Create test OMS data from September 2nd, 2025."""
    
    # Sample OMS email data from September 2nd, 2025
    test_oms_emails = {
        "email_analyses": [
            {
                "subject": "New Order Alert - OMS!",
                "sender": "service@neo-wealth.com",
                "clean_text": "Dear Team,New Orders added in OMS, details below. Kindly login into OMS & check.Ref.no.Trade DateClient CodeClient NameAccount TypeProductTransaction TypeScheme/ScripISINLOBBUY00644105897RAJANI SARANNON-POALISTED EQBUYMANAPPURAM FINANCE LTDINE522D01027NWMOMS Login URL: https://start.theneoworld.comThis is a system generated email, kindly do not reply to this email.",
                "date": "2025-09-02T10:30:00Z",
                "attachment_info": ""
            },
            {
                "subject": "New Order Alert - OMS!",
                "sender": "service@neo-wealth.com", 
                "clean_text": "Dear Team,New Orders added in OMS, details below. Kindly login into OMS & check.Ref.no.Trade DateClient CodeClient NameAccount TypeProductTransaction TypeScheme/ScripISINLOBBUY00644105897RAJANI SARANNON-POALISTED EQBUYMANAPPURAM FINANCE LTDINE522D01027NWMOMS Login URL: https://start.theneoworld.comThis is a system generated email, kindly do not reply to this email.",
                "date": "2025-09-02T11:15:00Z",
                "attachment_info": ""
            }
        ],
        "email_type": "oms_order_alert",
        "test_date": "2025-09-02"
    }
    
    # Save test data to file
    test_file = "test_oms_emails_20250902.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_oms_emails, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created test OMS data file: {test_file}")
    return test_file

def test_oms_parser():
    """Test the OMS order alert processor."""
    
    print("🔍 Testing OMS Order Alert Processor")
    print("-" * 50)
    
    # Create test data
    test_file = create_test_oms_data()
    
    try:
        # Test the processor
        output_file = process_oms_emails_from_file(test_file)
        
        if output_file:
            print(f"✅ OMS Parser Test PASSED")
            print(f"📁 Output file: {output_file}")
            
            # Load and display results
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"📊 Results Summary:")
            print(f"   📧 Emails processed: {results.get('processing_summary', {}).get('total_emails_processed', 0)}")
            print(f"   📋 Orders found: {results.get('processing_summary', {}).get('total_orders_found', 0)}")
            
            # Show sample order details
            for alert in results.get('oms_order_alerts', []):
                for order in alert.get('ai_analysis', {}).get('ai_order_details', []):
                    print(f"   📋 Order: {order.get('client_code')} - {order.get('symbol')} - {order.get('buy_sell')}")
            
            return output_file
        else:
            print("❌ OMS Parser Test FAILED")
            return None
            
    except Exception as e:
        print(f"❌ OMS Parser Test FAILED with error: {e}")
        return None
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_wealth_spectrum_api():
    """Test the Wealth Spectrum API client."""
    
    print("\n🔗 Testing Wealth Spectrum API Client")
    print("-" * 50)
    
    try:
        # Initialize API client
        api_client = WealthSpectrumAPIClient()
        
        # Test fetching client master data
        print("📊 Fetching client master data...")
        client_data = api_client.fetch_client_master_data()
        
        if client_data:
            print(f"✅ API Test PASSED - Fetched {len(client_data.get('data', []))} client records")
            
            # Test mapping a sample client code
            print("🔍 Testing client code mapping...")
            sample_code = "105897"  # From OMS email
            
            actual_code = api_client.map_wealth_spectrum_to_actual_client_code(sample_code, client_data)
            if actual_code:
                print(f"✅ Client mapping successful: {sample_code} -> {actual_code}")
            else:
                print(f"⚠️ No mapping found for {sample_code} (this is expected for test data)")
            
            return True
        else:
            print("❌ API Test FAILED - Could not fetch client data")
            return False
            
    except Exception as e:
        print(f"❌ API Test FAILED with error: {e}")
        return False

def test_individual_oms_parser():
    """Test the individual OMS email parser function."""
    
    print("\n🔍 Testing Individual OMS Email Parser")
    print("-" * 50)
    
    # Test data from real OMS email
    test_subject = "New Order Alert - OMS!"
    test_sender = "service@neo-wealth.com"
    test_clean_text = "Dear Team,New Orders added in OMS, details below. Kindly login into OMS & check.Ref.no.Trade DateClient CodeClient NameAccount TypeProductTransaction TypeScheme/ScripISINLOBBUY00644105897RAJANI SARANNON-POALISTED EQBUYMANAPPURAM FINANCE LTDINE522D01027NWMOMS Login URL: https://start.theneoworld.comThis is a system generated email, kindly do not reply to this email."
    
    try:
        # Test the parser function
        result = analyze_oms_order_alert_email(test_subject, test_sender, test_clean_text)
        
        print(f"✅ Individual Parser Test PASSED")
        print(f"📊 Analysis Results:")
        print(f"   🎯 Intent: {result.get('ai_email_intent')}")
        print(f"   📈 Confidence: {result.get('ai_confidence_score')}")
        print(f"   📋 Orders found: {len(result.get('ai_order_details', []))}")
        
        # Show order details
        for order in result.get('ai_order_details', []):
            print(f"   📋 Order Details:")
            print(f"      Client Code: {order.get('client_code')}")
            print(f"      Symbol: {order.get('symbol')}")
            print(f"      Side: {order.get('buy_sell')}")
            print(f"      Order ID: {order.get('order_id')}")
            print(f"      ISIN: {order.get('isin')}")
            print(f"      Client Name: {order.get('client_name')}")
            print(f"      LOB: {order.get('lob')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Individual Parser Test FAILED with error: {e}")
        return False

def main():
    """Run all OMS component tests."""
    
    print("🚀 OMS Components Test Suite")
    print("=" * 60)
    print(f"🕐 Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Individual OMS Parser
    test_results['individual_parser'] = test_individual_oms_parser()
    
    # Test 2: OMS Parser with File
    test_results['file_parser'] = test_oms_parser() is not None
    
    # Test 3: Wealth Spectrum API
    test_results['api_client'] = test_wealth_spectrum_api()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed_tests += 1
    
    print(f"\n📈 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All OMS component tests PASSED!")
        return True
    else:
        print("⚠️ Some OMS component tests FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
