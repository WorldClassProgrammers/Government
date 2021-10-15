from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from string import Template
from datetime import datetime
import os

app = Flask(__name__)

app.debug = os.getenv('DEBUG')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
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


@app.route('/citizen', methods=['PUT'])
def update_citizen_db():
    if request.method == 'PUT':
        citizen_id = request.values['citizen_id']
        vaccine_name = request.values['vaccine_name']
        try:
            citizen_data = db.session.query(Citizen).filter(Citizen.citizen_id == citizen_id).first()
            old_data = db.session.query(Citizen).filter(Citizen.citizen_id == citizen_id)
            vaccine_list = citizen_data.vaccine_taken
            vaccine_list.append(vaccine_name)
            old_data.update({"vaccine_taken": vaccine_list})
            db.session.commit()
        except:
            db.session.rollback()
            return {"feedbacks": "Can't find citizen_id in the database"}
    return {"feedbacks": f"{citizen_id} is updated"}


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
