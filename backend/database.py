import psycopg2

from settings import settings


def get_connection():
    connection = psycopg2.connect(settings.DATABASE_URL)
    return connection