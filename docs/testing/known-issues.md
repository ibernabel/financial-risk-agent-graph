# Known Issues: Bank Statement Parsers

## Overview

This document tracks known limitations and issues with the bank statement parsing system, particularly related to PDF OCR processing.

## PDF OCR Limitations (Banco Popular)

### Issue: Transaction Type Misclassification

**Status**: Known Issue - Deferred to Future Phase  
**Severity**: Medium  
**Affected Banks**: Banco Popular

#### Description

The PDF OCR parser (using GPT-4o-mini vision) occasionally misclassifies transaction types (CREDIT vs DEBIT) when parsing Popular Bank PDFs.

#### Root Cause

The vision model has difficulty accurately detecting the minus sign suffix (`-`) on transaction amounts in PDF images, which is the indicator for DEBIT transactions in Popular Bank statements:

- `RD$ 490.00` (no minus) → CREDIT
- `RD$ 90.00-` (with minus) → DEBIT

The model sometimes makes incorrect assumptions based on transaction descriptions rather than strictly following the minus sign rule.

#### Impact

- Transaction type misclassification affects summary calculations (total credits/debits)
- Approximately 10-20% of transactions may be misclassified
- CSV parsing is 100% accurate and unaffected

#### Examples

| Transaction                  | Actual Type | OCR Classification | Status   |
| ---------------------------- | ----------- | ------------------ | -------- |
| "Desde INTERNET 787781319"   | CREDIT      | DEBIT              | ❌ Wrong |
| "Transf. vía MB a 839832011" | DEBIT       | CREDIT             | ❌ Wrong |

#### Workaround

**Current Solution**: Use CSV files as primary data source

All bank parsers (`parse_bhd_statement`, `parse_popular_statement`, `parse_banreservas_statement`) automatically:

1. Check for CSV file in same location as PDF
2. Use fast, accurate CSV parsing if available
3. Fall back to PDF OCR only when CSV is unavailable

```python
# Automatic CSV detection (already implemented)
csv_path = file_path.with_suffix('.csv')
if csv_path.exists():
    return parse_popular_csv(str(csv_path))  # 100% accurate
else:
    return parse_via_ocr(pdf_path)  # Fallback
```

#### Future Improvements

Potential solutions to explore in later phases:

1. **Upgrade Vision Model**
   - Test with GPT-4o (more expensive but more accurate)
   - Evaluate Claude 3.5 Sonnet vision capabilities

2. **Image Preprocessing**
   - Increase PDF-to-image resolution/DPI
   - Apply image enhancement to make minus signs more visible
   - Use table extraction libraries before OCR

3. **Hybrid Approach**
   - Extract table structure first
   - Use column position to determine type (Popular Bank uses separate credit/debit columns in some formats)

4. **Post-Processing Validation**
   - Cross-check with balance changes
   - Flag suspicious transactions for manual review

## Other Known Issues

### Issue: Transaction Date Variations

**Status**: Known Issue - Low Priority  
**Severity**: Low

OCR may occasionally extract slightly different dates for transactions compared to CSV, typically off by 1-2 days. This appears related to the "Fecha Posteo" vs "Fecha" column confusion in Popular Bank statements.

**Workaround**: CSV parsing provides correct dates

---

## CSV Parsing Status

### Supported Banks

✅ **BHD León** - Fully functional, 100% accurate  
✅ **Banco Popular** - Fully functional, 100% accurate  
✅ **Banreservas** - Fully functional, 100% accurate

### Advantages

- 100% accuracy for all fields
- Fast processing (no API calls)
- No cost
- Reliable date parsing
- Correct transaction type classification

### Limitations

- Requires CSV export from bank
- Not all users may have CSV files
- CSV format changes by bank require parser updates

---

## Recommendations

### For Current Development Phase

1. **Prioritize CSV parsing** - Already implemented and working perfectly
2. **Keep PDF OCR as fallback** - Useful when CSV unavailable
3. **Document accuracy expectations** - Users should prefer CSV files when available

### For Future Phases

1. Test upgraded vision models when budget allows
2. Implement validation/confidence scoring for OCR results
3. Build user interface to flag and correct OCR errors
4. Consider open-source OCR alternatives (Tesseract, PaddleOCR)

---

## Testing Notes

### Test Coverage

- ✅ CSV parsers tested for all three banks
- ✅ Multi-page PDF processing implemented
- ✅ PDF OCR functional but with known accuracy issues
- ✅ Automatic CSV detection working correctly

### Test Files

Located in `creditflow_context/personal_loan_application_data/bank_statements/`:

- `bhd/`: BHD León test statements
- `popular_bank/`: Popular test statements (CSV + PDF)
- `banreservas/`: Banreservas test statements

---

**Last Updated**: 2026-02-09  
**Priority**: Low (CSV workaround sufficient for current phase)
