import pandas as pd
from utils.paths import (
    CURRENT_AR_PATH,
    CURRENT_REVENUE_PATH,
    REVENUE_HISTORY_PATH,
    AR_SNAPSHOT_DIR,
    REVENUE_SNAPSHOT_DIR,
)


def load_snapshots(folder, prefix):
    frames = []
    for path in sorted(folder.glob(f'{prefix}_*.csv')):
        df = pd.read_csv(path)
        snapshot_date = path.stem.replace(f'{prefix}_', '')
        if 'Snapshot Date' not in df.columns:
            df['Snapshot Date'] = snapshot_date
        else:
            df['Snapshot Date'] = df['Snapshot Date'].fillna(snapshot_date)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_revenue_history(include_current=True):
    if REVENUE_HISTORY_PATH.exists():
        return prep_revenue(pd.read_csv(REVENUE_HISTORY_PATH))
    if include_current and CURRENT_REVENUE_PATH.exists():
        return prep_revenue(pd.read_csv(CURRENT_REVENUE_PATH))
    history = load_snapshots(REVENUE_SNAPSHOT_DIR, 'revenue')
    return prep_revenue(history)


def save_revenue_history(df):
    REVENUE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(REVENUE_HISTORY_PATH, index=False)
    df.to_csv(CURRENT_REVENUE_PATH, index=False)


def revenue_week_values(df):
    if df.empty or 'Week' not in df.columns:
        return []
    return sorted(df['Week'].dropna().astype(str).unique().tolist())


def merge_revenue_history(existing, incoming, replace=False):
    existing = existing.copy() if existing is not None else pd.DataFrame()
    incoming = incoming.copy() if incoming is not None else pd.DataFrame()
    if incoming.empty:
        return existing, [], []
    if 'Week' not in incoming.columns:
        raise ValueError('The cleaned revenue upload does not contain a Week column.')

    incoming_weeks = set(revenue_week_values(incoming))
    existing_weeks = set(revenue_week_values(existing))
    duplicates = sorted(incoming_weeks & existing_weeks)
    new_weeks = sorted(incoming_weeks - existing_weeks)

    if duplicates and not replace:
        incoming = incoming[~incoming['Week'].astype(str).isin(duplicates)].copy()
    elif duplicates and replace:
        existing = existing[~existing['Week'].astype(str).isin(duplicates)].copy()

    combined = pd.concat([existing, incoming], ignore_index=True, sort=False)
    sort_cols = [c for c in ['Date', 'Week', 'Document Number'] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols, na_position='last').reset_index(drop=True)
    return combined, duplicates, new_weeks


def delete_revenue_weeks(existing, weeks):
    if existing.empty or not weeks or 'Week' not in existing.columns:
        return existing.copy()
    return existing[~existing['Week'].astype(str).isin([str(w) for w in weeks])].copy()



def parse_revenue_week(value):
    """Return the Sunday reporting-week start and week number from the stored Week key."""
    import re
    text = "" if pd.isna(value) else str(value).strip()
    match = re.search(r"\((\d{2})-[A-Za-z]{3}\)\s*(\d{1,2})$", text)
    if not match:
        return pd.NaT, pd.NA
    year = 2000 + int(match.group(1))
    week_number = int(match.group(2))
    try:
        week_start = (pd.Timestamp.fromisocalendar(year, week_number, 1) - pd.Timedelta(days=1)).normalize()
        return week_start, week_number
    except ValueError:
        return pd.NaT, pd.NA


def revenue_week_start(value):
    return parse_revenue_week(value)[0]


def revenue_week_label(value, include_range=False):
    """Human-readable Sunday-through-Saturday label for a stored Revenue week."""
    start, _ = parse_revenue_week(value)
    if pd.isna(start):
        return str(value)
    end = start + pd.Timedelta(days=6)
    if include_range:
        if start.year == end.year and start.month == end.month:
            return f"{start:%b %-d}–{end:%-d, %Y}"
        if start.year == end.year:
            return f"{start:%b %-d}–{end:%b %-d, %Y}"
        return f"{start:%b %-d, %Y}–{end:%b %-d, %Y}"
    return f"Week of {start:%b %-d, %Y}"


def revenue_week_table(df):
    """Summarize loaded Revenue weeks with readable reporting dates."""
    if df is None or df.empty or 'Week' not in df.columns:
        return pd.DataFrame(columns=['Week', 'Week Of', 'Week Ending', 'Rows', 'Revenue', 'Lbs', 'Weighted $/LB'])
    work = df.copy()
    work['Revenue'] = pd.to_numeric(work.get('Revenue', 0), errors='coerce').fillna(0)
    work['Lbs'] = pd.to_numeric(work.get('Lbs', 0), errors='coerce').fillna(0)
    grouped = work.groupby('Week', dropna=False).agg(Rows=('Revenue','size'), Revenue=('Revenue','sum'), Lbs=('Lbs','sum')).reset_index()
    grouped['Week Start'] = grouped['Week'].map(revenue_week_start)
    grouped['Week Of'] = grouped['Week Start'].dt.strftime('%b %d, %Y')
    grouped['Week Ending'] = (grouped['Week Start'] + pd.Timedelta(days=6)).dt.strftime('%b %d, %Y')
    grouped['Weighted $/LB'] = grouped['Revenue'].div(grouped['Lbs'].replace(0, pd.NA)).fillna(0)
    return grouped.sort_values('Week Start', ascending=False).drop(columns=['Week Start'])


