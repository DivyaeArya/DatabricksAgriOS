import requests

def get_soil_properties(lat, lon):
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["nitrogen", "phh2o", "soc"], # Nitrogen, pH, Soil Organic Carbon
        "depth": "0-5cm",
        "value": "mean"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        properties = data['properties']['layers']
        
        for layer in properties:
            name = layer['name']
            val = layer['depths'][0]['values']['mean']
            unit = layer['unit_measure']['target_units']
            print(f"{name.upper()}: {val} {unit}")
    else:
        print("API Error:", response.status_code)

# Example: Coordinates for Bhagalpur, Bihar
get_soil_properties(25.24, 87.01)