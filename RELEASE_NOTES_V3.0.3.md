# Groundwork Finance Portal v3.0.3

- Clean rebuild with all prior operational data removed.
- Official Revenue baseline initialized from the 03/01/2026–07/12/2026 template.
- Revenue pounds formula: Sum of # of Units × weight by lbs.
- Weighted $/LB: eligible Revenue ÷ eligible Pounds.
- Week Of is interpreted as a Sunday-through-Saturday reporting week.
- Administration displays readable Week Of and Week Ending dates.
- Chargeback multi-select filters work in current and historical views.
- Shared Revenue week helpers are included in utils/data.py, eliminating import mismatches.
