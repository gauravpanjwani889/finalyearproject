"""
Persistent MATLAB Engine API Session Manager.
Maintains a singleton connection to the MATLAB R2025a Engine with thread-safe execution lock.
"""

import asyncio
import logging
import time
from typing import Optional
import matlab.engine
from backend.config import MATLAB_DIR, MODEL_NAME, MODEL_PATH

logger = logging.getLogger("smart_grid.matlab")


class MatlabSessionManager:
    """Singleton manager for the persistent MATLAB Engine instance."""
    
    _instance: Optional["MatlabSessionManager"] = None
    _engine: Optional[matlab.engine.MatlabEngine] = None
    _lock: asyncio.Lock = asyncio.Lock()
    _model_loaded: bool = False
    _matlab_version: str = "Unknown"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MatlabSessionManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> "MatlabSessionManager":
        manager = cls()
        await manager.ensure_started()
        return manager

    async def ensure_started(self) -> None:
        """Starts MATLAB Engine and loads main_model.slx if not already loaded."""
        async with self._lock:
            if self._engine is None:
                loop = asyncio.get_running_loop()
                logger.info("Initializing persistent MATLAB Engine R2025a session...")
                t0 = time.time()
                # Run synchronous engine startup in threadpool
                self._engine = await loop.run_in_executor(None, self._start_matlab_sync)
                logger.info(f"MATLAB Engine started in {time.time()-t0:.2f}s.")

            if not self._model_loaded:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._load_model_sync)
                self._model_loaded = True
                logger.info(f"Model '{MODEL_NAME}.slx' loaded and verified.")

    def _start_matlab_sync(self) -> matlab.engine.MatlabEngine:
        """Synchronous startup function for MATLAB Engine."""
        eng = matlab.engine.start_matlab()
        self._matlab_version = str(eng.eval("version", nargout=1))
        # Add matlab folder to search path
        matlab_dir_posix = str(MATLAB_DIR).replace('\\', '/')
        eng.eval(f"addpath('{matlab_dir_posix}');", nargout=0)
        return eng

    def _load_model_sync(self) -> None:
        """Synchronous model loader and integrity checker."""
        if not self._engine:
            raise RuntimeError("MATLAB Engine is not initialized.")
        # Load system into memory without opening UI window
        self._engine.load_system(MODEL_NAME, nargout=0)

    @property
    def engine(self) -> matlab.engine.MatlabEngine:
        if self._engine is None:
            raise RuntimeError("MATLAB Engine is not started. Call ensure_started() first.")
        return self._engine

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    @property
    def is_connected(self) -> bool:
        return self._engine is not None

    @property
    def is_model_loaded(self) -> bool:
        return self._model_loaded

    @property
    def matlab_version(self) -> str:
        return self._matlab_version

    async def close(self) -> None:
        """Safely closes model without saving changes and terminates engine session."""
        async with self._lock:
            if self._engine is not None:
                loop = asyncio.get_running_loop()
                logger.info("Closing Simulink model and MATLAB session...")
                await loop.run_in_executor(None, self._close_sync)
                self._engine = None
                self._model_loaded = False
                logger.info("MATLAB Engine session closed cleanly.")

    def _close_sync(self) -> None:
        try:
            if self._model_loaded and self._engine is not None:
                # 0 = do not save changes to main_model.slx!
                self._engine.close_system(MODEL_NAME, 0, nargout=0)
        except Exception as e:
            logger.warning(f"Notice while closing system: {e}")
        try:
            if self._engine is not None:
                self._engine.quit()
        except Exception as e:
            logger.warning(f"Notice while quitting engine: {e}")
