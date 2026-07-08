import pandas as pd
import re
from io import BytesIO


# Official Chargeback / deduction reason list.
# Holdback is intentionally handled separately because it remains Invoice type.
CHARGEBACK_REASONS = {
    "Cash Discount",
    "Clearing",
    "Compliance",
    "CoOp",
    "Damages",
    "Duplicate PMT",
    "Freight",
    "Handling",
    "Marketing",
    "Merchandising",
    "Misshipment",
    "New Store / Remodel",
    "On Account Payment (OAP)",
    "Overpayment",
    "Placements",
    "PMT Transfer",
    "Price Protection",
    "Pricing",
    "Rebate",
    "Returns",
    "Shortage",
    "Slotting",
    "Spoilage",
    "TPR",
    "Training",
}


# Alternate spellings that may appear in the first section of Memo.
REASON_ALIASES = {
    "cash discount": "Cash Discount",
    "clearing": "Clearing",
    "compliance": "Compliance",
    "coop": "CoOp",
    "co-op": "CoOp",
    "co op": "CoOp",
    "damages": "Damages",
    "damage": "Damages",
    "duplicate pmt": "Duplicate PMT",
    "duplicate payment": "Duplicate PMT",
    "freight": "Freight",
    "handling": "Handling",
    "holdback": "Holdback",
    "marketing": "Marketing",
    "merchandising": "Merchandising",
    "misshipment": "Misshipment",
    "mis-shipment": "Misshipment",
    "mis shipment": "Misshipment",
    "new store / remodel": "New Store / Remodel",
    "new store": "New Store / Remodel",
    "remodel": "New Store / Remodel",
    "on account payment (oap)": "On Account Payment (OAP)",
    "on account payment": "On Account Payment (OAP)",
    "oap": "On Account Payment (OAP)",
    "overpayment": "Overpayment",
    "over payment": "Overpayment",
    "placements": "Placements",
    "placement": "Placements",
    "pmt transfer": "PMT Transfer",
    "payment transfer": "PMT Transfer",
    "price protection": "Price Protection",
    "pricing": "Pricing",
    "rebate": "Rebate",
    "returns": "Returns",
    "return": "Returns",
    "shortage": "Shortage",
    "slotting": "Slotting",
    "spoilage": "Spoilage",
    "tpr": "TPR",
    "training": "Training",
}


CUSTOMER_CODE_PATTERN = re.compile(r"^[A-Z]{1,3}\d+\s*", re.IGNORECASE)


def normalize_text(value):
    """Convert any cell value to clean lowercase text for matching."""
    if pd.isna(value):
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_blank_or_none(value):
    """Treat true blanks, NaN, and NetSuite's literal None as blank."""
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"none", "nan", "null"}


