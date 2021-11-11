from codecs import encode
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from string import Template
from datetime import datetime
from flasgger import Swagger
from flasgger.utils import swag_from
from flask_marshmallow import Marshmallow
import os
import logging
import json

app = Flask(__name__)
CORS(app)

app.debug = os.getenv("DEBUG")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

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
        Citizen.citizen_id == citizen_id).count() > 0


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
    address = db.Column(db.Text())
    vaccine_taken = db.Column(db.PickleType())

    def __init__(self, citizen_id, name, surname, birth_date, occupation, address):
        self.citizen_id = citizen_id
        self.name = name
        self.surname = surname
        self.birth_date = birth_date
        self.occupation = occupation
        self.address = address
        self.vaccine_taken = []
        logger.info(
            'created Citizen: {} - {} {} - birth date: {} occupation: {} address: {} vaccine taken: {}'
                .format(self.citizen_id, self.name, self.surname, self.birth_date,
                        self.occupation, self.address, self.vaccine_taken))

    def __str__(self):
        return f"""
        <tr>
            <th scope="row">{self.citizen_id}</th>
            <td>{self.name}</td>
            <td>{self.surname}</td>
            <td>{self.birth_date}</td>
            <td>{self.occupation}</td>
            <td>{self.address}</td>
            <td>{self.vaccine_taken}</td>
        </tr>
        """


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

    def __str__(self):
        print(type(self.timestamp))
        return f"""
        <tr>
            <th scope="row">{self.citizen_id}</th>
            <td>{self.site_name}</td>
            <td>{self.vaccine_name}</td>
            <td>{self.timestamp.strftime("%Y-%m-%d, %H:%M:%S")}</td>
            <td>{self.queue.strftime("%Y-%m-%d, %H:%M:%S") if self.queue else "TBC"}</td>
            <td>{self.checked}</td>
        </tr>
        """


class CitizenSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Citizen
        load_instance = True


class ReservationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Reservation
        load_instance = True


@app.route('/')
@cross_origin()
def index():
    """
    Render html template for index page.
    """
    return render_template('index.html')


@app.route('/registration', methods=['GET'])
@cross_origin()
@swag_from("swagger/regisget.yml")
def registration_as_json():
    """
    Return all citizen's information as json
    """
    citizen_schema = CitizenSchema(many=True)
    data = citizen_schema.dump(db.session.query(Citizen).all())
    logger.info("get registration data")
    # return json.dumps(data, ensure_ascii=False)
    return jsonify(data)


@app.route('/document/registration', methods=['GET'])
@cross_origin()
def registration_usage():
    """
    Render html template for registration usage.
    """
    return render_template('registration.html')


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
    address = request.values['address']

    if not (citizen_id and name and surname and birth_date and occupation
            and address):
        logger.error("registration failed: missing some attribute")
        return {"feedback": "registration failed: missing some attribute"}

    if not is_citizen_id(citizen_id):
        logger.error("registration failed: invalid citizen ID")
        return {"feedback": "registration failed: invalid citizen ID"}

    if is_registered(citizen_id):
        logger.error("registration failed: this person already registered")
        return {
            "feedback": "registration failed: this person already registered"
        }

    try:
        birth_date = parsing_date(birth_date)
        if delta_year(birth_date) <= 12:
            logger.error("registration failed: not archived minimum age")
            return {
                "feedback": "registration failed: not archived minimum age"
            }
    except ValueError:
        logger.error("registration failed: invalid birth date format")
        return {"feedback": "registration failed: invalid birth date format"}

    try:
        data = Citizen(int(citizen_id), name, surname, birth_date, occupation,
                       address)
        db.session.add(data)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(
            "registration failed: something go wrong, please contact admin")
        return {
            "feedback":
                "registration failed: something go wrong, please contact admin"
        }
    registration_data = {
        "citizen_id": data.citizen_id,
        "name": data.name,
        "surname": data.surname,
        "birth_date": data.birth_date,
        "occupation": data.occupation,
        "address": data.address,
        "vaccine_taken": data.vaccine_taken
    }
    # return json.dumps(registration_data, ensure_ascii=False), 201, \
    #     {'Location': url_for('citizen_get_by_citizen_id', citizen_id=data.citizen_id, _external=True)}
    return jsonify(registration_data), 201, \
           {'Location': url_for('citizen_get_by_citizen_id', citizen_id=data.citizen_id, _external=True)}
    # return {"feedback": "reservation success!"}


