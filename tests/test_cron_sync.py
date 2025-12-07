# tests/test_cron_sync.py

import unittest
from cron_sync import get_all_unique_symbols
from unittest.mock import patch, MagicMock


class TestGetAllUniqueSymbols(unittest.TestCase):

    @patch("cron_sync.MongoClient")
    def test_get_all_unique_symbols_success(self, mock_mongo_client):
        # Mock MongoDB client connection
        mock_db = MagicMock()
        mock_db.stocks.distinct.return_value = ["AAPL", "TSLA", "GOOGL"]
        mock_mongo_client.return_value.__getitem__.return_value = mock_db

        # Call the function and verify output
        result = get_all_unique_symbols()
        self.assertEqual(["AAPL", "TSLA", "GOOGL"], result)

    @patch("cron_sync.MongoClient")
    def test_get_all_unique_symbols_no_symbols(self, mock_mongo_client):
        # Test the case when no distinct symbols are found
        mock_db = MagicMock()
        mock_db.stocks.distinct.return_value = []
        mock_mongo_client.return_value.__getitem__.return_value = mock_db

        result = get_all_unique_symbols()
        self.assertEqual([], result)

    @patch("cron_sync.MongoClient")
    @patch("cron_sync.logging")
    def test_get_all_unique_symbols_connection_error(self, mock_logging, mock_mongo_client):
        # Mock MongoClient to raise an Exception
        mock_mongo_client.side_effect = Exception("Connection Error")

        result = get_all_unique_symbols()

        # Verify that the function returns an empty list and logs the error
        self.assertEqual([], result)
        mock_logging.error.assert_called_with("Error connecting to MongoDB or fetching symbols: Connection Error")
