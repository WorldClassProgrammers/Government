from codecs import encode
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from string import Template
from datetime import datetime
from flasgger import Swagger
from flasgger.utils import swag_from
import os
import logging
import json

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

app.config["SWAGGER"] = {"title": "WCG-API", "universion": 1}

swagger_config = {
    "headers": [],
    "specs": [{
        "title": "WCG-api",
        "description":
        "This is api documentation for World Class Government's government module",
        "version": "1.0.0",
        "externalDocs": {
            "description": "See our github",
            "url": "https://github.com/WorldClassProgrammers/Government-APIs",
        },
        "servers": {
            "url": "https://wcg-apis.herokuapp.com"
        },
        "endpoint": "api-doc",
        "route": "/api",
        "rule_filter": lambda rule: True,
        "model_filter": lambda tag: True,
    }],
    "static_url_path":
    "/flasgger_static",
    "swagger_ui":
    True,
    "specs_route":
    "/api-doc/",
}

swagger = Swagger(app, config=swagger_config)

VACCINE_PATTERN = [
    ["Pfizer", "Pfizer"],
    ["Astra", "Astra"],
    ["Sinopharm", "Sinopharm"],
    ["Sinovac", "Sinovac"],
    ["Sinovac", "Astra"],
    ["Astra", "Pfizer"],
    ["Pfizer", "Astra"],
    ["Sinovac", "Pfizer"],
    ["Sinopharm", "Pfizer"],
    ["Sinovac", "Sinovac", "Astra"],
    ["Sinovac", "Sinovac", "Pfizer"],
    ["Sinovac", "Sinopharm", "Astra"],
    ["Sinovac", "Sinopharm", "Pfizer"],
    ["Astra", "Astra", "Pfizer"],
]

REGISTRATION_FEEDBACK = {
    'success':              'registration success!',
    'missing_key':          'registration failed: missing some attribute',
    'registered':           'registration failed: this person already registered',
    'invalid_id':           'registration failed: invalid citizen ID',
    'invalid_birthdate':    'registration failed: invalid birth date format',
    'invalid_age':          'registration failed: not archived minimum age',
    'other':                'registration failed: something go wrong, please contact admin'
}

RESERVATION_FEEDBACK = {
    'success':              'reservation success!',
    'missing_key':          'reservation failed: missing some attribute',
    'invalid_id':           'reservation failed: invalid citizen ID',
    'not_registered':       'reservation failed: citizen ID is not registered',
    'double_reservation':   'reservation failed: there is already a reservation for this citizen',
    'invalid_vaccine':      'reservation failed: invalid vaccine name',
    'other':                'reservation failed: something went wrong, please contact the admin'
}

CANCEL_RESERVATION_FEEDBACK = {
    'success':              'cancel reservation success!',
    'missing_key':          'cancel reservation failed: no citizen id is given',
    'invalid_id':           'cancel reservation failed: invalid citizen ID',
    'not_registered':       'cancel reservation failed: citizen ID is not registered',
    'not_reservation':      'cancel reservation failed: there is no reservation for this citizen',
    'invalid_reservation':  'cancel reservation failed: couldn\'t find valid reservation'
}

REPORT_FEEDBACK = {
    'success':              'report success!',
    'missing_key':          'report failed: missing some attribute',
    'invalid_id':           'report failed: invalid citizen ID',
    'not_registered':       'report failed: citizen ID is not registered',
    'invalid_time':         'report failed: can only reserve vaccine in the future',
    'invalid_time_format':  'report failed: invalid queue datetime format',
    'invalid_reservation':  'report failed: couldn\'t find valid reservation',
    'invalid_vaccine':      'report failed: invalid vaccine name',
    'has_reservation':      'report failed: before walk-in, citizen need to cancel other reservation',
    'not_reservation':      'report failed: there is no reservation for this citizen',
    'not_match_vaccine':    'report failed: vaccine_name not match reservation',
    'other':                'report failed: something go wrong, please contact admin'
}

DELETE_FEEDBACK = {
    'success_reset':        'all citizens have been deleted',
    'fail_reset':           'failed to reset citizen database',
    'fail_delete':          'failed to delete citizen',
    'invalid_id':           'delete failed: invalid citizen ID',
    'not_registered':       'delete failed: citizen ID is not registered'
}


