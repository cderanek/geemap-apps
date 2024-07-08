import ee
import json
import streamlit as st
import geemap
import geemap.colormaps as cm
from google.oauth2 import service_account
from ee import oauth
import folium
import matplotlib.pyplot as plt
from streamlit_folium import st_folium

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

# Get AOP data
def get_AOP_data():
    NEON_SITE = 'SOAP'
    # Import the AOP surface directional reflectance (SDR)
    aopSDR = ee.ImageCollection('projects/neon-prod-earthengine/assets/DP3-30006-001')
    site_2021_sdr = aopSDR \
      .filterDate('2021-01-01', '2021-12-31') \
      .filterMetadata('NEON_SITE', 'equals', NEON_SITE) \
      .first()
    return site_2021_sdr

def get_wavelengths(site_2021_sdr):
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

    return wavelengths

# Function to create Folium map
def create_folium_map():
    m = folium.Map(location=[0, 0], zoom_start=2)
    return m

# Function to handle map click events
def handle_click(latlon):
    try:
        xy = ee.Geometry.Point(latlon[::-1])
        x = get_wavelengths(site_2021_sdr)
        y = site_2021_sdr.select('B.*').sample(xy, 1).first().toDictionary().values().getInfo()
        plt.figure(figsize=(8, 4))
        plt.plot(x, y)
        plt.xlabel('Wavelength')
        plt.ylabel('Reflectance')
        plt.title('Reflectance Spectrum')
        st.pyplot(plt)
    except Exception as e:
        st.error(f"Error: {e}")

def main():
    # Initialize GEE
    ee_initialize(force_use_service_account=True)

    # Import data
    site_2021_sdr = get_AOP_data()
    
    # Create page layout
    st.header("National Ecological Observatory Network (NEON) Airborne Observation Platform (AOP) reflectance data")

    # Create a layout containing two columns, one for the map and one for the layer dropdown list.
    row1_col1, row1_col2 = st.columns([3, 1])

    # Create a Folium map
    folium_map = create_folium_map()
    st_folium(m, width=725, returned_objects=[])

    # Click event handler for Folium map
    if folium_map.click_lat_lng:
        handle_click(folium_map.click_lat_lng)

if __name__ == '__main__':
    main()

