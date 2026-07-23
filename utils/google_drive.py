"""Google Drive persistence for the Groundwork Finance Portal.

The app uses a service account stored in Streamlit Secrets under
[gcp_service_account]. The shared Drive folder must be named
"Groundwork Finance Portal" and shared with the service account as Editor.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from utils.paths import AR_SNAPSHOT_DIR, REVENUE_HISTORY_PATH, CURRENT_REVENUE_PATH

SCOPES = ["https://www.googleapis.com/auth/drive"]
ROOT_FOLDER_NAME = "Groundwork Finance Portal"
AR_FOLDER_NAME = "Accounts Receivable"
REVENUE_FOLDER_NAME = "Revenue"


class DriveConfigurationError(RuntimeError):
    pass


def _secret_dict() -> dict[str, Any]:
    try:
        section = st.secrets["gcp_service_account"]
    except Exception as exc:
        raise DriveConfigurationError(
            "Streamlit Secrets is missing the [gcp_service_account] section."
        ) from exc
    return section.to_dict() if hasattr(section, "to_dict") else dict(section)


@st.cache_resource(show_spinner=False)
def drive_service():
    info = _secret_dict()
    required = {"type", "project_id", "private_key", "client_email", "token_uri"}
    missing = sorted(required.difference(info))
    if missing:
        raise DriveConfigurationError(
            "Google credentials are incomplete. Missing: " + ", ".join(missing)
        )
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _escape(value: str) -> str:
    return value.replace("'", "\\'")


def _shared_drive_id() -> str:
    try:
        section = st.secrets["gdrive"]
        drive_id = str(section.get("root_folder_id", "")).strip()
    except Exception as exc:
        raise DriveConfigurationError(
            "Streamlit Secrets is missing [gdrive] root_folder_id."
        ) from exc
    if not drive_id:
        raise DriveConfigurationError(
            "Streamlit Secrets [gdrive] root_folder_id is blank."
        )
    return drive_id


def _list_files(query: str, fields: str = "files(id,name,mimeType,modifiedTime,size)") -> list[dict]:
    service = drive_service()
    drive_id = _shared_drive_id()
    files: list[dict] = []
    token = None
    while True:
        response = service.files().list(
            q=query,
            corpora="drive",
            driveId=drive_id,
            spaces="drive",
            fields=f"nextPageToken,{fields}",
            pageToken=token,
            pageSize=1000,
            orderBy="modifiedTime desc",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files.extend(response.get("files", []))
        token = response.get("nextPageToken")
        if not token:
            return files

def _find_folder(name: str, parent_id: str | None = None) -> dict | None:
    clauses = [
        f"name = '{_escape(name)}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
    ]
    if parent_id:
        clauses.append(f"'{parent_id}' in parents")
    matches = _list_files(" and ".join(clauses))
    return matches[0] if matches else None


def _create_folder(name: str, parent_id: str) -> dict:
    return drive_service().files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id,name,mimeType",
        supportsAllDrives=True,
    ).execute()


@st.cache_data(ttl=300, show_spinner=False)
def portal_folder_ids() -> dict[str, str]:
    drive_id = _shared_drive_id()
    try:
        drive_service().drives().get(
            driveId=drive_id,
            fields="id,name",
        ).execute()
    except Exception as exc:
        raise DriveConfigurationError(
            "The configured Shared Drive ID could not be opened. "
            "Make sure the service account was added as a member of the Shared Drive "
            "with Content manager access, not merely shared on a folder."
        ) from exc

    # The Shared Drive ID is also the root folder ID for file operations.
    root_id = drive_id
    ar = _find_folder(AR_FOLDER_NAME, root_id) or _create_folder(AR_FOLDER_NAME, root_id)
    revenue = _find_folder(REVENUE_FOLDER_NAME, root_id) or _create_folder(REVENUE_FOLDER_NAME, root_id)
    return {"root": root_id, "ar": ar["id"], "revenue": revenue["id"]}


def connection_test() -> tuple[bool, str]:
    try:
        drive_id = _shared_drive_id()
        drive = drive_service().drives().get(
            driveId=drive_id,
            fields="id,name",
        ).execute()
        portal_folder_ids()
        return True, f'Connected to Shared Drive: {drive.get("name", "Google Drive")}'
    except Exception as exc:
        return False, str(exc)

def _remote_file(name: str, folder_id: str) -> dict | None:
    matches = _list_files(
        f"name = '{_escape(name)}' and '{folder_id}' in parents and trashed = false"
    )
    return matches[0] if matches else None


def upload_file(local_path: Path, folder_key: str, remote_name: str | None = None) -> dict:
    local_path = Path(local_path)
    if not local_path.exists():
        raise FileNotFoundError(local_path)
    folder_id = portal_folder_ids()[folder_key]
    name = remote_name or local_path.name
    media = MediaFileUpload(str(local_path), mimetype="text/csv", resumable=False)
    existing = _remote_file(name, folder_id)
    try:
        if existing:
            result = drive_service().files().update(
                fileId=existing["id"],
                media_body=media,
                fields="id,name,modifiedTime",
                supportsAllDrives=True,
            ).execute()
        else:
            result = drive_service().files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media,
                fields="id,name,modifiedTime",
                supportsAllDrives=True,
            ).execute()
        return result
    except Exception as exc:
        message = str(exc)
        if "storageQuotaExceeded" in message or "Service Accounts do not have storage quota" in message:
            raise DriveConfigurationError(
                "The service account cannot own files in a regular My Drive folder. "
                "Move the Groundwork Finance Portal folder into a Google Shared Drive, "
                "then share that folder with the service account as Content manager."
            ) from exc
        raise

def delete_file(folder_key: str, remote_name: str) -> bool:
    folder_id = portal_folder_ids()[folder_key]
    item = _remote_file(remote_name, folder_id)
    if not item:
        return False
    drive_service().files().delete(fileId=item["id"], supportsAllDrives=True).execute()
    return True


def _download(file_id: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = drive_service().files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    target.write_bytes(buffer.getvalue())


def list_folder(folder_key: str) -> list[dict]:
    folder_id = portal_folder_ids()[folder_key]
    return _list_files(f"'{folder_id}' in parents and trashed = false")


def sync_from_drive() -> dict[str, int | str]:
    """Download shared cloud data into Streamlit's local runtime.

    Drive becomes authoritative only when the corresponding cloud folder has files,
    so an empty newly configured Drive does not erase bundled/local data.
    """
    ar_files = [item for item in list_folder("ar") if item["name"].startswith("ar_") and item["name"].endswith(".csv")]
    if ar_files:
        AR_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        for path in AR_SNAPSHOT_DIR.glob("ar_*.csv"):
            path.unlink()
        for item in ar_files:
            _download(item["id"], AR_SNAPSHOT_DIR / item["name"])

    revenue_files = list_folder("revenue")
    history = next((item for item in revenue_files if item["name"] == "revenue_history.csv"), None)
    if history:
        _download(history["id"], REVENUE_HISTORY_PATH)
        _download(history["id"], CURRENT_REVENUE_PATH)

    # Import here to avoid a circular import at module load time.
    from utils.data import sync_current_ar_from_latest
    sync_current_ar_from_latest()
    return {
        "ar_snapshots": len(ar_files),
        "revenue_history": 1 if history else 0,
        "status": "Synced",
    }
