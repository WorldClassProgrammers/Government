from flask import render_template, request, redirect, url_for, make_response, jsonify
from flask_cors import cross_origin
from string import Template
from psycopg2.errors import UniqueViolation
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flasgger import Swagger
from flasgger.utils import swag_from
import json, os
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

from app.feedback import *
from app.assistant import *

app.config["SWAGGER"] = {"title": "WCG-API", "universion": 1}
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
jwt = JWTManager(app)

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
@jwt_required()
@swag_from("swagger/regispost.yml")
def registration():
    """
    Accept and validate registration information.
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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
                       phone_number, (is_risk == "true"), address)
        db.session.add(data)
        db.session.commit()
    except:
        db.session.rollback()
        logger.error(REGISTRATION_FEEDBACK["other"])
        return {"feedback": REGISTRATION_FEEDBACK["other"]}

    registration_data = data.get_dict()
    registration_data["feedback"] = REGISTRATION_FEEDBACK["success"]
    return json.dumps(registration_data, ensure_ascii=False), 201, {
        'Location':
        url_for('citizen_get_by_citizen_id',
                citizen_id=data.citizen_id,
                _external=True)
    }


@app.route('/registration', methods=['DELETE'])
@cross_origin()
@jwt_required()
@swag_from("swagger/citizendel.yml")
def reset_citizen_db():
    """
    Reset citizen database.
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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
@jwt_required()
@swag_from("swagger/citizendel.yml")
def delete_citizen_db(citizen_id):
    """
    Delete a citizen data.
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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
@jwt_required()
@swag_from("swagger/reservepost.yml")
def reservation():
    """
    Add reservation data to the database
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

    citizen_id = request.values['citizen_id']
    site_name = request.values['site_name']
    vaccine_name = request.values['vaccine_name']
    if not (citizen_id and site_name and vaccine_name):
        logger.error(RESERVATION_FEEDBACK["missing_key"])
        return {"feedback": RESERVATION_FEEDBACK["missing_key"]}

    if not is_citizen_id(citizen_id):
        logger.error(RESERVATION_FEEDBACK["invalid_id"])
        return {"feedback": RESERVATION_FEEDBACK["invalid_id"]}

    if not is_registered(citizen_id):
        logger.error(RESERVATION_FEEDBACK["not_registered"])
        return {"feedback": RESERVATION_FEEDBACK["not_registered"]}

    if is_reserved(citizen_id):
        logger.error(RESERVATION_FEEDBACK["double_reservation"])
        return {"feedback": RESERVATION_FEEDBACK["double_reservation"]}

    if not is_vaccine_name(vaccine_name):
        logger.error(RESERVATION_FEEDBACK["invalid_vaccine"])
        return {"feedback": RESERVATION_FEEDBACK["invalid_vaccine"]}

    citizen = get_citizen(citizen_id)
    is_valid, json_data = validate_vaccine(citizen, vaccine_name)

    if not is_valid:
        logger.error("{} - {}".format(citizen_id, json_data['feedback']))
        return json_data

    try:
        data = Reservation(int(citizen_id), site_name, vaccine_name)
        db.session.add(data)
        db.session.commit()
        reservation_data = data.get_dict()
        reservation_data["feedback"] = RESERVATION_FEEDBACK["success"]
        return json.dumps(reservation_data, ensure_ascii=False), 201, {
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
@jwt_required()
@swag_from("swagger/reservedel.yml")
def cancel_reservation(citizen_id):
    """
    Cancel reservation and remove it from the database.
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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
@jwt_required()
@swag_from("swagger/queuepost.yml")
def update_queue():
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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
@jwt_required()
@swag_from("swagger/reportpost.yml")
def update_citizen_db():
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

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

    if not is_vaccine_name(vaccine_name):
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
                is_valid, feedback = validate_vaccine(citizen, vaccine_name)

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
            reservation_data = get_unchecked_reservations(
                db, citizen_id).filter(
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

@app.route('/register_user', methods=['POST'])
@cross_origin()
def register_user():
    data = request.values
    feedback = ""
    try:
        hashed_password = generate_password_hash(data['password'], method='sha256')
        new_user = Users(username=data['username'], password=hashed_password, is_admin=False, has_privilege=True) 

        db.session.add(new_user)
        db.session.commit()
        feedback = REGISTER_USER_FEEDBACK["successful_registration"]
        return json.dumps(feedback, ensure_ascii=False), 201
    except Exception as e:
        if isinstance(e.orig, UniqueViolation):
            feedback = REGISTER_USER_FEEDBACK["duplicated_registration"]
        else:
            feedback = REGISTER_USER_FEEDBACK["failed_registration"]
        db.session.rollback()
        logger.error(feedback)
        return {"feedback": feedback}


@app.route('/login', methods=['POST'])  
def login_user(): 
    print("ffp")
    auth = request.authorization 
    print("bar")  

    if not auth or not auth.username or not auth.password:  
        return make_response('could not verify', 401, {'WWW.Authentication': 'Basic realm: "login required"'})    

    user = Users.query.filter_by(username=auth.username).first()   
        
    if check_password_hash(user.password, auth.password):  
        access_token = create_access_token(identity=auth.username)
        return jsonify(access_token=access_token)

    return make_response('could not verify',  401, {'WWW.Authentication': 'Basic realm: "login required"'})


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
