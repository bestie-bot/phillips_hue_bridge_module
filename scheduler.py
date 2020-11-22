import os
import db.pgsql_db_utils_read as dbUtils_read


class PhillipsHueBridgeLightScheduler():
    """
    Handles all light scheduling functionality

    Parameters
    ----------
    `conn <database connection>`
    The connection to the main Postgres database
    """
    def __init__(self, conn):
        self.conn = conn        
        print(f"[INFO]: Initialized Phillips Hue Bridge Lights scheduler module")

    def get_scheduled_lights(self):
        """
        Returns all the values from the database.

        Returns
        ----------
        `scheduled lights array <array>`\n
        An object of all the scheduled lights in the form (id, time, status, light_id):\n 
        [
            (1, '2020-07-27 18:00:00', 1, 38),
            (2, '2020-07-27 18:01:00', 0, 38),'
            (3, '2020-07-27 18:00:00', 0, 12),
            (4, '2020-07-27 18:05:00', 1, 1)
        ]
        """
        try:
            predictions = dbUtils_read.fetch_scheduled_light_predictions(self.conn)
            return predictions
        except:
            print(f"[ERROR]: Error retrieving scheduled predictions")
            

    