#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
After auditing is complete the next step is to prepare the data to be inserted into a SQL database.
To do so you will parse the elements in the OSM XML file, transforming them from document format to
tabular format, thus making it possible to write to .csv files.  These csv files can then easily be
imported to a SQL database as tables.

The process for this transformation is as follows:
- Use iterparse to iteratively step through each top level element in the XML
- Shape each element into several data structures using a custom function
- Utilize a schema and validation library to ensure the transformed data is in the correct format
- Write each data structure to the appropriate .csv files

We've already provided the code needed to load the data, perform iterative parsing and write the
output to csv files. Your task is to complete the shape_element function that will transform each
element into the correct format. To make this process easier we've already defined a schema (see
the schema.py file in the last code tab) for the .csv files and the eventual tables. Using the 
cerberus library we can validate the output against this schema to ensure it is correct.

## Shape Element Function
The function should take as input an iterparse Element object and return a dictionary.

### If the element top level tag is "node":
The dictionary returned should have the format {"node": .., "node_tags": ...}

The "node" field should hold a dictionary of the following top level node attributes:
- id
- user
- uid
- version
- lat
- lon
- timestamp
- changeset
All other attributes can be ignored

The "node_tags" field should hold a list of dictionaries, one per secondary tag. Secondary tags are
child tags of node which have the tag name/type: "tag". Each dictionary should have the following
fields from the secondary tag attributes:
- id: the top level node id attribute value
- key: the full tag "k" attribute value if no colon is present or the characters after the colon if one is.
- value: the tag "v" attribute value
- type: either the characters before the colon in the tag "k" value or "regular" if a colon
        is not present.

Additionally,

- if the tag "k" value contains problematic characters, the tag should be ignored
- if the tag "k" value contains a ":" the characters before the ":" should be set as the tag type
  and characters after the ":" should be set as the tag key
- if there are additional ":" in the "k" value they and they should be ignored and kept as part of
  the tag key. For example:

  <tag k="addr:street:name" v="Lincoln"/>
  should be turned into
  {'id': 12345, 'key': 'street:name', 'value': 'Lincoln', 'type': 'addr'}

- If a node has no secondary tags then the "node_tags" field should just contain an empty list.

The final return value for a "node" element should look something like:

{'node': {'id': 757860928,
          'user': 'uboot',
          'uid': 26299,
       'version': '2',
          'lat': 41.9747374,
          'lon': -87.6920102,
          'timestamp': '2010-07-22T16:16:51Z',
      'changeset': 5288876},
 'node_tags': [{'id': 757860928,
                'key': 'amenity',
                'value': 'fast_food',
                'type': 'regular'},
               {'id': 757860928,
                'key': 'cuisine',
                'value': 'sausage',
                'type': 'regular'},
               {'id': 757860928,
                'key': 'name',
                'value': "Shelly's Tasty Freeze",
                'type': 'regular'}]}

### If the element top level tag is "way":
The dictionary should have the format {"way": ..., "way_tags": ..., "way_nodes": ...}

The "way" field should hold a dictionary of the following top level way attributes:
- id
-  user
- uid
- version
- timestamp
- changeset

All other attributes can be ignored

The "way_tags" field should again hold a list of dictionaries, following the exact same rules as
for "node_tags".

Additionally, the dictionary should have a field "way_nodes". "way_nodes" should hold a list of
dictionaries, one for each nd child tag.  Each dictionary should have the fields:
- id: the top level element (way) id
- node_id: the ref attribute value of the nd tag
- position: the index starting at 0 of the nd tag i.e. what order the nd tag appears within
            the way element

The final return value for a "way" element should look something like:

{'way': {'id': 209809850,
         'user': 'chicago-buildings',
         'uid': 674454,
         'version': '1',
         'timestamp': '2013-03-13T15:58:04Z',
         'changeset': 15353317},
 'way_nodes': [{'id': 209809850, 'node_id': 2199822281, 'position': 0},
               {'id': 209809850, 'node_id': 2199822390, 'position': 1},
               {'id': 209809850, 'node_id': 2199822392, 'position': 2},
               {'id': 209809850, 'node_id': 2199822369, 'position': 3},
               {'id': 209809850, 'node_id': 2199822370, 'position': 4},
               {'id': 209809850, 'node_id': 2199822284, 'position': 5},
               {'id': 209809850, 'node_id': 2199822281, 'position': 6}],
 'way_tags': [{'id': 209809850,
               'key': 'housenumber',
               'type': 'addr',
               'value': '1412'},
              {'id': 209809850,
               'key': 'street',
               'type': 'addr',
               'value': 'West Lexington St.'},
              {'id': 209809850,
               'key': 'street:name',
               'type': 'addr',
               'value': 'Lexington'},
              {'id': '209809850',
               'key': 'street:prefix',
               'type': 'addr',
               'value': 'West'},
              {'id': 209809850,
               'key': 'street:type',
               'type': 'addr',
               'value': 'Street'},
              {'id': 209809850,
               'key': 'building',
               'type': 'regular',
               'value': 'yes'},
              {'id': 209809850,
               'key': 'levels',
               'type': 'building',
               'value': '1'},
              {'id': 209809850,
               'key': 'building_id',
               'type': 'chicago',
               'value': '366409'}]}
