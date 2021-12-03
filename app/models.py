from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging

app = Flask(__name__)
CORS(app)

app.debug = os.getenv("DEBUG")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s: %(message)s')

file_handler = logging.FileHandler('government.log')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class Citizen(db.Model):
    """
    A class to represent a citizen.
    Attributes:
        id (int): citizen ID
        name (str): name
        surname (str): surname
        birth_date (str): date of birth
        occupation (str): current occupation
        phone_number (str): phone number
        is_risk (bool): True if has risks medical conditions
        address (str): current home address
        vaccine_taken (list): list of vaccine taken
    """
    __tablename__ = 'citizen'
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Numeric, unique=True)
    name = db.Column(db.String(200))
    surname = db.Column(db.String(200))
    birth_date = db.Column(db.Date)
    occupation = db.Column(db.Text())
    phone_number = db.Column(db.String(200), unique=True)
    is_risk = db.Column(db.Boolean)
    address = db.Column(db.Text())
    vaccine_taken = db.Column(db.PickleType())

    def __init__(self, citizen_id, name, surname, birth_date, occupation,
                 phone_number, is_risk, address):
        self.citizen_id = citizen_id
        self.name = name
        self.surname = surname
        self.birth_date = birth_date
        self.occupation = occupation
        self.phone_number = phone_number
        self.is_risk = is_risk
        self.address = address
        self.vaccine_taken = []
        logger.info(
            'created Citizen: {} - {} {} - birth date: {} occupation: {} phone_number: {} is_risk: {} address: {} vaccine taken: {}'
            .format(self.citizen_id, self.name, self.surname, self.birth_date,
                    self.occupation, self.phone_number, self.is_risk,
                    self.address, self.vaccine_taken))

    def get_dict(self):
        return {
            "citizen_id": str(self.citizen_id),
            "name": str(self.name),
            "surname": str(self.surname),
            "birth_date": str(self.birth_date),
            "occupation": str(self.occupation),
            "phone_number": str(self.phone_number),
            "is_risk": str(self.is_risk),
            "address": str(self.address),
            "vaccine_taken": str(self.vaccine_taken)
        }


class Reservation(db.Model):
    """
    A class to represent a reservation data.
    Attributes:
        id (int): reservation ID
        citizen_id (int): citizen ID
        site_name (str): name of the place for vaccination
        vaccine_name (str): name of vaccine
        timestamp (date): Date and time of reservation
        queue (datetime): Date and time of vaccination
        checked (bool): Check whether you got the vaccine or not
    """
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Numeric)
    site_name = db.Column(db.String(200))
    vaccine_name = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime)
    queue = db.Column(db.DateTime, default=None)
    checked = db.Column(db.Boolean, default=False)

    def __init__(self, citizen_id, site_name, vaccine_name):
        self.citizen_id = citizen_id
        self.site_name = site_name
        self.vaccine_name = vaccine_name
        self.timestamp = datetime.now()
        logger.info(
            'created Reservation: {} - site name: {} vaccine name: {} time: {} queue: {} checked: {}'
            .format(self.citizen_id, self.site_name, self.vaccine_name,
                    self.timestamp, self.queue, self.checked))

    def get_dict(self):
        return {
            "citizen_id": str(self.citizen_id),
            "site_name": str(self.site_name),
            "vaccine_name": str(self.vaccine_name),
            "timestamp": str(self.timestamp),
            "queue": str(self.queue),
            "checked": str(self.checked)
        }


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean)
    has_privilege = db.Column(db.Boolean) # need to change variable name later

    # def __init__(self, username, password, is_admin=False, has_privilege=True):
    #     self.username = username
    #     hashed_password = generate_password_hash(password, method='sha256')
    #     self.password = hashed_password
    #     self.is_admin = is_admin
    #     self.has_privilege = has_privilege

    #     logger.info(
    #     'created authenticated user: {} - is-admin: {} - has-privilege: {}'
    #     .format(self.username, self.is_admin, self.has_privilege))