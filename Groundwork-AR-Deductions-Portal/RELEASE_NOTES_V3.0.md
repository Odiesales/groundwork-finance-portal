# Groundwork Finance Portal v3.0

## Revenue
- Rebuilt the revenue cleaner around the approved formula: `Line Pounds = Sum of # of Units x weight by lbs`.
- Calculates line-level `$ / LB = Revenue / Line Pounds`.
- Calculates dashboard weighted `$ / LB = eligible revenue / eligible pounds`; row-level values are never averaged.
- Included the March 1 through July 2026 historical workbook as the new consolidated baseline.
- Added append-new-week, replace-existing-week, duplicate-week protection, and delete-week controls.
- Added Revenue upload previews and data-health checks.

## Accounts Receivable and Chargebacks
- Added multi-select filters.
- Fixed empty-filter result handling on the AR customer summary.
- Preserved Holdback classification as Invoice with Deduction Type = Holdback.

## Administration
- Split Administration into AR Upload, Revenue History, and Data Health tabs.
- Added consolidated Revenue history management and validation.
