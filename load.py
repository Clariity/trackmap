import sqlite3 as lite
import math
import numpy
import sys

def setup():
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.executescript("DROP TABLE IF EXISTS ap1; DROP TABLE IF EXISTS ap2; DROP TABLE IF EXISTS ap3; DROP TABLE IF EXISTS data;")
        for i in range(1,4):
            c.execute("CREATE TABLE ap" + str(i) + """ (mac_address VARCHAR NOT NULL, signal_strength INT NOT NULL, timestamp VARCHAR NOT NULL,
                    prediction FLOAT NULL, info VARCHAR NOT NULL, date VARCHAR NOT NULL, PRIMARY KEY(mac_address, timestamp, date));""")
        c.execute("CREATE TABLE data (mac_address VARCHAR, info VARCHAR, ap1 FLOAT, ap2 FLOAT, ap3 FLOAT, timestamp VARCHAR, x FLOAT, y FLOAT);")
        conn.commit()
        conn.close()
    except Exception as e: print(e)

def load():
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        for i in range(1,4):
            records = []
            f = open("output" + str(i) + ".pcap", "r")
            for line in f:
                try:
                    fields = line.split(" ")
                    if i != 3:
                        record = (fields[14],fields[8].split("dB")[0],fields[0], 0.0, fields[19])
                    else: #catch case for added fields with antenna on ap3
                        record = (fields[16],fields[8].split("dB")[0],fields[0], 0.0, fields[21])
                    records.append(record)
                except: None
            c.executemany("INSERT INTO ap" + str(i) + " VALUES (?,?,?,?,?, date('now'));", records)
            f.close()
        conn.commit()
        conn.close()
    except Exception as e: print(e)
    
def predict():
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        for i in range(1,4):
            c.execute("SELECT mac_address, signal_strength, timestamp FROM ap" + str(i)+ ";")
            rows = c.fetchall()
            records = []
            for row in rows:
                distance = 10**((27.55 - (20 * math.log(2462, 10)) + float(abs(row[1]))) / 20)
                record = (distance, row[0], row[2])
                records.append(record)
            c.executemany("UPDATE ap" + str(i) + " SET prediction = ? WHERE mac_address = ? AND timestamp = ?;", records)
        conn.commit()
        conn.close()   
    except Exception as e: print(e)

def is_outlier(value, distances):
    data = numpy.array(distances)
    if len(distances) == 1:
        return False
    m = numpy.median(distances)
    d = []
    for distance in distances:
        d.append(numpy.abs(distance - m))
    mdev = numpy.median(d)
    if mdev == 0:
        mdev = 1e-6
    for i in range(len(d)):
        if d[i] / mdev > 1:
            return distances[i] == value
    return False 
    
def remove_outliers(rows):
    time_groups = {} #time group -> [distances]
    times_map = {} #time -> time_group
    new_rows = []
    for row in rows:
        time = convert_seconds(row[2])
        added = False
        for key in time_groups.keys():
            if abs(int(key) - time) < 5: #if time is within 5 seconds
                time_groups[key].append(row[1])
                times_map[str(time)] = key
                added = True 
        if not added:
            time_groups[str(time)] = [row[1]] #new time group
            times_map[str(time)] = time
    for row in rows:
        if not is_outlier(row[1], time_groups[str(times_map[str(convert_seconds(row[2]))])]):
            new_rows.append(row)
    return new_rows
    
def convert_seconds(time): #seconds from midnight
    hours = time.split(":")[0]
    minutes = time.split(":")[1]
    seconds = time.split(":")[2]
    return (int(hours)*60*60) + (int(minutes)*60) + int(seconds)

def revert_seconds(time): #seconds from midnight
    hours = str((time / 60) / 60).split(".")[0]
    remainder = time - (int(hours) * 60 * 60)
    minutes = str(remainder / 60).split(".")[0]
    seconds = str(time - (int(hours) * 60 * 60) - (int(minutes) * 60))
    if int(seconds) < 10:
        seconds = "0" + seconds
    return str(hours + ":" + minutes + ":" + seconds)
    
def check_time(keep_rows, row): #keep_rows = (mac_address, average prediction, seconds from midnight, original time HH:MM:SS, number of time repeats, running total)
    time = convert_seconds(row[2])
    if len(keep_rows) > 0:
        for i in range(len(keep_rows)):
            if abs(keep_rows[i][2] - time) < 5: #if time is within 5 seconds
                count = keep_rows[i][4] + 1
                total = keep_rows[i][5] + row[1]
                average = total / count
                copy = (keep_rows[i][0], average, keep_rows[i][2], keep_rows[i][3], count, total, keep_rows[i][6])
                keep_rows[i] = copy
                return keep_rows
        keep_rows.append((row[0], row[1], time, row[2], 1, row[1], row[3]))
        return keep_rows
    else: #first entry
        keep_rows.append((row[0], row[1], time, row[2], 1, row[1], row[3]))
    return keep_rows
    
