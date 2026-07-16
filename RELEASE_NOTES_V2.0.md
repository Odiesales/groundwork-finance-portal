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
