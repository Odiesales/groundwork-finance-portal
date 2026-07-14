from __future__ import annotations

from datetime import datetime
from pathlib import Path
import base64
import html

import pandas as pd
import streamlit as st

from utils.paths import ASSETS_DIR

CREAM = "#F6F1E8"
CARD = "#FFFFFF"
CHARCOAL = "#22251F"
MUTED = "#6F736A"
YELLOW = "#E6B92F"
BORDER = "#D8D1C5"
GREEN = "#143E33"
GREEN_2 = "#285B4B"
GREEN_PALE = "#E7EFEA"
RED = "#A44739"


def _asset_uri(path: Path) -> str:
    try:
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""


def inject_global_css() -> None:
    mark = _asset_uri(ASSETS_DIR / "Groundwork_mark_white.png")
    st.markdown(f"""
<style>
:root{{--gw-cream:{CREAM};--gw-card:{CARD};--gw-charcoal:{CHARCOAL};--gw-muted:{MUTED};--gw-yellow:{YELLOW};--gw-border:{BORDER};--gw-green:{GREEN};--gw-green2:{GREEN_2};--gw-red:{RED};}}
html,body,[class*="css"]{{color:var(--gw-charcoal)}}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{background:var(--gw-cream)!important}}
[data-testid="stHeader"]{{background:#11151D!important;height:3.25rem}}
.block-container{{max-width:1500px;padding:1.25rem 2.1rem 3rem}}

/* One shared sidebar shell */
[data-testid="stSidebar"]{{background:var(--gw-green)!important;border-right:0!important}}
[data-testid="stSidebarContent"]{{padding-top:.25rem}}
[data-testid="stSidebar"] *{{color:#F8F5EE!important}}
[data-testid="stSidebarNav"]{{padding:.25rem .65rem 0!important}}
[data-testid="stSidebarNav"]::before{{
 content:"GROUNDWORK COFFEE ROASTERS\\A FINANCE PORTAL";white-space:pre;display:block;
 padding:92px 8px 20px;text-align:center;color:#fff;font-weight:800;font-size:.78rem;
 line-height:1.42;letter-spacing:.06em;border-bottom:1px solid rgba(255,255,255,.16);
 background-image:url('{mark}');background-repeat:no-repeat;background-position:center 8px;background-size:74px 74px;
}}
[data-testid="stSidebarNav"] ul{{gap:.3rem;padding-top:.6rem}}
[data-testid="stSidebarNav"] li{{border-radius:10px;overflow:hidden}}
[data-testid="stSidebarNav"] a{{border-radius:10px!important;padding:.72rem .78rem!important;font-weight:700!important}}
[data-testid="stSidebarNav"] a:hover{{background:rgba(255,255,255,.10)!important}}
[data-testid="stSidebarNav"] a[aria-current="page"]{{background:#F4F0E8!important}}
[data-testid="stSidebarNav"] a[aria-current="page"] *{{color:var(--gw-green)!important}}
.gw-sidebar-status{{margin:1rem .9rem .45rem;padding:.85rem .9rem;border-radius:12px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.15)}}
.gw-sidebar-status-label{{font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;color:#CFE0D7!important}}
.gw-sidebar-status-value{{font-size:.86rem;font-weight:800;margin-top:.25rem}}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{{color:#fff!important}}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea,[data-testid="stSidebar"] [contenteditable="true"]{{color:#22251F!important;-webkit-text-fill-color:#22251F!important;caret-color:#22251F!important}}
[data-testid="stSidebar"] div[data-baseweb="input"],[data-testid="stSidebar"] div[data-baseweb="select"]>div,[data-testid="stSidebar"] [role="combobox"]{{background:#fff!important;color:#22251F!important}}
div[data-baseweb="popover"],div[data-baseweb="menu"],ul[role="listbox"],li[role="option"],div[role="option"]{{background:#fff!important;color:#22251F!important}}

/* Shared banner */
.gw-page-head{{display:flex;justify-content:space-between;align-items:center;gap:1.4rem;background:#fff;border:1px solid var(--gw-border);border-radius:18px;padding:1.1rem 1.3rem;margin:.15rem 0 1.35rem;box-shadow:0 9px 26px rgba(37,46,39,.06)}}
.gw-greeting{{color:var(--gw-green2);font-size:.78rem;font-weight:800;margin-bottom:.25rem}}
.gw-page-title{{margin:0;color:var(--gw-charcoal);font-size:2rem;line-height:1.1;font-weight:880;letter-spacing:-.035em}}
.gw-page-subtitle{{color:var(--gw-muted);font-size:.92rem;margin-top:.4rem}}
.gw-head-status{{min-width:170px;background:var(--gw-green-pale);border:1px solid #CAD9D0;border-radius:12px;padding:.72rem .9rem;text-align:right;color:var(--gw-green)}}
.gw-head-status strong{{color:var(--gw-green);font-size:.8rem}} .gw-head-status small{{display:block;color:var(--gw-muted);margin-top:.15rem}}
.gw-section-title{{font-size:1.1rem;font-weight:840;margin:1.3rem 0 .1rem;color:var(--gw-charcoal)}}
.gw-section-caption{{color:var(--gw-muted);font-size:.87rem;margin-bottom:.65rem}}
.gw-card{{background:#fff;border:1px solid var(--gw-border);border-radius:14px;box-shadow:0 7px 22px rgba(37,46,39,.05);padding:1rem 1.05rem}}
.gw-kpi{{min-height:116px;position:relative;overflow:hidden}} .gw-kpi:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--gw-yellow)}}
.gw-kpi-label{{color:var(--gw-muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.085em;font-weight:780}}
.gw-kpi-value{{font-size:1.48rem;font-weight:860;margin-top:.45rem;color:var(--gw-charcoal);white-space:nowrap}}
.gw-kpi-delta{{font-size:.74rem;font-weight:720;margin-top:.5rem}} .gw-positive{{color:var(--gw-green2)}} .gw-negative{{color:var(--gw-red)}} .gw-neutral{{color:var(--gw-muted)}}
.gw-insight{{background:#FEFBF3;border:1px solid #E6D8AC;border-left:5px solid var(--gw-yellow);border-radius:14px;padding:1rem 1.15rem}}
.gw-insight-title{{font-weight:840;margin-bottom:.35rem}} .gw-insight p{{margin:.2rem 0;color:#44473F!important}}
[data-testid="stDataFrame"],[data-testid="stTable"]{{background:#fff!important;border:1px solid var(--gw-border)!important;border-radius:14px;overflow:hidden;box-shadow:0 7px 22px rgba(37,46,39,.04)}}
table{{background:#fff!important;color:var(--gw-charcoal)!important}} thead tr th{{background:#EEE9DF!important;color:var(--gw-charcoal)!important}} tbody tr td{{background:#fff!important;color:var(--gw-charcoal)!important}}
.gw-footer{{margin-top:2rem;padding-top:.9rem;border-top:1px solid var(--gw-border);color:var(--gw-muted);font-size:.75rem;text-align:center}}
@media(max-width:900px){{.gw-page-head{{display:block}}.gw-head-status{{margin-top:.8rem;text-align:left}}.gw-page-title{{font-size:1.65rem}}}}
</style>""", unsafe_allow_html=True)


