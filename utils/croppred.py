import pandas as pd
import numpy as np
import requests
from geopy.geocoders import Nominatim
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

import os

# --- CONFIGURATION ---
# Replace with your OpenWeatherMap API Key
WEATHER_API_KEY = "9263dfa9885ef03419fe5827ebb00de1" 
DATASET_PATH = os.path.join(os.path.dirname(__file__), "soildata.csv")

def get_coordinates(district_name):
    """Converts District Name to Lat/Lon"""
    geolocator = Nominatim(user_agent="crop_rec_system")
    location = geolocator.geocode(f"{district_name}, India")
    if location:
        return location.latitude, location.longitude
    return None, None

def get_soil_data(lat, lon):
    """Fetches and converts SoilGrids data to CSV units"""
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {"lon": lon, "lat": lat, "depth": "0-5cm", "value": "mean"}
    
    response = requests.get(url, params=params)
    if response.status_code != 200: return None, None
    
    raw_data = {l['name']: l['depths'][0]['values']['mean'] for l in response.json()['properties']['layers']}
    
    # IMPUTE MISSING URBAN PIXELS: Geocoder often resolves to city-centers which lack SoilGrid coverage.
    default_soil = {
        'bdod': 120, 'cec': 200, 'cfvo': 50, 'clay': 300, 
        'nitrogen': 1500, 'ocd': 200, 'phh2o': 65, 'sand': 450, 
        'silt': 250, 'soc': 150, 'wv0010': 300, 'wv0033': 200, 'wv1500': 100
    }
    for k in raw_data.keys():
        if raw_data[k] is None:
            raw_data[k] = default_soil.get(k, 0)
    
    # --- UNIT CONVERSION LOGIC ---
    processed_soil = {
        # PHH2O is in pH*10 -> divide by 10 for standard pH
        "Soil_pH": (raw_data.get('phh2o') or 0) / 10,
        
        # NITROGEN in cg/kg. Convert to ppm (approx 5% available for dataset match)
        "Soil_Nitrogen": ((raw_data.get('nitrogen') or 0) * 0.5), 
        
        # SOC is in dg/kg. Organic Matter % = (SOC / 100) * 1.724
        "Soil_Organic_Matter": ((raw_data.get('soc') or 0) / 100) * 1.724 
    }
    return processed_soil, raw_data

def get_weather_data(lat, lon):
    """Fetches current weather (Simulation of Rainfall/Humidity)"""
    # Note: For annual rainfall, historical APIs like Open-Meteo are better.
    # This uses a standard weather API call structure.
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    resp = requests.get(url).json()
    
    return {
        "Temperature": resp['main']['temp'],
        "Humidity": resp['main']['humidity'],
        "Rainfall": 1000 # Default annual mean if API doesn't provide historical
    }

def recommend_crop(district):
    # 1. Get Location
    lat, lon = get_coordinates(district)
    if not lat: return [], {}
    
    # 2. Get API Data
    soil, raw_soil_data = get_soil_data(lat, lon)
    if not soil: return [], {}
    weather = get_weather_data(lat, lon)
    
    # 3. Create Input Vector
    input_data = {**soil, **weather}
    query_df = pd.DataFrame([input_data])
    
    # 4. Vector Similarity on Dataset
    df = pd.read_csv(DATASET_PATH)
    features = ["Soil_pH", "Soil_Nitrogen", "Soil_Organic_Matter", "Temperature", "Rainfall", "Humidity"]
    
    # Scaling is mandatory for Similarity Search
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[features])
    query_scaled = scaler.transform(query_df[features])
    
    # Calculate Similarity
    sim = cosine_similarity(query_scaled, X_scaled).flatten()
    df['similarity'] = sim
    
    # Return top 3 matches as a list
    top_matches = df.sort_values('similarity', ascending=False).head(3)
    
    result_crops = []
    for i in range(len(top_matches)):
        crop = top_matches.iloc[i]['Crop_Type']
        result_crops.append(crop)
        
    return result_crops, raw_soil_data

# --- EXECUTION ---
print(recommend_crop("Bhagalpur"))