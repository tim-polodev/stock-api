from dotenv import load_dotenv

load_dotenv()
from bson.objectid import ObjectId, InvalidId
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from pymongo.database import Database
import yfinance as yf
from auth import validate_token_middleware
from database import db_mongo
from models import StockListResponse, StockRecord
import os
import math
from typing import Optional, List

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


class WatchListUpdate(BaseModel):
    name: Optional[str] = None
    symbols: Optional[List[str]] = None


class WatchlistCreate(BaseModel):
    name: str
    symbols: List[str]


class Watchlist(WatchlistCreate):
    id: str
    name: str
    symbols: List[str]
    user_id: int


class WatchListResponse(BaseModel):
    data: List[Watchlist]


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
        return {"symbol": request.symbol, "status": "done"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stocks", response_model=StockListResponse)
async def get_stocks(
        symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
        page: int = Query(1, ge=1, description="Page number (starts from 1)"),
        page_size: int = Query(10, ge=1, le=5000, description="Items per page (max 100)"),
        sort_by: str = Query("date", description="Field to sort by (date, symbol, open, high, low, close, volume)"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)"),
        db: Database = Depends(get_database)
):
    """
    Get stocks data with pagination, filtering, and sorting.

    - **symbol**: Filter by stock symbol (optional)
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (1-100)
    - **sort_by**: Field to sort by (date, symbol, open, high, low, close, volume)
    - **sort_order**: Sort order (asc or desc)
    """
    try:
        # Build the filter query
        filter_query = {}
        if symbol:
            filter_query["symbol"] = symbol.upper()

        # Validate sort_by field
        valid_sort_fields = ["date", "symbol", "open", "high", "low", "close", "volume"]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"
            )

        # Validate sort_order
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_order. Must be 'asc' or 'desc'"
            )

        # Set sort direction (1 for ascending, -1 for descending)
        sort_direction = 1 if sort_order == "asc" else -1

        # Get total count for pagination
        total = db.stocks.count_documents(filter_query)

        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Calculate skip value for pagination
        skip = (page - 1) * page_size

        # Query the database with filters, sorting, and pagination
        cursor = db.stocks.find(
            filter_query,
            {"_id": 0}  # Exclude MongoDB _id field
        ).sort(
            sort_by, sort_direction
        ).skip(skip).limit(page_size)

        # Convert cursor to list
        stocks_data = list(cursor)

        # Convert to StockRecord models
        stocks = [StockRecord(**stock) for stock in stocks_data]

        return StockListResponse(
            data=stocks,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stocks: {str(e)}")


@app.post("/watchlist", response_model=Watchlist)
async def create_watchlist(
        watchlist: WatchlistCreate,
        request: Request,
        db: Database = Depends(get_database)
):
    user = getattr(request.state, "user", None)
    print("[Tim debug] user", user)
    if not user or "id" not in user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = user["id"]

    watchlist_doc = {
        "name": watchlist.name,
        "symbols": watchlist.symbols,
        "user_id": user_id,
    }

    if db.watchlists.find_one({"name": watchlist.name, "user_id": user_id}):
        raise HTTPException(status_code=400, detail="Watchlist with this name already exists")

    result = db.watchlists.insert_one(watchlist_doc)

    return Watchlist(
        id=str(result.inserted_id),
        name=watchlist.name,
        symbols=watchlist.symbols,
        user_id=user_id
    )


@app.patch("/watchlist/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
        watchlist_id: str,
        watchlist_data: WatchListUpdate,
        request: Request,
        db: Database = Depends(get_database)
):
    user = getattr(request.state, "user", None)
    if not user or "id" not in user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = user["id"]

    try:
        obj_id = ObjectId(watchlist_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid watchlist ID format")

    # Find the existing watchlist
    existing_watchlist = db.watchlists.find_one({"_id": obj_id, "user_id": user_id})
    if not existing_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found or you don't have permission to edit it")

    # Prepare the update document
    update_doc = {}
    if watchlist_data.name is not None:
        # Check if the new name is already in use by another watchlist of the same user
        if watchlist_data.name != existing_watchlist["name"] and db.watchlists.find_one(
                {"name": watchlist_data.name, "user_id": user_id}):
            raise HTTPException(status_code=409, detail="Watchlist with this name already exists")
        update_doc["name"] = watchlist_data.name

    if watchlist_data.symbols is not None:
        update_doc["symbols"] = watchlist_data.symbols

    # If there's nothing to update, return the existing watchlist
    if not update_doc:
        return Watchlist(
            id=str(existing_watchlist["_id"]),
            name=existing_watchlist["name"],
            symbols=existing_watchlist["symbols"],
            user_id=existing_watchlist["user_id"]
        )

    # Perform the update
    db.watchlists.update_one(
        {"_id": obj_id},
        {"$set": update_doc}
    )

    # Fetch the updated document to return it
    updated_watchlist = db.watchlists.find_one({"_id": obj_id})

    return Watchlist(**updated_watchlist, id=str(updated_watchlist["_id"]))


@app.get("/watchlist", response_model=List[Watchlist])
async def get_watchlists(
        request: Request,
        db: Database = Depends(get_database)
):
    user = getattr(request.state, "user", None)
    if not user or "id" not in user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = user["id"]

    watchlist_cursor = db.watchlists.find({"user_id": user_id})

    watchlists: WatchListResponse = []
    for w in watchlist_cursor:
        watchlists.append(Watchlist(
            id=str(w["_id"]),
            name=w["name"],
            symbols=w["symbols"],
            user_id=w["user_id"]
        ))
    return watchlists


# Add health check for MongoDB connection
@app.get("/health")
async def health_check(db: Database = Depends(get_database)):
    try:
        # Ping the database to check if connection is working
        db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
