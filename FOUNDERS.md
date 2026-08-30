# ChefCulin — Founder setup & demo guide

This zip contains the **complete** CulinAI workspace demo: code, FooDB nutrition data, flavor-network artifacts, the tradition database, and a pre-configured `.env` with the OpenAI key. No extra downloads or API setup required.

> **File size:** ~1–2 GB compressed. Email providers block attachments this large. Open the link from Google Drive, Dropbox, or WeTransfer, download the zip, then follow the steps below.

---

## What you need before starting

| Requirement | How to check | Install if missing |
|-------------|--------------|-------------------|
| **macOS** 12+ or Linux | — | This guide is written for Mac Terminal |
| **Node.js 18+** | `node -v` | [nodejs.org](https://nodejs.org/) → LTS installer |
| **npm** (comes with Node) | `npm -v` | Reinstall Node |
| **Python 3.10+** | `python3 --version` | Mac: `brew install python3` or [python.org](https://www.python.org/downloads/) |
| **OpenAI API key** | Included in zip | Pre-configured in `.env` — no setup needed |

You do **not** need Docker unless you want to test **Save dish** (Palate Memory) at the bottom of the sidebar.

> **Private:** This zip includes a shared demo API key. Do not forward the zip or commit `.env` to git.

---

## Step 1 — Unzip the project

1. Download `chefculin-demo-*.zip` from the link you were sent.
2. Double-click the zip (or right-click → **Open With → Archive Utility**).
3. You should get a folder named **`ChefCulin`** (or similar).

Remember where it lives, e.g. `~/Downloads/ChefCulin`.

---

## Step 2 — Open Terminal in that folder

**Mac:**

1. Open **Terminal** (Spotlight → type `Terminal`).
2. Run (adjust the path if yours is different):

```bash
cd ~/Downloads/ChefCulin
```

3. Confirm you see project files:

```bash
ls
```

You should see `package.json`, `FOUNDERS.md`, `src/`, `pipeline/`, etc.

---

## Step 3 — Install JavaScript dependencies

```bash
npm install
```

Wait until it finishes (1–3 minutes). You should see `node_modules/` appear with no errors.

---

## Step 4 — Set up Python (API backend)

This creates a virtual environment and installs FastAPI + ETL tools:

```bash
npm run setup:demo
```

Expected output includes:

- `FooDB Content.csv present` (already in the zip)
- `Ready. Run: npm run demo`

If Python is missing, install it (see table above) and run this step again.

---

## Step 5 — Start the demo

```bash
npm run demo
```

This starts **two** processes:

| Service | URL | Purpose |
|---------|-----|---------|
| **Web app** | http://localhost:5173 | Main UI — open this in Chrome or Safari |
| **API** | http://localhost:8001 | Co-occurrence + compound artifacts (started automatically) |

Leave this terminal window **open** while you demo. Press `Ctrl+C` to stop.

You should see lines like:

```
[api]  Uvicorn running on http://127.0.0.1:8001
[web]  Local: http://localhost:5173/
```

---

## Step 6 — Open the app

1. Go to **http://localhost:5173**
2. You should see **CulinAI** at the top, a dish sidebar on the left, and lens tabs on the right.

---

## Demo walkthrough (10 minutes)

### A. Pick a focus ingredient

1. Top right → **Focus ingredient** → click **Choose ingredient…**
2. Search e.g. `Chicken`, `Garlic`, or `Lemon`
3. Click a result — the chef line updates to “Designing a dish around …”

### B. Name the dish

1. Left sidebar → click **Untitled** under “The dish”
2. Type a name (e.g. `Spring tasting`) and press **Enter**

### C. Compound lens (flavor chemistry)

1. Tab **Compound** (orange dot)
2. Click **+** on chips (e.g. neighbors of your focus) to add them to the plate
3. Ingredients appear in the left **Committed** list

### D. Tradition lens (documented dishes)

1. Tab **Tradition** (green dot)
2. Five tradition cards load automatically for your focus ingredient
3. Click a card to add companion ingredients to the plate

### E. Co-occurrence lens (recipe corpus)

1. Tab **Co-occurrence** (purple dot)
2. Neighbors load from the local API (first load may take a few seconds)
3. Add chips to the plate

### F. Balance read (left sidebar)

1. Add **at least 3 ingredients** to the plate
2. Scroll to **Balance read** — bars show umami, salt, fat, acid, sweet, heat
3. If one axis dominates (>40%), a **trend flag** appears with a corrective suggestion

### G. Form lens (needs OpenAI key)

1. Tab **Form**
2. Process frames load for your focus ingredient
3. Click a frame to commit it (e.g. **Confit**) — appears under Form in the sidebar

### H. Associate lens (needs OpenAI key)

1. Tab **Associate**
2. Waits for Compound + Tradition + Co-occurrence to agree on suggestions
3. Shows convergent hits and disagreements between lenses

### I. Brainstorm (needs OpenAI key)

1. Tab **Brainstorm**
2. Type a question about your plate (e.g. “What’s missing for balance?”)
3. Chat responds with plate-aware suggestions

### J. Optional — Cuisine scope

1. Top right → **Cuisine scope** → pick e.g. **China**
2. Tradition threads flag whether they match the locked region (nothing is hidden)

---

## What works without OpenAI

| Works offline / no key | Needs `VITE_OPENAI_API_KEY` |
|------------------------|----------------------------|
| Compound | Form |
| Tradition | Brainstorm |
| Co-occurrence | Associate |
| Balance / trending | |

---

## Troubleshooting

### `command not found: node` or `npm`

Install Node.js LTS from [nodejs.org](https://nodejs.org/), quit Terminal, reopen, try again.

### `command not found: python3`

Install Python 3.10+ (see requirements table), then re-run `npm run setup:demo`.

### Port 8001 already in use

```bash
lsof -ti:8001 | xargs kill
npm run demo
```

### “LLM unavailable” in Form / Brainstorm

1. Confirm `.env` exists in the project root (it ships with the zip)
2. Stop the demo (`Ctrl+C`) and run `npm run demo` again

### Co-occurrence tab shows an error

1. Confirm the API is running (terminal shows `[api]` lines)
2. Visit http://localhost:8001/health — should return JSON with `"ok": true`
3. Restart: `npm run demo`

### Blank page at :5173

1. Hard refresh (Cmd+Shift+R)
2. Check terminal for `[web]` errors
3. Try `npm install` again

### Zip unpacked to a nested folder

If you see `ChefCulin/ChefCulin`, `cd` into the inner folder that contains `package.json`.

---

## Optional — Save dish (F6 / Palate Memory)

Saving dishes to a database requires Postgres:

```bash
cd pipeline
docker compose up -d
cd ..
npm run demo
```

Then use **Save** at the bottom of the left sidebar. **Discard** is intentional no-op.

---

## Stopping the demo

In the terminal running `npm run demo`, press **Ctrl+C** once or twice.

---

## Quick reference (copy-paste)

```bash
cd ~/Downloads/ChefCulin    # adjust path
npm install
npm run setup:demo
npm run demo
```

Open **http://localhost:5173**

---

## Questions?

Contact the person who sent you this zip. Include a screenshot of the terminal error if something fails.
