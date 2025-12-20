from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StockData(BaseModel):
    stock_code: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "stock_code": "AAPL",
                "data": {
                    "Open": 150.17,
                    "High": 152.83,
                    "Low": 149.37,
                    "Close": 152.57,
                    "Volume": 76033200,
                },
                "timestamp": "2023-01-01T00:00:00.000Z",
            }
        }


class StockRecord(BaseModel):
    """Model for stock record from database"""

    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "date": "2024-01-15",
                "open": 150.17,
                "high": 152.83,
                "low": 149.37,
                "close": 152.57,
                "volume": 76033200,
            }
        }


class StockHistoryRecord(BaseModel):
    open: List[float]
    close: List[float]
    high: List[float]
    low: List[float]
    volume: List[float]
    date: List[str]
    symbol: str


class StockListResponse(BaseModel):
    """Response model for paginated stock list"""

    data: StockHistoryRecord
    total: int
    page: int
    page_size: int
    total_pages: int

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "data": [
    #                 {
    #                     "symbol": "AAPL",
    #                     "date": "2024-01-15",
    #                     "open": 150.17,
    #                     "high": 152.83,
    #                     "low": 149.37,
    #                     "close": 152.57,
    #                     "volume": 76033200,
    #                 }
    #             ],
    #             "total": 100,
    #             "page": 1,
    #             "page_size": 10,
    #             "total_pages": 10,
    #         }
    #     }
