Groundwork Finance Portals v4.1 — AR/DSO cleanup

AR & Deductions Portal changes:
- DSO now aligns AR snapshot date, sales cutoff date, and elapsed calendar days.
- Partial months no longer multiply partial-month sales by a full month's day count.
- AR Trends is now AR-only; Revenue, Lbs, $/LB, and pricing analytics were removed.
- Chargeback ranking charts use dynamic value-label positioning:
  * >=35% of chart maximum: label inside bar
  * smaller bars: label outside bar
  * x-axis padded to 125% of maximum to prevent clipping
- Chargeback snapshot matrix retains no "As of Total" and bold Grand Total.

Sales Revenue Portal remains separate and unchanged.
