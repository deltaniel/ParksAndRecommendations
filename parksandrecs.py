#
# SI 507 W22 Final Project
# Parks and Recommendations
#
# Daniel Ruan
# deltar@umich.edu
#

import json
import requests
import datetime as dt

# API keys
owAPI = "<API key>"              # OpenWeather API key
govAPI = "<API key>"     # data.gov API key
geoAPI = "<API key>"      # Google maps geocoding API key

# Constants
CACHE_FILENAME = "cache.json"


class Park():
    def __init__(self, json):
        self.parseJson(json)
        self.getForecast()
        self.calculateWeather()

    def parseJson(self, json):
        self.name = json['fullName']
        self.parkCode = json['parkCode']
        self.description = json['description']
        self.coords = (json['latitude'], json['longitude'])
        self.activities = [x['name'] for x in json['activities']]
        self.topics = [x['name'] for x in json['topics']]
        self.states = json['states']
        self.url = json['directionsUrl']
        self.designation = json['designation']

    def searchKeyword(self, keyword):
        for activity in self.activities:
            if keyword.lower() in activity.lower():
                return True
        return False

    def getForecast(self):
        self.weather = requestForecast(self.coords)

    def calculateAverageClouds(self, date):
        values = [x.cloudiness for x in self.weather if x.date == date]
        if len(values) == 0:    # Date out of range from forecast
            return None
        else:
            return sum(values)/len(values)

    def isRaining(self, date):
        for x in self.weather:
            if x.condition == 'Rain':
                return True
        return False    # No rain forecasted on this date

    def calculateWeather(self):
        cloudiness = 0
        # rainDays = 0
        for i in range(1,5):
            delta = dt.timedelta(days=i)
            cloudiness += self.calculateAverageClouds(dt.date.today() + delta)
            # if self.isRaining(dt.date.today() + delta):
            #     rainDays += 1
        self.cloudiness = cloudiness/4
        # self.rainDays = rainDays


class Location():
    def __init__(self, json):
        self.parseJson(json)

    def parseJson(self, json):
        self.name = json['formatted_address']
        lat = json['geometry']['location']['lat']
        long = json['geometry']['location']['lng']
        self.coords = (lat, long)

        self.country = None
        self.state = None
        for x in json['address_components']:
            if x['types'][0] == "country":
                self.country = x['short_name']
            elif x['types'][0] == "administrative_area_level_1":
                self.state = x['short_name']


class WeatherPoint():
    def __init__(self, json, coords):
        self.coords = coords
        self.parseJson(json)

    def parseJson(self, json):
        self.date = dt.date(int(json['dt_txt'][:4]),
                            int(json['dt_txt'][5:7]),
                            int(json['dt_txt'][8:10]))      # YYYY-MM-DD
        self.hour = int(json['dt_txt'][11:13])
        self.temp = float(json['main']['temp'])             # Temperature in F
        self.humidity = float(json['main']['humidity'])     # RH %
        self.condition = json['weather'][0]['main']
        self.cloudiness = float(json['clouds']['all'])


def openCache():
    try:
        cacheFile = open(CACHE_FILENAME, 'r')
        cacheContents = cacheFile.read()
        cacheDict = json.loads(cacheContents)
        cacheFile.close()
    except:
        cacheDict = {}
    return cacheDict


def saveCache(cacheDict):
    dumpedJsonCache = json.dumps(cacheDict)
    fw = open(CACHE_FILENAME, "w")
    fw.write(dumpedJsonCache)
    fw.close()


def generateCacheKey(baseUrl, params):
    paramStr = '_'.join(params)
    return f'{baseUrl}_{paramStr}'


def requestJson(url):
    return requests.get(url).json()


def requestForecast(coords, units="imperial"):
    lat, long = coords
    url = f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={long}&appid={owAPI}&unit={units}'
    weatherJson = requestJson(url)
    return [WeatherPoint(json, coords) for json in weatherJson['list']]


def requestParks(cacheDict, state=None):
    baseUrl = 'https://developer.nps.gov/api/v1/parks'
    cacheKey = generateCacheKey(baseUrl, [state])
    if cacheKey in cacheDict:
        parkJson = cacheDict[cacheKey]
    else:
        url = f'{baseUrl}?stateCode={state}&api_key={govAPI}'
        parkJson = requestJson(url)
        cacheDict[cacheKey] = parkJson
    return [Park(json) for json in parkJson['data']]


def geocode(address):
    address = address.replace(' ', '%20')   # url-escape spaces
    address = address.replace('+', '%2B')   # url-escape plus signs
    url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={geoAPI}'
    geoJson = requestJson(url)
    if geoJson['status'] == 'OK':
        return Location(geoJson['results'][0])
    else:   # Error processing address
        return None


def checkLocation(location):
    if location is None:
        return False
    if location.country == "US":
        return True
    return False


def main():
    # Prompt user for a valid location in the US
    while True:
        address = input('Please enter a location in the US to search around: ')
        location = geocode(address)
        if checkLocation(location):     # Location is valid
            print(f'Searching for parks nearby {location.name}...')
            break
        else:
            print('No valid location found! Trying again...')
            continue

    cacheDict = openCache()
    parks = requestParks(cacheDict, state=location.state)
    saveCache(cacheDict)
    parks = sorted(parks, key=lambda x: x.cloudiness)
    recPark = parks[0]
    cp = int(100 - recPark.cloudiness)   # % clear skies in the next four days

    print(f'I recommend you go visit {recPark.name}!\nIt will be {cp}% clear skies over the next four days.')
    activities = ', '.join(recPark.activities)
    print(f'This {recPark.designation} offers the following activities: {activities}')


if __name__ == '__main__':
    main()