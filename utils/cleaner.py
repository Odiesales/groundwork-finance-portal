import re
from io import BytesIO
from pathlib import Path
from datetime import date
import pandas as pd

CHARGEBACK_REASONS = {
    "Cash Discount", "Clearing", "Compliance", "CoOp", "Damages", "Duplicate PMT",
    "Freight", "Handling", "Marketing", "Merchandising", "Misshipment",
    "New Store / Remodel", "On Account Payment (OAP)", "Overpayment", "Placements",
    "PMT Transfer", "Price Protection", "Pricing", "Rebate", "Returns", "Shortage",
    "Slotting", "Spoilage", "TPR", "Training",
}

REASON_ALIASES = {
    "cash discount": "Cash Discount", "cash disc": "Cash Discount", "clearing": "Clearing",
    "compliance": "Compliance", "coop": "CoOp", "co-op": "CoOp", "co op": "CoOp",
    "damages": "Damages", "damage": "Damages", "duplicate pmt": "Duplicate PMT",
    "duplicate payment": "Duplicate PMT", "freight": "Freight", "handling": "Handling",
    "holdback": "Holdback", "marketing": "Marketing", "merchandising": "Merchandising",
    "misshipment": "Misshipment", "mis-shipment": "Misshipment", "mis shipment": "Misshipment",
    "new store / remodel": "New Store / Remodel", "new store": "New Store / Remodel",
    "remodel": "New Store / Remodel", "on account payment (oap)": "On Account Payment (OAP)",
    "on account payment": "On Account Payment (OAP)", "oap": "On Account Payment (OAP)",
    "overpayment": "Overpayment", "over payment": "Overpayment", "placements": "Placements",
    "placement": "Placements", "pmt transfer": "PMT Transfer", "payment transfer": "PMT Transfer",
    "price protection": "Price Protection", "pricing": "Pricing", "rebate": "Rebate",
    "returns": "Returns", "return": "Returns", "shortage": "Shortage", "slotting": "Slotting",
    "spoilage": "Spoilage", "tpr": "TPR", "training": "Training",
}

CUSTOMER_CODE_PATTERN = re.compile(r"^[A-Z]{1,3}\d+\s*", re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(lb|lbs|pound|pounds|oz|ounce|ounces|kg|g|gram|grams)\b", re.I)


def money(value):
    try:
        return "${:,.2f}".format(float(value))
    except Exception:
        return "$0.00"


def read_table(uploaded_file, sheet_name=None):
    name = getattr(uploaded_file, "name", str(uploaded_file)).lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file, sheet_name=sheet_name or 0)


def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


def normalize_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def is_blank_or_none(value):
    if pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "none", "nan", "null"}


def strip_customer_code(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", CUSTOMER_CODE_PATTERN.sub("", str(value).strip())).strip()


def clean_customer_name(parent_customer, customer):
    raw_name = customer if is_blank_or_none(parent_customer) else parent_customer
    clean_name = strip_customer_code(raw_name)
    return clean_name if clean_name else "Unknown"


def calculate_bucket(age):
    try:
        age_num = float(age)
    except Exception:
        return "Unknown"
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


def get_memo_reason(memo):
    if pd.isna(memo):
        return ""
    first = str(memo).split("|")[0].strip()
    return REASON_ALIASES.get(normalize_text(first), first)


def classify_transaction(row):
    memo_reason = get_memo_reason(row.get("Memo", ""))
    original_type = row.get("Transaction Type", row.get("Type", ""))
    original_type = "" if pd.isna(original_type) else str(original_type).strip()
    if memo_reason == "Holdback":
        return pd.Series(["Invoice", "Holdback"])
    if memo_reason in CHARGEBACK_REASONS:
        return pd.Series(["Chargeback", memo_reason])
    low = original_type.lower()
    if "payment" in low:
        return pd.Series(["Payment", ""])
    if "credit" in low:
        return pd.Series(["Credit", ""])
    if "chargeback" in low or "charge back" in low:
        return pd.Series(["Chargeback", "Other"])
    return pd.Series([original_type or "Invoice", ""])


def clean_uploaded_ar_report(uploaded_file):
    df = read_table(uploaded_file).copy()
    df.columns = [str(c).strip() for c in df.columns]

    parent_col = "Parent Customer/Project: Company Name"
    customer_col = "Customer"
    if "Reporting Customer" in df.columns:
        df = df.drop(columns=["Reporting Customer"])
    parent_values = df[parent_col] if parent_col in df.columns else ""
    customer_values = df[customer_col] if customer_col in df.columns else ""
    df.insert(0, "Reporting Customer", [clean_customer_name(p, c) for p, c in zip(parent_values, customer_values)])

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0)
        if "Bucket" in df.columns:
            df = df.drop(columns=["Bucket"])
        df.insert(df.columns.get_loc("Age") + 1, "Bucket", df["Age"].apply(calculate_bucket))

    if "Memo" not in df.columns:
        df["Memo"] = ""
    df[["Transaction Type", "Deduction Type"]] = df.apply(classify_transaction, axis=1)
    # Backward compatibility for older exports is handled in utils.data.prep_ar.

    if "Open Balance" in df.columns:
        df["Open Balance"] = pd.to_numeric(df["Open Balance"], errors="coerce").fillna(0)
    if "Sales Channel: Name" in df.columns and "Channel Clean" not in df.columns:
        df["Channel Clean"] = df["Sales Channel: Name"].fillna("Unknown")
    return df


def find_col(df, candidates, fallback_contains=None):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    if fallback_contains:
        for col in df.columns:
            low = str(col).strip().lower()
            if all(part in low for part in fallback_contains):
                return col
    return None


