# Deploy the Streamlit dashboard on Vercel

The project now includes a Vercel entry point for the existing Streamlit dashboard. It uses Streamlit's `st.App` ASGI interface and Vercel's Python/WebSocket runtime support. The dashboard remains in `app.py`.

**Live deployment:** [kerala-climate-digital-twin.vercel.app](https://kerala-climate-digital-twin.vercel.app), deployed to the `greeshma-05s-projects` Hobby workspace on 25 October 2026. Public HTTP, WebSocket dashboard execution, live collection for all 14 districts and both CSV downloads passed verification. See [the verification record](VERIFICATION.md).

This setup is for a **Phase 1 demonstration**. The local SQLite database is not a permanent or shared cloud database, and function duration limits can interrupt a browser session. Check the hosted dashboard after future deployments as well.

## 1. What each new file does

| File | Purpose |
| --- | --- |
| `vercel_app.py` | Exposes the Streamlit dashboard as an ASGI application that Vercel can load. |
| `vercel.json` | Defines a Python service at `vercel_app:app`, routes all public paths to it, sets a 300-second function duration, and excludes development files and local data. |
| `requirements.txt` | Supplies all Python packages installed by the Vercel build. |
| `.vercelignore` | Keeps the virtual environment, local secrets, data and development files out of CLI uploads. |
| `.python-version` | Selects Python 3.14, supported by Vercel. |

`requirements.txt` pins Streamlit to the version tested with this adapter. `config.py` uses a directory under `/tmp` when the platform sets `VERCEL=1`, because deployed application files are read-only. `KERALA_DATA_DIR`, if explicitly supplied, still takes precedence.

The `services.dashboard` block owns the Python entry point and `functions` settings. The top-level `rewrites` sends requests to that service. There is no `pyproject.toml`: Vercel gives that file priority over `requirements.txt`, so an entry-point-only file would leave the application dependencies uninstalled.

## 2. Deploy from GitHub

1. Sign in to [Vercel](https://vercel.com/new) using GitHub.
2. Import **`Greeshma-05/kerala-climate-digital-twin`**. Authorize Vercel to access this private repository if prompted.
3. Use branch **`main`** and the repository root as the root directory.
4. Let Vercel read the Python service and `vercel_app:app` entry point from `vercel.json`. Do not enter a static output directory or `streamlit run` as a build command.
5. Leave custom build/install commands unset. The Python runtime installs `requirements.txt`.
6. Use the **Hobby** plan for the initial non-commercial demo if your account is eligible. Do not add a paid plan or storage service just to import this configuration.
7. Deploy, read the build logs, and wait for **Ready**. Copy the actual deployment URL that Vercel returns.

The Vercel integration can also be used from this conversation after installation and account connection. GitHub repository access may still require a separate authorization step.

## 3. Deploy using the CLI

If you have Node.js/npm installed:

```bash
npx vercel login
npx vercel
```

The first deployment is a preview. After confirming that it works:

```bash
npx vercel --prod
```

Complete the account sign-in in your browser. Do not paste passwords or API tokens into chat. The local `.vercel/` project metadata is excluded from Git.

## 4. Verify the live app

1. Open the returned URL. If Vercel deployment protection is enabled, sign in before testing.
2. Confirm that the actual dashboard appears, not just a successful build status.
3. Click **Collect weather** and check for 14 complete districts.
4. Change a district filter and inspect the charts and map.
5. Test a CSV download.
6. Reconnect and check whether the temporary dataset is still available. If empty, collect again.

The `/_stcore/health` endpoint checks server readiness. It does not replace testing the WebSocket, dashboard widgets or collection.

## 5. Storage and session limits

- SQLite, CSV and raw JSON are stored in temporary storage belonging to one function instance. They can disappear when an instance is replaced, and other instances do not share them.
- A WebSocket stays attached to one instance but closes when the function reaches its maximum duration. The configured limit is 300 seconds; the browser may reconnect and lose session/data state.
- A separate HTTP request, including a download, can reach a different instance. Streamlit's in-memory downloads therefore need live verification and shared storage before relying on them with many simultaneous users.
- This app does not perform continuous collection or background scheduling on Vercel.
- The deployment includes scientific Python packages. Check the build's reported bundle size against Vercel's current limits; do not enable paid large-function features without reviewing the plan.

For durable multi-user hosting, move weather history and downloadable files to shared external storage, and verify reconnect behavior. Until then, use this deployment as a demonstration and keep the local SQLite dataset for your project report.

## 6. Local verification

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m tests.check_vercel_server
```

The second command opens a temporary local server, requests the frontend and health endpoint, performs a same-origin WebSocket handshake, runs the actual dashboard with synthetic test records, and verifies 14/14 coverage. It shuts down the temporary server afterward and leaves your real data unchanged.

For manual local use of the hosting entry point:

```bash
python -m uvicorn vercel_app:app --port 8502
```

Your original `streamlit run app.py` command also continues to work.

## References

- [Vercel Python runtime and entry points](https://vercel.com/docs/functions/runtimes/python)
- [Vercel service configuration and routing](https://vercel.com/kb/guide/vercel-services)
- [Vercel WebSocket support and duration limits](https://vercel.com/kb/guide/do-vercel-serverless-functions-support-websocket-connections)
- [Streamlit ASGI application interface](https://docs.streamlit.io/1.64.0/develop/api-reference/server/st.app)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
