import unittest
import requests
from datetime import datetime

URL = "https://wcg-apis.herokuapp.com/"


class QueueReportApiTest(unittest.TestCase):
    """Test government api"""

    def setUp(self):
        """Register and reserve a person"""
        endpoint = URL + "registration"
        endpoint2 = URL + "reservation"
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "name": "John",
                                          "surname": "Doe",
                                          "birth_date": "15 Aug 2002",
                                          "occupation": "Student",
                                          "address": "Bangkok",
                                          "is_risk": False,
                                          "phone_number": "0888775991"})
        date = str(datetime.now())
        requests.post(url=endpoint2, data={"citizen_id": 8888888888888,
                                           "site_name": "Hospital 1",
                                           "vaccine_name": "Pfizer",
                                           "timestamp": date,
                                           "queue": None,
                                           "checked": False})

    def test_post_valid_report_taken(self):
        """Update vaccination info with correct information"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "vaccine_name": "Pfizer"})
        self.assertIn(b'report success', response.content)

    def test_post_report_taken_with_missing_attribute(self):
        """Update vaccination info with missing attribute"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "vaccine_name": ""})
        self.assertIn(b'missing some attribute', response.content)

    def test_post_report_taken_with_incorrect_vaccine(self):
        """Update vaccination info with wrong vaccine"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "vaccine_name": "Astra"})
        self.assertIn(b'vaccine_name not match reservation', response.content)

    def test_post_report_taken_with_invalid_vaccine(self):
        """Update vaccination info with wrong vaccine"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "vaccine_name": "Astro"})
        self.assertIn(b'invalid vaccine name', response.content)

    def test_post_valid_report_taken_walk_in_as_option(self):
        """Update vaccination info with option walk-in"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "vaccine_name": "Pfizer", "option":"walk-in"})
        self.assertIn(b'citizen need to cancel other reservation', response.content)

    def test_post_report_taken_with_invalid_citizen_id(self):
        """Update vaccination info with invalid citizen id"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8899, "vaccine_name": "Pfizer"})
        self.assertIn(b'invalid citizen ID', response.content)

    def test_post_report_taken_with_citizen_id_not_yet_registered(self):
        """Update vaccination info with citizen id that is not yet registered"""
        endpoint = URL + "report_taken"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888799, "vaccine_name": "Pfizer"})
        self.assertIn(b'citizen ID is not registered', response.content)

    def tearDown(self):
        """Delete registration and reservation from database"""
        endpoint = URL + "registration/8888888888888"
        endpoint2 = URL + "reservation/8888888888888"
        requests.delete(url=endpoint)
        requests.delete(url=endpoint2)
