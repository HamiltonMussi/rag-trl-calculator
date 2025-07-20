from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from api.routes import router as api_router
import logging
import pathlib
import sys

logger = logging.getLogger(__name__)

# Add scripts directory to path for glossary initialization
backend_root = pathlib.Path(__file__).parent
sys.path.insert(0, str(backend_root))

app = FastAPI(title="TRL-AI local API")

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup, including glossary data if needed."""
    logger.info("Starting TRL-AI system...")
    
    # Check and initialize glossary if needed
    try:
        from scripts.init_glossary import check_trl_collection, init_glossary
        
        if not check_trl_collection():
            logger.info("TRL collection not found or empty. Initializing glossary data...")
            success = init_glossary()
            if success:
                logger.info("Glossary initialization completed successfully on startup")
            else:
                logger.warning("Glossary initialization failed on startup - continuing without glossary data")
        else:
            logger.info("TRL collection already exists with data")
            
    except Exception as e:
        logger.error(f"Error during startup glossary check: {str(e)}", exc_info=True)
        logger.warning("Continuing startup without glossary initialization")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "errors": exc.errors(),
            "body": exc.body
        }
    )

app.include_router(api_router)