@app.route('/document/reservation', methods=['GET'])
@cross_origin()
def reservation_usage():
    return render_template('reservation.html')


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
        feedback = "reservation failed: missing some attribute"
        json_data["feedback"] = feedback
        logger.error(feedback)
        return jsonify(json_data)

    if not is_citizen_id(citizen_id):
        feedback = "reservation failed: invalid citizen ID"
        json_data["feedback"] = feedback
        logger.error(feedback)
        return jsonify(json_data)

    if not is_registered(citizen_id):
        feedback = "reservation failed: citizen ID is not registered"
        json_data["feedback"] = feedback
        logger.error(feedback)
        return jsonify(json_data)

    if is_reserved(citizen_id):
        feedback = "reservation failed: there is already a reservation for this citizen"
        json_data["feedback"] = feedback
        logger.error(feedback)
        return jsonify(json_data)

    if not vaccine_name in ["Pfizer", "Astra", "Sinopharm", "Sinovac"]:
        logger.error("report failed: invalid vaccine name")
        return {"feedback": "report failed: invalid vaccine name"}

    citizen = get_citizen(citizen_id)
    is_valid, json_data = validate_vaccine(citizen, vaccine_name, json_data)

    if not is_valid:
        logger.error("{} - {}".format(citizen_id, json_data['feedback']))
        return json_data

    try:
        data = Reservation(int(citizen_id), site_name, vaccine_name)
        db.session.add(data)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(
            "reservation failed: something went wrong, please contact the admin"
        )
        return {
            "feedback":
                "reservation failed: something went wrong, please contact the admin"
        }

    return {"feedback": "reservation success!"}


@app.route('/reservation', methods=['DELETE'])
@cross_origin()
@swag_from("swagger/reservedel.yml")
def cancel_reservation():
    """
    Cancel reservation and remove it from the database.
    """
    citizen_id = request.values['citizen_id']

    if not (citizen_id):
        logger.error("cancel reservation failed: no citizen id is given")
        return {
            "feedback": "cancel reservation failed: no citizen id is given"
        }

    if not is_citizen_id(citizen_id):
        logger.error("cancel reservation failed: invalid citizen ID")
        return {"feedback": "cancel reservation failed: invalid citizen ID"}

    if not is_registered(citizen_id):
        logger.error("reservation failed: citizen ID is not registered")
        return {"feedback": "reservation failed: citizen ID is not registered"}

    if not is_reserved(citizen_id):
        logger.error(
            "cancel reservation failed: there is no reservation for this citizen"
        )
        return {
            "feedback":
                "cancel reservation failed: there is no reservation for this citizen"
        }

    try:
        reservation = get_unchecked_reservations(citizen_id).first()
        db.session.delete(reservation)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(
            "cancel reservation failed: couldn't find valid reservation")
        return {
            "feedback":
                "cancel reservation failed: couldn't find valid reservation"
        }

    logger.info("{} - cancel reservation".format(citizen_id))
    return {"feedback": "cancel reservation successfully"}


@app.route('/document/queue_report', methods=['GET'])
@cross_origin()
def queue_report_usage():
    return render_template('queue_report.html')


@app.route('/queue_report', methods=['POST'])
@cross_origin()
@swag_from("swagger/queuepost.yml")
def update_queue():
    citizen_id = request.values['citizen_id']
    queue = request.values['queue']

    try:
        queue = datetime.strptime(queue, "%Y-%m-%d %H:%M:%S.%f")
        if queue <= datetime.now():
            logger.error(
                "report failed: can only reserve vaccine in the future")
            return {
                "feedback":
                    "report failed: can only reserve vaccine in the future"
            }
    except ValueError:
        logger.error("report failed: invalid queue datetime format")
        return {"feedback": "report failed: invalid queue datetime format"}

    try:
        reservation = get_unchecked_reservations(citizen_id).first()
        reservation.queue = queue
        db.session.commit()
    except:
        db.session.rollback()
        logger.error("report failed: couldn't find valid reservation")
        return {"feedback": "report failed: couldn't find valid reservation"}

    logger.info("{} - updated queue - queue: {}".format(citizen_id, queue))
    return {"feedback": "report success!"}


