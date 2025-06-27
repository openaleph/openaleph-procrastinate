[![Python test and package](https://github.com/openaleph/openaleph-procrastinate/actions/workflows/python.yml/badge.svg)](https://github.com/openaleph/openaleph-procrastinate/actions/workflows/python.yml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Coverage Status](https://coveralls.io/repos/github/openaleph/openaleph-procrastinate/badge.svg?branch=main)](https://coveralls.io/github/openaleph/openaleph-procrastinate?branch=main)
[![AGPLv3+ License](https://img.shields.io/pypi/l/openaleph-procrastinate)](./LICENSE)

# OpenAleph Procrastinate

The most dumbest task queue for [OpenAleph](https://openaleph.org) based on [procrastinate](https://procrastinate.readthedocs.io/en/stable/)

## Documentation

https://openaleph.org/docs/lib/openaleph-procrastinate

## Development

This package is using [poetry](https://python-poetry.org/) for packaging and dependencies management, so first [install it](https://python-poetry.org/docs/#installation).

Clone this repository to a local destination.

Within the repo directory, run

    poetry install --with dev

This installs a few development dependencies, including [pre-commit](https://pre-commit.com/) which needs to be registered:

    poetry run pre-commit install

Before creating a commit, this checks for correct code formatting (isort, black) and some other useful stuff (see: `.pre-commit-config.yaml`)

### requirements.txt

To lock dependencies, we use `poetry lock` and a pre-commit hook that exports the lockfile to `requirements.txt`. Always make sure to check in the lockfile when adding packages.

## License and Copyright

`openaleph-procrastinate`, (C) 2025 [Data and Research Center – DARC](https://dataresearchcenter.org)

`openaleph-procrastinate` is licensed under the AGPLv3 or later license.

see [NOTICE](./NOTICE) and [LICENSE](./LICENSE)
