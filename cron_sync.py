import os
import httpx
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load Environment Variables ---
# This ensures that the script can be run from any directory where .env is accessible
load_dotenv()

# --- Configuration ---
MONGO_DB_HOST = os.getenv("MONGO_DB_HOST")
MONGO_DB_PORT = os.getenv("MONGO_DB_PORT")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_DB_USER = os.getenv("MONGO_DB_USER")
CRON_AUTH_TOKEN = os.getenv("ADMIN_API_KEYS")  # A dedicated, long-lived token for this job
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

MONGO_URI = f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}"


def get_all_unique_symbols():
    """
    Connects to MongoDB and retrieves a unique set of all stock symbols
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB_NAME]
        results = db.stocks.distinct("symbol")
        return results

    except Exception as e:
        logging.error(f"Error connecting to MongoDB or fetching symbols: {e}")
        return []


def sync_stock_data(symbol: str, apikey: str):
    """
    Calls the /stocks/sync endpoint for a given symbol.
    """
    sync_url = f"{API_BASE_URL}/stocks/sync"
    headers = {
        "x-api-key": f"{apikey}",
        "Content-Type": "application/json"
    }
    # Fetching '5d' is safer for a daily job to catch up on weekends or market holidays
    payload = {"symbol": symbol, "period": "5d"}

    try:
        with httpx.Client() as client:
            response = client.post(sync_url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            logging.info(f"Successfully synced data for {symbol}. Status: {response.json().get('status')}")
    except httpx.HTTPStatusError as e:
        logging.error(f"Error syncing {symbol}: HTTP {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        logging.error(f"Error syncing {symbol}: Request failed - {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while syncing {symbol}: {e}")


def main():
    """
    Main function to run the entire sync process.
    """
    logging.info("Starting daily stock data sync...")

    if not CRON_AUTH_TOKEN:
        logging.error("CRON_AUTH_TOKEN environment variable not set. Aborting sync.")
        return

    symbols_to_sync = get_all_unique_symbols()

    if not symbols_to_sync:
        logging.info("No symbols found in any watchlist. Nothing to sync.")
        return

    logging.info(f"Found {len(symbols_to_sync)} unique symbols to sync: {', '.join(symbols_to_sync)}")

    for symbol in symbols_to_sync:
        sync_stock_data(symbol, CRON_AUTH_TOKEN)

    logging.info("Daily stock data sync finished.")


if __name__ == "__main__":
    main()
