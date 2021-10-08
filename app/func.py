from datetime import datetime

def delta_year(birth_date):
    birth_date = datetime.strptime(birth_date, "%Y-%m-%d")
    return datetime.now().year - birth_date.year