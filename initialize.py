import os
import schedule

import db.pgsql_db_utils_create as dbUtils_create
import db.pgsql_db_utils_read as dbUtils_read
from db.pgsql_db_utils import create_connection_from_file

from .main import PhillipsHueBridgeLight
from .db import *
from .scheduler import PhillipsHueBridgeLightScheduler

def initialize_system():
     # Load Postgres connection
    conn = create_connection_from_file()

    # Confirm we have a valid Hue Bridge, config Hue 
    # Make sure we have an initial state to compare our light status
    light_control = PhillipsHueBridgeLight(conn)
    save_brain_status_hue_bridge(conn, "Discovery")

    try:
        light_control.bridge_connect() 
        save_brain_status_hue_bridge(conn, "Connected")
    except:
        light_control.scan_for_bridge()

    light_scheduler = PhillipsHueBridgeLightScheduler(conn)

    # Not sure if the scheduler picks up all schedules globally. Will have to check.
    schedule.every().day.at(os.getenv("STARTING_DAY_STATUS")).do(light_control.get_all_lights_status)

    return light_control