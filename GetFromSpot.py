import urllib.request
from os import path
from datetime import datetime
from ogn.client import AprsClient
from ogn.parser import parse, ParseError
from datetime import datetime, timedelta
from time import sleep
from ctypes import *
import math
import threading
import argparse
import traceback
import csv
import socket
import time
import sys
import os
import os.path
import signal
import atexit
import requests
import xmltodict
import psutil
import logging

def restart_program():
    """Restarts the current program, with file objects and descriptors cleanup"""
    try:
        p = psutil.Process(os.getpid())
        for handler in p.get_open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logging.error(e)
    python = sys.executable
    os.execl(python, python, *sys.argv)

global APRSbeacon

# NEW: Helper function to send each APRS sentence to the API endpoint
def send_to_api(message):
    url = "https://soaringsattracker.com/api/positions/"
    api_key = "soaring_sattracker_api_key_2025_03_18_v1"
    headers = {
        'X-API-Key': api_key,
        'HTTP_X_API_KEY': api_key
    }
    payload = {"ogn_packet": message}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print("API POST response:", response.status_code)
    except Exception as e:
        print("Error posting to API:", e)

class aircraft():
    def __init__(self):
        self.user = ''
        self.latitude = ''
        self.latitudeNS = ''
        self.longitude = ''
        self.longitudeEW = ''
        self.altitude = ''
        self.groundSpeed = ''
        self.heading = ''
        self.timeUTC = ''
        self.transmissionAge = 10000

class getSPOT():
    def __init__(self, user):
        self.user = user
        self.latitude = ''
        self.latitudeNS = ''
        self.longitude = ''
        self.longitudeEW = ''
        self.altitude = ''
        self.groundSpeed = ''
        self.heading = ''
        self.timeUTC = ''
        self.transmissionAge = 10000
        self.status = ''
        self.ICAO = ''
        
        try:
            url = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/" + user + "/latest.xml"
            response = requests.get(url)
            data = xmltodict.parse(response.content)
        except:
            print('error parsing url:', user)

        try:
            #find latitude
            try:
                lat = data['response']['feedMessageResponse']['messages']['message'][0]['latitude']
            except:
                lat = data['response']['feedMessageResponse']['messages']['message']['latitude']
            lat_f = float(lat)
            lat_d = math.trunc(lat_f)
            if lat_d > 0:
                lat_m = round((lat_f*60) % 60,2)
                self.latitudeNS = 'N'
            else:
                lat_m = round((lat_f*-1*60) % 60,2)
                self.latitudeNS = 'S'
                lat_d = abs(lat_d)
            lat_s = str(lat_d)    
            lat_m_s = "{:.2f}".format(lat_m)
            lat_m_afterDec = lat_m_s[-2:]
            lat_m_o = str(int(lat_m)).zfill(2)
            lat_c = lat_s + lat_m_o + '.' + lat_m_afterDec
            self.latitude = lat_c

            #find longitude
            try:
                lon = data['response']['feedMessageResponse']['messages']['message'][0]['longitude']
            except:
                lon = data['response']['feedMessageResponse']['messages']['message']['longitude']
            lon_f = float(lon)
            lon_d = math.trunc(lon_f)            
            if lon_d > 0:
                lon_m = round((lon_f*60) % 60,2)
                self.longitudeEW = 'E'
            else:
                lon_m = round((lon_f*-1*60) % 60,2)
                self.longitudeEW = 'W'
                lon_d = abs(lon_d)
            lon_s = str(lon_d)
            if abs(lon_d) < 100 and abs(lon_d) > -100:
                lon_s = lon_s.zfill(3)
            lon_m_s = "{:.2f}".format(lon_m)
            lon_m_afterDec = lon_m_s[-2:]
            lon_m_o = str(int(lon_m)).zfill(2)
            lon_c = lon_s + lon_m_o + '.' + lon_m_afterDec
            self.longitude = lon_c

            #find elevation (meters)
            try:
                elev_s = data['response']['feedMessageResponse']['messages']['message'][0]['altitude']
            except:
                elev_s = data['response']['feedMessageResponse']['messages']['message']['altitude']
            elev_f = float(elev_s)
            elev = int(elev_f * 3.28084)
            elev = "{:06d}".format(elev)
            self.altitude = elev

            #find time UTC of transmission
            try:
                timeUTC_time = data['response']['feedMessageResponse']['messages']['message'][0]['unixTime']
            except:
                timeUTC_time = data['response']['feedMessageResponse']['messages']['message']['unixTime']
            timeUTC_time_i = int(timeUTC_time) + 25200
            time_UTC_str = datetime.fromtimestamp(timeUTC_time_i).strftime("%H%M%S")
            timeUTCnow = datetime.utcnow()
            age = timeUTCnow - datetime.fromtimestamp(timeUTC_time_i)
            age_s = age.total_seconds()
            print('----', user, '----', 'Last Transmission:', age, 'ago')
            self.timeUTC = time_UTC_str
            self.transmissionAge = age_s
        except:
            try:
                if data['response']['errors']['error']['code'] == 'E-0195':
                    print(user, 'has no displayable messages')
                    self.status = 'No Messages'
                else:
                    print('***', user, 'user not found')
                    self.status = 'User Not Found'
            except:
                pass
            pass

