import unittest
import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, init_db, add_sample_classes


class BookingApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        init_db()  # reset the DB
        add_sample_classes()

    def test_get_classes(self):
        response = self.app.get('/classes')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(len(data), 0)
        self.assertIn("available_slots", data[0])

    def test_book_class_success(self):
        response = self.app.post('/book', json={
            "class_id": 1,
            "client_name": "Test User",
            "client_email": "test@example.com"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Booking successful", response.get_data(as_text=True))

    def test_book_class_no_slots(self):
        # Book the same class until no slots left (initially 10)
        for _ in range(10):
            self.app.post('/book', json={
                "class_id": 1,
                "client_name": "User",
                "client_email": f"user{_}@example.com"
            })
        # Now try one more time
        response = self.app.post('/book', json={
            "class_id": 1,
            "client_name": "Extra User",
            "client_email": "extra@example.com"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("No slots available", response.get_data(as_text=True))

    def test_get_bookings_by_email(self):
        self.app.post('/book', json={
            "class_id": 2,
            "client_name": "Alice",
            "client_email": "alice@example.com"
        })
        response = self.app.get('/bookings?email=alice@example.com')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data[0]['class_name'], "Zumba")

    def test_invalid_booking_missing_fields(self):
        response = self.app.post('/book', json={
            "class_id": 1,
            "client_name": "No Email"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing fields", response.get_data(as_text=True))

    def test_get_bookings_missing_email_param(self):
        response = self.app.get('/bookings')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Email required", response.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
