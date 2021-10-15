from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from string import Template
from datetime import datetime
import os

app = Flask(__name__)

app.debug = os.getenv("DEBUG")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def parsing_date(birth_date: str):
    for fmt in ('%d %b %Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(birth_date, fmt)
        except ValueError:
            pass
    raise ValueError('invalid date format')


def delta_year(birth_date: datetime):
    return datetime.now().year - birth_date.year


class Citizen(db.Model):
    __tablename__ = 'citizen'
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Numeric, unique=True)
    name = db.Column(db.String(200))
    surname = db.Column(db.String(200))
    birth_date = db.Column(db.Date)
    occupation = db.Column(db.Text())
    address = db.Column(db.Text())
    vaccine_taken = db.Column(db.PickleType())

    # vaccine_taken = db.Column(db.PickleType(mutable=True))

    def __init__(self, citizen_id, name, surname, birth_date, occupation,
                 address):
        self.citizen_id = citizen_id
        self.name = name
        self.surname = surname
        self.birth_date = birth_date
        self.occupation = occupation
        self.address = address
        self.vaccine_taken = []

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
    citizen_id = db.Column(db.Numeric, unique=True)
    site_name = db.Column(db.String(200))
    vaccine_name = db.Column(db.String(200))
    timestamp = db.Column(db.Date)
    queue = db.Column(db.Date)
    checked = db.Column(db.Boolean)

    # vaccine_taken = db.Column(db.PickleType(mutable=True))

    def __init__(self, citizen_id, site_name, vaccine_name, timestamp, queue, checked):
        self.citizen_id = citizen_id
        self.site_name = site_name
        self.vaccine_name = vaccine_name
        self.timestamp = timestamp
        self.queue = queue
        self.checked = checked

    def __str__(self):
        return f"""
        <tr>
            <th scope="row">{self.citizen_id}</th>
            <td>{self.site_name}</td>
            <td>{self.vaccine_name}</td>
            <td>{self.timestamp}</td>
            <td>{self.queue}</td>
            <td>{self.checked}</td>
        </tr>
        """


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/registration', methods=['GET'])
def registration_usage():
    return render_template('registration.html')


@app.route('/registration', methods=['POST'])
def registration():
    if request.method == 'POST':
        citizen_id = request.values['citizen_id']
        name = request.values['name']
        surname = request.values['surname']
        birth_date = request.values['birth_date']
        occupation = request.values['occupation']
        address = request.values['address']

        if not (citizen_id and name and surname and birth_date and occupation
                and address):
            return {"feedback": "registration fail: missing some attribute"}

        if not (citizen_id.isdigit() and len(citizen_id) == 13):
            return {"feedback": "registration fail: invalid citizen ID"}

        try:
            birth_date = parsing_date(birth_date)
            if delta_year(birth_date) <= 12:
                return {"feedback": "registration fail: not archived minimum age"}
        except ValueError:
            return {"feedback": "registration fail: invalid birth date format"}

        if db.session.query(Citizen).filter(Citizen.citizen_id == citizen_id).count() > 0:
            return {"feedback": "registration fail: this person already registed"}

        data = Citizen(int(citizen_id), name, surname, birth_date, occupation, address)
        db.session.add(data)
        db.session.commit()
        return {"feedback": "registration success!"}


@app.route('/reservation', methods=['POST'])
def reservation():
    """
    Add reservation data to the database
    """
    if request.method == 'POST':
        citizen_id = request.values['citizen_id']
        site_name = request.values['site_name']
        vaccine_name = request.values['vaccine_name']
        timestamp = datetime.now()
        queue = request.values['queue']
        checked = request.values.get('checked', type=bool)
        json_data = {"citizen_id": citizen_id, "site_name": site_name, "vaccine_name": vaccine_name, "timestamp": timestamp, "queue": queue, "checked": checked}

        if not (citizen_id and site_name and vaccine_name and timestamp):
            return {"feedback": "reservation fail: missing some attribute"}

        if not (citizen_id.isdigit() and len(citizen_id) == 13): 
            return {"feedback": "reservation fail: invalid citizen ID"}

        if db.session.query(Citizen).filter(Citizen.citizen_id == citizen_id).count() <= 0:
            return {"feedback": "reservation fail: citizen ID is not registered"}

        try:
            queue = parsing_date(queue)  # Convert queue to datetime object.
            if queue <= datetime.now():  # Can only reserve vaccine in the future.
                return jsonify(json_data)
        except ValueError:  # If queue can't be convert to datetime object.
            return jsonify(json_data)

        data = Reservation(int(citizen_id), site_name, vaccine_name, timestamp, queue, checked)
        db.session.add(data)
        db.session.commit()
        return {"feedback": "reservation success!"}


@app.route('/cancel_reservation', methods=['DELETE'])
def cancel_reservation():
    """
    Cancel reservation and remove it from the database.
    """
    if request.method == 'DELETE':
        citizen_id = request.values['citizen_id']

        if not (citizen_id):
            return {"feedback": "cancel reservation failed: no citizen id is given"}

        if not (citizen_id.isdigit() and len(citizen_id) == 13): 
            return {"feedback": "cancel reservation failed: invalid citizen ID"}

        data = db.session.query(Reservation).filter(Reservation.citizen_id == citizen_id)

        if data.count() == 0:
            return {"feedback": "cancel reservation failed: there is no reservation for this citizen id"}

        for elem in data:
            db.session.delete(elem)
        db.session.commit()
    return {"feedback" : "cancel reservation successfully"}


@app.route('/citizen', methods=['GET'])
def citizen():
    tbody = ""
    for person in db.session.query(Citizen).all():
        tbody += str(person)

    html = render_template('database.html')
    html = Template(html).safe_substitute(
        title="Citizen",
        count=db.session.query(Citizen).count(),
        unit="person(s)",
        note="",
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


@app.route('/citizen', methods=['DELETE'])
def reset_citizen_db():
    try:
        deleted_time = db.session.query(Citizen).delete()
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('citizen'))


if __name__ == '__main__':
    app.run()