def openClient():
    global APRSbeacon
    while True:
        try:
            packet_b = sock_file.readline().strip()
            packet_str = packet_b.decode(errors="replace")
            APRSbeacon = parse(packet_str)
            time.sleep(0.01)
        except:
            pass

def WatchDog():
    while True:
        time.sleep(120)
        try:
            r = requests.get('http://glidern3.glidernet.org:14501/status.json')
            print('Scanning APRS server for SPOT connectivity')
            t = r.text
            s = 'SPOTa'
            found = t.find(s)
            if found > 0:
                print('Still connected,', found)
            else:
                print('Not found, restarting program')
                time.sleep(1)
                restart_program()
        except:
            print('error scanning APRS server')
            pass

APRS_SERVER_PUSH = 'glidern3.glidernet.org'
APRS_SERVER_PORT = 14580
APRS_USER_PUSH = 'SPOTa'
BUFFER_SIZE = 1024
APRS_FILTER = 'g/ALL'

traffic_list = []
shortuser = []  # for rapid updates
longuser = []   # for infrequent updates
erroruser = []  # for users with parsing errors

##################################   DISABLED FOR TESTING!!!!!! ##########################
#Get most recent user list from GitHub
urllib.request.urlretrieve("https://soaringsattracker.com/spotcsv", "Spotuser.csv")
print('Downloading Spotuser.csv from https://soaringsattracker.com/spotcsv')
time.sleep(2)
########################

#assign GitHub user list to user
with open('Spotuser.csv', 'r') as read_obj:
    csv_reader = csv.reader(read_obj)
    user = list(csv_reader)
    #print(user)

##connect to the APRS server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((APRS_SERVER_PUSH, APRS_SERVER_PORT))
sock_file = sock.makefile('rb')

data = sock.recv(BUFFER_SIZE)
print("APRS Login reply:  ", data)

#login to APRS server
login = 'user SPOTa pass 12006 vers SPOTPushClient 0.1 filter r/33/-112/10 \n'
login = login.encode(encoding='utf-8', errors='strict')
sock.send(login)

data = sock.recv(BUFFER_SIZE)
print("APRS Login reply:  ", data)

if data == b'':
    print('No response from APRS server, restarting program in 5s')
    time.sleep(5)
    restart_program()

#callsign/pass generator at https://www.george-smart.co.uk/aprs/aprs_callpass/

startTime = time.time()

AprsThread = threading.Thread(target=openClient)
AprsThread.daemon = True
AprsThread.start()

L = 0  # Loop counter for long-term running

# Initial user sorting
print('Running initial sort')
for i in range(1, len(user)):
    time.sleep(3)
    sort_spot = getSPOT(user[i][0])
    sort_spot.ICAO = user[i][1]  # add icao in
    if sort_spot.transmissionAge < 172800 and sort_spot.transmissionAge != 10000:
        print(sort_spot.user, 'last pos is within 2 days, adding to short list')
        shortuser.append(sort_spot)
        print('shortlist length', len(shortuser))
    elif sort_spot.status == 'User Not Found':
        print(sort_spot.user, ' adding to error list')
        erroruser.append(sort_spot.user)
        print('erroruser length', len(erroruser), erroruser)
    else:
        print(sort_spot.user, 'last pos is longer than 2 days, adding to long list')
        longuser.append(sort_spot)
        print('longlist length', len(longuser))
        
    if i % 10 == 0:
        try:
            sock.send('#keepalive\n'.encode())
            print('Sending APRS keep alive at user', i)
        except:
            print('error sending keepalive')
            pass

