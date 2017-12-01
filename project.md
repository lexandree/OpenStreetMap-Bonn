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


**SELECT * FROM nodes_tags WHERE id in (SELECT id FROM nodes_tags WHERE key ='amenity'<br />
AND value='charging_station');**<br />
There are only 8 charging stations with capacity 12 for electric cars in the city.<br />

**SELECT count(*) AS cc, value FROM ways_tags WHERE key='etymology:wikidata'<br />
GROP BY value ORDER BY cc DESC;**<br />
this sql commando counts 1768 records and gets 402 unique references to wikidata. The most popular reference<br />
with the occurence 95 or 0.5% is the Q2492 about Konrad Adenauer, the former Federal Chancellor of Germany.<br />

**SELECT tags.value, COUNT(*) as count FROM<br />
(SELECT * FROM nodes_tags UNION ALL<br />
SELECT * FROM ways_tags) tags WHERE tags.key='postcode'<br />
GROUP BY tags.value ORDER BY count DESC;**<br />
the commando gets 28 unique postcodes.<br />
6 records from nodes_tags with the postcode 53754 and type 'contact' reserved for<br />
Institute Center Schloss Birlinghoven - a german informatic research center. It possible for big companies<br />
in Germany to become an own postcode but it is only one in Openstreet for this big area<br />
and it is an IT research company.<br />

Two users founded they have different german spelling interpretation.<br />
User Ashley99:<br />
**SELECT nodes_tags.*, user<br />
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id<br />
WHERE value LIKE 'kolnstr';**<br />
- false versions are **tag k="addr:street" v="Kolnstr"** 5 records and one record with **v=kolnstr**<br />
- a right version is **tag k="addr:street" v="Kölnstraße"**<br />

Set the right value:<br />
**UPDATE nodes_tags SET value='Kölnstraße'<br />
WHERE key='street' AND value LIKE 'kolnstr' AND type='addr';**<br />

Both users Ashley99 again and wheelmap_visitor have 'straße' as 'strasse' misspelled:<br />
**SELECT nodes_tags.*, user<br />
FROM nodes_tags LEFT JOIN nodes ON nodes.id = nodes_tags.id<br />
WHERE value LIKE '%strasse'; ** -- givs 12 records<br />
