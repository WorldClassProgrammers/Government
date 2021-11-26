import unittest
import requests
from datetime import datetime

URL = "https://wcg-apis-test.herokuapp.com/"


class ReservationApiTest(unittest.TestCase):
    """Test government api"""

    def setUp(self):
        """Register a person"""
        endpoint = URL + "registration"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": "15 Aug 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})

    def test_post_valid_reservation(self):
        """Test post valid reservation data."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "site_name": "Hospital 1",
                                                     "vaccine_name": "Pfizer",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        requests.delete(url=endpoint, data={"citizen_id": 8888888888888,
                                            "site_name": "Hospital 1",
                                            "vaccine_name": "Pfizer",
                                            "timestamp": date,
                                            "queue": None,
                                            "checked": False})
        self.assertIn(b'reservation success!', response.content)

    def test_cancel_reservation(self):
        """Test cancel reservation."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "site_name": "Hospital 1",
                                          "vaccine_name": "Pfizer",
                                          "timestamp": date,
                                          "queue": None,
                                          "checked": False})
        response = requests.delete(url=endpoint+"/8888888888888")
        self.assertIn(b'cancel reservation success', response.content)

    def test_post_invalid_id_reservation(self):
        """Test post reservation data with invalid citizen id."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        response = requests.post(url=endpoint, data={"citizen_id": 999,
                                                     "site_name": "Hospital 1",
                                                     "vaccine_name": "Pfizer",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        self.assertIn(b'invalid citizen ID', response.content)

    def test_post_reservation_with_missing_attribute(self):
        """Test post reservation data with missing attribute."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "site_name": "",
                                                     "vaccine_name": "Pfizer",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        self.assertIn(b'missing some attribute', response.content)

    def test_post_reservation_already_reserved(self):
        """Test post valid reservation data more than once."""
        endpoint = URL + "reservation"
        delete_endpoint = URL + "reservation/8888888888888"
        date = str(datetime.now())
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "site_name": "Hospital 1",
                                          "vaccine_name": "Pfizer",
                                          "timestamp": date,
                                          "queue": None,
                                          "checked": False})
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "site_name": "Hospital 1",
                                                     "vaccine_name": "Pfizer",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        requests.delete(url=delete_endpoint)
        self.assertIn(b'there is already a reservation for this citizen', response.content)

    def test_post_reservation_with_invalid_vaccine_name(self):
        """Test post reservation data with invalid vaccine name."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "site_name": "Hospital 1",
                                                     "vaccine_name": "test",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        self.assertIn(b'invalid vaccine name', response.content)

    def test_post_reservation_with_non_registered_id(self):
        """Test post reservation data with id that is not registered."""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        citizen_id = 5794653124586
        database = requests.get(URL+"citizen")
        while True:
            if str(citizen_id) not in database.text:
                break
            citizen_id += 1
        response = requests.post(url=endpoint, data={"citizen_id": citizen_id,
                                                     "site_name": "Hospital 1",
                                                     "vaccine_name": "test",
                                                     "timestamp": date,
                                                     "queue": None,
                                                     "checked": False})
        self.assertIn(b'citizen ID is not registered', response.content)

    def test_get_specific_reservation(self):
        """Test get specified reservation by citizen id"""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "site_name": "Hospital 1",
                                          "vaccine_name": "Pfizer",
                                          "timestamp": date,
                                          "queue": None,
                                          "checked": False})
        response = requests.get(endpoint+"/8888888888888")
        requests.delete(endpoint+"/8888888888888")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Hospital 1', response.content)
        self.assertIn(b'Pfizer', response.content)
        self.assertIn(b'8888888888888', response.content)

    def test_all_reservation(self):
        """Test get all reservation"""
        endpoint = URL + "reservation"
        date = str(datetime.now())
        requests.post(url=URL+"registration", data={"citizen_id": 8888888888889,
                                                    "name": "Jimmy",
                                                    "surname": "Doe",
                                                    "birth_date": "16 Aug 2002",
                                                    "occupation": "Student",
                                                    "address": "Bangkok",
                                                    "is_risk": False,
                                                    "phone_number": "0888775991"})
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "site_name": "Hospital 1",
                                          "vaccine_name": "Pfizer",
                                          "timestamp": date,
                                          "queue": None,
                                          "checked": False})
        requests.post(url=endpoint, data={"citizen_id": 8888888888889,
                                          "site_name": "Hospital 2",
                                          "vaccine_name": "Astra",
                                          "timestamp": date,
                                          "queue": None,
                                          "checked": False})
        response = requests.get(endpoint+"s")
        requests.delete(endpoint+"/8888888888888")
        requests.delete(endpoint+"/8888888888889")
        requests.delete(URL+"registration/8888888888889")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Hospital 1', response.content)
        self.assertIn(b'Pfizer', response.content)
        self.assertIn(b'8888888888888', response.content)
        self.assertIn(b'Hospital 2', response.content)
        self.assertIn(b'Astra', response.content)
        self.assertIn(b'8888888888889', response.content)

    def test_get_reservation_document(self):
        """Test get document for reservation api"""
        endpoint = URL + "document"
        response = requests.get(endpoint+"/reservation")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Return a reservation (citizen) data', response.content)
        self.assertIn(b'Return all reservations data with it owner', response.content)
        self.assertIn(b'To reserve vaccine reservation', response.content)
        self.assertIn(b'To cancel the citizen unchecked vaccine reservation', response.content)

    def test_get_reservation_database(self):
        """Test get reservation database"""
        endpoint = URL + "database"
        response = requests.get(endpoint+"/reservation")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Reservation', response.content)
        self.assertIn(b'Current database has', response.content)

    def tearDown(self):
        """Delete a registration from database"""
        endpoint = URL + "registration/8888888888888"
        response = requests.delete(url=endpoint)


if __name__ == '__main__':
    unittest.main()
