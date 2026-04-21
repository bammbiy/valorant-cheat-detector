from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.api.routes import router
from backend.core.config import get_settings

cfg = get_settings()

app = FastAPI(
    title="ValoScan",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)

# serve frontend
FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND, "static")), name="static")

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
