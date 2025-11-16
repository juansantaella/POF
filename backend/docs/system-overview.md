Here’s a concise “runbook” style document you can save in your project (for example as `docs/architecture-overview.md`).
I’ll include a simple diagram plus a clear description of how everything connects and how changes flow.

---

# Put-Opportunity-Finder – Architecture & Deployment Overview

## 1. Big picture

```text
+-------------------------+             +------------------------+
|  Your PC (Windows)      |             |  Cloud Hosting         |
|                         |             |                        |
|  VS Code                |             |   Render (backend)     |
|  GitHub Desktop         |             |   Netlify (frontend)   |
|                         |             |                        |
|  H:\...\GitHub\         |             |   Polygon / Massive    |
|    Put-Oportunity-Finder|             +-----------+------------+
+---------------+---------+                         ^
                |                                   |
                v                                   |
          Git (push/pull)                           |
                |                                   |
        +-------+------------------+                |
        |       GitHub             |                |
        | repo: Put-Oportunity-    |<---------------+
        |       Finder             |
        +--------------------------+
```

High level:

* **Local machine**: you edit code in `H:\Other computers\My Computer\Documents\GitHub\Put-Oportunity-Finder`.
* **GitHub**: central source of truth for the code.
* **Render**: pulls the code from GitHub and runs the **backend** (FastAPI).
* **Netlify**: pulls the code from GitHub and builds/serves the **frontend** (Vite/React).
* **Polygon/Massive**: external data provider used by the backend.

---

## 2. Local project layout

Local folder (synced by Google Drive and tracked by Git):

```text
H:\Other computers\My Computer\Documents\GitHub\Put-Oportunity-Finder
│
├─ backend/
│   ├─ main.py                 # FastAPI app (routes, CORS, Massive calls, etc.)
│   ├─ strategy_defaults.env   # Default rolling parameters (local dev)
│   ├─ Polygon_API_Key.env     # LOCAL ONLY – contains POLYGON_API_KEY
│   ├─ requirements.txt        # Python dependencies for Render
│   └─ ... other backend files
│
├─ frontend/
│   ├─ src/
│   │   └─ App.tsx             # Main React/Vite UI
│   ├─ .env.development        # Local Vite env (API URL)
│   └─ package.json            # Frontend dependencies
│
└─ .gitignore                  # Tells Git what to ignore (env files, etc.)
```

Notes:

* You edit **`main.py`**, **`strategy_defaults.env`** and **`App.tsx`** primarily.
* `.gitignore` is configured so private files like `Polygon_API_Key.env` are **not** committed to GitHub.

---

## 3. Git & GitHub

* The folder `Put-Oportunity-Finder` is a **Git repository**.

* **GitHub Desktop** connects this local repository to your **GitHub account** and the remote repository:

  * Remote URL: `https://github.com/juansantaella/Put-Oportunity-Finder.git`

* Typical Git operations:

  1. You edit code in VS Code.
  2. GitHub Desktop shows the changed files.
  3. You **Commit** with a message (for example, “Fix CORS order and add Netlify origin”).
  4. You **Push** to GitHub.
     Now GitHub has the latest version of your code.

GitHub itself does **not** run your code. Render and Netlify each watch this repo and deploy from it.

---

## 4. Backend hosting – Render

* Service name: **Put-Oportunity-Finder** (Python 3 / Free plan).
* Public URL:
  `https://put-oportunity-finder.onrender.com`

### 4.1 What Render does

1. When you push to GitHub, Render automatically notices a new commit.
2. It pulls the code from the **Put-Oportunity-Finder** repo.
3. It creates a build environment:

   * Installs Python.
   * Installs packages from `backend/requirements.txt`.
4. It runs the start command (for example):
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. It serves your FastAPI app at the Render URL.

### 4.2 Environment variables on Render

Render uses its own **Environment** settings (not `.env` files) for secrets:

* `POLYGON_API_KEY` – your private Polygon API key.
  (This is why we can safely keep `Polygon_API_Key.env` out of GitHub.)
* Rolling parameters (optional):
  `ROLLING_DELTA_MIN`, `ROLLING_DELTA_MAX`, etc., can override defaults if desired.

