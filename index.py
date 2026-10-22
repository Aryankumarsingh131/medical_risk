"""
index.py
--------
Root entrypoint for Vercel Serverless / FastAPI deployments.
Exports FastAPI `app` instance.
"""
try:
    from api.main import app
except Exception:
    from fastapi import FastAPI
    app = FastAPI(title="Medical Risk API", description="Vercel Entrypoint")

    @app.get("/")
    def read_root():
        return {"status": "ok", "service": "Medical Risk System"}

    @app.get("/health")
    def health():
        return {"status": "healthy"}
