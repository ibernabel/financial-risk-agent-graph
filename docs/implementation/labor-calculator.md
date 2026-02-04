# Labor Benefits Calculator Implementation

The Labor Benefits Calculator is a deterministic tool designed to calculate legal compensation (Prestaciones Laborales) according to the Dominican Republic Labor Code.

## Features

- **Inclusive Time Calculation**: Correctly handles date ranges as inclusive (e.g., Jan 1 to Dec 31 is 1 full year).
- **Notice Pay (Preaviso)**: Calculates days and amount based on Art. 76.
- **Severance Pay (Cesantía)**: Calculates days and amount based on Art. 80, including fractional years.
- **Christmas Salary (Salario de Navidad)**: Calculates the proportional amount for the current calendar year.
- **Type Safety**: Uses `TypedDict` and strict type hints for robust data handling.
- **Validation**: Ensures logical date ranges and positive salary inputs.

## Technical Details

### Key Classes

- `LaborCalculator`: Main engine for calculation.
- `LaborBenefitResult`: Schema for the calculation output.

### Constants

- `DAILY_SALARY_DIVISOR`: `23.83` (Standard DIVARD divisor).

### Calculation Logic

#### Time Difference

The tool calculates years, months, and days by adding 1 day to the end date to ensure inclusivity.

#### Notice (Art. 76)

- > = 1 year: 28 days
- 6-12 months: 14 days
- 3-6 months: 7 days

#### Severance (Art. 80)

- > = 5 years: 23 days per year
- 1-5 years: 21 days per year
- 6-12 months: 13 days
- 3-6 months: 6 days
- _Fractional_: If >= 1 year, extra months are added:
  - 6-12 months: +13 days
  - 3-6 months: +6 days

## Usage

```python
from datetime import date
from decimal import Decimal
from app.tools.labor_calculator import LaborCalculator

calc = LaborCalculator()
result = calc.calculate(
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    monthly_salary=Decimal("30000")
)

print(result['total_received'])
```
