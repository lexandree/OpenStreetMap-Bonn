# OpenStreetMap-Bonn
# Wrangle OpenStreetMap Data

## Map Area 

Bonn, Germany.

I have received the data direct from the site using the export tool.  
My hometown is St.Petersburg, Russia, but the map of St.Petersburg weights 944MB and it is too big for this work. I have lived in Bonn last ten years and it is a better choice.  The osm map file of Bonn is 230MB only and was created precisely. 
Nevertheless, there is always something to improve.

### Project

I have set k=10 (select every 10th record) for the test run and received the csv files to import into the database. I have chosen the SQLite database and DB Browser for SQLite to interact with the database. The test import of nodes and ways has passed without problems, but slave tables have rejected the data because of the constraints of the database's integrity (since k=10).
Having evaluated the time of the validation task, I have used a dedicated server to get validated csv files for import. Import to the database has gone errorfree.


### Project files

File | Size
--- | ---
bonn.db | 150MB
bonn.osm | 231MB
bonn.osm.rar | 18MB
nodes.csv | 73MB
nodes_tags.csv | 4,9MB
ways.csv | 11MB
ways_nodes.csv | 30MB
ways_tags.csv | 23MB

### Data overview and statistics
```sql
SELECT COUNT(id) AS sum_all_nodes FROM nodes;
```
--returns 929536 nodes (records in the table nodes)  

```sql
SELECT COUNT(id) AS sum_all_ways FROM ways;
```
--returns 179784 ways (records in the table ways)  

```sql
SELECT COUNT(DISTINCT uid) AS cnt_all_uid FROM
(SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) AS all_users;
```
--returns 1309 - number of unique users and they created 1109320 records in both tables - **nodes** and **ways**.  

```sql
SELECT SUM(cc) FROM
(SELECT count(uid) AS cc, uid FROM
(SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) AS nodes_ways_users
GROUP BY uid ORDER BY cc DESC LIMIT 131);
```
--returns 1084789 - number of records created by top 10% or 131 users. It is 98% of the all records.  



### Problems found in the data

- Misspelled street names

