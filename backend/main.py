from fastapi import FastAPI, APIRouter
from ingest import docling



app = FastAPI()

app.include_router(
    docling.router,
    prefix="/api/v1",
    tags=["users"],
    responses={418: {"description": "I'm a teapot"}}, # Optional: Add specific responses
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)