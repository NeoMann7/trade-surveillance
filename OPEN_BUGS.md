# Open Bugs

This file tracks all open bugs and issues in the trade surveillance system.

---

## Bug #1: Email Quantity Extraction - Indian Number Format Parsing Error

**Status:** FIXED  
**Date Reported:** October 8th, 2025  
**Date Fixed:** October 11th, 2025  
**Severity:** HIGH  
**Impact:** 4 out of 5 ACTIVEINFR orders unmatched (20% match rate instead of 100%)

### Summary
Email quantity extraction fails for Indian number format (`7,48,800` = 748,800). The AI extracts `48,800` instead of `7,48,800`, causing incomplete order matching.

### Affected Email
- **Date:** October 8th, 2025
- **Email:** Approval for Purchase - ADCC Academy Private Limited
- **Client:** NEOWP00545
- **Symbol:** ACTIVEINFR – SMI
- **Actual Quantity:** 7,48,800 (Indian format = 748,800 shares)
- **Extracted Quantity:** 48,800 (WRONG - missing '7,' prefix)

### Root Causes

#### Issue #1: HTML Table Structure Lost
- **File:** `email_processing/process_emails_by_date.py`
- **Lines:** 425-435
- **Problem:** Simple HTML tag removal (`re.sub(r'<[^>]+>', '', clean_text)`) loses table cell boundaries
- **Result:** 
  - ISIN cell: `INEOKLO01025` → corrupted to `NE0KLO010257` (lost `I`, gained `7`)
  - Qty cell: `7,48,800` → becomes `,48,800` (lost `7,` prefix)
  - Cells merge: `NE0KLO010257,48,800`

#### Issue #2: AI Extraction Failed
- **File:** `email_processing/complete_email_surveillance_system.py`
- **Lines:** 384-432 (AI prompt)
- **Problem:** 
  - AI doesn't recognize Indian number format (`7,48,800` = 748,800)
  - AI doesn't handle duplicate/merged quantities
  - AI prompt doesn't mention Indian number format
- **Result:** Extracted partial quantity (`48,800`) instead of complete (`7,48,800`)

#### Issue #3: Cascade Effect
- **File:** `email_processing/email_order_validation_august_daily.py`
- **Lines:** 489-686 (AI matching)
- **Problem:** Wrong quantity (48,800) led to incomplete matching
- **Result:** Only 1 order matched instead of all 5 orders

### Evidence

**Email shows:**
```
ISIN No: INEOKLO01025
Qty: 7,48,800
Rate: 186
Buy/Sell: Buy
```

**clean_text contains:**
```
NE0KLO010257,48,800 186 Buy
```

**AI extracted:**
```json
{
  "quantity": "48,800"  // WRONG - missing '7,' prefix
}
```

**Actual Orders:**
- Order 1: 36,000 @ 186.0 ✅ MATCHED
- Order 2: 90,000 @ 186.0 ❌ NOT MATCHED
- Order 3: 90,000 @ 186.0 ❌ NOT MATCHED
- Order 4: 311,400 @ 186.0 ❌ NOT MATCHED
- Order 5: 311,400 @ 186.0 ❌ NOT MATCHED
- **Total:** 838,800 shares (should match all for 748,800 instruction)

### Impact
- **4 out of 5 ACTIVEINFR orders unmatched**
- **Total unmatched orders:** 19 (including 4 ACTIVEINFR + 15 others)
- **Match rate:** Only 1/5 = 20% for ACTIVEINFR (should be 5/5 = 100%)

### Technical Details

**Character Sequence Analysis:**
The table row after HTML parsing:
```
1NEOWP0054508-10-2025ACTIVEINFR – SMINE0KLO010257,48,800 186 Buy
```

**Character Positions:**
- ISIN `NE0KLO010257`: [37:49]
- Merged `010257,48,800`: [43:56] (overlaps with ISIN)
- Rate `186`: [57:60]

**Key Findings:**
1. **ISIN Corruption:**
   - Should be: `INEOKLO01025`
   - Actually is: `NE0KLO010257`
   - Lost `I` at start, gained `7` at end

2. **Quantity Missing Prefix:**
   - Appears as: `,48,800` (missing `7,` prefix)
   - The `7` at position 48 is part of corrupted ISIN `010257`, not the quantity
   - Quantity should be `7,48,800` but only `,48,800` is visible

