# Government APIs

## Installation

Create .env file

```.env
DEBUG=True
SQLALCHEMY_DATABASE_URI=postgresql://<USERNAME>:<PASSEORD>@localhost/government
```

Run [app.py](app/app.py)

## APIs

- [/index](https://wcg-apis.herokuapp.com)

- [/registration](https://wcg-apis.herokuapp.com/registration)

  - GET: API usage, detail, format
  - POST: add a person data to database 'citizen'
    ![alt text](static/images/registration.png)

- [/citizen](https://wcg-apis.herokuapp.com/citizen)
  - GET: check citizen table
  - DELETE: reset citizen table (delete all rows)

## Basic CMD

```zsh
# install dependencies
$ pipenv shell
# install pip to pipFile
$ pipenv install <PACKAGE_NAME>

# create requirements.txt
$ pip freeze > requirements.txt
```

```python shell
# initial database
> from app import db
> db.create_all()
```
