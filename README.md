# Groundwork Finance Portal

Streamlit dashboard for Groundwork Coffee finance reporting.

## Included pages
- Executive Summary
- Accounts Receivable
- Revenue & Pricing
- Trends
- Admin

## Weekly workflow
1. Export AR Aging and/or Revenue from NetSuite.
2. Open **Admin**.
3. Upload the file.
4. Select the snapshot / week-ending date.
5. Click **Save Snapshot**.
6. Review Executive, Revenue, AR, and Trends pages.

## Run locally
```bash
streamlit run app.py
```

## Deploy
Push this folder to GitHub and connect the repo to Streamlit Cloud. The app entry point is:

```text
app.py
```

## Notes
- Snapshot CSVs are stored in `data/snapshots/ar` and `data/snapshots/revenue`.
- Current cleaned files are stored in `data/exports`.
- Keep `.venv`, `__pycache__`, and old ZIP/backups out of Git.
