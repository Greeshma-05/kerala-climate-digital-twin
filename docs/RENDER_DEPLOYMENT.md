# Deploy the existing dashboard on Render

This is an alternative to Streamlit Community Cloud. The dashboard still uses Python, Streamlit, Open-Meteo, pandas, SQLite, Plotly and PyDeck.

## Deploy using the prepared configuration

1. Sign in to [Render](https://dashboard.render.com/) and connect your GitHub account.
2. Grant Render access to the private `Greeshma-05/kerala-climate-digital-twin` repository.
3. Choose **New → Blueprint**, then select that repository and its `main` branch.
4. Render reads `render.yaml`. Review the proposed service and confirm that the instance plan is **Free** before creating it.
5. Start the deployment. Wait for Render to report the service as live, then open the actual URL shown in its dashboard.
6. Click **Collect weather** to populate the hosted database. The local dataset on your laptop is not uploaded.

Connecting the Render integration in this conversation lets the assistant inspect the available deployment controls and continue setup where supported. The integration and Render's GitHub repository access are separate connections; the latter may still need authorization in your browser.

## What the new files do

- `render.yaml` defines one free Python web service. It installs `requirements.txt`, starts `app.py`, and checks the Streamlit health endpoint.
- `.python-version` selects the latest Python 3.14 patch available on Render. Local verification used Python 3.14.6.
- `$PORT` is supplied by Render. Listening on `0.0.0.0` allows the hosting platform to reach the server.

If creating a **Web Service** manually, use these settings instead of creating a second Blueprint service:

| Setting | Value |
| --- | --- |
| Repository | `Greeshma-05/kerala-climate-digital-twin` |
| Branch | `main` |
| Runtime | Python |
| Build command | `pip install -r requirements.txt` |
| Start command | `python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true` |
| Health check | `/_stcore/health` |
| Instance plan | Free |

## Demo availability and storage

Render's free web services sleep after 15 minutes without traffic and wake on a new request. This plan is not an always-running service. Local filesystem changes, including SQLite, CSV and raw JSON, are lost when the service restarts, redeploys or sleeps. Download data you need to keep; collect again if the dashboard starts empty.

Always-running hosting with permanent SQLite storage would require a suitable paid service and persistent disk, or a separate durable database. No paid plan, disk or database is included in this configuration.

## Verify after deployment

Open the service URL and check the initial page, collection status, charts, map and download. The `/_stcore/health` endpoint verifies server availability; it does not prove that the weather collection or every UI feature succeeded.

References: [Blueprint specification](https://render.com/docs/blueprint-spec), [Python versions](https://render.com/docs/python-version), [free-plan limitations](https://render.com/docs/free).