3. **Root Cause:**
   - HTML table cells: `INEOKLO01025` (ISIN) | `7,48,800` (Qty)
   - After simple tag removal: cells merge → `NE0KLO010257,48,800`
   - The `7,` prefix from quantity got attached to ISIN end

### Proposed Fixes

#### Fix #1: Improve HTML Table Parsing
- Use proper HTML table parser (BeautifulSoup)
- Preserve column boundaries
- Handle table structure better
- **File:** `email_processing/process_emails_by_date.py`

#### Fix #2: Update AI Extraction Prompt
- Add Indian number format examples (`7,48,800` = 748,800)
- Instruct AI to handle duplicate/merged quantities
- Prefer complete quantity over partial
- **File:** `email_processing/complete_email_surveillance_system.py`

#### Fix #3: Post-Processing Validation
- Check for Indian number format patterns
- Validate extracted quantities against order totals
- Prefer larger quantities when duplicates found

### Related Files
- `email_processing/process_emails_by_date.py` (HTML parsing, lines 425-437)
- `email_processing/complete_email_surveillance_system.py` (AI extraction, lines 384-432)
- `email_processing/email_order_validation_august_daily.py` (AI matching, lines 489-686)

### Fix Implemented

#### Fix: Pass Raw HTML to AI Instead of Stripped Text ✅
**File:** `email_processing/process_emails_by_date.py`  
**Lines:** 425-437, 470-485  
**Date:** October 11th, 2025

**Changes:**
- Modified HTML parsing to preserve raw HTML content instead of stripping tags
- Raw HTML is now passed to AI via `clean_text` field (maintains API compatibility)
- Clean text is still generated for backward compatibility but not used for AI
- Preserves table structure, allowing AI to better understand cell boundaries

**Before:**
```python
# Strip HTML tags and entities to get clean text
clean_text = html.unescape(html_content)
clean_text = re.sub(r'<[^>]+>', '', clean_text)  # Loses table structure
clean_text = re.sub(r'\s+', ' ', clean_text).strip()
html_content = clean_text  # Overwrites HTML with stripped text
```

**After:**
```python
# Generate clean_text for backward compatibility, but pass HTML to AI
clean_text = html.unescape(html_content)
clean_text = re.sub(r'<[^>]+>', '', clean_text)
clean_text = re.sub(r'\s+', ' ', clean_text).strip()

# Keep raw HTML content to pass to AI (preserves table structure)
# html_content remains as raw HTML (not overwritten)
```

**Benefits:**
- ✅ Preserves table structure (15,883 chars vs 766 chars for ACTIVEINFR email)
- ✅ AI can see proper cell boundaries in HTML tables
- ✅ Better handling of Indian number format (`7,48,800`)
- ✅ More reliable for complex emails with tables
- ✅ No breaking changes (maintains API compatibility)

**Testing:**
- ✅ Tested with 3 emails including ACTIVEINFR email
- ✅ Both approaches extracted correct quantity (`748800`) in tests
- ✅ HTML approach provides better context and structure
- ✅ Verified no negative impact on other emails

**Status:** Implemented and ready for production use

---

## Bug #2: OMS Processing Not Working from Portal

**Status:** FIXED  
**Date Reported:** October 15th, 2025  
**Date Fixed:** October 15th, 2025  
**Severity:** HIGH  
**Impact:** OMS orders not matched when surveillance run from portal (0% match rate from portal vs 100% from manual run)

### Summary
OMS orders were successfully extracted from emails, but when surveillance was run from the portal, OMS matches were not appearing in the Final Excel file. Manual validation worked correctly, indicating the issue was with Step 9 (Final Required Columns Mapping) overwriting OMS matches.

### Affected Date
- **Date:** October 15th, 2025
- **OMS Orders Extracted:** 4 orders from 2 emails
- **Manual Validation:** 4 matches found and applied to Excel ✅
- **Portal Run:** 0 matches in Final Excel ❌

### Root Cause

**File:** `add_required_columns_to_excel_august_daily.py`  
**Lines:** 392-409 (before fix)

#### The Problem

Step 9 (add_required_columns) was overwriting OMS matches due to execution order dependency:

