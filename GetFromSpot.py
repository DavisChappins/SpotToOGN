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



global APRSbeacon

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
        
        try:
            url = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/" + user + "/latest.xml"
            response = requests.get(url)
            data = xmltodict.parse(response.content)
        except:
            print('error parsing url:',user)


        try:
            #find latitude
            try:
                lat = data['response']['feedMessageResponse']['messages']['message'][0]['latitude']
            except:
                lat = data['response']['feedMessageResponse']['messages']['message']['latitude']
            lat_f = float(lat)
            #get decimal
            lat_d = math.trunc(lat_f)
            #get minutes and get N or S
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
            #isolate minutes only
            lat_m_o = str(int(lat_m))
            lat_m_o = lat_m_o.zfill(2)
            #combine them
            lat_c = lat_s + lat_m_o + '.' + lat_m_afterDec
            #print('latitude:',lat_c) #formatted for APRS
            self.latitude = lat_c


            #find longitude
            try:
                lon = data['response']['feedMessageResponse']['messages']['message'][0]['longitude']
            except:
                lon = data['response']['feedMessageResponse']['messages']['message']['longitude']
            lon_f = float(lon)
            #lon_f = lon_f * -1  #only works in North America
            #get decimal
            lon_d = math.trunc(lon_f)            
            #get minutes and get E or W
            if lon_d > 0:
                lon_m = round((lon_f*60) % 60,2)
                self.longtiudeEW = 'E'
            else:
                lon_m = round((lon_f*-1*60) % 60,2)
                self.longitudeEW = 'W'
                lon_d = abs(lon_d)
            lon_s = str(lon_d)
            lon_m_s = "{:.2f}".format(lon_m)
            lon_m_afterDec = lon_m_s[-2:]
            #isolate minutes only
            lon_m_o = str(int(lon_m))
            lon_m_o = lon_m_o.zfill(2)
            #combine them
            lon_c = lon_s + lon_m_o + '.' + lon_m_afterDec
            #print('longitude:',lon_c) #formatted for APRS
            self.longitude = lon_c


            #find elevation (meters)
            try:
                elev_s = data['response']['feedMessageResponse']['messages']['message'][0]['altitude']
            except:
                elev_s = data['response']['feedMessageResponse']['messages']['message']['altitude']
            elev_f = float(elev_s)
            elev = int(elev_f * 3.28084) #change to feet (from m)
            elev = "{:06d}".format(elev)
            #print('altitude:',elev)
            self.altitude = elev

            #find time UTC of transmission
            try:
                timeUTC_time = data['response']['feedMessageResponse']['messages']['message'][0]['unixTime']
            except:
                timeUTC_time = data['response']['feedMessageResponse']['messages']['message']['unixTime']
            timeUTC_time_i = int(timeUTC_time) + 25200 #convert to UTC time, 7 hour difference
            time_UTC_str = datetime.fromtimestamp(timeUTC_time_i).strftime("%H%M%S")# - timedelta(hours=7)
            #print('formatted time:',time_UTC_str)
            timeUTCnow = datetime.utcnow()
            age = timeUTCnow - datetime.fromtimestamp(timeUTC_time_i)# - timedelta(hours=7)
            age_s = age.total_seconds()
            print('----',user,'----','Last Transmission:',age,'ago')
            #print('Position age (s):',age_s)

            self.timeUTC = time_UTC_str
            self.transmissionAge = age_s

        except Exception as e:
            #print(e)
            print(user,'has no location messages')
            pass


def openClient():
    global APRSbeacon
    while True:
        try:
            packet_b = sock_file.readline().strip()
            packet_str = packet_b.decode(errors="replace") #if ignore_decoding_error else packet_b.decode()
            #print(packet_str)
            APRSbeacon = parse(packet_str)
            #print(APRSbeacon)
            time.sleep(.01)
        except:
            pass
    #time.sleep(1)



#main


APRS_SERVER_PUSH = 'glidern2.glidernet.org'
APRS_SERVER_PORT =  14580 #10152
APRS_USER_PUSH = 'SPOT'
BUFFER_SIZE = 1024
APRS_FILTER = 'g/ALL'

traffic_list = []

