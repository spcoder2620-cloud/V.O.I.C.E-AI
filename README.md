# V.O.I.C.E. backend

This folder is ready for a Python web service host such as Render.

## Local Mac test

```bash
cd voice-bot
python3 backend.py
```

Then, in another Terminal:

```bash
curl http://127.0.0.1:8765/health
```

Test chat:

```bash
curl -X POST http://127.0.0.1:8765/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message":"what is mathematics?"}'
```

## Render

Connect this folder/repository to a Render Web Service. The included
`render.yaml` starts `backend.py`. Render supplies the `PORT` environment
variable automatically.

After deployment, use:

```text
https://YOUR-SERVICE.onrender.com/chat
```

as `BACKEND_URL` in your GitHub Pages `index.html`.

## Important

The supplied brain is standard-library-only and performs its own web
research. No AI API key is used by these files.

The JSON memory file is local process storage. On a free ephemeral server,
that file should not be treated as permanent storage across restarts.