"""

import csv
import codecs
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "example.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

import io
import json
import googlemaps
from metaphone import doublemetaphone 
STREETS_PATH = 'checked_streets.json'
checked_streets = {}

def get_route(address_components):
    #gets the street name from Googles address_components list
    for component in address_components:
        if 'route' in component['types']:
            return component['long_name']

def ask_google(parent_node, street_tag, checked_routes):
    #
    #check the first occurence of a street by its coordinate by Google
    #with the Google Maps APIs Premium Plan every point can by checked, 
    #without the Premium Plan you have only 2,500 free requests per day

    # return existing value from dictionary without check. 
    if street_tag['value'] in checked_routes and checked_routes[street_tag['value']]!='':
        return checked_routes[street_tag['value']]

    #creating googlemaps client does not mean sending a request
    gmaps = googlemaps.Client(key='') #Google API user key

    # Look up an address with reverse geocoding
    reverse_geocode_result = gmaps.reverse_geocode((parent_node['lat'], parent_node['lon']))# e.g.((40.714224, -73.961452))
    # Google returns several address_components - a hierarchic structure: [address, district, city, ..]
    for address_components in reverse_geocode_result:
        # seek the first route in Google response
        google_street = get_route(address_components['address_components'])
        #print(google_street)
        # route is not found near this point, check the next address_component
        if google_street == None: 
            #print('street {0} from {1} is not found'.format(street_tag['value'], parent_node['id']))
            continue
        #the street is found by google and is conform 
        if street_tag['value'].lower().strip() == google_street.lower():
            checked_routes[street_tag['value']] = google_street
            return google_street
        #the street is misspelled but sounds conform, doublemetaphone+'S' is because shortening Straße->Str
        if doublemetaphone(street_tag['value'])[0] == doublemetaphone(google_street)[0] or \
            doublemetaphone(street_tag['value'])[0]+'S' == doublemetaphone(google_street)[0]:
            checked_routes[street_tag['value']] = google_street
            return google_street
    
    # route is not found near this point, this node is in OpenStreet only
    checked_routes[street_tag['value']] = ''
    return street_tag['value']

def shape_tag(subelement, parent_id):
    
    if LOWER_COLON.match(subelement.attrib.get('k')):
        tag_key = subelement.attrib.get('k')[subelement.attrib.get('k').index(':')+1:]
        tag_type = subelement.attrib.get('k')[:subelement.attrib.get('k').index(':')]
    else:
        tag_key = subelement.attrib.get('k')
        tag_type = 'regular'
    tag = {'id': parent_id, 
          'key': tag_key,    
          'value': subelement.attrib.get('v'),
          'type': tag_type} 
    return tag


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    if element.tag == 'node':
        for f in node_attr_fields:
            node_attribs[f] = element.attrib.get(f)
        for subelement in element.getiterator('tag'):
            if problem_chars.search(subelement.attrib.get('k')): 
                continue
            tag = shape_tag(subelement, element.attrib.get('id'))   
            #check street names by Google
            if (tag['key']=='street') and (tag['type']=='addr'):
                tag['value'] = ask_google(node_attribs, tag, checked_streets)
            tags.append(tag) 
            
        return {'node': node_attribs, 'node_tags': tags}
    
    elif element.tag == 'way':
        for f in way_attr_fields:
            way_attribs[f] = element.attrib.get(f)
        counter = 0
        for subelement in element.getiterator('nd'):
            way_nodes.append({'id': element.attrib.get('id'), 'node_id': subelement.attrib.get('ref'), 'position': counter})
            counter += 1
        #        way tags
        for subelement in element.getiterator('tag'):
            if problem_chars.search(subelement.attrib.get('k')): 
                continue
            tag = shape_tag(subelement, element.attrib.get('id'))    
            tags.append(tag) 
 
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.items())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.items()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )

# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""
    with open(NODES_PATH, 'w', encoding='utf-8') as nodes_file, \
            open(NODE_TAGS_PATH, 'w', encoding='utf-8') as nodes_tags_file, \
            open(WAYS_PATH, 'w', encoding='utf-8') as ways_file, \
            open(WAY_NODES_PATH, 'w', encoding='utf-8') as way_nodes_file, \
            open(WAY_TAGS_PATH, 'w', encoding='utf-8') as way_tags_file:

        nodes_writer = csv.DictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = csv.DictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = csv.DictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = csv.DictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = csv.DictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

OSM_IN_FILE = "bonn.osm"  # Replace this with your osm file

if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True) 
    if len(checked_streets)>0:
       # Write JSON file
        with io.open(STREETS_PATH, 'w', encoding='utf8') as outfile:
            str_ = json.dumps(checked_streets,
                              indent=4, sort_keys=True,
                              separators=(',', ': '), ensure_ascii=False)
            outfile.write(str(str_))
