"""FastAPI app entrypoint."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, get_db
from app.routers import auth, groups, expenses, settlements

Base.metadata.create_all(bind=engine)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(
    title="Expense Splitter API",
    description="Split expenses with friends and groups. Track who paid and who owes whom.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(settlements.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Expense Splitter API", "docs": "/docs"}