@app.route('/document/report_taken', methods=['GET'])
@cross_origin()
def report_taken_usage():
    return render_template('report_taken.html')


@app.route('/report_taken', methods=['POST'])
@cross_origin()
@swag_from("swagger/reportpost.yml")
def update_citizen_db():
    citizen_id = request.values['citizen_id']
    vaccine_name = request.values['vaccine_name']
    option = request.values['option']

    if not (citizen_id and vaccine_name and option):
        logger.error("report failed: missing some attribute")
        return {"feedback": "report failed: missing some attribute"}

    if not is_citizen_id(citizen_id):
        logger.error("report failed: invalid citizen ID")
        return {"feedback": "report failed: invalid citizen ID"}

    if not is_registered(citizen_id):
        logger.error("report failed: citizen ID is not registered")
        return {"feedback": "report failed: citizen ID is not registered"}

    if not vaccine_name in ["Pfizer", "Astra", "Sinopharm", "Sinovac"]:
        logger.error("report failed: invalid vaccine name")
        return {"feedback": "report failed: invalid vaccine name"}

    try:
        option = request.values['option']
        if (option == "walk-in"):
            if is_reserved(citizen_id):
                logger.error(
                    "report failed: before walk-in, citizen need to cancel other reservation"
                )
                return {
                    "feedback":
                        "report failed: before walk-in, citizen need to cancel other reservation"
                }

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
                logger.error(
                    "report failed: something go wrong, please contact admin")
                return {
                    "feedback":
                        "report failed: something go wrong, please contact admin"
                }
    except:
        pass

    if not is_reserved(citizen_id):
        logger.error("report failed: there is no reservation for this citizen")
        return {
            "feedback":
                "report failed: there is no reservation for this citizen"
        }

    try:
        citizen_data = db.session.query(Citizen).filter(
            Citizen.citizen_id == citizen_id).first()
        citizen_data.vaccine_taken = [
            *(citizen_data.vaccine_taken), vaccine_name
        ]
        reservation_data = get_unchecked_reservations(citizen_id).filter(
            Reservation.vaccine_name == vaccine_name).first()
        reservation_data.checked = True
        db.session.commit()
    except:
        db.session.rollback()
        logger.error("report failed: vaccine_name not match reservation")
        return {
            "feedback": "report failed: vaccine_name not match reservation"
        }

    logger.info("{} - updated citizen - vaccine name: {}".format(
        citizen_id, vaccine_name))
    return {"feedback": "report success!"}


@app.route('/database/reservation', methods=['GET'])
@cross_origin()
def reservation_database():
    """
    Render html template that display reservation's information.
    """
    tbody = ""
    for reservation in db.session.query(Reservation).all():
        tbody += str(reservation)
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


@app.route('/reservations', methods=['GET'])
@cross_origin()
@swag_from("swagger/reserveget.yml")
def get_reservation():
    """
    Send reservation information to service site.
    """
    reservations = []
    for reservation in db.session.query(Reservation).all():
        citizen = db.session.query(Citizen).filter(
            reservation.citizen_id == Citizen.citizen_id).first()
        citizen_data = {
            "citizen_id": str(citizen.citizen_id),
            "name": citizen.name,
            "surname": citizen.surname,
            "birth_date": str(citizen.birth_date),
            "occupation": citizen.occupation,
            "address": citizen.address,
            "vaccine_taken": citizen.vaccine_taken
        }
        reservation_data = {
            "citizen_id": str(reservation.citizen_id),
            "site_name": reservation.site_name,
            "vaccine_name": reservation.vaccine_name,
            "timestamp": str(reservation.timestamp),
            "queue": reservation.queue,
            "checked": str(reservation.checked),
            "citizen_data": citizen_data
        }
        reservations.append(reservation_data)

    logger.info("service site get reservation data")
    return jsonify(reservations)


