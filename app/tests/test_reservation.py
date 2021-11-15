import unittest
import requests
from datetime import datetime

URL = "https://wcg-apis.herokuapp.com/"


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

    def tearDown(self):
        """Delete a registration from database"""
        endpoint = URL + "registration/8888888888888"
        response = requests.delete(url=endpoint)


if __name__ == '__main__':
    unittest.main()