def get_available_vaccine(vaccine_taken: list):
    """Return sorted list of available vaccine calculate from the vaccine that citizen have taken

    Args:
        vaccine_taken (list): the vaccine that citizen have taken

    Returns:
        list: list of available vaccine
    """
    available_vaccine = set()
    for pattern in VACCINE_PATTERN:
        length = len(vaccine_taken)
        if length < len(pattern) and pattern[:length] == vaccine_taken:
            available_vaccine.add(pattern[length])

    return sorted(list(available_vaccine))


def parsing_date(birth_date: str):
    """
    Reparse birthdate into datetime format.
    Args:
        birth_date (str): birthdate of citizen
    Raises:
        ValueError: invalid date format
    Returns:
        struct_time: Birthdate in datetime format.
    """
    for fmt in ('%d %b %Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(birth_date, fmt)
        except ValueError:
            pass
    raise ValueError('invalid date format')


def delta_year(birth_date: datetime):
    """
    Find the age from birthdate.
    Args:
        birth_date (datetime): birthdate in datetime format
    Returns:
        int: Age from current year minus birth year.
    """
    return datetime.now().year - birth_date.year


def is_citizen_id(citizen_id):
    """Return True if citizen_id is a string 10 digits

    Args:
        citizen_id (string): id of a citizen

    Returns:
        bool: True if valid citizen_id, False otherwise
    """
    return citizen_id.isdigit() and len(citizen_id) == 13


def is_registered(citizen_id):
    """Return True if citizen_id is registered in database

    Args:
        citizen_id (string): id of a citizen

    Returns:
        bool: True if citizen_id is registered, False otherwise
    """
    return db.session.query(Citizen).filter(
        Citizen.citizen_id == citizen_id).count() == 1


def is_reserved(citizen_id):
    """Return True if citizen_id is reserved in database

    Args:
        citizen_id (string): id of a citizen

    Returns:
        bool: True if citizen_id is reserved, False otherwise
    """
    return db.session.query(Reservation).filter(
        Reservation.citizen_id == citizen_id).filter(
            Reservation.checked == False).count() > 0


def get_unchecked_reservations(citizen_id):
    """Return query of unchecked reservations of citizen

    Args:
        citizen_id (string): id of a citizen

    Returns:
        query: citizen's unchecked reservations
    """
    return db.session.query(Reservation).filter(
        Reservation.citizen_id == citizen_id).filter(
            Reservation.checked == False)


def get_citizen(citizen_id):
    """Return citizen of the citizen_id

    Args:
        citizen_id (string): id of a citizen

    Returns:
        Citizen: citizen of the citizen_id
    """
    return db.session.query(Citizen).filter(
        Citizen.citizen_id == citizen_id).first()


def validate_vaccine(citizen, vaccine_name, json_data):
    vaccines = get_available_vaccine(citizen.vaccine_taken)
    print("Going to check vaccine")
    if not vaccine_name in vaccines:
        if len(vaccines) == 0:
            feedback = f"reservation failed: you finished all vaccinations"
        elif len(vaccines) == 1:
            feedback = f"reservation failed: your next vaccine can be {vaccines} only"
        else:
            feedback = f"reservation failed: your available vaccines are only {vaccines}"

        if json_data == None:
            return False, {"feedback": feedback}
        json_data["feedback"] = feedback
        return False, json.dumps(json_data, ensure_ascii=False)

    return True, {}


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
    phone_number = db.Column(db.String(200))
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


@app.route('/registration/<citizen_id>', methods=['GET'])
@cross_origin()
@swag_from("swagger/singleID.yml")
def citizen_get_by_citizen_id(citizen_id):
    if not is_citizen_id(citizen_id):
        logger.error(REPORT_FEEDBACK["invalid_id"])
        return redirect(url_for('citizen'), 404)

    if not is_registered(citizen_id):
        logger.error(REPORT_FEEDBACK["not_registered"])
        return redirect(url_for('citizen'), 404)

    person = get_citizen(citizen_id)
    personal_data = person.get_dict()
    logger.info("{} - get citizen data".format(citizen_id))
    return json.dumps(personal_data, ensure_ascii=False)


@app.route('/registration', methods=['POST'])
@cross_origin()
@swag_from("swagger/regispost.yml")
def registration():
    """
    Accept and validate registration information.
    """
    citizen_id = request.values['citizen_id']
    name = request.values['name']
    surname = request.values['surname']
    birth_date = request.values['birth_date']
    occupation = request.values['occupation']
    phone_number = request.values['phone_number']
    is_risk = request.values['is_risk']
    address = request.values['address']

    if not (citizen_id and name and surname and birth_date and occupation
            and phone_number and is_risk and address):
        logger.error(REGISTRATION_FEEDBACK["missing_key"])
        return {"feedback": REGISTRATION_FEEDBACK["missing_key"]}

    if not is_citizen_id(citizen_id):
        logger.error(REGISTRATION_FEEDBACK["invalid_id"])
        return {"feedback": REGISTRATION_FEEDBACK["invalid_id"]}

    if is_registered(citizen_id):
        logger.error(REGISTRATION_FEEDBACK["registered"])
        return {"feedback": REGISTRATION_FEEDBACK["registered"]}

    try:
        birth_date = parsing_date(birth_date)
        if delta_year(birth_date) <= 12:
            logger.error(REGISTRATION_FEEDBACK["invalid_age"])
            return {"feedback": REGISTRATION_FEEDBACK["invalid_age"]}
    except ValueError:
        logger.error(REGISTRATION_FEEDBACK["invalid_birthdate"])
        return {"feedback": REGISTRATION_FEEDBACK["invalid_birthdate"]}

    # TODO: check phone_number

    try:
        data = Citizen(int(citizen_id), name, surname, birth_date, occupation,
                       phone_number, (is_risk == "True"), address)
        db.session.add(data)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(REGISTRATION_FEEDBACK["other"])
        return {"feedback": REGISTRATION_FEEDBACK["other"]}

    registration_data = data.get_dict()
    registration_data["feedback"] = REGISTRATION_FEEDBACK["success"]
    return jsonify(registration_data), 201, {
        'Location':
        url_for('citizen_get_by_citizen_id',
                citizen_id=data.citizen_id,
                _external=True)
    }


@app.route('/registration', methods=['DELETE'])
@cross_origin()
@swag_from("swagger/citizendel.yml")
def reset_citizen_db():
    """
    Reset citizen database.
    """
    try:
        db.session.query(Citizen).delete()
        db.session.query(Reservation).delete()
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(DELETE_FEEDBACK["fail_reset"])

    logger.info(DELETE_FEEDBACK["success_reset"])
    return redirect(url_for('citizen'))


@app.route('/registration/<citizen_id>', methods=['DELETE'])
@cross_origin()
@swag_from("swagger/citizendel.yml")
def delete_citizen_db(citizen_id):
    """
    Delete a citizen data.
    """
    if not is_citizen_id(citizen_id):
        logger.error(DELETE_FEEDBACK["invalid_id"])
        return redirect(url_for('citizen'), 404)

    if not is_registered(citizen_id):
        logger.error(DELETE_FEEDBACK["not_registered"])
        return redirect(url_for('citizen'), 404)

    try:
        person = get_citizen(citizen_id)
        db.session.delete(person)
        db.session.query(Reservation).filter(
            Reservation.citizen_id == citizen_id).delete()
        db.session.commit()
        logger.info("{} - citizen has been deleted".format(citizen_id))
    except:
        db.session.rollback()
        logger.error(DELETE_FEEDBACK["fail_delete"])

    return redirect(url_for('citizen'))


@app.route('/reservation/<citizen_id>', methods=['GET'])
@cross_origin()
def reservation_get_by_citizen_id(citizen_id):
    if not is_citizen_id(citizen_id):
        logger.error(REPORT_FEEDBACK["invalid_id"])
        return redirect(url_for('citizen'), 404)

    if not is_registered(citizen_id):
        logger.error(REPORT_FEEDBACK["not_registered"])
        return redirect(url_for('citizen'), 404)

    reservations = []
    for reservation in db.session.query(Reservation).filter(
            Reservation.citizen_id == citizen_id):
        reservation_data = reservation.get_dict()
        reservations.append(reservation_data)

    logger.info("{} - get reservation data".format(citizen_id))
    return json.dumps(reservations, ensure_ascii=False)


@app.route('/reservations', methods=['GET'])
@cross_origin()
@swag_from("swagger/reserveget.yml")
def get_reservation():
    """
    Send reservation information to service site.
    """
    reservations = []
    for reservation in db.session.query(Reservation).all():
        citizen_data = get_citizen(reservation.citizen_id).get_dict()
        reservation_data = reservation.get_dict()

        reservation_data["citizen_data"] = citizen_data
        reservations.append(reservation_data)

    logger.info("service site get reservation data")
    return json.dumps(reservations, ensure_ascii=False)


@app.route('/reservation', methods=['POST'])
@cross_origin()
@swag_from("swagger/reservepost.yml")
def reservation():
    """
    Add reservation data to the database
    """
    citizen_id = request.values['citizen_id']
    site_name = request.values['site_name']
    vaccine_name = request.values['vaccine_name']
    json_data = {
        "citizen_id": citizen_id,
        "site_name": site_name,
        "vaccine_name": vaccine_name,
        "timestamp": datetime.now(),
        "queue": None,
        "checked": False
    }

    if not (citizen_id and site_name and vaccine_name):
        json_data["feedback"] = RESERVATION_FEEDBACK["missing_key"]
        logger.error(RESERVATION_FEEDBACK["missing_key"])
        return json.dumps(json_data, ensure_ascii=False)

    if not is_citizen_id(citizen_id):
        json_data["feedback"] = RESERVATION_FEEDBACK["invalid_id"]
        logger.error(RESERVATION_FEEDBACK["invalid_id"])
        return json.dumps(json_data, ensure_ascii=False)

    if not is_registered(citizen_id):
        json_data["feedback"] = RESERVATION_FEEDBACK["not_registered"]
        logger.error(RESERVATION_FEEDBACK["not_registered"])
        return json.dumps(json_data, ensure_ascii=False)

    if is_reserved(citizen_id):
        json_data["feedback"] = RESERVATION_FEEDBACK["double_reservation"]
        logger.error(RESERVATION_FEEDBACK["double_reservation"])
        return json.dumps(json_data, ensure_ascii=False)

    if not vaccine_name in ["Pfizer", "Astra", "Sinopharm", "Sinovac"]:
        logger.error(RESERVATION_FEEDBACK["invalid_vaccine"])
        return {"feedback": RESERVATION_FEEDBACK["invalid_vaccine"]}

    citizen = get_citizen(citizen_id)
    is_valid, json_data = validate_vaccine(citizen, vaccine_name, json_data)

    if not is_valid:
        logger.error("{} - {}".format(citizen_id, json_data['feedback']))
        return json_data

    try:
        data = Reservation(int(citizen_id), site_name, vaccine_name)
        db.session.add(data)
        db.session.commit()
        reservation_data = data.get_dict()
        reservation_data["feedback"] = RESERVATION_FEEDBACK["success"]
        return jsonify(reservation_data), 201, {
            'Location':
            url_for('reservation_get_by_citizen_id',
                    citizen_id=data.citizen_id,
                    _external=True)
        }
    except:
        db.session.rollback()
        logger.error(RESERVATION_FEEDBACK["other"])
        return {"feedback": RESERVATION_FEEDBACK["other"]}


@app.route('/reservation/<citizen_id>', methods=['DELETE'])
@cross_origin()
@swag_from("swagger/reservedel.yml")
def cancel_reservation(citizen_id):
    """
    Cancel reservation and remove it from the database.
    """
    if not (citizen_id):
        logger.error(CANCEL_RESERVATION_FEEDBACK["missing_key"])
        return {"feedback": CANCEL_RESERVATION_FEEDBACK["missing_key"]}

    if not is_citizen_id(citizen_id):
        logger.error(CANCEL_RESERVATION_FEEDBACK["invalid_id"])
        return {"feedback": CANCEL_RESERVATION_FEEDBACK["invalid_id"]}

    if not is_registered(citizen_id):
        logger.error(CANCEL_RESERVATION_FEEDBACK["not_registered"])
        return {"feedback": CANCEL_RESERVATION_FEEDBACK["not_registered"]}

    if not is_reserved(citizen_id):
        logger.error(CANCEL_RESERVATION_FEEDBACK["not_reservation"])
        return {"feedback": CANCEL_RESERVATION_FEEDBACK["not_reservation"]}

    try:
        reservation = get_unchecked_reservations(citizen_id).first()
        db.session.delete(reservation)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(CANCEL_RESERVATION_FEEDBACK["invalid_reservation"])
        return {"feedback": CANCEL_RESERVATION_FEEDBACK["invalid_reservation"]}

    logger.info("{} - cancel reservation".format(citizen_id))
    return {"feedback": CANCEL_RESERVATION_FEEDBACK["success"]}


@app.route('/queue_report', methods=['POST'])
@cross_origin()
@swag_from("swagger/queuepost.yml")
def update_queue():
    citizen_id = request.values['citizen_id']
    queue = request.values['queue']

    try:
        queue = datetime.strptime(queue, "%Y-%m-%d %H:%M:%S.%f")
        if queue <= datetime.now():
            logger.error(REPORT_FEEDBACK["invalid_time"])
            return {"feedback": REPORT_FEEDBACK["invalid_time"]}
    except ValueError:
        logger.error(REPORT_FEEDBACK["invalid_time_format"])
        return {"feedback": REPORT_FEEDBACK["invalid_time_format"]}

    try:
        reservation = get_unchecked_reservations(citizen_id).first()
        reservation.queue = queue
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(REPORT_FEEDBACK["invalid_reservation"])
        return {"feedback": REPORT_FEEDBACK["invalid_reservation"]}

    logger.info("{} - updated queue - queue: {}".format(citizen_id, queue))
    return {"feedback": REPORT_FEEDBACK["success"]}


@app.route('/report_taken', methods=['POST'])
@cross_origin()
@swag_from("swagger/reportpost.yml")
def update_citizen_db():
    citizen_id = request.values['citizen_id']
    vaccine_name = request.values['vaccine_name']

    if not (citizen_id and vaccine_name):
        logger.error(REPORT_FEEDBACK["missing_key"])
        return {"feedback": REPORT_FEEDBACK["missing_key"]}

    if not is_citizen_id(citizen_id):
        logger.error(REPORT_FEEDBACK["invalid_id"])
        return {"feedback": REPORT_FEEDBACK["invalid_id"]}

    if not is_registered(citizen_id):
        logger.error(REPORT_FEEDBACK["not_registered"])
        return {"feedback": REPORT_FEEDBACK["not_registered"]}

    if not vaccine_name in ["Pfizer", "Astra", "Sinopharm", "Sinovac"]:
        logger.error(REPORT_FEEDBACK["invalid_vaccine"])
        return {"feedback": REPORT_FEEDBACK["invalid_vaccine"]}

    try:
        option = request.values['option']
        if (option == "walk-in"):
            if is_reserved(citizen_id):
                logger.error(REPORT_FEEDBACK["has_reservation"])
                return {"feedback": REPORT_FEEDBACK["has_reservation"]}

            try:
                citizen = get_citizen(citizen_id)
                is_valid, feedback = validate_vaccine(citizen, vaccine_name,
                                                      None)

                if not is_valid:
                    logger.error("{} - {}".format(citizen_id,
                                                  feedback['feedback']))
                    return feedback

                citizen.vaccine_taken = [
                    *(citizen.vaccine_taken), vaccine_name
                ]
                db.session.commit()

            except:
                db.session.rollback()
                logger.error(REPORT_FEEDBACK["other"])
                return {"feedback": REPORT_FEEDBACK["other"]}
    except:
        if not is_reserved(citizen_id):
            logger.error(REPORT_FEEDBACK["not_reservation"])
            return {"feedback": REPORT_FEEDBACK["not_reservation"]}

        try:
            citizen_data = get_citizen(citizen_id)
            citizen_data.vaccine_taken = [
                *(citizen_data.vaccine_taken), vaccine_name
            ]
            reservation_data = get_unchecked_reservations(citizen_id).filter(
                Reservation.vaccine_name == vaccine_name).first()
            reservation_data.checked = True
            db.session.commit()
        except:
            db.session.rollback()
            logger.error(REPORT_FEEDBACK["not_match_vaccine"])
            return {"feedback": REPORT_FEEDBACK["not_match_vaccine"]}

    logger.info("{} - updated citizen - vaccine name: {}".format(
        citizen_id, vaccine_name))
    return {"feedback": REPORT_FEEDBACK["success"]}


@app.route('/')
@cross_origin()
def index():
    """
    Render html template for index page.
    """
    return render_template('index.html')


@app.route('/document/registration', methods=['GET'])
@cross_origin()
def registration_usage():
    """
    Render html template for registration usage.
    """
    return render_template('registration.html')


@app.route('/document/reservation', methods=['GET'])
@cross_origin()
def reservation_usage():
    return render_template('reservation.html')


@app.route('/document/report_taken', methods=['GET'])
@cross_origin()
def report_taken_usage():
    return render_template('report_taken.html')


@app.route('/document/queue_report', methods=['GET'])
@cross_origin()
def queue_report_usage():
    return render_template('queue_report.html')


@app.route('/database/citizen', methods=['GET'])
@cross_origin()
def citizen():
    """
    Render html template that display citizen's information.
    """
    tbody = ""
    for person in db.session.query(Citizen).all():
        tbody += f"<tr>"
        tbody += f'<th scope="row">{person.citizen_id}</th>'
        tbody += f"<td>{person.name}</td>"
        tbody += f"<td>{person.surname}</td>"
        tbody += f"<td>{person.birth_date}</td>"
        tbody += f"<td>{person.occupation}</td>"
        tbody += f"<td>{person.phone_number}</td>"
        tbody += f"<td>{person.is_risk}</td>"
        tbody += f"<td>{person.address}</td>"
        tbody += f"<td>{person.vaccine_taken}</td>"
        tbody += f"</tr>"

    html = render_template('database.html')
    html = Template(html).safe_substitute(
        title="Citizen",
        count=db.session.query(Citizen).count(),
        unit="person(s)",
        thead="""<tr>
            <th scope="col">Citizen ID</th>
            <th scope="col">Firstname</th>
            <th scope="col">Lastname</th>
            <th scope="col">Birth Date</th>
            <th scope="col">Occupation</th>
            <th scope="col">Phone Number</th>
            <th scope="col">COVID-risks medical</th>
            <th scope="col">Address</th>
            <th scope="col">Vaccine Taken</th>
            </tr>""",
        tbody=tbody)
    return html


@app.route('/database/reservation', methods=['GET'])
@cross_origin()
def reservation_database():
    """
    Render html template that display reservation's information.
    """
    tbody = ""
    for reservation in db.session.query(Reservation).all():
        tbody += f"<tr>"
        tbody += f'<th scope="row">{reservation.citizen_id}</th>'
        tbody += f"<td>{reservation.site_name}</td>"
        tbody += f"<td>{reservation.vaccine_name}</td>"
        tbody += f'<td>{reservation.timestamp.strftime("%Y-%m-%d, %H:%M:%S")}</td>'
        tbody += f'<td>{reservation.queue.strftime("%Y-%m-%d, %H:%M:%S") if reservation.queue else "TBC"}</td>'
        tbody += f"<td>{reservation.checked}</td>"
        tbody += f"</tr>"

    html = render_template('database.html')
    html = Template(html).safe_substitute(
        title="Reservation",
        count=db.session.query(Reservation).count(),
        unit="reservation(s)",
        thead="""<tr>
            <th scope="col">Citizen ID</th>
            <th scope="col">Site Name</th>
            <th scope="col">Vaccine Name</th>
            <th scope="col">Timestamp</th>
            <th scope="col">Queue</th>
            <th scope="col">Checked</th>
            </tr>""",
        tbody=tbody)
    return html


if __name__ == '__main__':
    app.run()