def clean():
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        for i in range(1,4):
            print("cleaning data from ap" + str(i))
            c.execute("SELECT DISTINCT(mac_address) FROM ap" + str(i) + ";")
            addresses = c.fetchall()
            for address in addresses:
                c.execute("SELECT mac_address, prediction, timestamp, info FROM ap" + str(i) + " WHERE mac_address = ?;", address)
                rows = c.fetchall()
                keep_rows = []
                for j in range(len(rows)): #set new timestamp
                    time = rows[j][2].split('.')[0]
                    new_row = (rows[j][0], rows[j][1], time, rows[j][3])
                    rows[j] = new_row
                rows = remove_outliers(rows)
                for row in rows:
                    copy = check_time(keep_rows, row) #see if row matches a time in keep_rows and average prediction, else add new keep_row with new time
                    keep_rows = copy
                for k in keep_rows:
                    time = revert_seconds(k[2])
                    c.execute("SELECT * FROM data WHERE mac_address = ? AND timestamp = ?;", (k[0], time))
                    if c.fetchone() == None:
                        c.execute("INSERT INTO data(mac_address, info, ap" + str(i) + ", timestamp) VALUES (?,?,?,?);", (k[0], k[6], k[1], time))
                        conn.commit()
                    else:
                        c.execute("UPDATE data SET ap" + str(i) + " = ? WHERE mac_address = ? AND timestamp = ?;", (k[1], k[0], time))
                        conn.commit()
        conn.close()
    except Exception as e: print("ERROR: ",e)

def trilaterate():
    ar1_x = float(sys.argv[1])
    ar1_y = float(sys.argv[2])
    ar2_x = float(sys.argv[3])
    ar2_y = float(sys.argv[4])
    ar3_x = float(sys.argv[5])
    ar3_y = float(sys.argv[6])
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT mac_address, ap1, ap2, ap3, timestamp FROM data;")
        rows = c.fetchall()
        for row in rows:
            if row[1] != None and row[2] != None and row[3] != None:
                s = (math.pow(ar3_x, 2.) - math.pow(ar2_x, 2.) + math.pow(ar3_y, 2.) - math.pow(ar2_y, 2.) + math.pow(row[2], 2.) - math.pow(row[3], 2.)) / 2.0
                t = (math.pow(ar1_x, 2.) - math.pow(ar2_x, 2.) + math.pow(ar1_y, 2.) - math.pow(ar2_y, 2.) + math.pow(row[2], 2.) - math.pow(row[1], 2.)) / 2.0
                y = ((t * (ar2_x - ar3_x)) - (s * (ar2_x - ar1_x))) / (((ar1_y - ar2_y) * (ar2_x - ar3_x)) - ((ar3_y - ar2_y) * (ar2_x - ar1_x)))
                x = ((y * (ar1_y - ar2_y)) - t) / (ar2_x - ar1_x)
                if x < 100.0 and x > -100.0 and y < 100.0 and y > -100.0:
                    c.execute("UPDATE data SET x = ?, y = ? WHERE mac_address = ? AND timestamp = ?;", (x, y, row[0], row[4]))
                    conn.commit()
                else:
                    c.execute("DELETE FROM data WHERE mac_address = ? AND timestamp = ?;", (row[0], row[4]))
                    conn.commit()
        conn.close
        print("DONE")
    except Exception as e: print(e)

def trilaterate1():
    earthR = 6371
    LatA = float(sys.argv[1])
    LonA = float(sys.argv[2])
    LatB = float(sys.argv[3])
    LonB = float(sys.argv[4])
    LatC = float(sys.argv[5])
    LonC = float(sys.argv[6])
    try:
        conn = lite.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT * FROM data;")
        rows = c.fetchall()
        for row in rows:
            if row[1] != None and row[2] != None and row[3] != None:
                print("SUCCESS " + str(row))
                xA = earthR * (math.cos(math.radians(LatA)) * math.cos(math.radians(LonA)))
                yA = earthR * (math.cos(math.radians(LatA)) * math.sin(math.radians(LonA)))
                zA = earthR * (math.sin(math.radians(LatA)))
                xB = earthR * (math.cos(math.radians(LatB)) * math.cos(math.radians(LonB)))
                yB = earthR * (math.cos(math.radians(LatB)) * math.sin(math.radians(LonB)))
                zB = earthR * (math.sin(math.radians(LatB)))
                xC = earthR * (math.cos(math.radians(LatC)) * math.cos(math.radians(LonC)))
                yC = earthR * (math.cos(math.radians(LatC)) * math.sin(math.radians(LonC)))
                zC = earthR * (math.sin(math.radians(LatC)))
                P1 = numpy.array([xA, yA, zA])
                P2 = numpy.array([xB, yB, zB])
                P3 = numpy.array([xC, yC, zC])
                ex = (P2 - P1) / (numpy.linalg.norm(P2 - P1))
                i = numpy.dot(ex, P3 - P1)
                ey = (P3 - P1 - i * ex) / (numpy.linalg.norm(P3 - P1 - i * ex))
                ez = numpy.cross(ex, ey)
                d = numpy.linalg.norm(P2 - P1)
                j = numpy.dot(ey, P3 - P1)
                x = (pow(row[1], 2) - pow(row[2], 2) + pow(d, 2)) / (2 * d)
                y = ((pow(row[1], 2) - pow(row[3], 2) + pow(i, 2) + pow(j, 2)) / (2 * j)) - ((i / j) * x)
                z = numpy.sqrt(abs(pow(row[1], 2) - pow(x, 2) - pow(y, 2)))
                triPt = P1 + x * ex + y * ey + z * ez
                
                print(triPt[2])
                print(triPt[2] / earthR)
                print(math.asin(triPt[2] / earthR))
                lat = math.degrees(math.asin(triPt[2] / earthR))
                lon = math.degrees(math.atan2(triPt[1], triPt[0]))
                
                c.execute("UPDATE data SET lat = ?, lon = ? WHERE mac_address = ? AND timestamp = ?;", (lat, lon, row[0], row[4]))
                conn.commit()
        conn.close
        print("DONE")
    except Exception as e: print(e)
    
if __name__ == '__main__':
    print("RUNNING SETUP")
    setup()
    print("LOADING DATA")
    load()
    print("PREDICTING DISTANCES")
    predict()
    print("CLEANING DATA")
    clean()
    print("TRILATERATING")
    trilaterate()