There are two users who has a different german spelling interpretation: Ashley99 and wheelmap_visitor.  
```sql
SELECT nodes_tags.*, user
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id
WHERE key ='street' AND value LIKE 'kolnstr%';
```
![](https://user-images.githubusercontent.com/33815535/33553053-795de7dc-d8f7-11e7-9e3c-3b20da4a4cb1.JPG)  
- the false spelled tags are:  
  - **tag k="addr:street" v="Kolnstr"** 5 records  
  - **v=kolnstrasse** 4 records  
  - **v=Kolnstrasse** 1 record  
  - **v=kolnstr**  2 records  
- the right version is **tag k="addr:street" v="Kölnstraße"**

Set the right values:
```sql
UPDATE nodes_tags SET value='Kölnstraße'
WHERE key='street' AND type='addr' AND value LIKE 'kolnstr%';
```

The user Ashley99 has '-straße' as '-strasse' misspelled:  
```sql
SELECT nodes_tags.*, user
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id
WHERE value LIKE '%strasse';
```
![](https://user-images.githubusercontent.com/33815535/33530962-099f8286-d887-11e7-83d3-74fa8e0b8edd.JPG)

Set the right values:
```sql
UPDATE nodes_tags SET value=replace(value,'trasse','traße')
WHERE key ='street' AND value LIKE '%strasse';
```
After the first review I decided to perform a check with Google API reverse geocoding. Every node has a latitude/longitude and the Google returns an address of a nearest point of interest. Successful outcome, the street name is found, was in my case about 99.2%. All streets from OSM file and the returned names are saved to the JSON file as a dictionary:

```python
    {"Wilhelm-Levison-Strasse": "Wilhelm-Levison-Straße",
    "Wolfstraße": "Wolfstraße",
    "Wurzerstraße": "Wurzerstraße",
    "kaiser-karl-ring": "Kaiser-Karl-Ring",   # misspelled
    "Michaelplatz": "",                       # not found by Google
    "kolnstr": "Kölnstraße",                  # misspelled, checked with doublemetaphone phonetic encoding algorithm
    "kolnstrasse": "Kölnstraße",              # misspelled, checked with doublemetaphone phonetic encoding algorithm
    "oxfordstrasse": "Oxfordstraße",          # misspelled, checked with doublemetaphone phonetic encoding algorithm
    "schumannstrasse": "Schumannstraße"}      # misspelled, checked with doublemetaphone phonetic encoding algorithm
```

Here is an excerpt from the program. The Google API user key created on [this](https://developers.google.com/maps/documentation/geocoding/start?refresh=1#reverse) site. All work is done in the function ask_google():
```python
    #creating googlemaps client does not mean sending a request
    gmaps = googlemaps.Client(key='abc123') #Google API user key

    # Look up an address with reverse geocoding
    reverse_geocode_result = gmaps.reverse_geocode((parent_node['lat'], parent_node['lon']))# e.g.((40.714224, -73.961452))
    
    # get_route seeks for tag 'route' in address component and returns a value for component['long_name']
    google_street = get_route(reverse_geocode_result[i]['address_components'])
  
    #the street is found by google and is conform 
    if street_tag['value'].lower().strip() == google_street.lower():
        checked_routes[street_tag['value']] = google_street
        return google_street
        
    #the street is misspelled but sounds conform, doublemetaphone+'S' is because shortening Strasse->Str
    if doublemetaphone(street_tag['value'])[0] == doublemetaphone(google_street)[0] or \
        doublemetaphone(street_tag['value'])[0]+'S' == doublemetaphone(google_street)[0]:
        checked_routes[street_tag['value']] = google_street
        return google_street

    # the route not found near this point, this node is in OpenStreet only
    checked_routes[street_tag['value']] = ''
    return street_tag['value']
```
It was a surprise to me that well-known functions and libraries like soundex are not suitable for international use. The [metaphone](https://github.com/oubiwann/metaphone) library is well created and does not require a pre-processing of the whole phrase.

Along with google I checked the possibility of verification using web scraping. The way provided by Google proves to be the most universal and fast, although it has a limited bandwidth of 50 requests per second and 2500 per day or for small money.



### Additional Observations

I found several interesting things in the data.

There are only 8 charging stations for electric cars in the city with combined capacity of 12:
```sql
SELECT * FROM nodes_tags WHERE id in (SELECT id FROM nodes_tags WHERE key ='amenity'
AND value='charging_station');
```
![](https://user-images.githubusercontent.com/33815535/33530959-08f6b7b4-d887-11e7-9e7e-65567c9e41d1.JPG)

This sql command counts 1768 records and gets 402 unique references to wikidata:  
```sql
SELECT count(*) AS cc, value FROM ways_tags WHERE key='etymology:wikidata'
GROUP BY value ORDER BY cc DESC;
```
![](https://user-images.githubusercontent.com/33815535/33530960-095572ae-d887-11e7-915d-6b0cb429111d.JPG)  
The most popular reference with the occurence 95 or 0.5% is the [Q2492](https://www.wikidata.org/wiki/Q2492) about Konrad Adenauer, the former Federal Chancellor of Germany.

This command gets 28 unique postcodes:
```sql
SELECT tags.value, COUNT(*) as count FROM
(SELECT * FROM nodes_tags UNION ALL
SELECT * FROM ways_tags) tags WHERE tags.key='postcode'
GROUP BY tags.value ORDER BY count ASC;
```
![](https://user-images.githubusercontent.com/33815535/33530961-0974f2dc-d887-11e7-9059-c34a344f62fe.JPG)  
6 records from nodes_tags with the postcode 53754 and the type 'contact' are reserved for  
Institute Center Schloss Birlinghoven - a german informatic research center. It is possible for big companies  
in Germany to have an own postcode but it is only one case in the Openstreet for this big area  
and it is an IT research company.

### Conclusion
Even if you do not take into account technical errors in mass automatic data import, language differences and nuances are a big source of errors. I'm sure I have found only a part of them.
It is obvious that the OpenStreetMap is not exhaustive and has small inaccuracy but is usefull, open and free too use. It is usefull not only as map, but also as a database. E.g. I can find opening hours of my hairdresser with one shot query -)
```sql
SELECT * FROM nodes_tags WHERE id IN (
SELECT id FROM nodes_tags WHERE value LIKE '%by sam%');
```
![](https://user-images.githubusercontent.com/33815535/33530958-08a59bcc-d887-11e7-9e9f-4e6e2f20b800.JPG)
