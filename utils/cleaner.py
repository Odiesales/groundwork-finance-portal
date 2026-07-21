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
    patterns = [
        r"CASE\s+OF\s+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:PER|/)\s*CASE",
        r"CASE\s*PACK\s*(?:OF)?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return max(float(match.group(1)), 1.0)
    return 1.0


def parse_description_pack(value):
    """Parse package weight and case count from an item description.

    Returns (package_lbs, case_multiplier, source, review_required).  The parser
    deliberately ignores empty packaging descriptions such as valve bags because
    their stated weight is container capacity, not pounds of product sold.
    """
    if pd.isna(value):
        return None, None, "", False

    text = str(value).strip()
    if not text:
        return None, None, "", False
    low = text.lower()

    packaging_markers = (
        "kraft bag w/valve",
        "kraft bag with valve",
        "empty bag",
        "packaging",
    )
    if any(marker in low for marker in packaging_markers):
        return 0.0, 1.0, "Excluded packaging supply", False

    # Examples: 12x1lb case, 6x2lb case, 12 x 10 oz.
    cross = re.search(
        r"(?<![\d.])(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*"
        r"(lb|lbs|pound|pounds|oz|ounce|ounces|g|gram|grams|kg)\b",
        text,
        flags=re.IGNORECASE,
    )
    if cross:
        count = float(cross.group(1))
        package_lbs = weight_to_lbs(f"{cross.group(2)} {cross.group(3)}")
        return package_lbs, count, "Description: count x weight", False

    # Find the first explicit package weight anywhere in the description.
    package_lbs = weight_to_lbs(text)

    case_patterns = [
        r"CASE\s+OF\s+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s+PER\s+CASE",
        r"(\d+(?:\.\d+)?)\s*/\s*CASE",
        r"CASE\s*PACK\s*(?:OF)?\s*(\d+(?:\.\d+)?)",
    ]
    case_count = None
    for pattern in case_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            case_count = max(float(match.group(1)), 1.0)
            break

    if package_lbs is not None and case_count is not None:
        return package_lbs, case_count, "Description: package weight + case count", False
    if package_lbs is not None:
        # A weight is useful, but descriptions such as GCASE ... (1lb) Can do
        # not state the cans per case. Let the Unit/UOM column supply the case
        # count when possible and flag unresolved GCASE rows for review.
        needs_review = "gcase" in low or "case" in low
        return package_lbs, None, "Description: package weight", needs_review
    if case_count is not None:
        return None, case_count, "Description: case count only", True
    return None, None, "", False

def clean_uploaded_revenue_report(uploaded_file):
    """Clean a NetSuite revenue export using units sold x package weight.

    Authoritative formula:
        Line Pounds = Sum of # of Units x weight by lbs
        Line $/LB = Revenue / Line Pounds
    """
    raw = read_table(uploaded_file, sheet_name=0).copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    df = raw.loc[:, ~raw.columns.str.startswith("Unnamed")].copy()

    amount_col = find_col(df, ["Revenue", "Sales", "Amount", "Sum of Amount", "Sum of Amount (Credit)"], ["amount"])
    date_col = find_col(df, ["Date", "Transaction Date"])
    week_col = find_col(df, ["Week", "Week Of", "Week Number"])
    period_col = find_col(df, ["Period", "Month"])
    channel_col = find_col(df, ["sales channel extract (override)", "Sales Channel", "Sales Channel 1", "Channel"])
    customer_col = find_col(df, ["Top Level Parent", "Customer", "Reporting Customer"])
    rep_col = find_col(df, ["Sales Rep", "Sales Rep: Name"])
    class_col = find_col(df, ["Item Class", "Class"])
    item_col = find_col(df, ["Memo", "Item", "Description"])
    quantity_col = find_col(df, ["Sum of Quantity", "Quantity", "Qty"])
    units_col = find_col(df, ["Sum of # of Units", "# of Units", "Units Sold", "Total Units"])
    explicit_weight_col = find_col(df, ["weight by lbs", "Weight by lbs", "Package Lbs", "Unit Weight Lbs"])
    unit_col = find_col(df, ["Unit", "Units Type", "Unit of Measure", "UOM"])
    multiplier_col = find_col(df, ["Case Multiplier", "Unit Multiplier", "Units per Case", "Units Per Case"])
    document_col = find_col(df, ["Document Number", "Document No.", "Invoice Number"])
    location_col = find_col(df, ["Location"])
    coffee_size_col = find_col(df, ["Roasted Coffee Size", "Coffee Size", "Size"])

    if amount_col is None:
        raise ValueError("Could not find revenue amount column. Expected 'Sum of Amount' or similar.")

    out = pd.DataFrame(index=df.index)
    out["Date"] = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    raw_week = df[week_col] if week_col else out["Date"].dt.isocalendar().week
    period_text = df[period_col].astype(str) if period_col else out["Date"].dt.strftime("%b %Y")

    def canonical_week(value, row_date, period_value):
        text = "" if pd.isna(value) else str(value).strip()
        if re.search(r"\(\d{2}-[A-Za-z]{3}\)\s*\d{1,2}$", text):
            return text
        try:
            week_number = int(float(value))
        except Exception:
            return text or "Unknown"
        parsed_date = pd.to_datetime(row_date, errors="coerce")
        year = parsed_date.year if not pd.isna(parsed_date) else None
        if year is None:
            match = re.search(r"(20\d{2})", str(period_value))
            year = int(match.group(1)) if match else date.today().year
        try:
            week_start = (pd.Timestamp.fromisocalendar(int(year), week_number, 1) - pd.Timedelta(days=1)).normalize()
            month = week_start.strftime("%b")
        except ValueError:
            month = parsed_date.strftime("%b") if not pd.isna(parsed_date) else "Jan"
        return f"({str(int(year))[-2:]}-{month}) {week_number}"

    out["Week"] = [canonical_week(w, d, p) for w, d, p in zip(raw_week, out["Date"], period_text)]
    out["Period"] = period_text
    out["Customer"] = df[customer_col].astype(str).map(strip_customer_code) if customer_col else "Unknown"
    out["Sales Channel"] = df[channel_col].fillna("Unknown").astype(str) if channel_col else "Unknown"
    out["Sales Rep"] = df[rep_col].fillna("Unknown").astype(str) if rep_col else "Unknown"
    out["Item Class"] = df[class_col].fillna("Unknown").astype(str) if class_col else "Unknown"
    out["Coffee Size"] = df[coffee_size_col].fillna("Unknown") if coffee_size_col else "Unknown"
    out["Item / Memo"] = df[item_col].fillna("").astype(str) if item_col else ""
    out["Document Number"] = df[document_col].fillna("").astype(str) if document_col else ""
    out["Location"] = df[location_col].fillna("").astype(str) if location_col else ""
    out["Revenue"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    quantity = pd.to_numeric(df[quantity_col], errors="coerce").abs().fillna(0) if quantity_col else pd.Series(0.0, index=df.index)
    authoritative_units = pd.to_numeric(df[units_col], errors="coerce").abs() if units_col else pd.Series(pd.NA, index=df.index, dtype="Float64")
    authoritative_weight = pd.to_numeric(df[explicit_weight_col], errors="coerce") if explicit_weight_col else pd.Series(pd.NA, index=df.index, dtype="Float64")

    description_pack = out["Item / Memo"].apply(parse_description_pack)
    desc_package_lbs = pd.to_numeric(description_pack.map(lambda x: x[0]), errors="coerce")
    desc_multiplier = pd.to_numeric(description_pack.map(lambda x: x[1]), errors="coerce")
    desc_review = description_pack.map(lambda x: bool(x[3]))
    size_package_lbs = df[coffee_size_col].apply(weight_to_lbs) if coffee_size_col else pd.Series(pd.NA, index=df.index, dtype="object")
    size_package_lbs = pd.to_numeric(size_package_lbs, errors="coerce")
    explicit_multiplier = pd.to_numeric(df[multiplier_col], errors="coerce") if multiplier_col else pd.Series(pd.NA, index=df.index, dtype="Float64")
    uom_multiplier = df[unit_col].apply(unit_multiplier).astype(float) if unit_col else pd.Series(1.0, index=df.index)
    fallback_multiplier = explicit_multiplier.where(explicit_multiplier.gt(0)).fillna(desc_multiplier).fillna(uom_multiplier).fillna(1.0)
    fallback_weight = authoritative_weight.fillna(size_package_lbs).fillna(desc_package_lbs).fillna(0.0)
    fallback_units = (quantity * fallback_multiplier).where(quantity.gt(0), 0.0)

    use_authoritative = authoritative_units.notna() & authoritative_weight.notna() & authoritative_weight.gt(0)
    units_sold = authoritative_units.where(use_authoritative, fallback_units).fillna(0.0)
    package_lbs = authoritative_weight.where(use_authoritative, fallback_weight).fillna(0.0)

    out["Quantity"] = quantity
    out["Units Sold"] = units_sold.astype(float)
    out["Unit"] = df[unit_col].fillna("").astype(str) if unit_col else ""
    out["Unit Multiplier"] = fallback_multiplier.astype(float)
    out["Package Lbs"] = package_lbs.astype(float)
    out["Weight Source"] = "Fallback parser"
    out.loc[use_authoritative, "Weight Source"] = "Sum of # of Units x weight by lbs"
    out["Multiplier Source"] = "Not used - authoritative units"
    out.loc[~use_authoritative, "Multiplier Source"] = "Legacy fallback"
    out["Weight Review"] = (~use_authoritative) | desc_review | package_lbs.le(0) | units_sold.le(0)
    out["Lbs"] = (out["Units Sold"] * out["Package Lbs"]).fillna(0.0)
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