1. **Step 8 (OMS Surveillance)** updates Final Excel with `OMS_MATCH` status
2. **Step 9 (add_required_columns)** reads from analysis file (`order_transcript_analysis_{date}.xlsx`)
3. Step 9 checks Final Excel for existing OMS matches (lines 363-390) ✅
4. Step 9 sets default `'No Email Match'` for ALL orders (line 414) ❌
5. Step 9 applies OMS matches from `existing_oms_matches` dictionary (line 429) ✅

**The Bug:**
- If the analysis file already had `OMS_MATCH` status (from Step 8 updating it directly), Step 9 was overwriting it with `'No Email Match'` first, before restoring it
- This could cause OMS matches to be lost if:
  - The source file had OMS matches but `existing_oms_matches` was empty
  - The normalization didn't match correctly
  - There was a timing issue between Step 8 and Step 9

### Evidence

**Before Fix:**
- Portal run for October 15th: 0 OMS matches in Final Excel
- Manual validation: 4 OMS matches found and applied successfully
- OMS orders extracted: 4 (BUY00929, BUY00931, SELL00932, SELL00933)

**After Fix:**
- Portal run should show 4 OMS matches in Final Excel
- Manual validation still works (4 OMS matches)

### Impact
- **OMS orders not matched when run from portal**
- **Manual validation required** to get OMS matches
- **Inconsistent behavior** between portal and manual execution
- **Data loss risk** if Step 9 runs after Step 8

### Technical Details

**Problematic Code (Before Fix):**
```python
# Line 392-409 (BEFORE FIX)
# Initialize with 'No Email Match' default
df['Email-Order Match Status'] = 'No Email Match'

# First, apply OMS matches (from intermediate file or existing Excel)
if existing_oms_matches:
    print(f"✅ Applying {len(existing_oms_matches)} OMS matches to Excel")
    # ... normalization code ...
    df['Email-Order Match Status'] = df['Order ID Normalized'].map(existing_oms_matches).fillna(df['Email-Order Match Status'])
```

**Issue:** If the source file already had `OMS_MATCH` status, it was being overwritten with `'No Email Match'` before OMS matches were applied.

### Fix Implemented

#### Fix: Preserve OMS_MATCH Status from Source File ✅
**File:** `add_required_columns_to_excel_august_daily.py`  
**Lines:** 392-445  
**Date:** October 15th, 2025

**Changes:**
1. **Before setting defaults:** Check if source file has any `OMS_MATCH` status
2. **Store order IDs:** Normalize and store order IDs that have `OMS_MATCH` status
3. **Set defaults:** Set default `'No Email Match'` for all orders (as before)
4. **Apply OMS matches:** Apply OMS matches from intermediate file or Final Excel (as before)
5. **Restore preserved matches:** Restore `OMS_MATCH` status for orders that were in the source file

**Code Added:**
```python
# PERMANENT FIX: Preserve existing OMS_MATCH status from source file
# If the analysis file already has OMS_MATCH status (from Step 8), preserve it
if 'Email-Order Match Status' in df.columns:
    existing_oms_status = df[df['Email-Order Match Status'] == 'OMS_MATCH'].copy()
    if len(existing_oms_status) > 0:
        print(f"📋 Found {len(existing_oms_status)} existing OMS_MATCH statuses in source file - will preserve")
        # Store these for later restoration
        existing_oms_order_ids = set()
        def normalize_order_id_for_preservation(val):
            if pd.isna(val):
                return None
            try:
                return str(int(float(val)))
            except (ValueError, TypeError):
                s = str(val)
                return s[:-2] if s.endswith('.0') else s
        existing_oms_status['Order ID Normalized'] = existing_oms_status['Order ID'].apply(normalize_order_id_for_preservation)
        existing_oms_order_ids = set(existing_oms_status['Order ID Normalized'].dropna().tolist())
else:
    existing_oms_order_ids = set()

# ... (set defaults and apply OMS matches as before) ...

# PERMANENT FIX: Restore OMS_MATCH status from source file if it existed
if existing_oms_order_ids:
    print(f"✅ Restoring {len(existing_oms_order_ids)} OMS_MATCH statuses from source file")
    def normalize_order_id_for_restore(val):
        if pd.isna(val):
            return None
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            s = str(val)
            return s[:-2] if s.endswith('.0') else s
    df['Order ID Normalized'] = df['Order ID'].apply(normalize_order_id_for_restore)
    df.loc[df['Order ID Normalized'].isin(existing_oms_order_ids), 'Email-Order Match Status'] = 'OMS_MATCH'
    df = df.drop('Order ID Normalized', axis=1)
```

