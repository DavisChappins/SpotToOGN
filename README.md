# SPOTToOGN
This script grabs SPOT location data from [Spotuser.csv](https://github.com/DavisChappins/SpotToOGN/blob/main/Spotuser.csv) in this repository and uploads it to the OGN to be viewable on OGN sites like https://glidertracker.org/. For more information about the OGN see http://wiki.glidernet.org/.  
It's currently running on my local machine 24 hrs a day, 7 days a week.
  
## How can I add my SPOT?
First, [enable an XML feed](https://www.findmespot.com/en-us/support/spot-x/get-help/general/spot-api-support).  
Second, ensure your SPOT XML Feed ID is not already added in the [Spotuser.csv](https://github.com/DavisChappins/SpotToOGN/blob/main/Spotuser.csv) file in this repository. Ctrl+f for your name or XML Feed ID. The data was pulled from the SSA website.   
If you do not find your XML Feed ID, fill out the google form at https://forms.gle/KxWvSTnmL9XkKg2V6  
You will need:
* Your XML FEED ID
* The N number or ICAO id of your aircraft
* Your name

## How can I tell if it is running?
After turning on your SPOT device, your position may take 5-15 minutes to appear. If your position is not valid or is older than 30 minutes at maps.findmespot.com you will not appear. Ensure your username and aircraft info is in the [Spotuser.csv](https://github.com/DavisChappins/SpotToOGN/blob/main/Spotuser.csv) file. The csv file is updated by filling out [this google form](https://forms.gle/KxWvSTnmL9XkKg2V6). If you have recently filled out the form it may take a short amount of time for your info to be added.  
The script connects to http://glidern2.glidernet.org:14501/ ctrl+f for "SPOT" to verify the script is connected and running.  

## What does it look like on a map?
Go to https://glidertracker.org/ and find your location. SPOT position data is pushed to the OGN as an "unknown object" and will appear as a an earth icon. SPOT position data will be 5-15 minutes behind your actual location but will update every 10 minutes.  
See below for an example  
![SPOT on glidertracker.org](https://github.com/DavisChappins/SpotToOGN/blob/main/Images/spot1.JPG?raw=true)

## How does this script work?
Every 3 minutes, this script parses the list of SPOT XML API positions contained in Spotuser.csv. If a position is found to be within the last 30 minutes, that position, timestamp,and  altitude are transmitted to the OGN servers to be displayed on any website that subscribes to OGN data. SPOT positions are transmitted as an "unknown" data type in order to not overwrite the "glider" data type. Some websites may reject "unknown" objects. Spotuser.csv contains your ICAO hex code so the same information that you entered at http://ddb.glidernet.org/ is carried over and displayed on your SPOT position.
