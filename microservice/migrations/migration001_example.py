from microservice.models import connection


class Migration:
    def __init__(self):
        connection.execute_sql("""
            SELECT 'just example, it's not applying';
        """)
