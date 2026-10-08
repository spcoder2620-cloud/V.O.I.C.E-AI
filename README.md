# V.O.I.C.E. — GitHub Pages

This is the static website for V.O.I.C.E.

GitHub Pages hosts the HTML page.

Your existing Python brain remains separate:

- `voice.py`
- `smart.py`
- `language.py`
- `voice_memory.json`

## 1. Create the GitHub repository

Create a repository on GitHub.

Example:

`voice-bot`

For a GitHub Free account, GitHub Pages is available for public repositories.

## 2. Upload the website

Upload:

- `index.html`
- `.nojekyll`

to the repository.

The Python files do NOT run on GitHub Pages.

## 3. Turn on GitHub Pages

In your repository:

Settings
→ Pages
→ Build and deployment
→ Source: Deploy from a branch
→ Branch: `main`
→ Folder: `/ (root)`
→ Save

GitHub will publish the page from the repository.

## 4. Connect your Python brain

Open `index.html`.

Find:

```javascript
const BACKEND_URL = "PUT_YOUR_PYTHON_BACKEND_URL_HERE";
```

Change it to the public address of your Python server:

```javascript
const BACKEND_URL = "https://YOUR-PYTHON-SERVER/chat";
```

Do NOT use:

```text
http://127.0.0.1:8765/chat
```

for the public website. That points back to the visitor's own computer.

## 5. Your Python backend

Run the supplied backend on a Python-capable host.

It needs:

```text
POST /chat
GET  /health
```

The POST body is:

```json
{
  "message": "what is mathematics?"
}
```

and it should return:

```json
{
  "research": "> searching...\n> went to 'wikipedia.org'",
  "reply": "..."
}
```

The backend must send CORS headers allowing your GitHub Pages site to call it.

## 6. Local testing

For your Mac:

```bash
python3 backend.py
```

Then temporarily set:

```javascript
const BACKEND_URL = "http://127.0.0.1:8765/chat";
```

Open the HTML in a browser through a local web server if your browser blocks local fetches.

## Important

GitHub Pages is static hosting. GitHub's own documentation explicitly says GitHub Pages does not support server-side languages such as Python.

So the final architecture is:

```text
GitHub Pages
    ↓
index.html
    ↓
Python /chat endpoint
    ↓
voice.py
    ├── smart.py
    ├── language.py
    ├── memory
    └── web research
```
