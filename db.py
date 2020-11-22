import datetime
from django.db import transaction, DatabaseError

def fetch_phillips_bridges(conn):
    """
    Fetch all bridges
    :param conn:
    :param id:
    :return:
    """

    sql = ''' SELECT * FROM "eranaAPI_item" WHERE "item_type" = 'phillips_hue_bridge' ORDER BY item_type ; '''

    try:
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        print(f"[ERROR]: Fetch phillips hue bridges - {e}")

def fetch_phillips_active_bridge(conn):
    """
    Fetch active bridge
    :param conn:
    :return:
    """
    
    sql = ''' SELECT access_token, ip_address FROM "eranaAPI_item" WHERE "item_type" = 'phillips_hue_bridge' AND "is_active" = 'true' ; '''
    
    try:
        cur = conn.cursor()
        cur.execute(sql, ())
        access_token, ip_address = cur.fetchone()
        return access_token, ip_address
    except Exception as e:
        print(f"[ERROR]: Fetch active bridge - {e}")
        return None, None

def save_phillips_active_bridge_state(conn, username, value):
    """
    Create a new bridge is_active state
    :param conn:
    :param username:
    :param value:
    :return:
    """
    truthy = bool(value)
    data_tuple = (truthy, username)

    sql = ''' UPDATE "eranaAPI_item" SET is_active = %s WHERE "username" = %s AND "item_type" = 'phillips_hue_bridge'
              VALUES(%s, %s) RETURNING id ; '''

    try:
        cur = conn.cursor()
        cur.execute(sql, data_tuple)
        conn.commit()
        data = cur.fetchone()[0]
        return data
    except DatabaseError as d:
        print(f"[ERROR]: Save phillips active bridge state DB Error - {d}")
        transaction.rollback()
    except Exception as e:
        print(f"[ERROR]: Save phillips active bridge active state - {e}")

def save_phillips_bridge_ip(conn, ip, username):
    """
    Create a new bridge is_active state
    :param conn:
    :param username:
    :param ip:
    :return:
    """
    data_tuple = (ip, username)

    sql = ''' UPDATE "eranaAPI_item" SET ip = %s WHERE "username" = %s AND "item_type" = 'phillips_hue_bridge' RETURNING id ;'''

    try:
        cur = conn.cursor()
        cur.execute(sql, data_tuple)
        conn.commit()
        data = cur.fetchone()[0]
        return data
    except DatabaseError as d:
        print(f"[ERROR]: Save phillips active bridge ip DB Error - {d}")
        transaction.rollback()
    except Exception as e:
        print(f"[ERROR]: Save phillips bridge ip - {e}")

def save_brain_status_hue_bridge(conn, status):
    """
    Save the hue_bridge status in the brain status table
    :param conn:
    :param status:
    :return:
    """

    data_tuple = (status, "phillips_hue_bridge_lights")

    sql = ''' UPDATE "eranaAPI_brain_ability" SET status = %s WHERE "ability" = %s RETURNING id; '''

    try:
        cur = conn.cursor()
        cur.execute(sql, data_tuple)
        conn.commit()
        data = cur.fetchone()[0]
        return data
    except DatabaseError as d:
        print(f"[ERROR]: Save phillips brain_status DB Error - {d}")
        transaction.rollback()
    except Exception as e:
        print(f"[ERROR]: Save brain status for hue bridge - {e}")

def delete_phillips_hue_bridge(conn):
    """
    delete bridge information
    :param conn:
    :return:
    """

    sql = ''' DELETE * FROM "eranaAPI_item" WHERE "item_type" = 'phillips_hue_bridge'; '''

    try:
        cur = conn.cursor()
        cur.execute(sql, ())
        return None
    except Exception as e:
        print(f"[ERROR]: Delete hue bridges - {e}")