#Get most recent user list from Github
urllib.request.urlretrieve("https://raw.githubusercontent.com/DavisChappins/SpotToOGN/main/Spotuser.csv", "Spotuser.csv")
print('Downloading Spotuser.csv from https://raw.githubusercontent.com/DavisChappins/SpotToOGN/main/Spotuser.csv')
time.sleep(2)

#assign Github user list to user
with open('Spotuser.csv', 'r') as read_obj:
    csv_reader = csv.reader(read_obj)
    user = list(csv_reader)
#print(user)

##connect to to the APRS server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((APRS_SERVER_PUSH, APRS_SERVER_PORT))
sock_file = sock.makefile('rb')

data = sock.recv(BUFFER_SIZE)
print("APRS Login reply:  ", data) #server response

#login to APRS server
login = 'user SPOT pass 28646 vers SPOTPushClient 0.1 filter r/33/-112/10 \n'
login = login.encode(encoding='utf-8', errors='strict')
sock.send(login)

data = sock.recv(BUFFER_SIZE)
print("APRS Login reply:  ", data) #server response

#callsign/pass generator at https://www.george-smart.co.uk/aprs/aprs_callpass/


startTime = time.time()

AprsThread = threading.Thread(target=openClient)
AprsThread.daemon = True
AprsThread.start()


while True:

    #timers#
    timer_now = time.time()
    timer = timer_now - startTime
    fiveMinuteTimer = timer % 300   #300 seconds in 5 min, if >299.9 then action
    threeMinuteTimer = timer % 180   #180 seconds in 3 min, if >179.9 then action
    tenSecondTimer = timer % 10   #10 seconds in 10 s, if >9.9 then action
    timenow = datetime.utcnow().strftime("%H%M%S")

    #get SPOT location
    if tenSecondTimer > 9.9: #9.9 with 2s per user over 90 users just use this timer
    #if threeMinuteTimer > 179.9: #179.9
        print('Local time:',datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),'Uptime:',int(timer//3600),'hours',int((timer%3600)//60),'minutes',int((timer%3600)%60),'seconds')
        
        for i in range(1,len(user)):
            SPOT = getSPOT(user[i][0])
            time.sleep(2) #request of spot API to wait 2secs between API calls for multiple users
            if SPOT.transmissionAge < 3000: #2000: #50 mins and recent, only
                print('Tracking',user[i][2],SPOT.user,SPOT.transmissionAge,'seconds ago')
                
                #test encode parameters: -- works
                ICAO = 'ICA' + user[i][1]           #   'FLRDDBA99'
                APRS_stuff = '>APRS,qAS,SPOT:/'
                time_UTC = SPOT.timeUTC              
                lat = SPOT.latitude + SPOT.latitudeNS   #'N'        #   '3300.02N'
                lon = SPOT.longitude + SPOT.longitudeEW   #'W'       #   '11200.00W'
                ac_type = "'"
                heading = SPOT.heading           #   '000' 
                speed = '000'         #   '000'
                #print('speed',speed)
                alt = SPOT.altitude              #   '001368'
                ICAO_id = 'id3D'+ ICAO[3:]
                climb = ' +' + '000' 
                turn = ' +' + '0.0' 
                sig_stren = ' ' + '3.0' 
                errors = '0e'
                offset = '+' + '0.0' 
                gps_stren = ' gps2x3'
                newline = '\n'
                
                
                if lat != 0 and lon != 0:
                    encode_ICAO = ICAO + '>APRS,qAS,SPOT:/' + time_UTC + 'h' + lat + '/' + lon + ac_type + heading + '/' + speed + '/' + 'A=' + alt + ' !W00! ' + ICAO_id + climb + 'fpm' + turn + 'rot' + sig_stren + 'dB ' + errors + ' ' + offset + 'kHz' + gps_stren + newline
                    print('sending data:',encode_ICAO)
                    #print(APRS_TEST)

                    #print('sending encode_test_ICAO',encode_ICAO)
                    try:
                        sock.send(encode_ICAO.encode())
                        time.sleep(.1)
                        sock.send(encode_ICAO.encode())
                    except:
                        print('error encoding somehow')
                        pass
                        
        try:
            sock.send('#keepalive\n'.encode())
            #print('Sending APRS keep alive')
        except:
            print('error encoding somehow')
        
    time.sleep(.09)


