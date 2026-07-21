
Today 4:56 PM

Feedback.docx
Document
I have a few feedback,

I reviewed your feedback document, and I think these are all worthwhile improvements. Most of them are relatively straightforward, while a few require changes to the underlying snapshot logic. 


Here's how I'd prioritize them.

Phase 1 (High Impact / Quick Wins)
These will immediately improve usability.

✅ Executive Scorecard

Add Week-over-Week (WoW) values for Accounts Receivable KPIs.

Show green/red indicators for increases and decreases consistently across all KPI cards. 


✅ Export Buttons

Add Export to CSV/Excel on every section instead of only the full page.

Examples:

Top Customer Exposure

Collection Priority

Chargeback Center

Revenue tables

Executive KPIs 


✅ "Show All"
Anywhere we currently limit results (Top 10, Top 25), add:

Top 10

Top 25

Top 50

All

for:

Customer Exposure

Collection Priority

Chargeback Charts

Deduction Type Charts 


Phase 2 (Dashboard Improvements)
Customer Exposure
Instead of only:

Rank By:

Past Due

Total AR

Add:

Current

1–14

15–30

31–60

61–90

91+

Total AR

Past Due

Then allow Show All.

Chargeback Charts
Instead of only bars...

Show labels inside each bar.

Example:

UNFI        $251,700
██████████████████
Same for Deduction Type. 


Phase 3 (Revenue)
I agree with these.

Instead of weekly line charts for everything...

I'd build KPI tables like:

Week	Revenue	Cases	Pounds	$/lb
Jul 6	$412,123	19,233	142,990	$2.88
Jul 13	$428,441	20,114	149,771	$2.86
Jul 20	$436,019	21,331	151,337	$2.88
Much easier to read than another line graph. 


Also:

Convert the current Year-over-Year monthly graph to a Month-over-Month (MoM) view since that's more actionable for operations. 


Phase 4 (Historical Reporting)
This is probably the biggest improvement.

Instead of always showing the newest snapshot:

Add:

Current Snapshot
▼ Jul 21

Compare Against
▼ Jul 14

or

▼ Jun 30

Then every KPI becomes:

AR
$3.21M

▲ $245k WoW
or

Past Due

▼ $112k
This will make the portal feel much more like Power BI. 

 


Phase 5 (Layout Fixes)
I noticed your comments about overlapping text.

We'll fix:

chart titles

legends

responsive spacing

mobile widths

graph padding

so nothing overlaps anymore. 


One Additional Suggestion
I would add something that wasn't in the document but would make the portal even stronger.

On the Executive page, add an Executive Insights section generated automatically, for example:

Week of July 21

• Total AR decreased $468K week over week.
• Past Due improved $152K.
• Chargebacks increased $28K, primarily due to UNFI.
• New Sales increased 11.4%.
• CB Recoveries exceeded new Chargebacks by $42K.

This gives your CEO an immediate narrative without having to interpret every chart.

My recommended build order
Historical Snapshot selector (Current vs Compare)

WoW calculations across all KPIs

Export buttons for every section

"Show All" options throughout the portal

Bar labels and chart improvements

Revenue page redesign (MoM and more tabular metrics)

Layout cleanup and overlap fixes

Executive Insights summary

I think these changes will move the portal from looking like a polished dashboard to feeling like a true executive reporting platform, with faster access to trends, comparisons, and exportable data.


514b5d2e-3664-4826-8c89-370e7dd45dd5.png
da2bba23-58b6-4be1-999b-627db337694a.png
current snapshots are off
also change the number format on the MoM rev and AR snapshot.
for AR snapshot comparison, we should just have, Total AR, Current and Past due

Edit


Edit


Edit


Edit


Edit


d34a5ff5-2b6b-43a9-9523-da7e7f1b73d3.png


Pasted text(1).txt
Document

18b704b5-ff99-43b4-8e64-8b7a5f62f083.png

That's actually expected. You're typing Python code into PowerShell, and PowerShell is trying to interpret it as PowerShell commands.

Instead, run Python with the code inside quotes, like this:

py -c "from utils.data import ar_snapshot_files; print(ar_snapshot_files())"
or simply:

py -c "from utils.data import ar_snapshot_files; print('IMPORT OK')"
The important thing is that you already told me this worked earlier, and py_compile also passed.

That means we've now proven:

✅ utils/data.py has no syntax errors.

✅ ar_snapshot_files() exists.

✅ Python can import it locally.

✅ GitHub has the correct commit (a18b372).

At this point, I no longer believe the code is the problem.

I think Streamlit Cloud is deploying a different revision or stale environment.
The next thing I want to verify is the app configuration.

