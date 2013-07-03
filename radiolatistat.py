#!/usr/bin/python
#
# This script will automatically set the thermostat temperature
# to the away or home temperatures based on google latitude of
# location for all configured users.  If any user is within the
# configured 'min_range', the thermostat will be set to the home
# temp. If no one is in range, it will be set to the away temp.
# 
# Example Config
# This should be stored in $HOME/.radiothermostat/config
#
# {
#  'users': {'GOOGLE_EMAIL1': 0, 'GOOGLE_EMAIL2': 0},
#  'home_long': HOME_LONGITUDE,
#  'home_lat': HOME_LATITUDE,
#  'client_id': 'GOOGLE_PROJECT_CLIENT_ID',
#  'client_secret': 'GOOGLE_PROJECT_CLIENT_SECRET',
#  'api_key': 'GOOGLE_DEVELOPER_PROJECT_API_KEY',
#  'tstat_url': 'http://IPADDRESS', #url of thermostat
#  'min_range': 10 #Distance in miles
# }
#

import os
import sys
import math
import json
import httplib2
from urlparse import urlparse

#
# Import the google/oauth modules
#
# $ pip-python install google-api-python-client
# $ pip-python install oauth2client
#
from oauth2client.tools import run
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow

#
# Setup some vars
#
CONFIG_STORE = os.path.join(os.environ['HOME'], '.radiothermostat')
inrange = False
VERBOSE = True if len(sys.argv) > 1 and '-v' in sys.argv else False

def log(message):
  '''
  Stupid function to log a message if VERBOSE is set
  '''
  if VERBOSE:
    print "INFO: " + message

def load_config(config_dir=CONFIG_STORE):
  '''
  Function to load the configuration file
  '''
  if not os.path.exists(config_dir):
    os.makedirs(config_dir)

  try:
    config_file = open(os.path.join(config_dir,'config'))
  except:
    print "Config file not found.  Create one first"
    sys.exit(3)
  
  return json.load(config_file)

def distance_calc(lat1, long1, lat2, long2):
  '''
  Function to determine distance between to points

  http://www.johndcook.com/python_longitude_latitude.html
  '''
  degrees_to_radians = math.pi/180.0
  phi1 = (90.0 - lat1)*degrees_to_radians
  phi2 = (90.0 - lat2)*degrees_to_radians
  theta1 = long1*degrees_to_radians
  theta2 = long2*degrees_to_radians
  cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
         math.cos(phi1)*math.cos(phi2))
  arc = math.acos( cos )
  return (arc * 3959)

def get_distances(users, client_id, client_secret, api_key, home_long, home_lat, config_dir=CONFIG_STORE):
  '''
  Function get pull location information and distances from google latitude
  '''
  #Build our google flow object
  flow = OAuth2WebServerFlow(
    client_id=client_id,
    client_secret=client_secret,
    scope='https://www.googleapis.com/auth/latitude.current.best')

  #Go through each configured user to get their location
  for user in users:
    cred_file = os.path.join(CONFIG_STORE, ".google_%s" % user)
    http = httplib2.Http()
    storage = Storage(cred_file)

    #Get login information from cred store or authorize new access
    try:
      credentials = storage.get()
      http = credentials.authorize(http)
    except:
      print "Logging in for %s.  You may want to log out of google in your browser." % user
      print "Press [ENTER] to continue..."
      raw_input()
      credentials = run(flow, storage)
      http = credentials.authorize(http)

    #Get latitude information for user
    if VERBOSE:
      print "INFO: Getting location for %s" % user 
    service = build('latitude', 'v1', developerKey=api_key, http=http)
    phone = service.currentLocation().get().execute()

    #Look for valid data and get distance from home
    if 'latitude' in phone and 'longitude' in phone:
      distance = distance_calc(home_lat, home_long, phone['latitude'], phone['longitude'])
      users[user] = distance
    else:
      print "No location data for %s" % user

  return users

class TstatException(Exception):
  '''
  Simple exception class to die gracefully
  '''
  def __init__(self, message, code=1):
    sys.stderr.write("ERROR: %s\n" % message)
    sys.exit(code)