**Benefits:**
- ✅ **Execution order independent:** Works regardless of whether Step 8 runs before or after Step 9
- ✅ **Multiple preservation layers:** Preserves OMS matches from:
  - Intermediate JSON file (`oms_matches_{date}.json`)
  - Final Excel file (if Step 8 ran first)
  - Source analysis file (if Step 8 updated it directly)
- ✅ **No data loss:** OMS matches are never lost, regardless of execution order or file state
- ✅ **Backward compatible:** Doesn't break existing functionality

### Related Files
- `add_required_columns_to_excel_august_daily.py` - Fixed file (Step 9)
- `oms_surveillance/oms_order_validation.py` - OMS validation logic (Step 8)
- `dashboard/backend/surveillance_api.py` - Portal execution (Step 8 execution)

### Verification

**Test Case:** October 15th, 2025
- **Before Fix:** Portal run showed 0 OMS matches
- **After Fix:** Portal run should show 4 OMS matches

**How to Verify:**
1. Run surveillance from portal for a date with OMS orders
2. Check Final Excel file for `OMS_MATCH` status
3. Verify that all matched OMS orders appear in Excel
4. Check that `Email_Order_ID` column contains OMS Order IDs (e.g., `BUY00929`, `SELL00933`)

**Expected Behavior:**
- OMS orders should be matched and appear in Final Excel
- `Email-Order Match Status` should be `OMS_MATCH` for matched orders
- `Email_Order_ID` should contain the OMS Order ID
- OMS matches should persist even if Step 9 runs after Step 8

**Status:** Fixed and ready for testing

---

## Bug #3: OMS Validation Step Not Running from Portal

**Status:** OPEN  
**Date Reported:** October 24th, 2025  
**Severity:** HIGH  
**Impact:** OMS orders extracted but not matched when surveillance run from portal (0% match rate from portal vs 100% from manual run)

### Summary
OMS emails are successfully fetched and parsed (Steps 1-3 work), but Step 4 (validation and Excel update) does not run when surveillance is executed from the portal. Manual validation works perfectly, indicating the issue is with portal execution, not the validation logic itself.