Please click:

⋮ → Settings

and send me a screenshot of that page.

I want to verify:

Repository

Branch

Main file path

Whether it's pointing at the correct GitHub repo

One incorrect setting there (for example, an old fork, a different branch, or a different app.py) would produce exactly the behavior you're seeing: GitHub is correct, your local code is correct, but the deployed app never picks up the changes.

I think we're one step away from finding the root cause.


PS C:\Projects\Groundwork-Finance-Portal> py -c "from utils.data import ar_snapshot_files; print(ar_snapshot_files())"
[(Timestamp('2026-07-13 00:00:00'), WindowsPath('C:/Projects/Groundwork-Finance-Portal/data/snapshots/ar/ar_2026-07-13.csv')), (Timestamp('2026-07-10 00:00:00'), WindowsPath('C:/Projects/Groundwork-Finance-Portal/data/snapshots/ar/ar_2026-07-10.csv'))]

Perfect—that proves the function works correctly and finds both AR snapshots locally:

July 13, 2026

July 10, 2026

So the issue is now isolated to Streamlit Cloud deployment, not your code.

Open the app’s Settings and verify:

Repository: Odiesales/groundwork-finance-portal

Branch: main

Main file path: app.py

Then use Reboot again. If it still shows the old import error, send me a screenshot of the Settings page. The most likely cause is Streamlit pointing to the wrong repo, branch, or entry file.


1e75daab-b225-40ef-9cea-ba69751719c7.png
few things changed, but number format didnt

You’re right. The layout changes deployed, but the table formatting is still using raw values.

From the screenshot, these still need fixing:

Revenue should be $3,163,642.89, not $3163642.89

Pounds should be 26,031.75, not 26031.75

Percentages are being calculated as decimals but displayed as whole percentages incorrectly:

-0.03% likely should be about -3.0%

0.25% likely should be about 25.0%

AR values need comma separators.

None should display as —

Negative currency should preferably display as ($73,674.37) or -$73,674.37

The fix needs to be made in pages/3_Trends.py, specifically where the three dataframes are sent to st.dataframe().

Please paste or upload the complete pages/3_Trends.py file. I’ll give you a full replacement so we fix all three tables together rather than patching one column at a time.



3_Trends.py
Python

I rebuilt the Trends page so the displayed tables use:

Comma-separated currency: $3,163,642.89

Comma-separated pounds: 26,031.75

Parentheses for negative amounts: ($73,674.37)

Percentages converted correctly from decimals: 0.25 → 25.00%

Em dashes instead of None

The original exports remain numeric for Excel. The formatting issue came from the current NumberColumn formats, which did not add thousands separators and displayed the percentage decimals directly. 



Replace:

pages/3_Trends.py
with the downloaded file, rename it to 3_Trends.py, and run:

git add pages\3_Trends.py
git commit -m "Fix Trends number and percentage formatting"
git push origin main



Library
/
3_Trends_v3_2_1.py


import pandas as pd
import streamlit as st

from utils.data import load_revenue_history, load_ar_history, monthly_revenue_summary
from utils.ui import page_header, section, footer


def format_currency(value):
    """Format currency with commas and parentheses for negative amounts."""
    if pd.isna(value):
        return "—"
    amount = float(value)
    return f"(${abs(amount):,.2f})" if amount < 0 else f"${amount:,.2f}"


def format_number(value):
    """Format numeric values with commas."""
    if pd.isna(value):
        return "—"
    return f"{float(value):,.2f}"


def format_percent(value):
    """Format decimal percentages, such as 0.25, as 25.00%."""
    if pd.isna(value):
        return "—"
    return f"{float(value) * 100:,.2f}%"


page_header(
    "Trends & Analytics",
    "Month-over-month Revenue and selectable AR snapshot comparisons.",
    badge="Historical",
)

rev = load_revenue_history(include_current=False)
ar = load_ar_history(include_current=False)

if rev.empty and ar.empty:
    st.info("Save snapshots in Administration first. Trends will appear once historical data exists.")
    st.stop()


