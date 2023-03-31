import enum


class ScNames(enum.Enum):
    RDF_TYPES = 'RDF types'
    GEOM_FIELD = 'geometry'
    OUTPUT_LAYER_NAME = 'Output layer name'
    INCLUDE_DEFAULT_TYPE = 'Include default type'
    OUTPUT_FIELD_NAME = 'Output field name'
    LITERAL_TYPE = 'Literal type'
    INCLUDE_DEFAULT_RDF_TYPE = 'Include default RDF Type'
    CUSTOM_URI = 'Custom URI'
    AS_RELATION = 'As Relation'
    URI_KEY = 'Uri Key'
    WGS84_BASIC_GEO = 'WGS84 Basic Geo'
    GEOSPARQL_WKT = 'GeoSPARQL WKT'
    XML_SCHEMA_BASE_URI = 'http://www.w3.org/2001/XMLSchema#'

    SC_GEOM = 'sc_geom'
    GEOMETRY = 'geometry'
    LON = 'lon'
    LAT = 'lat'
    LON_LAT = 'lon_lat'
    GEOMETRY_VARIABLE = 'sc_geometry_variable'

    SC_SAVE_FORMAT = 'sc_save_format'
    GEOJSON = 'GeoJSON'
    GEOPACKAGE = 'GPKG'
    MEMORY = 'Memory'

