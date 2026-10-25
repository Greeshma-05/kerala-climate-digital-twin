# GitHub and live dashboard deployment

The GitHub repository stores the source code. Streamlit Community Cloud runs the Python dashboard and gives you a shareable web address. GitHub Pages only serves static websites and cannot run this Streamlit server.

## 1. Repository

Repository: **[Greeshma-05/kerala-climate-digital-twin](https://github.com/Greeshma-05/kerala-climate-digital-twin)**

- Branch: `main`
- Dashboard entrypoint: `app.py`
- Dependencies: `requirements.txt`
- Theme: `.streamlit/config.toml`

The repository is initially private. Generated weather data, SQLite files, the virtual environment and local secrets are excluded by `.gitignore`. Your local collected dataset remains on your computer.

## 2. Deploy on Streamlit Community Cloud

1. Open **[share.streamlit.io](https://share.streamlit.io/)** and sign in using your GitHub account, `Greeshma-05`.
2. If prompted, connect GitHub and allow Streamlit to access this private repository. Complete account sign-in and authorization yourself.
3. Select the `Greeshma-05` workspace and click **Create app**.
4. Choose the option to deploy an existing app from GitHub.
5. Fill in these values:

   | Setting | Value |
   | --- | --- |
   | Repository | `Greeshma-05/kerala-climate-digital-twin` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | Python version, under Advanced settings | `3.12` |
   | Secrets | Leave empty; this app does not need an API key |

6. Choose an available app subdomain if you want a custom address, then click **Deploy**.
7. Wait for dependency installation and app startup. The platform displays the actual `https://...streamlit.app` URL after deployment; no particular subdomain is reserved by this project.
8. Open the dashboard and click **Collect weather**. The cloud app starts without your local database, so this creates its initial dataset.
9. Check the collection report for **14/14** successful districts and inspect charts and map tooltips.

Python 3.12 is Community Cloud's documented default. The local project was verified with Python 3.14.6; deployment installs the compatible ranges from `requirements.txt`, rather than the local `requirements-lock.txt` snapshot.

## 3. Share the live dashboard

An app deployed from a private repository starts private. To let anyone open the dashboard, use **App settings → Sharing → Who can view this app → This app is public and searchable**. Making the dashboard public does not require making the GitHub source repository public.

For a restricted presentation, keep the app private and use Streamlit's viewer-sharing settings instead. The repository itself remains private unless you change its GitHub visibility separately.

## 4. Understand cloud storage

The cloud database is separate from the database on your laptop. Treat SQLite, CSV and raw JSON stored on the cloud app's local filesystem as temporary: restarts or redeployments can remove local files. Use the dashboard's CSV download before relying on a dataset for your report. Click **Collect weather** again if the app starts empty.

This is suitable for a Phase 1 demonstration. Durable cloud history needs persistent external storage in a later phase. The cloud app still collects only when its button is clicked; this deployment does not introduce a background schedule.

## 5. Publish later code changes

From your project folder:

```bash
git status
git add app.py
git commit -m "Improve dashboard"
git push origin main
```

Replace `app.py` with the specific files you changed. Streamlit detects changes to its connected branch and updates the app. Dependency changes can take longer because packages must be installed again.

If you change code that affects data processing or the dashboard, run the existing checks before pushing:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

## Official guides

- [Deploy a Streamlit app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Share a public or private app](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Community Cloud status and limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)
- [GitHub Pages capabilities](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
