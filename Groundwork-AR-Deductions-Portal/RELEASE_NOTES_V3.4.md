# Groundwork Finance Portal v3.4

## Google Drive persistence
- Connects with the `[gcp_service_account]` Streamlit Secrets section.
- Finds the shared `Groundwork Finance Portal` folder automatically.
- Creates `Accounts Receivable` and `Revenue` subfolders when needed.
- Saves AR snapshots to Google Drive when **Save AR Snapshot** is clicked.
- Saves the consolidated Revenue history to Google Drive after uploads or deletions.
- Downloads the shared cloud data once when a browser session starts.
- Adds Google Drive connection status and a manual **Sync from Drive** button to Administration.
- Keeps local processing available and displays a clear error if a cloud save fails.

## Dependencies
- Added `google-api-python-client` and `google-auth`.

## Important Google Drive note
New service accounts generally cannot own files in a normal personal My Drive folder. If Google reports a storage quota error, move the portal folder into a Google Workspace Shared Drive and give the service account Content manager access.