def strip_customer_code(value):
    """
    Remove leading NetSuite customer/project codes.

    Examples:
    CX111119 GWC Samples -> GWC Samples
    CW135806 SYSCO Los Angeles, INC. -> SYSCO Los Angeles, INC.
    CP136020 Whisha:CW136248 Whisha: Northern California -> Whisha:CW136248 Whisha: Northern California
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()
    text = CUSTOMER_CODE_PATTERN.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def clean_customer_name(parent_customer, customer):
    """
    Build a clean customer name for reporting.

    Rule:
    - Use Parent Customer/Project when it has a real value.
    - If Parent Customer/Project is None/blank, use Customer instead.
    - Remove leading customer IDs like CX111119, CW135806, CP136020.
    """
    if is_blank_or_none(parent_customer):
        raw_name = customer
    else:
        raw_name = parent_customer

    clean_name = strip_customer_code(raw_name)
    return clean_name if clean_name else "Unknown"


def add_reporting_customer(df):
    """Create/replace Reporting Customer and place it near the Customer columns."""
    df = df.copy()

    parent_col = "Parent Customer/Project: Company Name"
    customer_col = "Customer"

    if parent_col not in df.columns and customer_col not in df.columns:
        if "Reporting Customer" not in df.columns:
            df["Reporting Customer"] = "Unknown"
        return df

    parent_values = df[parent_col] if parent_col in df.columns else ""
    customer_values = df[customer_col] if customer_col in df.columns else ""

    reporting_customer = [
        clean_customer_name(parent, customer)
        for parent, customer in zip(parent_values, customer_values)
    ]

    if "Reporting Customer" in df.columns:
        df = df.drop(columns=["Reporting Customer"])

    insert_position = 0
    if customer_col in df.columns:
        insert_position = df.columns.get_loc(customer_col) + 1
    elif parent_col in df.columns:
        insert_position = df.columns.get_loc(parent_col) + 1

    df.insert(insert_position, "Reporting Customer", reporting_customer)
    return df


def calculate_bucket(age):
    """
    Bucket logic:
    Age <= 0 = Current
    1-14 = 1-14
    15-30 = 15-30
    31-60 = 31-60
    61-90 = 61-90
    91+ = 91+
    """
    try:
        age_num = float(age)
    except Exception:
        return ""

    if age_num <= 0:
        return "Current"
    if age_num <= 14:
        return "1-14"
    if age_num <= 30:
        return "15-30"
    if age_num <= 60:
        return "31-60"
    if age_num <= 90:
        return "61-90"
    return "91+"


def add_bucket_after_age(df):
    """Create/replace Bucket column and place it immediately after Age."""
    if "Age" not in df.columns:
        return df

    df = df.copy()

    if "Bucket" in df.columns:
        df = df.drop(columns=["Bucket"])

    age_position = df.columns.get_loc("Age")
    bucket_values = df["Age"].apply(calculate_bucket)
    df.insert(age_position + 1, "Bucket", bucket_values)

    return df


def get_memo_reason(memo):
    """
    Extract the reason from Memo.

    Expected format:
    Reason | Reference | Customer

    Examples:
    CoOp | 018069093PTYTFM | The Fresh Market -> CoOp
    Freight | 634664V -> Freight
    Holdback | INV831410PP -> Holdback
    """
    if pd.isna(memo):
        return ""

    memo_text = str(memo).strip()
    if not memo_text:
        return ""

    first_part = memo_text.split("|")[0].strip()
    normalized_first_part = normalize_text(first_part)

    return REASON_ALIASES.get(normalized_first_part, first_part)


def classify_transaction(row):
    """
    Main classification rule:
    - Read Memo reason from the first section before "|".
    - If Memo reason is Holdback, keep as Invoice and reason Holdback.
    - If Memo reason is in CB list, classify as Chargeback and use that reason.
    - Otherwise preserve original Transaction Type.
    """
    memo = row.get("Memo", "")
    memo_reason = get_memo_reason(memo)

    original_type = row.get("Transaction Type", "")
    if pd.isna(original_type):
        original_type = ""

    if memo_reason == "Holdback":
        return pd.Series(["Invoice", "Holdback"])

    if memo_reason in CHARGEBACK_REASONS:
        return pd.Series(["Chargeback", memo_reason])

    return pd.Series([original_type, ""])


def add_transaction_classification(df):
    """Create Transaction Type Clean and Transaction Reason."""
    df = df.copy()

    if "Memo" in df.columns:
        df[["Transaction Type Clean", "Transaction Reason"]] = df.apply(classify_transaction, axis=1)
    else:
        if "Transaction Type" in df.columns:
            df["Transaction Type Clean"] = df["Transaction Type"]
        else:
            df["Transaction Type Clean"] = ""
        df["Transaction Reason"] = ""

    return df


def clean_ar_report(df):
    """
    Cleans the raw AR report for the Groundwork Finance Portal.

    Adds:
    - Reporting Customer, using Parent Customer unless Parent is None/blank
    - Bucket, calculated from Age and placed after Age
    - Transaction Type Clean
    - Transaction Reason
    """
    df = df.copy()

    # Normalize column names by stripping leading/trailing spaces.
    df.columns = [str(col).strip() for col in df.columns]

    # Add cleaned reporting customer before dashboard logic runs.
    df = add_reporting_customer(df)

    # Add aging bucket from Age.
    df = add_bucket_after_age(df)

    # Add classification fields.
    df = add_transaction_classification(df)

    return df


def load_ar_report(uploaded_file):
    """
    Load CSV or Excel file into a pandas DataFrame.
    Designed for Streamlit uploaded files.
    """
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")


def clean_uploaded_ar_report(uploaded_file):
    """
    Streamlit-friendly helper:
    uploaded_file -> cleaned DataFrame
    """
    df = load_ar_report(uploaded_file)
    return clean_ar_report(df)


def convert_df_to_excel(df):
    """
    Convert cleaned DataFrame to Excel bytes for Streamlit download button.
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cleaned AR")

    output.seek(0)
    return output.getvalue()


def convert_df_to_csv(df):
    """
    Convert cleaned DataFrame to CSV bytes for Streamlit download button.
    """
    return df.to_csv(index=False).encode("utf-8")