def weight_to_lbs(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        # NetSuite export sometimes stores Roasted Coffee Size as 12 for 12 oz.
        return float(value) / 16 if float(value) > 5 else float(value)
    text = str(value).strip().lower()
    m = WEIGHT_PATTERN.search(text)
    if not m:
        return None
    qty = float(m.group(1))
    unit = m.group(2).lower()
    if unit in {"lb", "lbs", "pound", "pounds"}:
        return qty
    if unit in {"oz", "ounce", "ounces"}:
        return qty / 16
    if unit in {"g", "gram", "grams"}:
        return qty / 453.59237
    if unit == "kg":
        return qty * 2.20462262
    return None


def unit_multiplier(value):
    """Return the number of individual packages represented by one selling unit."""
    if pd.isna(value):
        return 1.0
    if isinstance(value, (int, float)):
        return max(float(value), 1.0)
    text = str(value).strip().upper()
    if not text:
        return 1.0
    match = re.search(r"CASE\s+OF\s+(\d+(?:\.\d+)?)", text)
    if match:
        return max(float(match.group(1)), 1.0)
    return 1.0


def clean_uploaded_revenue_report(uploaded_file):
    raw = read_table(uploaded_file, sheet_name=0).copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    df = raw.loc[:, ~raw.columns.str.startswith("Unnamed")].copy()

    amount_col = find_col(df, ["Revenue", "Sales", "Amount", "Sum of Amount (Credit)"], ["amount", "credit"])
    lbs_col = find_col(df, ["lbs", "Lbs", "Pounds", "Weight (lbs)"])
    date_col = find_col(df, ["Date", "Transaction Date"])
    week_col = find_col(df, ["Week"])
    period_col = find_col(df, ["Period", "Month"])
    channel_col = find_col(df, ["Sales Channel", "Sales Channel 1", "Channel"])
    customer_col = find_col(df, ["Top Level Parent", "Customer", "Reporting Customer"])
    rep_col = find_col(df, ["Sales Rep", "Sales Rep: Name"])
    class_col = find_col(df, ["Item Class", "Class"])
    size_col = find_col(df, ["Roasted Coffee Size", "Coffee Size", "Size", "Weight"])
    item_col = find_col(df, ["Memo", "Item", "Description"])
    quantity_col = find_col(df, ["Sum of Quantity", "Quantity", "Qty"])
    unit_col = find_col(df, ["Unit", "Units Type", "Unit of Measure", "UOM"])
    multiplier_col = find_col(df, ["Case Multiplier", "Unit Multiplier", "Units per Case", "Units Per Case"])

    if amount_col is None:
        raise ValueError("Could not find revenue amount column. Expected 'Sum of Amount (Credit)' or similar.")

    out = pd.DataFrame(index=df.index)
    out["Date"] = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    out["Week"] = df[week_col].astype(str) if week_col else out["Date"].dt.to_period("W").astype(str)
    out["Period"] = df[period_col].astype(str) if period_col else out["Date"].dt.to_period("M").astype(str)
    out["Customer"] = df[customer_col].astype(str).map(strip_customer_code) if customer_col else "Unknown"
    out["Sales Channel"] = df[channel_col].fillna("Unknown").astype(str) if channel_col else "Unknown"
    out["Sales Rep"] = df[rep_col].fillna("Unknown").astype(str) if rep_col else "Unknown"
    out["Item Class"] = df[class_col].fillna("Unknown").astype(str) if class_col else "Unknown"
    out["Coffee Size"] = df[size_col] if size_col else "Unknown"
    out["Item / Memo"] = df[item_col].fillna("").astype(str) if item_col else ""
    out["Revenue"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    quantity = (
        pd.to_numeric(df[quantity_col], errors="coerce").abs().fillna(1.0)
        if quantity_col else pd.Series(1.0, index=df.index)
    )
    quantity = quantity.where(quantity.ne(0), 1.0)

    if multiplier_col:
        multiplier = pd.to_numeric(df[multiplier_col], errors="coerce").fillna(1.0)
        multiplier = multiplier.where(multiplier.gt(0), 1.0)
    elif unit_col:
        multiplier = df[unit_col].apply(unit_multiplier)
    else:
        multiplier = pd.Series(1.0, index=df.index)

    package_lbs = (df[size_col].apply(weight_to_lbs) if size_col else pd.Series(pd.NA, index=df.index, dtype="object"))
    package_lbs = pd.to_numeric(package_lbs, errors="coerce")
    if lbs_col:
        source_lbs = pd.to_numeric(df[lbs_col], errors="coerce")
        package_lbs = package_lbs.fillna(source_lbs)

    out["Quantity"] = quantity
    out["Unit"] = df[unit_col].fillna("").astype(str) if unit_col else ""
    out["Unit Multiplier"] = multiplier
    out["Package Lbs"] = package_lbs.fillna(0.0)
    out["Lbs"] = (out["Package Lbs"] * out["Quantity"] * out["Unit Multiplier"]).fillna(0.0)
    out["$/LB"] = out["Revenue"].div(out["Lbs"].replace(0, pd.NA)).fillna(0.0)
    out["Snapshot Date"] = date.today().isoformat()
    return out


def summarize_revenue(df, group_col):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "Revenue", "Lbs", "Weighted $/LB", "Mix %"])
    total_rev = df["Revenue"].sum()
    out = df.groupby(group_col, dropna=False).agg(Revenue=("Revenue", "sum"), Lbs=("Lbs", "sum")).reset_index()
    out["Weighted $/LB"] = out.apply(lambda r: r["Revenue"] / r["Lbs"] if r["Lbs"] else 0, axis=1)
    out["Mix %"] = out["Revenue"] / total_rev if total_rev else 0
    return out.sort_values("Revenue", ascending=False)
