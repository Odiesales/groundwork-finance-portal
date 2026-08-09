# Groundwork Finance Portal v3.1

Implemented feedback from Feedback.docx in one consolidated build.

## Accounts Receivable
- Added selectable As of Date and Compare Against snapshot controls.
- Added WoW comparison amounts and percentages to AR KPI cards.
- Added Top 25, Top 50, and All options for Customer Exposure.
- Added section-level CSV exports for Customer Exposure, Suggested Holds, Collection Priority, and Chargeback Center.

## Chargebacks
- Added Top 10, Top 25, and All chart-row controls.
- Moved value labels inside horizontal bars.
- Added export for the filtered chargeback/holdback detail.

## Weekly Revenue
- Added a numbers-first weekly summary table with export.
- Removed duplicate chart titles that were overlapping legends.
- Added selected-week detail export.

## Trends
- Rebuilt Trends as a numbers-first page.
- Replaced the primary YoY emphasis with Month-over-Month revenue reporting.
- Added selectable AR As of Date and Compare Against controls.
- Added AR snapshot comparison, all-snapshot history, WoW change, and section exports.

## Validation
- Python syntax compilation passed for the complete project.
- Streamlit runtime smoke testing was not available in the build environment because Streamlit is not installed there.
