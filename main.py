from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from base64_routes import router as base64_router
import uvicorn

app = FastAPI(title="Base64 File Converter", version="1.0.0")

# API routes
app.include_router(base64_router, prefix="/api", tags=["base64"])

# Serve the current folder (so / returns base64.html)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def index():
    return FileResponse("base64.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