class Rest:
  '''
  Simple rest class
  '''
  def __init__(self, server):
    p = urlparse(server)

    if not p.port:
      self.port = 80 if p.scheme == 'http' else 443
    else:
      self.port = p.port

    self.server = '%s://%s:%s' % (p.scheme, p.netloc, self.port)
    self.base = p.path

    self.conn = httplib2.Http()

  def call(self, url, data=None, method='GET'):
    url = self.server + os.path.join(self.base, url)
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    if data:
      data = json.dumps(data)

    try:
      response, content = self.conn.request(url, method, headers=headers, body=data)
    except Exception as e:
      raise Exception('ERROR: Could not connect to server:\n%s' % e)

    try:
      data = json.loads(content)
      return data
    except:
      raise Exception('Could not parse json data')

class Tstat:
  '''
  Simple class to interface with the Radio Thermostat
  '''
  def __init__(self, server):
    self.url = os.path.join(server,'tstat')
    self.conn = Rest(self.url)

  def message_uma(self, line, message):
    data = {'line': line, 'message': message}
    resp = self.conn.call('uma', data, 'POST')

  def message_pma(self, line, message):
    data = {'line': line, 'message': str(message)}
    resp = self.conn.call('pma', data, 'POST')

  def state(self, body=None):
    if not body:
      return self.conn.call('')
    else:
      return self.conn.call('', body, 'POST')

  def program(self, mode, day="0"):
      modes = ['heat','cool']

      if mode not in modes:
        raise Exception('Invalid program mode.')

      return self.conn.call('program/%s/%s' % (mode,day))

  def program_heat(self, day="0"):
      return self.program('heat', day)

  def program_cool(self, day="0"):
      return self.program('cool', day)

  def led(self,color):
    colors = {'red': 4, 'orange': 2, 'green': 1, 'off': 0}
    if color in colors:
      self.conn.call('led', {'energy_led': colors[color]},'POST')
    else:
      raise Exception('Invalid LED color')

#
# Load our config file
#
config = load_config()

#
# Get each users distance
#
users = get_distances(
  config['users'], 
  config['client_id'], 
  config['client_secret'], 
  config['api_key'], 
  config['home_long'], 
  config['home_lat']
)

#
# Check if any users are within range of home
#
for user in users:
  if users[user] < config['min_range']:
    inrange = True
    log("%s in range" % user)
  else:
    log("%s out of range: %d mi" % (user, users[user]))

#
# Setup our Radio Thermostat resouce
#
tstat = Tstat(config['tstat_url'])
inside = tstat.state()

#
# Figure out what mode the A/C is set to
#
# 0 - Off
# 1 - Heat
# 2 - Cool
#
# If we are set to COOL, get the first program
if inside['tmode'] == 2:
  program = tstat.program_cool()
  mode = "t_cool"

#
# If we are set to HEAT, get the first program
#
if  inside['tmode'] == 1:
  program = tstat.program_heat()
  mode = "t_heat"

#
# If we are turned off, exit
#
if inside['tmode'] == 0:
  raise TstatException("A/C is off, not doing anything")

#
# Get the home and away temperatures from the first schedule
# The data is in an array in the form of:
#
# INDEX DESCRIPTION
# [0]   Morning Time
# [1]   Morning Temp
# [2]   Away Time
# [3]   Away Temp
# [4]   Home Time
# [5]   Home Temp
# [6]   Sleep Time
# [7]   Sleep Temp
#

#
# If we don't have a program, raise exception
#
if "0" not in program:
  raise TstatException("Could not determine home/away temperatures\nDoes the thermostat have a schedule?",2)

#
# Go ahad and set the temps
#
temp_away = program["0"][3]
temp_home = program["0"][5]

#
# If no one is in range, set A/C to away temp
#
if not inrange:
  tstat.state({mode: temp_away})
  log("Set A/C to away temp: %s" % temp_away)
  sys.exit(0)

#
# If anyone is in range, set A/C to home temp.
# We only want to adjust the temp if it is higher then
# the home temp in cooling mode and lower in heat mode
#
settemp = inside[mode] > temp_home if 't_cool' else inside[mode] < temp_home

if settemp:
  tstat.state({mode: temp_home})
  log("Set A/C to home temp: %s" % temp_home)
elif inside[mode] == temp_home:
  log("Thermostat temp is already set")
else:
  log("Thermostat temp is already lower")