if not rev.empty:
    section(
        "Month-over-Month Revenue",
        "Monthly numbers are shown first for faster executive review.",
    )

    monthly = monthly_revenue_summary(rev)
    monthly["Revenue Change"] = monthly["Revenue"].diff()
    monthly["$/LB Change"] = monthly["Weighted $/LB"].diff()

    st.download_button(
        "⇩ Export MoM Revenue",
        monthly.to_csv(index=False).encode("utf-8"),
        "Revenue_MoM.csv",
        "text/csv",
    )

    monthly_display = monthly.copy()

    if "Month" in monthly_display.columns:
        monthly_display["Month"] = monthly_display["Month"].astype(str)

    for column in ["Revenue", "Weighted $/LB", "Revenue Change", "$/LB Change"]:
        if column in monthly_display.columns:
            monthly_display[column] = monthly_display[column].map(format_currency)

    if "Lbs" in monthly_display.columns:
        monthly_display["Lbs"] = monthly_display["Lbs"].map(format_number)

    for column in ["MoM Revenue %", "MoM $/LB %"]:
        if column in monthly_display.columns:
            monthly_display[column] = monthly_display[column].map(format_percent)

    st.dataframe(monthly_display, width="stretch", hide_index=True)


if not ar.empty:
    ar["Snapshot Date"] = pd.to_datetime(ar.get("Snapshot Date"), errors="coerce")
    ar["Open Balance"] = pd.to_numeric(
        ar.get("Open Balance", 0),
        errors="coerce",
    ).fillna(0)
    ar["Bucket"] = (
        ar.get("Bucket", "Unknown")
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    dates = sorted(
        ar["Snapshot Date"].dropna().dt.normalize().unique(),
        reverse=True,
    )

    section(
        "AR Snapshot Comparison",
        "Pick any two saved as-of dates and compare Total AR, Current, and Past Due.",
    )

    c1, c2 = st.columns(2)
    date_options = [pd.Timestamp(d) for d in dates]

    with c1:
        current_date = st.selectbox(
            "As of Date",
            date_options,
            format_func=lambda d: d.strftime("%b %d, %Y"),
            key="trend_ar_current",
        )

    with c2:
        prior_date = st.selectbox(
            "Compare Against",
            date_options,
            index=min(1, len(date_options) - 1),
            format_func=lambda d: d.strftime("%b %d, %Y"),
            key="trend_ar_prior",
        )

    def snapshot_values(value):
        snap = ar[
            ar["Snapshot Date"].dt.normalize().eq(pd.Timestamp(value))
        ].copy()

        balances = snap["Open Balance"]
        current_mask = snap["Bucket"].str.casefold().eq("current")

        total = float(balances.sum())
        current = float(balances[current_mask].sum())

        return {
            "Total AR": total,
            "Current": current,
            "Past Due": total - current,
        }

    current_values = snapshot_values(current_date)
    prior_values = snapshot_values(prior_date)

    rows = []

    for metric in ["Total AR", "Current", "Past Due"]:
        current_amount = current_values[metric]
        prior_amount = prior_values[metric]
        change = current_amount - prior_amount
        change_pct = change / abs(prior_amount) if prior_amount else pd.NA

        rows.append(
            {
                "Metric": metric,
                pd.Timestamp(current_date).strftime("%b %d, %Y"): current_amount,
                pd.Timestamp(prior_date).strftime("%b %d, %Y"): prior_amount,
                "Change": change,
                "Change %": change_pct,
            }
        )

    comparison = pd.DataFrame(rows)

    st.download_button(
        "⇩ Export AR Comparison",
        comparison.to_csv(index=False).encode("utf-8"),
        "AR_Snapshot_Comparison.csv",
        "text/csv",
    )

    comparison_display = comparison.copy()

    amount_columns = [
        column
        for column in comparison_display.columns
        if column not in ["Metric", "Change %"]
    ]

    for column in amount_columns:
        comparison_display[column] = comparison_display[column].map(format_currency)

    comparison_display["Change %"] = comparison_display["Change %"].map(format_percent)

    st.dataframe(comparison_display, width="stretch", hide_index=True)

    section(
        "AR Snapshot History",
        "All saved snapshots are preserved and shown newest first.",
    )

    history_rows = []

    for snapshot_date in sorted(date_options):
        values = snapshot_values(snapshot_date)
        history_rows.append({"As of Date": snapshot_date, **values})

    hist = (
        pd.DataFrame(history_rows)
        .sort_values("As of Date", ascending=False)
        .reset_index(drop=True)
    )

    hist["WoW Change"] = hist["Total AR"] - hist["Total AR"].shift(-1)

    st.download_button(
        "⇩ Export AR History",
        hist.to_csv(index=False).encode("utf-8"),
        "AR_History.csv",
        "text/csv",
    )

    hist_display = hist.copy()
    hist_display["As of Date"] = hist_display["As of Date"].dt.strftime("%b %d, %Y")

    for column in ["Total AR", "Current", "Past Due", "WoW Change"]:
        hist_display[column] = hist_display[column].map(format_currency)

    st.dataframe(hist_display, width="stretch", hide_index=True)


footer()
