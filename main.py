from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from auth.auth import token_required
from config.settings import settings

# Create FastAPI app
app = FastAPI(title=settings.app_name, description="AUDIT Management API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def read_root():
    return {"message": "Welcome to Audit Management API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "OK"}


@app.get("/current")
async def current_employee(
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return current_user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.debug, workers=2)
