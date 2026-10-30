"""
Main FastAPI Application Entrypoint.
Initializes lifespan lifecycle for persistent MATLAB Engine session and configures API routes.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.matlab_engine import MatlabSessionManager
from backend.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("smart_grid.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes the persistent MATLAB Engine on server boot and cleans up resources on shutdown.
    """
    logger.info("Initializing Smart Grid Simulation API server...")
    session_manager = await MatlabSessionManager.get_instance()
    logger.info("Persistent MATLAB Engine R2025a session verified and ready.")
    yield
    logger.info("Shutting down API server and closing MATLAB Engine session...")
    await session_manager.close()
    logger.info("Server shutdown complete.")


app = FastAPI(
    title="Smart Grid Stability Monitoring & Fault Diagnostic API",
    description=(
        "Authoritative simulation and analytics platform connecting modern web interfaces "
        "to a high-fidelity MATLAB/Simulink power systems model."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(router, prefix="/api")
from fault_ml.api_router import router as ml_router
app.include_router(ml_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": "Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform",
        "authoritative_engine": "MATLAB R2025a Update 1 / Simulink (main_model.slx)",
        "api_documentation": "/docs",
        "health_check": "/api/health",
        "simulation_endpoint": "/api/simulation/run",
    }


if __name__ == "__main__":
    import uvicorn
    from backend.config import API_HOST, API_PORT
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=False)
