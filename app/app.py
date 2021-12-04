from flask import render_template, request, redirect, url_for, make_response, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.errors import UniqueViolation
from flask_cors import cross_origin
from flasgger.utils import swag_from
from flasgger import Swagger
from datetime import datetime
from string import Template
import json, os

from app.feedback import *
from app.assistant import *

app.config["SWAGGER"] = {"title": "WCG-API", "universion": 1}
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
# app.config['SECRET_KEY'] = "DUMMY_KEY_IS_NOT_A_SECRET"
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
    """Get the citizen information.
    
    Params:
        citizen_id (string): the valid 13 digit citizen id

    Response Codes:
        200: get citizen information successfully
        404: invalid citizen id or the citizen is not registered

    Returns:
        json data: the data of the citizen which includes
            {
                "citizen_id",
                "name",
                "surname",
                "birth_date",
                "occupation",
                "phone_number",
                "is_risk",
                "address",
                "vaccine_taken"
            }
        response: the redirection to the list of citizens page with 404 status code due to:
            - invalid citizen id
            - citizen not register or in database
    """

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
    """Register a citizen into the database.
    
    Params (POST):
        citizen_id (string): the valid 13 digit citizen id
        name (string): 
        surname (string): 
        birth_date (string): the birthdate in the formats below
            ['%d %b %Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']
        occupation (string):
        phone_number (string):
        is_risk (bool):
        address (string):

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint

    Response Codes:
        201: the citizen is registered successfully
        401: the user does not have permission to invoke this endpoint
        404: invalid citizen id or the citizen is not registered

    Returns:
        json data: the data of the citizen and the feedback of successful response
        json data: the feedback of failed registration if the following occurs:
            - invalid citizen id
            - age is less than 12 (comparing birth_date to registration date)
            - citizen already registered
            - invalid birthdate values
        json data: the feedback for unauthenticated usage of this endpoint
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

    if not is_phone_number(phone_number):
        logger.error(REGISTRATION_FEEDBACK["invalid_phone_number"])
        return {"feedback": REGISTRATION_FEEDBACK["invalid_phone_number"]}

    if is_registered(citizen_id):
        logger.error(REGISTRATION_FEEDBACK["registered"])
        return {"feedback": REGISTRATION_FEEDBACK["registered"]}

    if is_phoned(phone_number):
        logger.error(REGISTRATION_FEEDBACK["phoned"])
        return {"feedback": REGISTRATION_FEEDBACK["phoned"]}

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
    """Reset the citizen database.
    
    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint
            and the authenticated user must have admin permissions.

    Response Codes:
        200: the citizen database has been reset successfully
        401: user does not have admin privileges to reset the citizen table

    Returns:
        response: the redirection to the list of citizens page
        json data: the feedback for unauthenticated usage of this endpoint
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
    """Remove a citizen from the database.
    
    Params (DELETE):
        citizen_id (string): the valid 13 digit citizen id

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint
            and the authenticated user must have admin permissions.


    Response Codes:
        200: the citizen has been removed from the database successfully
        401: user does not have admin privileges to reset the citizen table
        404: invalid citizen id or the citizen is not registered

    Returns:
        response: the redirection to the citizen database with 200 status code
        response: "same as above" but with 404 status code due to:
            - invalid citizen id
            - citizen not register or in database
        json data: the feedback for unauthenticated usage of this endpoint
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
    """Get all reservations for a specific citizen.
    
    Params (GET):
        citizen_id (string): the valid 13 digit citizen id

    Response Codes:
        200: gets the reservations of the citizen successfully
        404: invalid citizen id or the citizen is not registered

    Returns:
        list[json data]: a list of reservations of the citizen
        response: the redirection to the list of citizens page
            with 404 status code due to:
            - invalid citizen id
            - citizen not register or in database
    """
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
    """Get all reservations in the database.

    Response Codes:
        200: gets the reservations of the citizen successfully

    Returns:
    list[json data]: a list of all reservations in the database
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
    """Make a reservation for a citizen and store it in the database.

    Params (POST):
        citizen_id (string): the valid 13 digit citizen id
        site_name (string): the name of the appointed vaccination site
        vaccine_name (string): the name of the reserved vaccine

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint

    Response Codes:
        201: the reservation has been made successfully
        401: the user does not have permission to invoke this endpoint
        404: invalid citizen id, the citizen is not registered,
            the citizen has already reserved, or the vaccine name is invalid

    Returns:
        json data: the data of the reservation which includes:
            {
                "citizen_id",
                "site_name",
                "vaccine_name",
                "timestamp",
                "queue",
                "checked",
                "feedback"
            }
        json data: the feedback of failed registration if the following occurs:
            - invalid citizen id
            - citizen is not registered
            - invalid vaccine name
            - citizen already has a reservation
        json data: the feedback for unauthenticated usage of this endpoint
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
    """Cancel a citizen's reservation and remove it from the database.

    Params (DELETE):
        citizen_id (string): the valid 13 digit citizen id

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint

    Response Codes:
        200: the citizen is registered successfully
        401: the user does not have permission to invoke this endpoint
        404: invalid citizen id or the citizen is not registered

    Returns:
        json data: the feedback of successful response and status code 200
        json data: the feedback of failed registration if the following occurs:
            - invalid citizen id
            - no reservation for this citizen
        json data: the feedback for unauthenticated usage of this endpoint
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
    """Update the queue of the reservation.
    
    Params (POST):
        citizen_id (string): the valid 13 digit citizen id
        queue (string): the date of the appointment

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint

    Response Codes:
        200: the queue has been updated successfully
        400: the queue or reservation is invalid
        401: the user does not have permission to invoke this endpoint

    Returns:
        json data: the feedback of the queue being updated successfully
        json data: the feedback of failed registration if the following occurs:
            - invalid queue date
            - invalid queue value
            - invalid reservation
        json data: the feedback for unauthenticated usage of this endpoint
    """
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
    """Accepts the report sent by service sites and update citizen's list of vaccine taken.

    Params (POST):
        citizen_id (string): the valid 13 digit citizen id
        vaccine_name (string): the name of the vaccine taken
        option (string): the method of how the user registered for the vaccine

    Authentication:
        jwt token: the bearer token that is required for invoking this endpoint

    Response Codes:
        200: the citizen vaccine taken information has been updated successfully
        401: the user does not have permission to invoke this endpoint
        400: invalid citizen id or the citizen is not registered

    Returns:
        json data: the feedback of a report being successfully taken.
        json data: the feedback of failed reporting if the following occurs:
            - invalid citizen id
            - citizen has not been registered
            - invalid vaccine name
            - no reservation found for the citizen
            - invalid vaccine sequence
            - citizen already has reservation when the option is walk-in
        json data: the feedback for unauthenticated usage of this endpoint
    """
    user = Users.query.filter_by(username=get_jwt_identity()).first()
    if not user.has_privilege and not user.is_admin:
        return {"feedback": AUTHENTICATION_FEEDBACK["unauthenticated"]}

    citizen_id = request.values['citizen_id']
    vaccine_name = request.values['vaccine_name']
    option = request.values['option']

    if not (citizen_id and vaccine_name and option):
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
            citizen.vaccine_taken = [*(citizen.vaccine_taken), vaccine_name]
            db.session.commit()
        except:
            db.session.rollback()
            logger.error(REPORT_FEEDBACK["other"])
            return {"feedback": REPORT_FEEDBACK["other"]}

        logger.info("{} - updated citizen - vaccine name: {}".format(
            citizen_id, vaccine_name))
        return {"feedback": REPORT_FEEDBACK["success"]}

    elif (option == "reserve"):
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

    else:
        logger.error(REPORT_FEEDBACK["invalid_option"])
        return {"feedback": REPORT_FEEDBACK["invalid_option"]}


