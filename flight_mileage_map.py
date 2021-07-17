from lxml import html
import requests
import pandas as pd
import numpy as np
from googleapiclient.discovery import build
from google.oauth2 import service_account
import plotly.graph_objects as go

# Declare Google Auth credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'keys.json'
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Set unique spreadsheet ID
SPREADSHEET_ID = '1EoxML489o9tSV5VunJ--e-Nk68p2RvpUAVGYFKw62PI'

# Initiate service with our credentials
service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
sheet = service.spreadsheets()
values = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                            range='Sheet1').execute()['values']

# Load flight data into DataFrame
flight_info = pd.DataFrame(values[1:], columns=values[0])
flight_info['Mileage'] = pd.to_numeric(flight_info['Mileage'])

# Load Airport information database
airports = pd.read_csv('airports.csv', encoding='utf-8')

# Flight and airport frequency dictionary
frequencies = {}
locations = {}


class Airport:
    """"
    Airport class stores the name and locations (coords + country) of an
    airport. Each airport is an attribute stored by each flight as its origin
    and destination.
    """
    def __init__(self, name):
        self.identifier = name
        if self.identifier not in locations:
            locations[self.identifier] = self

    def set_coordinates(self, origin_coords):
        self.airport_lat, self.airport_lon = origin_coords

    def set_country(self, country):
        self.country = country


class Flight:
    """
    Each flight is unique for ecah airport combination regardless of origin
    and destination (Ex: MIA-EZE is the same flight as EZE-MIA).

    Every flight has two airports referenced. For every flight, the flight
    distance is computed. If the respective airports belong to the same
    country, the flight is marked as domestic.
    """
    def __init__(self, identifier):
        self.identifier = identifier
        if identifier[:3] in airports:
            self.airport1 = airports[identifier[:3]]
        else:
            self.airport1 = Airport(identifier[:3])

        if identifier[4:] in airports:
            self.airport2 = airports[identifier[4:]]
        else:
            self.airport2 = Airport(identifier[4:])

        self.count = 0

    def set_coordinates(self, origin_coords, dest_coords):
        self.airport1.set_coordinates(origin_coords)
        self.airport2.set_coordinates(dest_coords)

    def set_region(self, origin_country, dest_country):
        self.airport1.set_country(origin_country)
        self.airport2.set_country(dest_country)
        if origin_country == dest_country:
            self.region_type = 'Domestic'
        else:
            self.region_type = 'International'

    def set_distance(self, dist):
        if pd.isna(dist):
            self.dist = get_mileage(self.airport1.identifier, self.airport2.identifier)
        else:
            self.dist = dist

    def get_distance(self):
        return self.dist


def get_mileage(origin, destination):
    """
    Calculate the distance between both airports. Uses webflyer calculator and
    creates a HTML request. The XML path to the given distance field is
    extracted. This distance could be calculated easily with coordinates, but
    this project was to play with requets and XML.

    :param origin: airport's code
    :param destination: airport's code
    :return: the distance between each airports
    """
    url = "http://www.webflyer.com/travel/mileage_calculator/getmileage.php?city={0}&city={" \
          "1}&city=&city=&city=&city=&bonus=0&bonus_use_min=0&class_bonus=0&class_bonus_use_min=0&promo_bonus=0" \
          "&promo_bonus_use_min=0&min=0&min_type=m&ticket_price=".format(origin, destination)
    page = requests.get(url)
    tree = html.fromstring(page.content)
    mile = tree.xpath(
        '/html/body/table/tr[3]/td/table/tr/td[2]/table[2]/tr/td/form/table/tr[5]/td[2]/b/span/text()')
    mile = ''.join(x for x in mile[0] if x.isdigit())
    return int(mile)


# Create unique flight code in form XXX-YYY, where XXX and YYY are airport codes
for index, flight in flight_info.iterrows():
    flight_origin = min(flight['From'], flight['To'])
    flight_dest = max(flight['From'], flight['To'])
    flight_code = flight_origin + '-' + flight_dest

    # Filling frequency dictionary
    if flight_code not in frequencies:
        new_flight = Flight(flight_code)

        origin_airport_info = airports[airports['iata_code'] == flight_origin]
        dest_airport_info = airports[airports['iata_code'] == flight_dest]

        new_flight.set_coordinates(origin_airport_info[['latitude_deg', 'longitude_deg']].values[0],
                                   dest_airport_info[['latitude_deg', 'longitude_deg']].values[0])

        new_flight.set_region(origin_airport_info['iso_country'].item(), dest_airport_info['iso_country'].item())
        frequencies[flight_code] = new_flight

        new_flight.set_distance(flight['Mileage'])
    else:
        frequencies[flight_code].count += 1

    # Calculate flight distance if missing.
    if np.isnan(flight['Mileage']):
        flight_info.loc[index, 'Mileage'] = new_flight.get_distance()


# Update the Google spreadsheet
request = sheet.values().update(spreadsheetId=SPREADSHEET_ID,
                                range='Sheet1!A2:E',
                                body={'values': flight_info.values.tolist()},
                                valueInputOption='USER_ENTERED').execute()

# Compute some flight statistics
most_frequent_flight_count = frequencies[max(frequencies, key=lambda m: frequencies[m].count)].count
total_distance_flown = sum(flight_info['Mileage'])
flights_flown = len(flight_info)
airports_visited = len(locations)
num_distinct_countries = len(np.unique([loc.country for n, loc in locations.items()]))

# Initialize plotly graph.
fig = go.Figure()

# Plot each flight as a line
for code, flight in frequencies.items():
    fig.add_trace(
        go.Scattergeo(
            name=flight.identifier,
            opacity=0.5 + (flight.count / most_frequent_flight_count) / 2,
            mode='lines',
            lat=[flight.airport1.airport_lat, flight.airport2.airport_lat],
            lon=[flight.airport1.airport_lon, flight.airport2.airport_lon],
            line=dict(width=1, color='red' if flight.region_type == 'Domestic' else 'blue')
        )
    )
# Plot each airport as a point
for airport_name, details in locations.items():
    fig.add_trace(
        go.Scattergeo(
            name=airport_name,
            mode='markers',
            lat=[details.airport_lat],
            lon=[details.airport_lon],
            marker_color='red'
        )
    )

# Set map parameters and title
fig.update_layout(title=dict(
    text=f'My 2017-2021 flights',
    font_size=24,
    x=0.5,
    xanchor='center'),
    showlegend=False,
    geo=dict(
        projection=dict(
            type='orthographic',
            rotation=dict(
                lon=-45,
                lat=10
            )
        )
    ))

# Add basic statistics
fig.update_layout(annotations=[
    go.layout.Annotation(
        text=f'{int(total_distance_flown)} miles flown',
        showarrow=False,
        x=1,
        y=0.05,
        font=dict(size=18)
    ),
    go.layout.Annotation(
        text=f'{flights_flown} flights flown',
        showarrow=False,
        x=1,
        y=0.1,
        font=dict(size=18)
    ),
    go.layout.Annotation(
        text=f'{airports_visited} airports visited in {num_distinct_countries} countries',
        showarrow=False,
        x=1,
        y=0.15,
        font=dict(size=18)
    )
])
go.Figure.write_html(fig, 'map.html')
go.Figure.write_image(fig, 'map.png', width=1200, height=600)

fig.show()
