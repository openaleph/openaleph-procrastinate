import psycopg

from openaleph_procrastinate.settings import OpenAlephSettings


def get_status() -> dict:
    settings = OpenAlephSettings()
    db_uri = settings.procrastinate_db_uri

    status = {}
    jobs_data = []

    with psycopg.connect(db_uri) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT count(*) as number_of_jobs, (args->>'dataset') as dataset, status, queue_name FROM procrastinate_jobs GROUP BY (args->>'dataset'), status, queue_name"""
            )
            jobs_data = cursor.fetchall()

    for job_data in jobs_data:
        number_of_jobs = job_data[0]
        collection_id = job_data[1]
        job_status = job_data[2]
        stage = job_data[3]
        if collection_id in status:
            status[collection_id].append(
                {
                    "stage": stage,
                    "number_of_jobs": number_of_jobs,
                    "status_of_jobs": job_status,
                }
            )
        else:
            status[collection_id] = [
                {
                    "stage": stage,
                    "number_of_jobs": number_of_jobs,
                    "status_of_jobs": job_status,
                }
            ]

    return status
