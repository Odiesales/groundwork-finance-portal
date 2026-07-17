# Groundwork Finance Portal v2.0

## Release status
Validated release candidate for CEO review and Streamlit deployment.

## Consolidated fixes
- Centralized Streamlit page configuration in `app.py` so navigation pages no longer attempt conflicting configuration calls.
- Repaired the shared CSS runtime error in `utils/ui.py` and added the missing pale status-card color variable.
- Standardized light-theme text, filters, tables, buttons, page banners, and sidebar styling.
- Updated deprecated Streamlit width parameters to the current `width="stretch"` API.
- Clarified Admin upload dates as the Monday reporting/snapshot date.
- Added overwrite warnings when an AR or Revenue snapshot already exists for the selected date.
- Preserved existing AR, chargeback, holdback, revenue, and snapshot calculations.

## Validation performed
- Python compilation completed successfully.
- Streamlit application health endpoint returned `ok`.
- Streamlit runtime tests passed with zero exceptions for:
  - Main application / navigation
  - Executive Scorecard
  - Accounts Receivable
  - Chargebacks
  - Weekly Revenue Report
  - Trends
  - Administration

## Deployment
Upload the contents of this folder to the existing GitHub repository and redeploy/reboot the Streamlit app. The entry point remains `app.py`.

## July 16, 2026 UI update
- Increased and darkened graph axis, legend, data-label, and hover fonts across the portal.
- Added Chargebacks filters for Customer, Deduction Type, Channel, Sales Rep, and Bucket.
- Kept Holdbacks available as a separate invoice view and excluded from chargeback KPIs.

## Chargebacks sidebar filter fix
- Moved Record View, Customer, Deduction Type, Channel, Sales Rep, and Bucket filters into the left navigation sidebar.
- Corrected sidebar select and multiselect text styling so selected values and dropdown options remain readable.

## AR executive layout refresh
- Rebuilt the Accounts Receivable sidebar filters as clearly labeled single-select fields with an `All` option.
- Added a one-click Clear Filters button.
- Fixed white-on-black and blank selected-value issues in sidebar and page dropdowns.
- Updated the Executive Summary cards with icons, supporting context, and a cleaner compact layout.
- Simplified Top 25 Customer Exposure to an executive table with rank, channel, sales rep, terms, past due, total AR, and share of total AR.
- Added a Top 25 CSV export.
