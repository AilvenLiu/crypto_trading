import unittest
from data_processing.data_fetcher import DataFetcher
import os

class TestDataFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = DataFetcher(config_path='config/config_simulation.yaml')
        # Use a test database
        self.test_db = 'test_data.db'
        self.fetcher.db_path = self.test_db
        self.fetcher.initialize_db()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_initialize_db(self):
        self.assertTrue(os.path.exists(self.test_db))

    def test_insert_kline(self):
        self.fetcher.cursor.execute('''
            INSERT INTO kline (timestamp, open, high, low, close, volume)
            VALUES ('2023-10-01 12:00:00', 50000, 50500, 49500, 50200, 10)
        ''')
        self.fetcher.conn.commit()
        self.fetcher.cursor.execute("SELECT * FROM kline WHERE timestamp='2023-10-01 12:00:00'")
        row = self.fetcher.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], 50000)

if __name__ == '__main__':
    unittest.main()