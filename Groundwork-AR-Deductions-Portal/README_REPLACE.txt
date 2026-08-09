Groundwork AR & Deductions Portal - deployment compatibility repair

Replace your existing app.py and all Python files in the pages folder with the files in this package.

Repairs included:
- Keeps app.py import-root fix for Streamlit Cloud subfolder deployment.
- Replaces incompatible st.dataframe(width="stretch") usage with use_container_width=True.
- Repairs malformed dataframe blocks introduced during patching.
- Repairs indentation/syntax issues in Executive Scorecard, Accounts Receivable, Chargeback Analysis, Chargebacks, Trends, and Administration.
- Preserves existing dashboard calculations and page structure.

Validation performed:
- All included .py files successfully compile with Python syntax checking.

After replacing files:
1. Save all files.
2. Commit in GitHub Desktop.
3. Push origin.
4. Let Streamlit redeploy automatically.