timer_now = time.time()
timer = timer_now - startTime
print('Initial sort complete:', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
      'Uptime:', int((timer % 3600)//60), 'minutes', int((timer % 3600)%60), 'seconds')

print('Shortuser length:', len(shortuser))
print('Longuser length', len(longuser))
print('Error users', len(erroruser), 'Delete the following users:', erroruser)

num = 0  # Even/odd counter
i = 0    # Iterator for shortuser list
z = 0    # Iterator for longuser list

# Initialize a variable to track the start of a shortuser cycle
short_cycle_start = time.time()

while True:
    timer_now = time.time()
    timer = timer_now - startTime
    timenow = datetime.utcnow().strftime("%H%M%S")
    
    shortlen = len(shortuser)
    longlen = len(longuser)
    
    # Protection if shortuser list is empty
    if shortlen == 0:
        print("No short users available, waiting 10 seconds...")
        time.sleep(10)
        continue

    # If in the shortuser branch and we've reached the end of the list,
    # pause until 60 seconds have elapsed since the cycle started.
    if num % 2 == 0 and i == shortlen:
        elapsed = time.time() - short_cycle_start
        if elapsed < 60:
            wait_time = 60 - elapsed
            while wait_time > 0:
                print("Waiting for", int(wait_time), "seconds...")
                sleep_interval = min(5, wait_time)
                time.sleep(sleep_interval)
                wait_time -= sleep_interval
        print("Resetting shortuser list.")
        i = 0
        short_cycle_start = time.time()
    
    # Protection for longuser list: if empty, skip longuser branch.
    if longlen == 0:
        print("No long-term users available, skipping longuser branch.")
    
    if num % 2 == 0:
        # Process shortuser list
        SPOT = getSPOT(shortuser[i].user)
        time.sleep(2)
    
        if SPOT.transmissionAge < 600:
            print('Tracking', shortuser[i].user, SPOT.transmissionAge, 'seconds ago')
            ICAO = 'ICA' + shortuser[i].ICAO
            time_UTC = SPOT.timeUTC              
            lat = SPOT.latitude + SPOT.latitudeNS
            lon = SPOT.longitude + SPOT.longitudeEW
            ac_type = "'"
            heading = '000'  # SPOT.heading
            speed = '000'
            alt = SPOT.altitude
            ICAO_id = 'id3D' + ICAO[3:]
            climb = ' +' + '000'
            turn = ' +' + '0.0'
            sig_stren = ' ' + '0.0'
            errors = '0e'
            offset = '+' + '0.0'
            gps_stren = ' gps2x3'
            newline = '\n'
            
            if lat != 0 and lon != 0:
                encode_ICAO = ICAO + '>SPOT,qAS,SPOT:/' + time_UTC + 'h' + lat + '/' + lon + ac_type + heading + '/' + speed + '/' + 'A=' + alt + ' !W00! ' + ICAO_id + climb + 'fpm' + turn + 'rot' + sig_stren + 'dB ' + errors + ' ' + offset + 'kHz' + gps_stren + newline
                print('sending data:', encode_ICAO)
                try:
                    sock.send(encode_ICAO.encode())
                    time.sleep(0.1)
                    sock.send(encode_ICAO.encode())
                except:
                    print('error sending position')
                    pass
                # Send to API
                send_to_api(encode_ICAO)
        i = i + 1  # increment counter on shortuser list
        
    else:
        # Process longuser list if not empty
        if longlen > 0:
            time.sleep(2)
            SPOT = getSPOT(longuser[z].user)    
        
            if SPOT.transmissionAge < 1200:
                print('Tracking', longuser[z].user, SPOT.transmissionAge, 'seconds ago')
                ICAO = 'ICA' + longuser[z].ICAO
                time_UTC = SPOT.timeUTC              
                lat = SPOT.latitude + SPOT.latitudeNS
                lon = SPOT.longitude + SPOT.longitudeEW
                ac_type = "'"
                heading = '000'  # SPOT.heading
                speed = '000'
                alt = SPOT.altitude
                ICAO_id = 'id3D' + ICAO[3:]
                climb = ' +' + '000'
                turn = ' +' + '0.0'
                sig_stren = ' ' + '0.0'
                errors = '0e'
                offset = '+' + '0.0'
                gps_stren = ' gps2x3'
                newline = '\n'
                
                if lat != 0 and lon != 0:
                    encode_ICAO = ICAO + '>APRS,qAS,SPOT:/' + time_UTC + 'h' + lat + '/' + lon + ac_type + heading + '/' + speed + '/' + 'A=' + alt + ' !W00! ' + ICAO_id + climb + 'fpm' + turn + 'rot' + sig_stren + 'dB ' + errors + ' ' + offset + 'kHz' + gps_stren + newline
                    print('sending data:', encode_ICAO)
                    try:
                        sock.send(encode_ICAO.encode())
                        time.sleep(0.1)
                        sock.send(encode_ICAO.encode())
                    except:
                        print('error sending position')
                        pass
                    # Send to API
                    send_to_api(encode_ICAO)
            z = z + 1
        else:
            print("Skipping longuser branch; no long-term users available.")
    
    num = num + 1  # even/odd incrementer
    
    if L % 10 == 0:
        print('Local time:', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
              'Uptime:', int(timer // 3600), 'hours', int((timer % 3600) // 60),
              'minutes', int((timer % 3600) % 60), 'seconds')
        try:
            sock.send('#keepalive\n'.encode())
            print('Sending APRS keep alive at loop', L)
        except:
            print('error sending keepalive at loop', L)
            pass     
    
    L = L + 1  # increment total loop counter        
    time.sleep(0.09)