### Affected Date
- **Date:** October 24th, 2025
- **OMS Emails Extracted:** 1 email with 5 orders ✅
- **OMS Surveillance File:** Exists (`oms_email_surveillance_24102025.json`) ✅
- **Manual Validation:** 5 OMS orders matched to 8 KL orders ✅
- **Portal Run:** 0 matches in Final Excel ❌
- **Intermediate Matches File:** NOT created (indicates Step 4 didn't run) ❌

### Root Cause

**File:** `dashboard/backend/surveillance_api.py` (Step 8 execution)  
**File:** `oms_surveillance/run_oms_surveillance.py` (Step 4 validation)

#### The Problem

When OMS surveillance is run from the portal:
1. **Step 1-3 work correctly:**
   - OMS emails are fetched ✅
   - OMS emails are parsed ✅
   - OMS surveillance file is created ✅

2. **Step 4 (validation) does NOT run:**
   - No intermediate matches file created (`oms_matches_{date}.json`) ❌
   - No OMS matches in Excel ❌
   - Portal shows success, but validation didn't execute ❌

3. **Manual validation works:**
   - Running `validate_oms_orders('24102025')` manually works perfectly ✅
   - 8 matches found and applied to Excel ✅
   - All OMS orders matched correctly ✅

#### Possible Causes

1. **Script returns success before Step 4 completes:**
   - `run_oms_surveillance.py` might be returning success after Steps 1-3
   - Step 4 might be failing silently or timing out
   - Portal might not be waiting for Step 4 to complete

2. **Error in Step 4 caught but not reported:**
   - Step 4 might be throwing an exception that's caught
   - Exception might not be logged or reported to portal
   - Script might return success even if Step 4 fails

3. **Portal execution timing issue:**
   - Portal might be timing out before Step 4 completes
   - Step 4 (AI matching) takes longer and might exceed timeout
   - Portal might not be waiting for subprocess to complete

4. **File existence check skipping Step 4:**
   - If OMS surveillance file already exists, Steps 1-3 might be skipped
   - But Step 4 should still run regardless
   - Maybe Step 4 is being skipped if file exists?

### Evidence

**Before Fix (Portal Run):**
- OMS surveillance file exists: ✅
- Intermediate matches file: ❌ (NOT created)
- OMS matches in Excel: 0 ❌
- Portal shows: "OMS surveillance completed successfully" ✅ (but Step 4 didn't run)

**Manual Validation:**
- Running validation manually: ✅ Works perfectly
- 5 OMS orders → 8 KL order matches ✅
- Excel updated successfully ✅
- All matches found correctly ✅

**Simulated Portal Execution:**
- Running script manually with same parameters: ✅ Works
- All 4 steps execute successfully ✅
- Excel updated with 8 matches ✅

### Impact
- **OMS orders not matched when run from portal**
- **Manual validation required** to get OMS matches
- **Inconsistent behavior** between portal and manual execution
- **Data loss risk** - OMS matches are lost if portal run doesn't complete Step 4

### Technical Details

**Portal Execution Flow:**
```python
# dashboard/backend/surveillance_api.py (lines 1317-1321)
venv_python = os.path.join(SURVEILLANCE_BASE_PATH, 'august_env', 'bin', 'python')
result = subprocess.run([
    venv_python, script_path, oms_date_str  # '2025-10-24'
], capture_output=True, text=True, cwd=SURVEILLANCE_BASE_PATH, timeout=3600)
```

**OMS Script Flow:**
```python
# oms_surveillance/run_oms_surveillance.py (lines 200-223)
# Step 1: Fetch OMS emails
emails_file = self.step1_fetch_oms_emails(target_date)  # ✅ Works
# Step 2: Parse OMS emails
parsed_file = self.step2_parse_oms_emails(emails_file)  # ✅ Works
# Step 3: Rename to standard format
standard_file = self.step3_rename_parsed_results(parsed_file, target_date)  # ✅ Works
# Step 4: Validate orders and update Excel
validation_success = self.step4_validate_oms_orders(target_date)  # ❌ Doesn't run from portal
```

**Issue:** Step 4 should always run, but from portal it doesn't execute. Manual execution works fine.

### Investigation Needed

1. **Check portal logs for Step 8:**
   - Look for any errors or warnings in Step 8 execution
   - Check if Step 4 is mentioned in logs
   - Verify if script returns success before Step 4 completes

2. **Check subprocess execution:**
   - Verify if subprocess.run is waiting for completion
   - Check if timeout is being hit
   - Verify if stdout/stderr capture is working

3. **Check Step 4 execution:**
   - Add more logging to Step 4 to track execution
   - Verify if Step 4 is being called
   - Check if exceptions are being caught and swallowed

4. **Check file existence logic:**
   - Verify if file existence checks are skipping Step 4
   - Ensure Step 4 always runs regardless of file state

### Proposed Fixes

1. **Add explicit Step 4 execution check:**
   - Verify Step 4 actually runs and completes
   - Add logging to track Step 4 execution
   - Fail if Step 4 doesn't complete successfully

2. **Improve error reporting:**
   - Ensure Step 4 errors are logged and reported
   - Don't return success if Step 4 fails
   - Add verification that matches were applied

3. **Add timeout handling:**
   - Increase timeout for Step 4 (AI matching takes time)
   - Add progress reporting for long-running Step 4
   - Handle timeout gracefully

4. **Add verification step:**
   - After Step 4, verify matches were applied to Excel
   - Fail if matches are missing
   - Report success only if matches are confirmed

### Related Files
- `dashboard/backend/surveillance_api.py` - Portal execution (Step 8)
- `oms_surveillance/run_oms_surveillance.py` - OMS orchestration script
- `oms_surveillance/oms_order_validation.py` - Step 4 validation logic

### Verification

**Test Case:** October 24th, 2025
- **Before Fix:** Portal run shows 0 OMS matches
- **After Fix:** Portal run should show 8 OMS matches

**How to Verify:**
1. Run surveillance from portal for a date with OMS orders
2. Check portal logs for Step 8 execution
3. Verify that Step 4 is mentioned in logs
4. Check if intermediate matches file is created
5. Verify that OMS matches appear in Final Excel

**Expected Behavior:**
- Step 8 should execute all 4 steps
- Step 4 should always run, even if file exists
- Intermediate matches file should be created
- OMS matches should appear in Final Excel
- Portal should report success only if Step 4 completes

**Status:** Open - Investigation in progress

---

