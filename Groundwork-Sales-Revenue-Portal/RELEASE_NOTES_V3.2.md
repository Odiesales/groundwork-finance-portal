# Groundwork Finance Portal v3.2

- Preserves every existing dated AR snapshot during code updates and new uploads.
- Uses dated AR snapshots as the source of truth for the current snapshot date.
- Adds an AR Snapshot Manager with selective, confirmed deletion.
- Automatically refreshes current_ar_clean.csv from the newest remaining snapshot after save or deletion.
- Corrects MoM Revenue currency, quantity, and percentage formatting.
- Simplifies AR Snapshot Comparison to Total AR, Current, and Past Due.
- Improves AR Snapshot History formatting.

## Data safety
This update package intentionally excludes the data folder. Copying the update into an existing project will not overwrite uploaded AR snapshots or Revenue history.
