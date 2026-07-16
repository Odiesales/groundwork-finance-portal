import pandas as pd
from utils.paths import CURRENT_AR_PATH, CURRENT_REVENUE_PATH, AR_SNAPSHOT_DIR, REVENUE_SNAPSHOT_DIR


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
    history = load_snapshots(REVENUE_SNAPSHOT_DIR, 'revenue')
    if history.empty and include_current and CURRENT_REVENUE_PATH.exists():
        history = pd.read_csv(CURRENT_REVENUE_PATH)
    return prep_revenue(history)


def load_ar_history(include_current=True):
    history = load_snapshots(AR_SNAPSHOT_DIR, 'ar')
    if history.empty and include_current and CURRENT_AR_PATH.exists():
        history = pd.read_csv(CURRENT_AR_PATH)
    return prep_ar(history)


def prep_revenue(df):
    if df.empty:
        return df
    df = df.copy()
    for col in ['Revenue', 'Lbs', '$/LB']:
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
    df['Trend Date'] = df['Snapshot Date'].fillna(df['Date'])
    df['Month'] = df['Trend Date'].dt.to_period('M').astype(str)
    df['Year'] = df['Trend Date'].dt.year
    return df


def prep_ar(df):
    if df.empty:
        return df
    df = df.copy()
    defaults = {
        'Reporting Customer': 'Unknown',
        'Channel Clean': 'Unknown',
        'Sales Channel: Name': 'Unknown',
        'Sales Rep: Name': 'Unknown',
        'Terms: Name': 'Unknown',
        'Bucket': 'Unknown',
        'Open Balance': 0,
        'Transaction Type': 'Invoice',
        'Deduction Type': '',
        'Memo': '',
        'Snapshot Date': pd.NaT,
    }
    # Upgrade older snapshots without requiring users to re-upload them.
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
        Revenue=('Revenue', 'sum'),
        Lbs=('Lbs', 'sum'),
        Avg_dollar_lb=('$/LB', 'mean'),
    ).reset_index()
    grouped['Weighted $/LB'] = grouped.apply(lambda r: r['Revenue'] / r['Lbs'] if r['Lbs'] else 0, axis=1)
    grouped['Avg $/LB'] = grouped['Avg_dollar_lb'].fillna(0)
    grouped['Mix %'] = grouped['Revenue'] / total_revenue if total_revenue else 0
    grouped = grouped.drop(columns=['Avg_dollar_lb'])
    return grouped.sort_values('Revenue', ascending=False)


def monthly_revenue_summary(df):
    if df.empty:
        return pd.DataFrame(columns=['Month', 'Revenue', 'Lbs', 'Weighted $/LB', 'MoM Revenue %', 'MoM $/LB %'])
    monthly = df.dropna(subset=['Trend Date']).groupby('Month').agg(Revenue=('Revenue', 'sum'), Lbs=('Lbs', 'sum')).reset_index()
    monthly = monthly.sort_values('Month')
    monthly['Weighted $/LB'] = monthly.apply(lambda r: r['Revenue'] / r['Lbs'] if r['Lbs'] else 0, axis=1)
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
    yoy['Weighted $/LB'] = yoy.apply(lambda r: r['Revenue'] / r['Lbs'] if r['Lbs'] else 0, axis=1)
    yoy['YoY Revenue %'] = yoy.groupby('Month Num')['Revenue'].pct_change()
    yoy['YoY $/LB %'] = yoy.groupby('Month Num')['Weighted $/LB'].pct_change()
    yoy['Month'] = pd.to_datetime(yoy['Month Num'], format='%m').dt.strftime('%b')
    return yoy