### 4.3 CORS configuration (very important)

In `backend/main.py` the relevant section is:

```python
app = FastAPI(
    title="Polygon / Massive backend",
    description="Backend for rolling short PUT strategy helper.",
    version="1.0.0",
)

# Allow local dev frontends + Netlify frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://loquacious-malabi-a19565.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This is what lets your Netlify frontend call the Render backend from the browser.

---

## 5. Frontend hosting – Netlify

* Site name (auto-generated):
  `loquacious-malabi-a19565`
* Public URL:
  `https://loquacious-malabi-a19565.netlify.app`

### 5.1 What Netlify does

1. Netlify is connected to the **same GitHub repo** (`Put-Oportunity-Finder`).

2. Build settings:

   * **Base directory:** `frontend`
   * **Build command:** `npm run build`
   * **Publish directory:** `dist`

3. On each deploy, Netlify:

   * Installs Node dependencies for the frontend.
   * Runs `npm run build` to produce a static bundle in `dist/`.
   * Serves that bundle at the Netlify URL.

### 5.2 Frontend API base URL (env var)

In Netlify **Environment variables**, you configured:

```text
VITE_API_BASE_URL = https://put-oportunity-finder.onrender.com
```

In `App.tsx`, the API base is read from this variable, so when your app calls the backend it uses the Render URL.

---

## 6. External data – Polygon / Massive

The backend (`main.py`) calls Massive/Polygon using:

* `BASE_URL = "https://api.massive.com"` (or the appropriate API URL).
* `POLYGON_API_KEY` from environment variables.

The data is used to:

* Fetch options chains.
* Compute deltas, credit %, and select rolling candidates.

If Massive/Polygon has no data (e.g., weekend), the backend returns an empty result and the UI shows “No opportunities for the current filters.”

---

## 7. Typical “change → deploy” workflow

Here’s the full path for a change you make in, say, `App.tsx` or `main.py`:

1. **Edit code**

   * Use VS Code to change `backend/main.py`, `backend/strategy_defaults.env`, or `frontend/src/App.tsx`.

2. **Save** files locally.

3. **Commit & push via GitHub Desktop**

   * Review changes.
   * Write a commit message.
   * Click **Commit**.
   * Click **Push origin**.

4. **GitHub updated**

   * The `Put-Oportunity-Finder` repo on GitHub now has your new commit.

5. **Render deploys backend**

   * Render sees the new commit.
   * It runs a new deploy of the `Put-Oportunity-Finder` service.
   * When finished, status is **Live** and logs show `Your service is live`.

6. **Netlify deploys frontend**

   * Netlify sees the new commit.
   * It runs the build (`npm run build`) and publishes the updated frontend.
   * The site URL stays the same: `https://loquacious-malabi-a19565.netlify.app`.

7. **End result**

   * From any browser:

     * Frontend: `https://loquacious-malabi-a19565.netlify.app`
     * Frontend calls backend at `https://put-oportunity-finder.onrender.com`
     * Backend calls Polygon/Massive for data.

If Render or Netlify automatic deploys ever get stuck, you can trigger a **Manual deploy** from their dashboards (as you’ve done).

---

## 8. Quick reference – “How do I…?”

**Edit backend logic?**
→ `backend/main.py` in VS Code → Commit & Push → Render auto-deploys.

**Change default strategy settings?**
→ `backend/strategy_defaults.env` or environment variables on Render → Commit & Push → Render auto-deploys.

**Change the UI or sliders?**
→ `frontend/src/App.tsx` (and related files) → Commit & Push → Netlify auto-builds and deploys.

**Change the API base URL for frontend?**
→ Netlify **Environment variables** (`VITE_API_BASE_URL`) → Trigger a new deploy.

**Check backend health?**
→ Open `https://put-oportunity-finder.onrender.com/` and `https://put-oportunity-finder.onrender.com/docs`.

**Check that frontend is talking to backend?**
→ Open Chrome DevTools → **Network → Fetch/XHR** while on Netlify URL → look for `rolling-put-candidates` calls to the Render URL.

