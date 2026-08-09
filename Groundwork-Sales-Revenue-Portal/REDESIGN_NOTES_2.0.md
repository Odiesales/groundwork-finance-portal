# Groundwork Finance Portal 2.0 - Redesign Foundation

Implemented:
- Groundwork mustard/yellow accent palette with charcoal sidebar and light cream background.
- Dark text on all light UI surfaces.
- New Chargebacks page with filters for customer, sales channel, deduction type, sales rep, and view.
- Chargeback KPIs are point-in-time balances from the selected AR aging snapshot (As of Date), not YTD.
- `Transaction Reason` renamed to `Deduction Type`.
- Older saved snapshots containing `Transaction Reason` are automatically upgraded when loaded.
- Holdbacks remain `Transaction Type = Invoice` and `Deduction Type = Holdback`.
- Holdbacks are excluded from chargeback KPIs and can be reviewed in a separate Holdbacks (Invoices) view.
- Customer and deduction-type summaries, snapshot matrix, charts, and sortable detail table added.

Validation:
- Python compilation completed successfully for app.py, pages, and utils.
- Streamlit runtime preview was not available in the build environment because Streamlit is not installed there.
