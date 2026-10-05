# Simple FastAPI server

One application endpoint: `GET /` returns:

```json
{"status": "ok", "message": "Hello from FastAPI!"}
```

## Run locally (PowerShell)

Use Python 3.10 or newer. From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/ or the interactive API documentation at
http://127.0.0.1:8000/docs. Stop the server with Ctrl+C.

Test from PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

## Deploy on Render's free plan

1. Push these files to a GitHub repository (do not upload `.venv`).
2. Sign in at https://render.com and choose **New > Blueprint**.
3. Connect the repository. Render reads the included `render.yaml`, which
   selects the free plan, installs dependencies, and starts the server.
4. After deployment, use your service URL, such as
   `https://your-service.onrender.com/`. API documentation is at `/docs`.

Alternatively, create a **Web Service** with runtime **Python 3**, build command
`pip install -r requirements.txt`, start command
`uvicorn main:app --host 0.0.0.0 --port $PORT`, and instance type **Free**.

Free instances sleep when idle, so the first request afterward can take longer.
Current limits: https://render.com/docs/free
Official deployment guide: https://render.com/docs/deploy-fastapi

## Call from a website

```javascript
const response = await fetch("https://your-service.onrender.com/");
const data = await response.json();
console.log(data);
```

Cross-origin GET requests are enabled for this public test endpoint. No
authentication or database is required. Change the response in `main.py`.
