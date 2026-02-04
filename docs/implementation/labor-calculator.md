# Labor Benefits Calculator (Dominican Republic)

## Overview

The `LaborCalculator` is a specialized tool developed to accurately compute labor benefits ("Prestaciones Laborales") based on the Labor Code of the Dominican Republic (Law 16-92). This tool provides high-fidelity results that match the official Ministry of Labor (MT) calculator while operating as an offline, deterministic micro-service component.

## Core Logic & Formulae

### 1. Salary Normalization

The most critical factor for matching official figures is the daily salary divisor.

- **Monthly to Daily Divisor**: `23.83`
- **Formula**: `Daily Rate = Monthly Salary / 23.83`
- **Note**: Intermediate calculations maintain high precision (Decimal 28+). Rounding is only applied to individual component totals for reporting.

### 2. Time Worked Calculation

Calculations are **inclusive** of the end date.

- **Tenure Computation**: `(End Date + 1 Day) - Start Date`
- This ensures that a worker leaving on Dec 31st after starting Jan 1st is credited with exactly 1 full year.

### 3. Benefit Logic (Standard Parameters)

#### Notice (Preaviso) - Art. 76

| Tenure         | Notice Days |
| -------------- | ----------- |
| 3 to 6 months  | 7 days      |
| 6 to 12 months | 14 days     |
| 1 year or more | 28 days     |

#### Severance (Cesantía) - Art. 80

| Tenure          | Severance Accrual |
| --------------- | ----------------- |
| 3 to 6 months   | 6 days            |
| 6 to 12 months  | 13 days           |
| 1 to 5 years    | 21 days per year  |
| 5 years or more | 23 days per year  |

**Progressive Accrual (> 1 year):**
Once the one-year threshold is crossed, fractional years accrue additional days based on the 3-6 and 6-12 month ranges.

#### Christmas Salary (Salario de Navidad)

- **Law**: One-twelfth of the total ordinary salary earned in the calendar year.
- **Implementation**: `(Sum of Monthly Salaries) / 12`
- For constant salaries, this simplifies to `Monthly Salary * (Months Worked in Year / 12)`.

## Technical Implementation

- **File**: `app/tools/labor_calculator.py`
- **Test Suite**: `tests/test_labor_calculator.py`
- **Language**: Python (utilizing `decimal` library for precise arithmetic).

## Validation Result (Golden Case)

Verified against MT Official Calculator:

- **Tenure**: 6 Years
- **Salary**: RD$ 29,988.00
- **Total Benefits**: RD$ 238,884.69 (Matches exactly)

---

_Last Updated: February 4, 2026_
