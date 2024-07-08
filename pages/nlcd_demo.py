import ee
import json
import streamlit as st
import geemap.foliumap as geemap
from google.oauth2 import service_account
from ee import oauth
from ipyleaflet import *
from bqplot import pyplot as plt

# Initialize EE helper fn
def ee_initialize(force_use_service_account=False):
    if force_use_service_account or "json_data" in st.secrets:
        json_credentials = st.secrets["json_data"]
        credentials_dict = json.loads(json_credentials)
        if 'client_email' not in credentials_dict:
            raise ValueError("Service account info is missing 'client_email' field.")
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=oauth.SCOPES
        )
        ee.Initialize(credentials)
    else:
        ee.Initialize()
        
# Initialize GEE
ee_initialize(force_use_service_account=True)

# Get AOP data
NEON_SITE = 'SOAP'
# Import the AOP surface directional reflectance (SDR)
aopSDR = ee.ImageCollection('projects/neon-prod-earthengine/assets/DP3-30006-001')
site_2021_sdr = aopSDR \
  .filterDate('2021-01-01', '2021-12-31') \
  .filterMetadata('NEON_SITE', 'equals', NEON_SITE) \
  .first()

# Select the WL_FWHM_B*** band properties (using regex)
properties = site_2021_sdr.toDictionary()
wl_fwhm_dict = properties.select(['WL_FWHM_B+\d{3}'])

# Pull out the wavelength, fwhm values to a list
wl_fwhm_list = wl_fwhm_dict.values()

# Function to pull out the wavelength values only and convert the string to float
def get_wavelengths(x):
  str_split = ee.String(x).split(',')
  first_elem = ee.Number.parse((str_split.get(0)))
  return first_elem

# apply the function to the wavelength full-width-half-max list
wavelengths = wl_fwhm_list.map(get_wavelengths)

# Create page layout
st.header("National Ecological Observatory Network (NEON) Airborne Observation Platform (AOP) reflectance data")

# Create a layout containing two columns, one for the map and one for the layer dropdown list.
row1_col1, row1_col2 = st.columns([3, 1])

# Create an interactive map
m = geemap.Map()
m.default_style = {"cursor": "crosshair"}


# Update map
with row1_col1:
    m.centerObject(site_2021_sdr)
    
    figure = plt.figure(
        1,
        title="Reflectance",
        layout={"height": "200px", "width": "600px"},
    )
    
    
    # Set up variables for plotting markers, reflectance
    x = wavelengths.getInfo()
    coordinates = []
    markers = []
    marker_cluster = MarkerCluster(name="Marker Cluster")
    #m.add_layer(marker_cluster)
    
    # Helper function called each time we click a new point
    def handle_interaction(**kwargs):
        latlon = kwargs.get("coordinates")
        if kwargs.get("type") == "click":
          try:
            coordinates.append(latlon)
            markers.append(Marker(location=latlon))
            marker_cluster.markers = markers
            xy = ee.Geometry.Point(latlon[::-1])
            y = site_2021_sdr.select('B.*').sample(xy, 1).first().toDictionary().values().getInfo()
            plt.clear()
            plt.plot(x, y)
          except:
            print('Please click a point inside the TEAK box.')
    
    
    m.on_interaction(handle_interaction)
    
    fig_control = WidgetControl(widget=figure, position="bottomright")
    m.add_control(fig_control)

    m.to_streamlit(height=600)