def greeting_for_now(now: datetime | None = None) -> str:
    h=(now or datetime.now()).hour
    return "Good Morning" if h<12 else "Good Afternoon" if h<17 else "Good Evening"


def sidebar_snapshot(snapshot_date=None) -> None:
    text="No snapshot loaded"
    if snapshot_date is not None and not pd.isna(snapshot_date):
        text=pd.Timestamp(snapshot_date).strftime("%b %d, %Y")
    st.sidebar.markdown(f'<div class="gw-sidebar-status"><div class="gw-sidebar-status-label">Current snapshot</div><div class="gw-sidebar-status-value">{html.escape(text)}</div></div>',unsafe_allow_html=True)


def page_header(title, subtitle="", badge=None, snapshot_date=None, compared_date=None):
    status=""
    if snapshot_date is not None and not pd.isna(snapshot_date):
        current=pd.Timestamp(snapshot_date).strftime("%b %d, %Y")
        compare=f'<small>Compared with {pd.Timestamp(compared_date).strftime("%b %d, %Y")}</small>' if compared_date is not None and not pd.isna(compared_date) else ""
        status=f'<div class="gw-head-status"><strong>● Current Snapshot</strong><small>{current}</small>{compare}</div>'
    elif badge:
        status=f'<div class="gw-head-status"><strong>{html.escape(str(badge))}</strong></div>'
    st.markdown(f'<div class="gw-page-head"><div><div class="gw-greeting">{greeting_for_now()}</div><h1 class="gw-page-title">{html.escape(str(title))}</h1><div class="gw-page-subtitle">{html.escape(str(subtitle))}</div></div>{status}</div>',unsafe_allow_html=True)