def load_ar_history(include_current=True):
    history = load_snapshots(AR_SNAPSHOT_DIR, 'ar')
    if history.empty and include_current and CURRENT_AR_PATH.exists():
        history = pd.read_csv(CURRENT_AR_PATH)
    return prep_ar(history)


def prep_revenue(df):
    if df.empty:
        return df
    df = df.copy()
    for col in ['Revenue', 'Lbs', '$/LB', 'Units Sold', 'Package Lbs']:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ['Date', 'Snapshot Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        else:
            df[col] = pd.NaT
    text_cols = ['Customer', 'Sales Channel', 'Sales Rep', 'Item Class', 'Coffee Size', 'Item / Memo', 'Period', 'Week']
    for col in text_cols:
        if col not in df.columns:
            df[col] = 'Unknown'
        df[col] = df[col].fillna('Unknown').astype(str)
    df['Trend Date'] = df['Date'].fillna(df['Snapshot Date'])
    df['Month'] = df['Trend Date'].dt.to_period('M').astype(str)
    df['Year'] = df['Trend Date'].dt.year
    return df


def prep_ar(df):
    if df.empty:
        return df
    df = df.copy()
    defaults = {
        'Reporting Customer': 'Unknown', 'Channel Clean': 'Unknown',
        'Sales Channel: Name': 'Unknown', 'Sales Rep: Name': 'Unknown',
        'Terms: Name': 'Unknown', 'Bucket': 'Unknown', 'Open Balance': 0,
        'Transaction Type': 'Invoice', 'Deduction Type': '', 'Memo': '',
        'Snapshot Date': pd.NaT,
    }
    if 'Deduction Type' not in df.columns and 'Transaction Reason' in df.columns:
        df['Deduction Type'] = df['Transaction Reason']
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df['Open Balance'] = pd.to_numeric(df['Open Balance'], errors='coerce').fillna(0)
    df['Snapshot Date'] = pd.to_datetime(df['Snapshot Date'], errors='coerce')
    return df


def revenue_summary(df, group_col):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, 'Revenue', 'Lbs', 'Weighted $/LB', 'Avg $/LB', 'Mix %'])
    total_revenue = df['Revenue'].sum()
    grouped = df.groupby(group_col, dropna=False).agg(
        Revenue=('Revenue', 'sum'), Lbs=('Lbs', 'sum'),
    ).reset_index()
    grouped['Weighted $/LB'] = grouped['Revenue'].div(grouped['Lbs'].replace(0, pd.NA)).fillna(0)
    grouped['Avg $/LB'] = grouped['Weighted $/LB']
    grouped['Mix %'] = grouped['Revenue'] / total_revenue if total_revenue else 0
    return grouped.sort_values('Revenue', ascending=False)


def monthly_revenue_summary(df):
    if df.empty:
        return pd.DataFrame(columns=['Month', 'Revenue', 'Lbs', 'Weighted $/LB', 'MoM Revenue %', 'MoM $/LB %'])
    monthly = df.dropna(subset=['Trend Date']).groupby('Month').agg(Revenue=('Revenue', 'sum'), Lbs=('Lbs', 'sum')).reset_index()
    monthly = monthly.sort_values('Month')
    monthly['Weighted $/LB'] = monthly['Revenue'].div(monthly['Lbs'].replace(0, pd.NA)).fillna(0)
    monthly['MoM Revenue %'] = monthly['Revenue'].pct_change()
    monthly['MoM $/LB %'] = monthly['Weighted $/LB'].pct_change()
    return monthly


def yoy_revenue_summary(df):
    if df.empty:
        return pd.DataFrame(columns=['Year', 'Month Num', 'Month', 'Revenue', 'Lbs', 'Weighted $/LB', 'YoY Revenue %', 'YoY $/LB %'])
    y = df.dropna(subset=['Trend Date']).copy()
    y['Month Num'] = y['Trend Date'].dt.month
    yoy = y.groupby(['Year', 'Month Num']).agg(Revenue=('Revenue', 'sum'), Lbs=('Lbs', 'sum')).reset_index()
    yoy = yoy.sort_values(['Month Num', 'Year'])
    yoy['Weighted $/LB'] = yoy['Revenue'].div(yoy['Lbs'].replace(0, pd.NA)).fillna(0)
    yoy['YoY Revenue %'] = yoy.groupby('Month Num')['Revenue'].pct_change()
    yoy['YoY $/LB %'] = yoy.groupby('Month Num')['Weighted $/LB'].pct_change()
    yoy['Month'] = pd.to_datetime(yoy['Month Num'], format='%m').dt.strftime('%b')
    return yoy
