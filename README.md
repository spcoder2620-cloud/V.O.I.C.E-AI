# V.O.I.C.E. fixed deployment

This package contains the corrected Python brain and backend.

Put these files in your Render repository:

- `backend.py`
- `voice.py`
- `smart.py`
- `language.py`
- `requirements.txt`
- `render.yaml`

Your GitHub Pages `index.html` should POST to:

`https://v-o-i-c-e-ai.onrender.com/chat`

## What was fixed

1. Explicit questions such as `what is mathematics` always enter research.
2. Webpage block boundaries are preserved, so an entire page is not treated
   as one giant sentence.
3. DuckDuckGo result snippets can be used as cleaner evidence.
4. Navigation, citation and metadata junk is filtered more aggressively.
5. Definition questions strongly prefer explicit definitions.
6. Research learns up to 25 useful findings per topic.
7. The final language layer receives a compact answer plan rather than raw
   webpage text.
8. `/health` reports the backend version as `research-v2`.

## Deploy

Push these files to GitHub.

In Render, either create/update the web service from the repository or use
the included `render.yaml`.

Build:
    pip install -r requirements.txt

Start:
    python backend.py

Then verify:

    https://v-o-i-c-e-ai.onrender.com/health

The response should contain:

    "brain": "online"
    "version": "research-v2"

## Connect GitHub Pages

Your frontend should use:

```javascript
const BACKEND_URL =
    "https://v-o-i-c-e-ai.onrender.com/chat";
```

Then push the frontend to GitHub Pages.
