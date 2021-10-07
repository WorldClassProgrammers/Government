from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
ENV = os.getenv('ENV')

if ENV == 'development':
    app.debug = os.getenv('DEBUG')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'SQLALCHEMY_DATABASE_URI')
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = ''

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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
        return f"citizen_id = {self.citizen_id}, fullname = {self.name} {self.surname}, birth_date = {self.birth_date}, occupation = {self.occupation},address = {self.address}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/registration', methods=['POST'])
def registration():
    if request.method == 'POST':
        citizen_id = int(request.values['citizen_id'])
        name = request.values['name']
        surname = request.values['surname']
        birth_date = request.values['birth_date']
        occupation = request.values['occupation']
        address = request.values['address']

        # print(customer, dealer, rating, comments)
        if citizen_id and name and surname and birth_date and occupation and address:
            if db.session.query(Citizen).filter(
                    Citizen.citizen_id == citizen_id).count() == 0:
                data = Citizen(citizen_id, name, surname, birth_date,
                               occupation, address)
                db.session.add(data)
                db.session.commit()
                return {"feedback": "registration success!"}
            else:
                return {
                    "feedback":
                    "registration fail -> this person already registed"
                }
        else:
            return {"feedback": "registration fail -> missing some attribute"}


if __name__ == '__main__':
    app.run()