def section(title, caption=""):
    st.markdown(f'<div class="gw-section-title">{html.escape(str(title))}</div>',unsafe_allow_html=True)
    if caption: st.markdown(f'<div class="gw-section-caption">{html.escape(str(caption))}</div>',unsafe_allow_html=True)


def footer(): st.markdown('<div class="gw-footer">Groundwork Coffee Roasters Finance Portal • Internal Use Only</div>',unsafe_allow_html=True)

def format_money(value, decimals=2):
    try:return f"${float(value):,.{decimals}f}"
    except Exception:return "$0.00"

def format_percent(value, decimals=2, signed=False):
    try:
        if pd.isna(value): return "—"
        return f"{float(value):+.{decimals}%}" if signed else f"{float(value):.{decimals}%}"
    except Exception:return "—"

def format_number(value, decimals=0):
    try:return f"{float(value):,.{decimals}f}"
    except Exception:return "0"

def _delta_parts(delta,inverse=False):
    if delta is None:return "","neutral"
    text=str(delta);neg=text.strip().startswith("-") or "▼" in text;pos=text.strip().startswith("+") or "▲" in text
    if inverse:neg,pos=pos,neg
    return text,"negative" if neg else "positive" if pos else "neutral"

def kpi_row(metrics):
    cols=st.columns(len(metrics))
    for col,item in zip(cols,metrics):
        text,cls=_delta_parts(item.get("delta"),item.get("inverse",False))
        delta=f'<div class="gw-kpi-delta gw-{cls}">{html.escape(text)}</div>' if text else ""
        with col: st.markdown(f'<div class="gw-card gw-kpi"><div class="gw-kpi-label">{html.escape(str(item.get("label","")))}</div><div class="gw-kpi-value">{html.escape(str(item.get("value","")))}</div>{delta}</div>',unsafe_allow_html=True)

def metric_row(metrics):
    kpi_row([m if isinstance(m,dict) else {"label":m[0],"value":m[1],"delta":m[2] if len(m)>2 else None} for m in metrics])

def insight_box(title,lines):
    body="".join(f'<p>• {html.escape(str(x))}</p>' for x in lines)
    st.markdown(f'<div class="gw-insight"><div class="gw-insight-title">{html.escape(str(title))}</div>{body}</div>',unsafe_allow_html=True)

def apply_multiselect_filter(df,label,column,sidebar=True):
    if column not in df.columns or df.empty:return df
    target=st.sidebar if sidebar else st
    values=sorted(df[column].fillna("Unknown").astype(str).unique())
    selected=target.multiselect(label,values,key=f"filter_{label}_{column}")
    return df[df[column].fillna("Unknown").astype(str).isin(selected)] if selected else df

def chart_layout(fig,height=360):
    fig.update_layout(height=height,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=CHARCOAL,family="Arial"),margin=dict(l=10,r=10,t=20,b=10),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    fig.update_xaxes(showgrid=False,zeroline=False);fig.update_yaxes(gridcolor="#E5DED2",zeroline=False)
    return fig

def bar_chart(df,x,y,title=None,orientation=None,text=None):
    import plotly.express as px
    fig=px.bar(df,x=x,y=y,title=title,orientation=orientation,text=text);fig.update_traces(marker_color=GREEN_2,marker_line_color=GREEN,marker_line_width=.4)
    return chart_layout(fig)

def line_chart(df,x,y,title=None):
    import plotly.express as px
    fig=px.line(df,x=x,y=y,title=title,markers=True);fig.update_traces(line_color=GREEN_2,marker=dict(color=YELLOW,size=8,line=dict(color=GREEN,width=1)))
    return chart_layout(fig)

def style_money_table(df):
    money=[c for c in df.columns if any(t in c.lower() for t in ["balance","revenue","amount","ar","chargeback","change","sales","credit"])]
    return df.style.format({c:"${:,.2f}" for c in money})

def style_revenue_table(df):
    formats={"Revenue":"${:,.2f}","Lbs":"{:,.2f}","Weighted $/LB":"${:,.2f}","Avg $/LB":"${:,.2f}","Mix %":"{:.2%}","MoM Revenue %":"{:.2%}","YoY Revenue %":"{:.2%}","MoM $/LB %":"{:.2%}","YoY $/LB %":"{:.2%}"}
    return df.style.format({k:v for k,v in formats.items() if k in df.columns})
