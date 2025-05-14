FROM ghcr.io/dataresearchcenter/ftmq:latest

COPY openaleph_procrastinate /app/openaleph_procrastinate
COPY setup.py /app/setup.py
COPY pyproject.toml /app/pyproject.toml
COPY VERSION /app/VERSION
COPY README.md /app/README.md

WORKDIR /app
RUN pip install gunicorn
RUN pip install ".[django]"
RUN pip install psycopg-binary

ENV PROCRASTINATE_APP="openaleph_procrastinate.app.app"

USER 1000
ENTRYPOINT ["gunicorn", "openaleph_procrastinate.wsgi", "--bind", "0.0.0.0:8000"]
