import os
from qhue import Bridge
from ratelimiter import RateLimiter
from request_ssdp import request_ssdp_by_key
import time
import datetime
import logging
import requests 
import json
from requests.exceptions import HTTPError

import db.pgsql_db_utils as dbUtils
import db.pgsql_db_utils_create as dbUtils_create
import db.pgsql_db_utils_read as dbUtils_read
import db.pgsql_db_utils_delete as dbUtils_delete

from .db import delete_phillips_hue_bridge, save_brain_status_hue_bridge, fetch_phillips_bridges, fetch_phillips_active_bridge

class PhillipsHueBridgeLight():
    """
    Controls the interactions with the Hue Bridge and light

    Parameters
    ----------
    `conn <database connection>`
    The connection to the main Postgres database
    """
    def __init__(self, conn):
        self.conn = conn        

        # Set up current logging mechanism
        self.log = logging.getLogger('modules')
        self.log.debug("[INFO]: Initialized Phillips Hue Bridge Lights main module")

    def authorize_bridge(self, ip):
        """
        Gets the authorization token from the bridge if the button is pressed. If the button is not
        pressed, handles the unauthorized response and returns None for a token.

        Returns
        ----------
        `Username <string>`
        A username token if authorized, else `None`
        """

        save_brain_status_hue_bridge(self.conn, "Discovery")

        url = f'http://{ip}/api'
        payload = {"devicetype": "erana-engine#local_user"}
        headers = {'content-type': 'application/json'}

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
        except HTTPError as http_err:
            log.critical(f'[ERROR]: HTTP error occurred: {http_err}')
            save_brain_status_hue_bridge(self.conn, "Not Found")
            return
        except Exception as err:
            self.log.error(f'[ERROR]: Other error occurred: {err}')
            save_brain_status_hue_bridge(self.conn, "Not Found")
            return
        
        response_object = response.json()

        for item in response_object:
            for key, value in item.items():
                if key == 'error':
                    # Is user ends up here, they can access the bridge, but it's sending back
                    # an error that the button is not pressed. Let's tell the user
                    # about our unauthorized state
                    save_brain_status_hue_bridge(self.conn, "Not Authorized")
                    time.sleep(5)
                    return
                elif key == 'success':
                    # The button is pushed and we got a value
                    self.log.debug("[INFO]: Successfully authorized and received token")
                    username = value['username']
                    return username

    
    def scan_for_bridge(self):
        """
        Searches for Phillips Hue bridges via SSDP. If it finds one, it will take the bridge IP, 
        check if the bridge previously existed at another IP, and update it. If it did not exist,
        it will go through checks and update old bridges to active_state:False, and create a new 
        active Phillips Hue Bridge. It returns a connection to the proper bridge.

        Note that if the system can NOT find a Hue Bridge via SSDP, it will continuously loop.

        Returns
        ----------
        `Phillips Hue Bridge <bridge>`
        A valid Phillips Hue Bridge object

        If there is an error, it restarts the function. 

        """
        save_brain_status_hue_bridge(self.conn, "Not Found")

        try:
            # Get the real ip and bridge id by passing in the key we locate it with, port, and any extra
            # keys to return besides the IP
            real_ip, unique_bridge_id_array = request_ssdp_by_key("hue-bridgeid", "80", ["hue-bridgeid"])
        except Exception as err:
            self.log.error(f'[ERROR]: Error on SSDP request: {err}')
            save_brain_status_hue_bridge(self.conn, "Not Found")
            time.sleep(5)
            return
        
        # Let's also add this here in case there is no error, just a null value return
        if real_ip == None or real_ip == '':
            self.log.error(f'[ERROR]: No error, and no return value on SSDP request')
            save_brain_status_hue_bridge(self.conn, "Not Found")
            time.sleep(5)
            return

        # Let's try getting any info first to see if the connection exists
        try:
            testing_url = f'http://{real_ip}/api/v1/'
            testing_response = requests.get(testing_url)
            testing_response_object = testing_response.json()

            # if we got an error reponse, we know the device is on
            # and we can't access it. If we get an unauthorized user
            # return, we know to request a button push from the user
            if testing_response_object is not None:
                # Otherwise, if we can't just restart, then we need to authorize
                token = self.authorize_bridge(real_ip)

                if token is not None:
                    # Check if other bridges exist.
                    try:
                        bridge_list = fetch_phillips_bridges(self.conn)
                    except:
                        bridge_list = []

                    # If there are old bridges in the DB, delete them for now
                    if(len(bridge_list) > 0):
                        for bridge in bridge_list:
                            delete_phillips_hue_bridge(self.conn)
                    
                    # Let's create the new bridge
                    try:
                        # Ok, let's connect to the new bridge and save brain status
                        dbUtils_create.create_item(
                            self.conn,
                            ip_address=real_ip,
                            access_token=token,
                            is_active=True,
                            item_type="phillips_hue_bridge",
                            manufacturer = "Phillips Manufacturing",
                            name = "Phillips Hue Bridge",
                            energy_watts = 1.6792,
                            unique_id = unique_bridge_id_array[0]['hue-bridgeid']
                        )
                        return
                    except:
                        log.warning("[ERROR]: Challenge saving states in lights.py")
        except:
            self.log.error("[ERROR]: Scan for bridge completely failed. Let's sleep.")
            # We're not able to connect to it at all
            time.sleep(5)
            raise

    def bridge_connect(self):
        """
        Connects to the Hue Bridge
        """

        access_token, ip = fetch_phillips_active_bridge(self.conn)

        if access_token and ip is not None:
            try:
                b = Bridge(ip, access_token)
                return b
            except:
                raise
        else:
            self.log.error(f"[ERROR]: Error connecting to Phillips Bridge")
            try:
                self.scan_for_bridge()
                return
            except:
                raise
            
    def get_lights(self, bridge):
        """
        Returns all the lights directly from the Hue bridge connection.

        Returns
        ----------
        `lights object <dictionary>`
        An object of all the lights in the form {1: {data}, 2: {data}, etc...}
        
        If there is an error, it returns an empty object {}
        
        """
        try:
            lights = bridge.lights
            lights_object = lights()
            save_brain_status_hue_bridge(self.conn, "Connected")
            return lights_object
        except Exception as err:
            self.log.error(f"[ERROR]: Error retrieving lights object from PhillipsHueBridgeLight.get_lights at {datetime.datetime.now()}")
            save_brain_status_hue_bridge(self.conn, "Not Found")
            return {}

    def toggle_light(self, unique_id, state, bridge):
        """
        Toggles the light to a specific state.

        Parameters
        ----------
        `unique_id <string>`
        The unique_id from the device, usually a MAC address

        `state <boolean>`
        The state to toggle. Either `True` or `False` for `on` or `off`

        Returns
        ----------
        Void
        """
        lights = self.get_lights()

        try:
            for key, value in lights.items():
                if value["uniqueid"] == unique_id:
                    bridge.lights[key].state(on=state)
                    self.log.debug(f"[INFO]: Light {key} \"on\" status is now {state}")
                    break
        except:
            self.log.error(f"[ERROR]: Error changing state of light {unique_id} to {state}")
    
    @RateLimiter(max_calls=1, period=1)
    def _determine_changed_lights(self, old_state):
        b = self.bridge_connect()
        lights = self.get_lights(b)
        
        # If this is the startup, then simply return the lights so it can be put in old state
        lights_array = []

        # Probably should be changed to a recursive loop for speed
        if bool(lights) is True:
            for new_key, new_light in lights.items():
                for old_key, old_light in old_state.items():
                    if new_light["uniqueid"] == old_light["uniqueid"]:
                        if (new_light["state"]["on"] != old_light["state"]["on"] or new_light["state"]["reachable"] != old_light["state"]["reachable"]):
                            # We changed this to name because the iOS ability to grab
                            # by serial number is now deprecated. After all, why would Apple
                            # allow you to make useful things?
                            lights_array.append({ "uniqueid": new_light["name"], "on": new_light["state"]["on"], "reachable": new_light["state"]["reachable"] })
                            break
                    else:
                        pass
        
        return lights_array, lights

    def get_all_lights_status(self):
        """
        saves the light status for all the current lights in the database

        Returns
        ----------
        Status<string>: Whether successful or not
        """
        try:
            lights = self.get_lights()
            event_time = datetime.datetime.now()

            if bool(lights) is True:
                for light in lights:
                    current_light = lights[light]

                    try:
                        unique_id = current_light["uniqueid"]
                        light_id = dbUtils_read.fetch_item(self.conn, unique_id)
                        
                        if light_id is not None:
                            dbUtils_create.create_action(self.conn, event_time, current_light["state"]["on"], current_light["state"]["reachable"], light_id)
                        else:
                            self.log.error(f"[ERROR]: Daily save at {event_time}. Light {unique_id} does not exist in the current db.")
                    except:
                        self.log.error(f"[ERROR]: Saving daily light status for {unique_id} on {event_time}")

            self.log.debug(f"[INFO]: Daily save successfully completed at {event_time}")

        except:
            self.log.error(f"[ERROR]: Error saving daily values.")
    
    def run(self):
        """
        Runs the continuous scans of Phillips Hue Bridge to get light data.

        Returns:
        ------
        `Void`

        """
        # log = logging.getLogger('modules')
        b = self.bridge_connect()
        old_state = self.get_lights(b)

        self.log.debug(f'[INFO]: Running {b}')


        while True:
            if b is not None:
                changed_lights, lights_object = self._determine_changed_lights(old_state)

                if len(changed_lights) == 0:
                    self.log.debug(f'[INFO]: No changed lights')
                    continue
                else:
                    # Get current time so it's same for all lights
                    event_time = datetime.datetime.now()
                    
                    # Narrowing down the error states using try/except to establish failure locations
                    for light in changed_lights:
                        self.log.debug(f"lights {light}")
                        try:
                            unique_id = light["uniqueid"]
                            light_id = dbUtils_read.fetch_item(self.conn, unique_id)

                        except:
                            # transliteration doesn't work with object keys it seems
                            on = light["on"]
                            reachable = light["reachable"]
                            light_id = light["id"]
                            self.log.error(f"[ERROR]: Fetching light_id and unique id for {unique_id} at {event_time} in main.py. \n Light on: {on} \n Light reachable: {reachable} \n Light id: {light_id}")
                            
                        try:
                            if light_id is not None:
                                dbUtils_create.create_action(self.conn, event_time=event_time, has_value=0.0, is_on=light["on"], is_reachable=light["reachable"], item_id=light_id)
                                self.log.debug(f"[INFO]: Light event recorded at {event_time} for {unique_id}")
                            else:
                                self.log.error(f"[Error]: Light_id is none for {unique_id}")
                                continue
                        except:
                            # transliteration doesn't work with object keys it seems
                            on = light["on"]
                            reachable = light["reachable"]
                            light_id = light["id"]
                            self.log.error(f"[ERROR]: Creating light event for {unique_id} at {event_time} in main.py. \n Light on: {on} \n Light reachable: {reachable} \n Light id: {light_id}")

                        try:
                            old_state = lights_object
                        except:
                            self.log.error(f"[Error]: Saving new state failed at {event_time}")
            else:
                b = self.bridge_connect()