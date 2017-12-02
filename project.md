# OpenStreetMap-Bonn
# Wrangle OpenStreetMap Data

## Map Area 

Bonn, Germany.

I have got the data direct from the site using the export tool.

I'm from St.Petersburg, Russia, but live in Bonn last ten years. The map of St.Petersburg weights 944MB and it is too big for this work. The osm map file of Bonn weights 230MB only and is precisely created. 
Nevertheless, there is always something to improve.

### Project

I had set k=10 for the test run and got the csv files to import into the database. I chose the SQLite database and DB Browser for SQLite to interact with the database. The test import of nodes and ways passed without problems, but the slave tables rejected the data because of the constraints of the database's integrity (since k=10).
Having evaluated the time of the validation task, I used a dedicated server to get validated csv files for import. Import to the database went errorfree.


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
returns 1309 - number of unique users and they created 1109320 records in both tables - **nodes** and **ways**.  

```sql
SELECT SUM(cc) FROM
(SELECT count(uid) AS cc, uid FROM
(SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) AS nodes_ways_users
GROUP BY uid ORDER BY cc DESC LIMIT 131);
```
returns 1084789 - number of records created by top 10% or 131 users. It is 98% of the all records.  



### Problems found in the data

- Misspelled street names

Two users founded they have different german spelling interpretation.  
Users Ashley99 and wheelmap_visitor:  
```
SELECT nodes_tags.*, user
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id
WHERE key ='street' AND value LIKE 'kolnstr%';
```
- false spelling is **tag k="addr:street" v="Kolnstr"** 5 records, **v=kolnstrasse** 5 records and one record with **v=kolnstr**  
- a right version is **tag k="addr:street" v="Kölnstraße"**

Set the right values:
```
UPDATE nodes_tags SET value='Kölnstraße'
WHERE key='street' AND type='addr' AND value LIKE 'kolnstr%';
```

Both users have '-straße' as '-strasse' misspelled:  
```
SELECT nodes_tags.*, user
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id
WHERE value LIKE '%strasse';
```
- shows 7 records

Set the right values:
```
UPDATE nodes_tags SET value=replace(value,'trasse','traße')
WHERE key ='street' AND value LIKE '%strasse';
```


There are only 8 charging stations with capacity 12 for electric cars in the city:
```
SELECT * FROM nodes_tags WHERE id in (SELECT id FROM nodes_tags WHERE key ='amenity'
AND value='charging_station');
```
  

This sql commando counts 1768 records and gets 402 unique references to wikidata. The most popular reference  
with the occurence 95 or 0.5% is the Q2492 about Konrad Adenauer, the former Federal Chancellor of Germany.
```
SELECT count(*) AS cc, value FROM ways_tags WHERE key='etymology:wikidata'
GROP BY value ORDER BY cc DESC;
```
The commando gets 28 unique postcodes:
```
SELECT tags.value, COUNT(*) as count FROM
(SELECT * FROM nodes_tags UNION ALL
SELECT * FROM ways_tags) tags WHERE tags.key='postcode'
GROUP BY tags.value ORDER BY count ASC;
```
6 records from nodes_tags with the postcode 53754 and type 'contact' reserved for  
Institute Center Schloss Birlinghoven - a german informatic research center. It possible for big companies  
in Germany to become an own postcode but it is only one in Openstreet for this big area  
and it is an IT research company.

