import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from hexr.encoder import render_hexr, MAX_CHARS
from hexr.decoder import decode_hexr

app = FastAPI(title="HexR")

FRONTEND = Path(__file__).parent.parent / "frontend"


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/encode")
async def encode(text: str = Form(...)):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Text is {len(text)} characters; the limit is {MAX_CHARS}.")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        render_hexr(text, output_path=tmp.name)
    except Exception as e:
        os.unlink(tmp.name)
        raise HTTPException(status_code=500, detail=str(e))
    # Delete the temp file only AFTER the response has been sent.
    return FileResponse(tmp.name, media_type="image/png",
                        headers={"Content-Disposition": "inline; filename=hexr.png"},
                        background=BackgroundTask(os.unlink, tmp.name))


@app.post("/decode")
async def decode(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix or ".png"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()
        text = decode_hexr(tmp.name)
        return JSONResponse({"text": text})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        os.unlink(tmp.name)


# ── Serve frontend (must come AFTER API routes) ───────────────────────────────

app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
