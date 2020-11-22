import db.pgsql_db_utils_create as dbUtils_create
import db.pgsql_db_utils_read as dbUtils_read
from db.pgsql_db_utils import create_connection_from_file

def run_setup():
    """
    This should setup all the information required to run the module in the main thread.

    Returns
    ----------
    `bridge`: The class object instanstiated and ready to receive a command to `.run()` from the main thread and process  
    """
     # Load Postgres connection
    conn = create_connection_from_file()

    # Create the ability for the brain
    try:
        name = dbUtils_read.fetch_brain_ability(conn, "phillips_hue_bridge_lights")
        
        if not name:
            # Create the ability
            dbUtils_create.create_brain_ability(
                conn,
                ability="phillips_hue_bridge_lights",
                status="Not Found",
                level="Normal",
                hub_type="phillips_hue_bridge",
                device_type="phillips_hue_bridge_light",
                machine_learning=False)

    except:
        print("[ERROR]: Phillips hue brain ability addition broken.")

