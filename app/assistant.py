from datetime import datetime
from app.models import *

VACCINE_SEQUENCE = [
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
    for pattern in VACCINE_SEQUENCE:
        length = len(vaccine_taken)
        if length < len(pattern) and pattern[:length] == vaccine_taken:
            available_vaccine.add(pattern[length])
            
    return sorted(list(available_vaccine))


def parsing_date(date_str: str):
    """
    Reparse birthdate into datetime format.
    Args:
        date_str (str): birthdate of citizen
    Raises:
        ValueError: invalid date format
    Returns:
        struct_time: Birthdate in datetime format.
    """
    for fmt in ('%d %b %Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt)
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


def valid_id(thai_id) -> bool:
    """
    Validate a 13-digit Thai National ID, given as a number or string.
    Args:
        thai_id (string): thai citizen id
    Returns:
        bool: True if the checksum is true, False otherwise.
    """
    if isinstance(thai_id, int):
        thai_id = str(thai_id)
    elif not isinstance(thai_id, str):
        return False
    if len(thai_id) != 13:
        return False
    try:
        digits = [int(d) for d in thai_id]
    except ValueError:
        return False
    # First digit is never 0; 0 is used for other IDs such as corporate tax ID
    if digits[0] == '0':
        return False
    # Apply checksum formula to first 12 digits
    sum = 0
    for i in range(0,12):
        sum += digits[i]*(13 - i)
    checksum = (11 - sum%11) % 10
    # last digit is checksum
    return checksum == digits[12]


def is_citizen_id(citizen_id):
    """Return True if citizen_id is a string 13 digits

    Args:
        citizen_id (string): id of a citizen

    Returns:
        bool: True if valid citizen_id, False otherwise
    """
    return citizen_id.isdigit() and len(citizen_id) == 13 and valid_id(citizen_id)


def is_phone_number(phone_number):
    return not (len(phone_number) != 10 or phone_number[0] != '0' or phone_number[1] not in ['6', '8', '9'])


def is_registered(citizen_id):
    """Return True if citizen_id is registered in database

    Args:
        citizen_id (string): id of a citizen

    Returns:
        bool: True if citizen_id is registered, False otherwise
    """
    return db.session.query(Citizen).filter(
        Citizen.citizen_id == citizen_id).count() >= 1


def is_phoned(phone_number):
    """Return True if phone_number is registered in database

    Args:
        phone_number (string): phone number

    Returns:
        bool: True if phone_number is registered, False otherwise
    """
    return db.session.query(Citizen).filter(
        Citizen.phone_number == phone_number).count() >= 1


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


def is_vaccine_name(vaccine_name):
    """Return True if vaccine_name is valid

    Args:
        vaccine_name (str): name of the vaccine

    Returns:
        bool: True if vaccine_name is valid, False otherwise
    """
    return any(vaccine_name in sublist for sublist in VACCINE_SEQUENCE)


def validate_vaccine(citizen, vaccine_name):
    vaccines = get_available_vaccine(citizen.vaccine_taken)
    print("Going to check vaccine")
    if not vaccine_name in vaccines:
        if len(vaccines) == 0:
            feedback = f"reservation failed: you finished all vaccinations"
        elif len(vaccines) == 1:
            feedback = f"reservation failed: your next vaccine can be {vaccines} only"
        else:
            feedback = f"reservation failed: your available vaccines are only {vaccines}"
        return False, {"feedback": feedback}
    return True, {}
