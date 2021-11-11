from app import *

citizen_id      = "1234567890123"
name            = "adem"
surname         = "fux"
birth_date      = "1890-3-12"
occupation      = "student"
phone_number    = "0987654321"
is_risk         = "True"
address         = "bkk"

# c = Citizen(
#     int(citizen_id), 
#     name, 
#     surname, 
#     birth_date, 
#     occupation,
#     phone_number, 
#     (is_risk == "True"), 
#     address
# )

# print(c.get_dict()["address"])

# if not is_registered("1234567890321"):
#     print("citizen not found")
# else:
#     print("registered")


print(db.session.query(Citizen).count())

for person in db.session.query(Citizen).all():
    print(person.citizen_id, person.name)