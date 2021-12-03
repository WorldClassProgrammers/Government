REGISTRATION_FEEDBACK = {
    'success':              'registration success!',
    'missing_key':          'registration failed: missing some attribute',
    'registered':           'registration failed: this person already registered',
    'phone':                'registration failed: this phone number already registered',
    'invalid_id':           'registration failed: invalid citizen ID',
    'invalid_birthdate':    'registration failed: invalid birth date format',
    'invalid_age':          'registration failed: not archived minimum age',
    'other':                'registration failed: something go wrong, please contact admin'
}

RESERVATION_FEEDBACK = {
    'success':              'reservation success!',
    'missing_key':          'reservation failed: missing some attribute',
    'invalid_id':           'reservation failed: invalid citizen ID',
    'not_registered':       'reservation failed: citizen ID is not registered',
    'double_reservation':   'reservation failed: there is already a reservation for this citizen',
    'invalid_vaccine':      'reservation failed: invalid vaccine name',
    'other':                'reservation failed: something went wrong, please contact the admin'
}

CANCEL_RESERVATION_FEEDBACK = {
    'success':              'cancel reservation success!',
    'missing_key':          'cancel reservation failed: no citizen id is given',
    'invalid_id':           'cancel reservation failed: invalid citizen ID',
    'not_registered':       'cancel reservation failed: citizen ID is not registered',
    'not_reservation':      'cancel reservation failed: there is no reservation for this citizen',
    'invalid_reservation':  'cancel reservation failed: couldn\'t find valid reservation'
}

REPORT_FEEDBACK = {
    'success':              'report success!',
    'missing_key':          'report failed: missing some attribute',
    'invalid_id':           'report failed: invalid citizen ID',
    'not_registered':       'report failed: citizen ID is not registered',
    'invalid_time':         'report failed: can only reserve vaccine in the future',
    'invalid_time_format':  'report failed: invalid queue datetime format',
    'invalid_reservation':  'report failed: couldn\'t find valid reservation',
    'invalid_vaccine':      'report failed: invalid vaccine name',
    'has_reservation':      'report failed: before walk-in, citizen need to cancel other reservation',
    'not_reservation':      'report failed: there is no reservation for this citizen',
    'not_match_vaccine':    'report failed: vaccine_name not match reservation',
    'invalid_option':       'report failed: option need to be neither "reserve" or "walk-in"',
    'other':                'report failed: something go wrong, please contact admin'
}

DELETE_FEEDBACK = {
    'success_reset':        'all citizens have been deleted',
    'fail_reset':           'failed to reset citizen database',
    'fail_delete':          'failed to delete citizen',
    'invalid_id':           'delete failed: invalid citizen ID',
    'not_registered':       'delete failed: citizen ID is not registered'
}

REGISTER_USER_FEEDBACK = {
    "successful_registration" : "new user created successfully",
    "failed_registration" : "registration failed: unable to register a new user",
    "duplicated_registration" : "registration failed: user already exists"
}

# LOGIN_FEEDBACK = {

# }

AUTHENTICATION_FEEDBACK = {
    "unauthenticated" : "no permissions allowed for this user"
}