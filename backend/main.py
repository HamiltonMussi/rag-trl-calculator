from fastapi import FastAPI
from api.routes import router as api_router

app = FastAPI(title="TRL-AI local API")
app.include_router(api_router)
