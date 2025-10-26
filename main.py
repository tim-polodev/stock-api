from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from pymongo.database import Database
import yfinance as yf
from auth import validate_token_middleware
from database import db_mongo
import os

load_dotenv()

MONGO_DB_HOST = os.getenv("MONGO_DB_HOST")
MONGO_DB_PORT = os.getenv("MONGO_DB_PORT")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_DB_USER = os.getenv("MONGO_DB_USER")

MONGO_URI = f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_mongo.connect(MONGO_URI, MONGO_DB_NAME)
    yield
    db_mongo.close()


app = FastAPI(lifespan=lifespan)
app.middleware("http")(validate_token_middleware)


class StockSyncRequest(BaseModel):
    symbol: str
    period: str


def get_database():
    return db_mongo.db


@app.post("/stocks/sync")
async def sync_stock(request: StockSyncRequest, db: Database = Depends(get_database)):
    try:
        stock_data = yf.download(request.symbol, period=request.period)
        if stock_data.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")

        for index, row in stock_data.iterrows():
            document = {
                "symbol": request.symbol,
                "date": index.strftime('%Y-%m-%d'),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            }
            db.stocks.update_one(
                {"symbol": request.symbol, "date": document["date"]},
                {"$set": document},
                upsert=True
            )

        return {"symbol": request.symbol, "status": "syncing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add health check for MongoDB connection
@app.get("/health")
async def health_check(db: Database = Depends(get_database)):
    try:
        # Ping the database to check if connection is working
        db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
