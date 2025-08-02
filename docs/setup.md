# Setup

This guide describes the setup of the `openaleph-procrastinate` app and mainly the [Django integration](https://procrastinate.readthedocs.io/en/stable/howto/django.html) that can be used to explore job statistics.

## Installation

Install [`openaleph-procrastinate`](https://github.com/openaleph/openaleph-procrastinate) with its Django requirements:

pip:

    pip install openaleph-procrastinate

poetry:

    poetry add openaleph-procrastinate

This will include all the required dependencies.

## Configuration

!!! info
    For local development or testing, set the environment variable `DEBUG=1` to use an in-memory task backend instead of postgresql.

The **OpenAleph** settings are configured via environment vars via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

For a full list of `openaleph-procrastinate` settings, refer to the [settings reference](./reference/settings.md).

### Database

Set up the environment variable `PROCRASTINATE_DB_URI` which falls back to `OPENALEPH_DB_URI` (default: `postgresql:///openaleph`).

### Initial database setup

    opal-procrastinate init-db

## Optional: Django integration

Django can be installed as an optional dependency to use the Django admin for better task status visibility.

pip:

    pip install openaleph-procrastinate[django]

poetry:

    poetry add openaleph-procrastinate[django]

This will include all the required Django dependencies.

[More information on Django settings.py](https://docs.djangoproject.com/en/5.2/topics/settings/)

[The full list of settings and their values](https://docs.djangoproject.com/en/5.2/ref/settings/)

### Initial database setup

**Don't use the [procrastinate database setup](https://procrastinate.readthedocs.io/en/stable/quickstart.html#prepare-the-database).**

Instead, as `procrastinate` is already configured in the Django app, use the Django database migrations:

    ./manage.py migrate

This will create the Django database tables as well as the procrastinate tables.

Create an admin user to visit the dashboard:

    ./manage.py createsuperuser


### Run the django app

Run the development server:

    ./manage.py runserver

Visit the admin dashboard at [http://localhost:8000/admin/](http://localhost:8000/admin/)
