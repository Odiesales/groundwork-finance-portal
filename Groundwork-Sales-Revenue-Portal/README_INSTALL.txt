GROUNDWORK SALES REVENUE PORTAL - REVENUE + DSO BUILD

What this page adds
- Executive Summary
- Weekly Revenue + weighted $/LB, always Monday-Sunday
- Monthly Revenue, calendar month, no $/LB
- Monthly DSO using exact month-end AR snapshots
- DSO by month and by the four trade channels
- Size in Pounds is authoritative for $/LB when present

Trade DSO population
Included:
- Foodservice Direct
- Foodservice Distributor
- Grocery Direct
- Grocery Distributor

Excluded:
- Retail
- E-Commerce
- Samples
- Employees
- All other non-trade channels

DSO formula
Month-end trade AR / calendar-month trade revenue * days in month

Install
1. In Groundwork-Sales-Revenue-Portal/pages, identify the current Revenue page (normally 2_Revenue.py).
2. Back up that file.
3. Replace it with the included 2_Revenue.py.
4. Restart Streamlit: python -m streamlit run app.py
5. In Administration, Sync from Drive so AR snapshots and Revenue history are local.
6. Reload the full revenue history with the Size in Pounds column before relying on $/LB.

Important
- The DSO section deliberately shows N/M unless an AR snapshot exists on the exact last calendar day of the month.
- The page reads AR snapshots already synchronized into AR_SNAPSHOT_DIR by the existing Google Drive sync logic.
