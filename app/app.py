from flask import Flask, render_template, request, redirect, url_for
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


def is_citizen_ID(citizen_id):
    return (citizen_id.isdigit() and len(citizen_id) == 13)


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


@app.route('/')
def index():
    """
    Render html template for index page.
    """
    return render_template('index.html')


@app.route('/registration', methods=['GET'])
def registration_usage():
    """
    Render template for registration page.
    """
    return render_template('registration.html')


@app.route('/registration', methods=['POST'])
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
        return {"feedback": "registration fail: missing some attribute"}

    if not is_citizen_ID(citizen_id):
        return {"feedback": "registration fail: invalid citizen ID"}
    
    try:
        birth_date = parsing_date(birth_date)
        if delta_year(birth_date) <= 12:
            return {"feedback": "registration fail: not archived minimum age"}
    except ValueError:
        return {"feedback": "registration fail: invalid birth date format"}

    if db.session.query(Citizen).filter(
            Citizen.citizen_id == citizen_id).count() > 0:
        return {"feedback": "registration fail: this person already registed"}

    data = Citizen(int(citizen_id), name, surname, birth_date, occupation, address)
    db.session.add(data)
    db.session.commit()
    return {"feedback": "registration success!"}


@app.route('/reservation', methods=['GET'])
def reservation_usage():
    return render_template('reservation.html')


@app.route('/reservation', methods=['POST'])
def reservation():
    """
    Add reservation data to the database
    """
    citizen_id = request.values['citizen_id']
    site_name = request.values['site_name']
    vaccine_name = request.values['vaccine_name']

    if not (citizen_id and site_name and vaccine_name):
        return {"feedback": "reservation fail: missing some attribute"}

    if not is_citizen_ID(citizen_id):
        return {"feedback": "reservation fail: invalid citizen ID"}

    if db.session.query(Citizen).filter(
            Citizen.citizen_id == citizen_id).count() <= 0:
        return {"feedback": "reservation fail: citizen ID is not registered"}

    data = Reservation(int(citizen_id), site_name, vaccine_name)
    db.session.add(data)
    db.session.commit()
    return {"feedback": "reservation success!"}


@app.route('/reservation', methods=['DELETE'])
def cancel_reservation():
    """
    Cancel reservation and remove it from the database.
    """
    citizen_id = request.values['citizen_id']
    
    if not (citizen_id):
        return {"feedback": "cancel reservation failed: no citizen id is given"}

    if not is_citizen_ID(citizen_id):
        return {"feedback": "cancel reservation failed: invalid citizen ID"}

    data = db.session.query(Reservation).filter(Reservation.citizen_id == citizen_id)
    if data.count() == 0:
        return {
            "feedback":
            "cancel reservation failed: there is no reservation for this citizen id"
        }

    for elem in data:
        db.session.delete(elem)

    db.session.commit()
    return {"feedback": "cancel reservation successfully"}


@app.route('/queue_report', methods=['GET'])
def queue_report_usage():
    return render_template('queue_report.html')


@app.route('/queue_report', methods=['POST'])
def update_queue():
    citizen_id = request.values['citizen_id']
    queue = request.values['queue']
    
    try:
        queue = datetime.strptime(queue, "%Y-%m-%d %H:%M:%S.%f")
        if queue <= datetime.now():
            return {
                "feedback":
                "report fail: can only reserve vaccine in the future"
            }
    except ValueError:
        return {"feedback": "report fail: invalid queue datetime format"}

    reservation = db.session.query(Reservation).filter(Reservation.citizen_id == citizen_id).first()
    reservation.queue = queue
    db.session.commit()
    return {"feedback": "report success!"}


@app.route('/report_taken', methods=['GET'])
def report_taken_usage():
    return render_template('report_taken.html')


@app.route('/report_taken', methods=['POST'])
def update_citizen_db():
    citizen_id = request.values['citizen_id']
    vaccine_name = request.values['vaccine_name']
    
    try:
        citizen_data = db.session.query(Citizen).filter(Citizen.citizen_id == citizen_id).first()
        citizen_data.vaccine_taken = [*(citizen_data.vaccine_taken), vaccine_name]
        
        reservation_data = db.session.query(Reservation).filter(Reservation.citizen_id == citizen_id).first()
        reservation_data.checked = True

        db.session.commit()
    except:
        db.session.rollback()
        return {"feedbacks": "report fail"}
    
    return {"feedbacks": "report success!"}


@app.route('/reservation_database', methods=['GET'])
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


@app.route('/citizen', methods=['GET'])
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


@app.route('/citizen', methods=['DELETE'])
def reset_citizen_db():
    """
    Reset citizen database.
    """
    try:
        deleted_time = db.session.query(Citizen).delete()
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('citizen'))


if __name__ == '__main__':
    app.run()
