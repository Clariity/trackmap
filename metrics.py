import sqlite3 as lite
import numpy

def convert_seconds(time): #seconds from midnight
    hours = time.split(":")[0]
    minutes = time.split(":")[1]
    seconds = time.split(":")[2]
    return (int(hours)*60*60) + (int(minutes)*60) + int(seconds)

def get_average(): #returns int for average overall time
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.executescript("DROP TABLE IF EXISTS averages; CREATE TABLE averages(mac_address VARCHAR, seconds INT);")
        conn.commit()
        c.execute("SELECT DISTINCT(mac_address) FROM data;")
        addresses = c.fetchall()
        results = []
        for address in addresses:
            c.execute("SELECT timestamp, info FROM data WHERE mac_address = ? ORDER BY timestamp;", address)
            rows = c.fetchall()
            stay_lengths = []
            start_time = end_time = int(convert_seconds(rows[0][0]))
            for i in range(len(rows)):
                if i > 0:
                    if int(convert_seconds(rows[i][0])) - int(convert_seconds(rows[i-1][0])) > 120:
                       stay_lengths.append(end_time - start_time)
                       start_time = end_time = int(convert_seconds(rows[i][0]))
                    else:
                        end_time = int(convert_seconds(rows[i][0]))
            stay_lengths.append(end_time - start_time)
            average = numpy.average(stay_lengths)
            results.append((address[0], average))
        c.executemany("INSERT INTO averages VALUES (?,?);", results)
        conn.commit()
        c.execute("SELECT AVG(seconds) FROM averages WHERE seconds > 1;")
        print(int(c.fetchone()[0]))
        conn.close()
    except Exception as e: print(e)
    
def get_no_of_users(): #returns int for no. of visitors
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT(mac_address)) FROM data;")
        print(int(c.fetchone()[0]))
        conn.close()
    except Exception as e: print(e)
    
def get_users_only_info(): #returns array of tuples [info, mac]
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT(info), mac_address FROM data WHERE info != \"()\";")
        return c.fetchall()
    except Exception as e: print(e)
    
def get_users_info(): #returns array of tuples [info, mac]
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT(info), mac_address FROM data;")
        return c.fetchall()
    except Exception as e: print(e)
    
def get_user_averages(): #returns array of tuples [mac, average time in seconds]
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT mac_address, seconds FROM averages;")
        return c.fetchall()
    except Exception as e: print(e)
    
def get_positions(): #returns array of tuples [mac, timestamp, x, y]
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT mac_address, timestamp, x, y  FROM data WHERE ap1 != "" AND ap2 != "" AND ap3 != "";)
        return c.fetchall()
    except Exception as e: print(e)
    
#python3 load.py 9.0 17.0 25.0 7.5 7.5 10.0