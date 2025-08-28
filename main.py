from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth_routes import router as auth_router
from database import connect_db, disconnect_db, create_tables
from config import FRONTEND_ORIGINS
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="Authentication API",
    description="API for user registration and login with OTP verification",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # <-- phải là list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routers
app.include_router(auth_router)

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """Connect to database on startup"""
    await connect_db()
    # Optionally create tables (better to use migrations in production)
    # create_tables()

@app.on_event("shutdown")
async def shutdown():
    """Disconnect from database on shutdown"""
    await disconnect_db()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Authentication API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
