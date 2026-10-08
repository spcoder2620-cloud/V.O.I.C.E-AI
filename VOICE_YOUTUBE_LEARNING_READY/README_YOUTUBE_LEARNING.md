# V.O.I.C.E. YouTube learning

Use:

    watch https://youtube.com/watch?v=VIDEO_ID

or:

    learn youtube https://youtu.be/VIDEO_ID

The command tries to read an available YouTube caption track and stores
many transcript observations in `voice_memory.json`.

It is transparent about the limitation: it reads captions/transcript text;
it does not claim to visually watch or understand parts of a video that
are not represented in the transcript.

## Deploy

Replace the current `voice.py` on the GitHub repository used by Render:

    git add voice.py
    git commit -m "Add YouTube learning command"
    git push

Wait for Render to redeploy, then test the endpoint/site again.

## Expected terminal output

    @you:~ % watch https://youtube.com/watch?v=XXXXXXXXXXX

    > opening YouTube video...
    > locating available captions...
    > reading transcript...
    > transcript acquired.
    > learned 37 transcript findings.
    > saved source: <video title>

    V.O.I.C.E.:

    "I have studied the available captions and stored what was said,
    So when you ask about this source, those findings can be weighed."