# @app.route('/reservation/<citizen_id>', methods=['GET'])
# @cross_origin()
# # @swag_from("swagger/singleID.yml")
# def reservation_get_by_citizen_id(citizen_id):
#     reservations = []
#     for reservation in db.session.query(Reservation).all():
#         citizen = db.session.query(Citizen).filter(
#             reservation.citizen_id == Citizen.citizen_id).first()
#         citizen_data = {
#             "citizen_id": str(citizen.citizen_id),
#             "name": citizen.name,
#             "surname": citizen.surname,
#             "birth_date": str(citizen.birth_date),
#             "occupation": citizen.occupation,
#             "address": citizen.address,
#             "vaccine_taken": citizen.vaccine_taken
#         }
#         reservation_data = {
#             "citizen_id": str(reservation.citizen_id),
#             "site_name": reservation.site_name,
#             "vaccine_name": reservation.vaccine_name,
#             "timestamp": str(reservation.timestamp),
#             "queue": reservation.queue,
#             "checked": str(reservation.checked),
#             "citizen_data": citizen_data
#         }
#         if reservation_data["citizen_id"] == citizen_id:
#             logger.info("service site get reservation data")
#             return jsonify(reservation_data)
#
#     return


@app.route('/database/citizen', methods=['GET'])
@cross_origin()
def citizen():
    """
    Render html template that display citizen's information.
    """
    tbody = ""
    for person in db.session.query(Citizen).all():
        tbody += str(person)

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
            <th scope="col">Address</th>
            <th scope="col">Vaccine Taken</th>
            </tr>""",
        tbody=tbody)
    return html


@app.route('/registration/<citizen_id>', methods=['GET'])
@cross_origin()
@swag_from("swagger/singleID.yml")
def citizen_get_by_citizen_id(citizen_id):
    if not is_citizen_id(citizen_id) or len(
            db.session.query(Citizen).filter_by(
                citizen_id=citizen_id).all()) != 1:
        feedback_message = "report failed: citizen not found"
        logger.error(feedback_message)
        return redirect(url_for('citizen'), 404)

    for reservation in db.session.query(Reservation).all():
        citizen = db.session.query(Citizen).all()
        reservation_data = {
            "citizen_id": str(reservation.citizen_id),
            "site_name": reservation.site_name,
            "vaccine_name": reservation.vaccine_name,
            "timestamp": str(reservation.timestamp),
            "queue": reservation.queue,
            "checked": str(reservation.checked),
        }
        if not is_reserved(citizen_id):
            reservation_data = {
                "citizen_id": "",
                "site_name": "",
                "vaccine_name": "",
                "timestamp": "",
                "queue": "",
                "checked": ""
            }
        citizen_data = {
            "citizen_id": str(citizen.citizen_id),
            "name": citizen.name,
            "surname": citizen.surname,
            "birth_date": str(citizen.birth_date),
            "occupation": citizen.occupation,
            "address": citizen.address,
            "vaccine_taken": citizen.vaccine_taken,
            "reservation_data": reservation_data
        }
        if citizen_data["citizen_id"] == citizen_id:
            logger.info("{} - get citizen data".format(citizen_id))
            return jsonify(citizen_data)
    return redirect(url_for('citizen'), 404)


@app.route('/registration', methods=['DELETE'])
@cross_origin()
@swag_from("swagger/citizendel.yml")
def reset_citizen_db():
    """
    Reset citizen database or delete a citizen data.
    """
    try:
        citizen_id = request.values['citizen_id']
        if not is_citizen_id(citizen_id):
            logger.error("report failed: invalid citizen ID")
            return {"feedback": "report failed: invalid citizen ID"}

        if get_citizen(citizen_id) is not None:
            get_citizen(citizen_id).delete()
            db.session.query(Reservation).filter(
                Reservation.citizen_id == citizen_id).delete()
            db.session.commit()
        else:
            db.session.rollback()
            logger.error("Could not find citizen ID in the database")
            return redirect(url_for('citizen'))
    except:
        db.session.rollback()
    else:
        logger.info("{} - citizen has been deleted".format(citizen_id))
        return redirect(url_for('citizen'))

    # try:
    #     db.session.query(Citizen).delete()
    #     db.session.query(Reservation).delete()
    #     db.session.commit()
    # except:
    #     db.session.rollback()
    #     logger.error("failed to delete citizen")
    # else:
    #     logger.info("all citizens have been deleted")
    #     return redirect(url_for('citizen'))


if __name__ == '__main__':
    app.run()
