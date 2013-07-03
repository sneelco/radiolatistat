radiolatistat
=============

### About
The Radio Thermostat Google Latitude Tracker keeps track of multiple Google Latitude users and as soon as any of them are within the configurable range, sets the Radio Thermostat temperature to the home setting.  If no users are within range, it will set the thermostat to the away setting.

### Requirements
In order for the script to run, you will need the following:
* Python 2.7
* oauth2client python module
* google-api-python-client python module
* Google Developer API Key (https://code.google.com/apis/console)
* Longitude/Latitude of your home address
* Address of your Radio Thermostat
 
### Compatibility
Here is the list of thermostats that are compatible:
* Radio Thermostat Company of America CT-80

### Installation
```bash
cd ~
mkdir .radiothermostat
cd .radiothermostat
cat > config << EOF
{
  'users': {'GOOGLE_EMAIL1': 0, 'GOOGLE_EMAIL2': 0},
  'home_long': HOME_LONGITUDE,
  'home_lat': HOME_LATITUDE,
  'client_id': 'GOOGLE_PROJECT_CLIENT_ID',
  'client_secret': 'GOOGLE_PROJECT_CLIENT_SECRET',
  'api_key': 'GOOGLE_DEVELOPER_PROJECT_API_KEY',
  'tstat_url': 'http://IPADDRESS', #url of thermostat
  'min_range': 10 #Distance in miles
}
EOF
```
Once the configuration file is complete, run the script. It prompts you to log out of google in your browser.  This is needed in case the latitude user you are trying to authenticate is not the user you have currently logged in your browsers session.  Once you hit enter, your browser will open up.  Login to google and accept the prompt, giving the script access to latitude.  At this point, you may cron the script to run on a schedule.

### Todo
This is just an initial pass and a lot can still be done:
* Add setup process to generate the config
* Ability to get long/lat based on an address
* Move from cron to a service
* Support multiple thermostats and home locations
* Lots of code cleanup
