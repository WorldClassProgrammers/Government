import unittest
import requests
from datetime import datetime

URL = "https://wcg-apis-test.herokuapp.com/"


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

    def test_post_valid_queue_report(self):
        """Update queue with valid information"""
        endpoint = URL + "queue_report"
        year = int(datetime.now().year)+1
        date = str(year) + "-11-16 09:00:00.0"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "queue": date})
        self.assertIn(b'report success', response.content)

    def test_post_invalid_queue_report_datetime_format(self):
        """Update queue with invalid datetime format"""
        endpoint = URL + "queue_report"
        year = int(datetime.now().year)+1
        date = str(year) + "-11-16"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "queue": date})
        self.assertIn(b'invalid queue datetime format', response.content)

    def test_post_reserve_queue_report_in_the_past(self):
        """Update queue with datetime in the past"""
        endpoint = URL + "queue_report"
        year = int(datetime.now().year)-5
        date = str(year) + "-11-16 09:00:00.0"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888, "queue": date})
        self.assertIn(b'can only reserve vaccine in the future', response.content)

    def test_post_queue_report_with_no_reservation(self):
        """Update queue with no reservation"""
        endpoint = URL + "queue_report"
        year = int(datetime.now().year)+1
        date = str(year) + "-11-16 09:00:00.0"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888751, "queue": date})
        self.assertIn(b'couldn\'t find valid reservation', response.content)

    def test_get_queue_report_document(self):
        """Test get document for queue report api"""
        endpoint = URL + "document"
        response = requests.get(endpoint+"/queue_report")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'To report for a vaccine reservation', response.content)

    def tearDown(self):
        """Delete registration and reservation from database"""
        endpoint = URL + "registration/8888888888888"
        endpoint2 = URL + "reservation/8888888888888"
        requests.delete(url=endpoint)
        requests.delete(url=endpoint2)
