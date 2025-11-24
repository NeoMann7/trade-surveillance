# Unmatched Emails Documentation

This folder contains detailed documentation of unmatched emails from the trade surveillance email processing system. Each date has its own markdown file with comprehensive analysis of why emails couldn't be matched to orders.

## 📁 File Structure

```
unmatched_emails_documentation/
├── README.md                                    # This overview file
├── September_01_2025_Unmatched_Emails.md       # Sept 1st analysis (0 unmatched)
├── September_02_2025_Unmatched_Emails.md       # Sept 2nd analysis (3 unmatched)
├── September_03_2025_Unmatched_Emails.md       # Sept 3rd analysis (3 unmatched)
└── September_05_2025_Unmatched_Emails.md       # Sept 5th analysis (1 unmatched)
```

## 📊 Summary Statistics

| Date | Total Emails | Trade Instructions | Matched | Unmatched | Match Rate |
|------|-------------|-------------------|---------|-----------|------------|
| **Sept 1st** | 11 | 3 | 3 | **0** | **100%** ✅ |
| **Sept 2nd** | 20 | 10 | 5 | **3** | 62.5% |
| **Sept 3rd** | 22 | 12 | 6 | **3** | 66.7% |
| **Sept 5th** | 6 | 3 | 1 | **1** | 50% |

## 🔍 Common Issues Identified

### 1. **Client Code Issues** (High Priority)
- **NWM Client Code:** Recurring issue across multiple dates
  - Appears in OMS alerts but never has corresponding orders
  - Likely a test client or mapping issue
- **NEO280 Client Code:** Not found in order book
- **AARCA8739L Client Code:** New issue - price confirmed but no order placed
- **Client Code Validation:** Need pre-validation against order book

### 2. **Symbol Mapping Issues** (Medium Priority)
- **ETF Symbol Variations:** 
  - "ICICI Prudential Nifty Private Bank ETF" not mapping correctly
  - "NIPPON INDIA ETF GOLD BEES" needs better mapping
- **Bank Name Variations:**
  - "Canara Bank" not mapping to order symbols
- **Company Name Variations:**
  - "CG POWER AND INDUSTRIAL SOLUTIONS LTD" needs normalization

### 3. **Quantity Discrepancies** (High Priority)
- **Typo Detection:** 
  - 1,731,271.47 vs 1,731 (1000x difference)
  - 15,000 vs 20 (massive difference)
- **Value-Based Instructions:**
  - "Worth INR X" calculations need improvement

### 4. **Data Quality Issues** (Medium Priority)
- **OMS Alert Emails:** System-generated alerts vs actual trade instructions
- **Missing Details:** Some emails lack quantity/price information
- **Forwarded Emails:** Some instructions are in forwarded emails
- **Missing Client Codes:** Some trade instructions lack client codes entirely

## 🎯 System Improvements Needed

### Immediate Actions (High Priority)
1. **Investigate NWM Client Code** - This is a recurring issue
2. **Investigate AARCA8739L Client Code** - Price confirmed but no order placed
3. **Implement Client Code Validation** - Pre-validate against order book
4. **Add Quantity Typo Detection** - Detect potential data entry errors

### Short-term Improvements (Medium Priority)
1. **Enhance Symbol Mapping** - Add more comprehensive symbol variations
2. **Improve ETF Handling** - Better mapping for ETF names
3. **Better OMS Email Classification** - Distinguish alerts from instructions

### Long-term Enhancements (Low Priority)
1. **Value-Based Matching** - Improve "Worth INR X" calculations
2. **Confidence Scoring** - Adjust based on data quality
3. **Automated Issue Detection** - Flag potential problems automatically

## 📈 Performance Trends

- **Best Performance:** September 1st (100% match rate)
- **Average Performance:** 60-70% match rate
- **Main Bottleneck:** Client code validation and symbol mapping

## 🔧 Technical Recommendations

### 1. **Client Code Validation**
```python
# Pre-validate client codes against order book
def validate_client_code(client_code, order_book):
    return client_code in order_book.get_client_codes()
```

### 2. **Symbol Mapping Enhancement**
```python
# Add comprehensive symbol variations
SYMBOL_MAPPINGS = {
    "ICICI Prudential Nifty Private Bank ETF": ["ICICIPRIVBK", "PRIVBKETF"],
    "Canara Bank": ["CANBK", "CANARABANK"],
    "NIPPON INDIA ETF GOLD BEES": ["GOLDBEES", "NIFTYGOLD"]
}
```

### 3. **Quantity Validation**
```python
# Detect potential typos in quantities
def detect_quantity_typo(email_qty, order_qty):
    ratio = max(email_qty, order_qty) / min(email_qty, order_qty)
    return ratio > 100  # Flag if difference is >100x
```

## 📝 Documentation Standards

Each date's documentation includes:
- **Summary Statistics** - Total emails, match rates, etc.
- **Detailed Analysis** - Each unmatched email with reasons
- **Issue Categorization** - Client code, symbol, quantity issues
- **Recommendations** - Specific improvements needed
- **Performance Metrics** - Match rates and data quality scores

## 🚀 Next Steps

1. **Review each date's documentation** for specific issues
2. **Prioritize fixes** based on frequency and impact
3. **Implement improvements** in the email processing system
4. **Monitor results** and update documentation accordingly

---
*Generated on: $(date)*
*System: Trade Surveillance Email Processing*
*Last Updated: September 2025*
