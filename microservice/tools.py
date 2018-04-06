#!/usr/bin/env python3
import logging
import pkgutil
import sys

import migrations
from microservice.models import Schema, ACTUAL_VERSION, connection


def migrate():
    """
    Find all files in migrations directory and run it
    """
    # migration001_example.Migration()
    current_version = int(Schema.get(key="version").value)
    if current_version < ACTUAL_VERSION:
        logging.info("Schema needs to be updated {} -> {}".format(current_version, ACTUAL_VERSION))
        for loader, name, _ in pkgutil.walk_packages(migrations.__path__):
            Migration = loader.find_module(name).load_module(name).Migration

            # separate migration
            version = Schema.get(key="version")
            version.value = int(version.value)
            if version.value == Migration.version - 1 and version.value < ACTUAL_VERSION:
                connection.execute_sql("SET STATEMENT_TIMEOUT TO 60000;")
                with connection.atomic():
                    try:
                        logging.info("Updating to version {}: {}".format(Migration.version, name))
                        Migration()
                    except Exception as e:
                        logging.error("Failed on step {}: {}. "
                                      "Rolling back because of error: {}".format(Migration.version, name, e))
                        connection.rollback()
                        exit(1)
                    else:
                        version.value = Migration.version
                        version.save()

    current_version = Schema.get(key="version").value
    logging.info("Schema version is: {}".format(current_version))


if __name__ == '__main__':
    _, func, *args = sys.argv
    globals()[func](*args)
    logging.info("Done")
