# flight-mapper

This is a very experimental project I developed to practice and explore a variety of libraries/technologies.

Since 2017, I had stored all flights I had taken in a Google Spreadsheets. It had the following structure:

| Date | From | To | Airline |
|------|------|----|---------|
|27/11/2017 | AEP |BRC	| Aerolineas Argentinas |
|23/2/2018  |BRC  | AEP	| LATAM |
| ... | ... | ... | ...|

I had wondered how many miles this totalled, but didn't want to manually calculate it.

This program:

1. Authenticates Google Sheets API and creates a connection service with the spreadsheet
2. Retrieves the data from the sheet and loads it into a table
3. Creates flight and airport objects for each new airport/flight seen.
4. Searches a dataset of all airports, to obtain each airport's lat/lon coordinates and country. 
5. Uses the airport codes to create a HTMl request to a website that stores distances between airports. Then, uses XML to find the relevant distance field
6. Updates the Google spreadsheet with the found mileages
7. Plots all flights/airports visited on a plotly map, with basic summary statistics.

The final output looks like this:
![Flight Map](https://github.com/jpFenley/flight-mapper/blob/main/map.png)

This is a static export of the graph. The plotly HTML version allows moving, panning, and zooming in on the map. Hovering on flights and airports also display the name. Access the interactive version [here](https://jpfenley.github.io/flight-mapper/map.html).

There are many ways this could be improved for efficiency, but that was not the scope of this project. For example,
finding the distance between airports can easily be done with coordinates. This however, would not have allowed me to 
use HTML requests and XML. Similarily, a lot of the functions could have been coded directly into the Google Sheets, or 
the sheet downloaded first and read in as a .csv. This would not have allowed me to experiment with the Google
Sheets API.