@app.route('/register_user', methods=['POST'])
@cross_origin()
def register_user():
    """Registers a user for API usage permissions.

    Params (POST):
        username (string): the username of the user
        password (string): the password of the user

    Response Codes:
        201: the user has been registered successfully
        400: the username has already been taken registered

    Returns:
        json data: the feedback of a user being registered successfully.
        json data: the feedback of failing a user registration due to the
            username has been taken already
    """
    data = request.values
    feedback = ""
    try:
        hashed_password = generate_password_hash(data['password'],
                                                 method='sha256')
        new_user = Users(username=data['username'],
                         password=hashed_password,
                         is_admin=False,
                         has_privilege=True)

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


@app.route('/login', methods=['GET', 'POST'])
def login_user():
    """Registers a user for API usage permissions.

    Authorization:
        username (string): the username of the user
        password (string): the password of the user

    Response Codes:
        201: the user has been registered successfully
        400: the username or password could not be verified
    Returns:
        json data: the access bearer token
        response: the response and the json feedback of failed login
    """
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(
            'could not verify', 401,
            {'WWW.Authentication': 'Basic realm: "login required"'})

    user = Users.query.filter_by(username=auth.username).first()

    if check_password_hash(user.password, auth.password):
        access_token = create_access_token(identity=auth.username)
        return jsonify(access_token=access_token)

    return make_response(
        'could not verify', 401,
        {'WWW.Authentication': 'Basic realm: "login required"'})


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
