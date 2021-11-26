import unittest
import requests
from datetime import datetime

URL = "https://wcg-apis-test.herokuapp.com/"


class RegistrationApiTest(unittest.TestCase):
    """Test government api"""

    def test_post_valid_registration(self):
        """Test post valid registration data"""
        endpoint = URL + "registration"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": "15 Aug 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        requests.delete(url=endpoint, data={"citizen_id": 8888888888888,
                                            "name": "John",
                                            "surname": "Doe",
                                            "birth_date": "15 Aug 2002",
                                            "occupation": "Student",
                                            "address": "Bangkok",
                                            "is_risk": False,
                                            "phone_number": "0888775991"})
        self.assertEqual(201, response.status_code)
        self.assertIn(b'registration success', response.content)

    def test_post_registration_with_missing_attribute(self):
        """Test post registration data with missing attribute"""
        endpoint = URL + "registration"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "",
                                                     "surname": "Doe",
                                                     "birth_date": "15 Aug 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        self.assertIn(b'missing some attribute', response.content)

    def test_post_invalid_id_registration(self):
        """Test post registration data with invalid id"""
        endpoint = URL + "registration"
        response = requests.post(url=endpoint, data={"citizen_id": 999,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": "15 Aug 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        self.assertIn(b'invalid citizen ID', response.content)

    def test_post_registration_already_registered(self):
        """Test post the same registration data more than once"""
        endpoint = URL + "registration"
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "name": "John",
                                          "surname": "Doe",
                                          "birth_date": "15 Aug 2002",
                                          "occupation": "Student",
                                          "address": "Bangkok",
                                          "is_risk": False,
                                          "phone_number": "0888775991"})
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": "15 Aug 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        requests.delete(url=endpoint, data={"citizen_id": 8888888888888,
                                            "name": "John",
                                            "surname": "Doe",
                                            "birth_date": "15 Aug 2002",
                                            "occupation": "Student",
                                            "address": "Bangkok",
                                            "is_risk": False,
                                            "phone_number": "0888775991"})
        self.assertIn(b'this person already registered', response.content)

    def test_post_registration_not_yet_achieve_minimum_age(self):
        """Test post registration data with age less than 12"""
        endpoint = URL + "registration"
        year = int(datetime.now().year)-3
        date = "15 Aug "+str(year)
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": date,
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        self.assertIn(b'not archived minimum age', response.content)

    def test_post_registration_invalid_birth_date_format(self):
        """Test post registration data with invalid birth_date format"""
        endpoint = URL + "registration"
        response = requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                                     "name": "John",
                                                     "surname": "Doe",
                                                     "birth_date": "15 8 2002",
                                                     "occupation": "Student",
                                                     "address": "Bangkok",
                                                     "is_risk": False,
                                                     "phone_number": "0888775991"})
        self.assertIn(b'invalid birth date format', response.content)

    def test_delete_registration(self):
        """Test deleting a registration"""
        endpoint = URL + "registration"
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "name": "John",
                                          "surname": "Doe",
                                          "birth_date": "15 Aug 2002",
                                          "occupation": "Student",
                                          "address": "Bangkok",
                                          "is_risk": False,
                                          "phone_number": "0888775991"})
        response = requests.delete(endpoint+"/8888888888888")
        self.assertEqual(200, response.status_code)

    def test_get_specific_citizen_detail(self):
        """Test get a detail for a specified citizen id"""
        endpoint = URL + "registration"
        requests.post(url=endpoint, data={"citizen_id": 8888888888888,
                                          "name": "John",
                                          "surname": "Doe",
                                          "birth_date": "15 Aug 2002",
                                          "occupation": "Student",
                                          "address": "Bangkok",
                                          "is_risk": False,
                                          "phone_number": "0888775991"})
        response = requests.get(endpoint+"/8888888888888")
        requests.delete(endpoint+"/8888888888888")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'John', response.content)
        self.assertIn(b'Doe', response.content)
        self.assertIn(b'0888775991', response.content)

    def test_get_registration_document(self):
        """Test get document for registration api"""
        endpoint = URL + "document"
        response = requests.get(endpoint+"/registration")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Return a registration (citizen) data as json', response.content)
        self.assertIn(b'To register citizen information', response.content)
        self.assertIn(b'Delete this citizen data and all of the reservations', response.content)

    def test_get_registration_database(self):
        """Test get registration database"""
        endpoint = URL + "database"
        response = requests.get(endpoint+"/citizen")
        self.assertEqual(200, response.status_code)
        self.assertIn(b'Citizen', response.content)
        self.assertIn(b'Current database has', response.content)

    def tearDown(self):
        """Delete registration and reservation from database"""
        endpoint = URL + "registration/8888888888888"
        requests.delete(url=endpoint)


if __name__ == '__main__':
    unittest.main()
