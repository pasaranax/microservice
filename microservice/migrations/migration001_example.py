from microservice.models import connection


class Migration:
    version = 1

    def __init__(self):
        connection.execute_sql("""
        SELECT 'Default statement timeout is 60000 ms';
        """)
