GROUNDWORK FINANCE PORTALS - V4.0 SPLIT RELEASE

This release separates the former Finance Portal into two deployable Streamlit apps.

1. Groundwork-AR-Deductions-Portal
   - Executive Scorecard
   - DSO
   - Accounts Receivable
   - Chargebacks
   - CB Analysis
   - AR Trends
   - Administration

   DSO methodology:
   Net AR / Monthly Sales x Calendar Days in Month

   Monthly DSO uses the latest saved AR snapshot in each month and monthly Revenue
   data synced from the shared Revenue history. Overall, channel, customer, and
   historical DSO are included.

   Chargeback corrections:
   - Removed the misleading As of Total column.
   - Historical weekly snapshots are not summed together.
   - The chargeback month matrix uses the latest saved snapshot in each month.
   - Grand Total is bold.
   - Added an executive Chargeback Analysis page.

2. Groundwork-Sales-Revenue-Portal
   - Weekly Revenue Report
   - Sales Revenue Administration

The two apps can be deployed as separate Streamlit Cloud apps/repositories while
continuing to use the same Google Drive data structure. The AR portal reads the
shared Revenue history only to calculate DSO; it does not expose Sales Revenue
reporting pages.
