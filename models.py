from datetime import datetime
from typing import Dict, Any, Optional
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
                    "Volume": 76033200
                },
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }