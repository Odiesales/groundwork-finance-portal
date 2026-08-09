# CEO Demo Deployment

This package includes the July 13, 2026 AR aging as the current snapshot.

## Replace the local project

Copy the contents of this folder into:

`C:\Projects\Groundwork-Finance-Portal`

Keep the folder structure unchanged.

## Push to GitHub

Open PowerShell in the project folder and run:

```powershell
git status
git add .
git commit -m "Publish July 13 AR dashboard for CEO review"
git push origin main
```

## Deploy or refresh Streamlit Community Cloud

Use the existing app connected to the GitHub repository and main file `app.py`.
After the GitHub push, Streamlit Community Cloud should rebuild automatically. If it does not, open **Manage app** and select **Reboot app**.

## Sharing recommendation

Because the app contains customer-level AR information, set the app to private and invite the CEO as a viewer from the app's Sharing settings. A private GitHub repository can also be used after granting Streamlit access to private repositories.

## Validated July 13 figures

- Total AR: $3,864,748.90
- Current AR: $2,426,755.34
- Past Due AR: $1,437,993.56
- Past Due %: 37.21%
- 60+ exposure: $272,671.19
- 91+ exposure: $122,579.03
- Customers: 288
