from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="AIG API", version="1.0.0")

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
