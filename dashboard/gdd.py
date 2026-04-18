import datetime

# -----------------------------
# 1. Crop Database
# -----------------------------
class DefaultCropDB(dict):
    def __missing__(self, key):
        # Universal fallback for any unsupported/unknown crop
        return {
            "base_temp": 10,
            "stages": {
                "germination": 150,
                "vegetative": 1000,
                "flowering": 1600,
                "harvest": 2100
            }
        }

CROP_DB = DefaultCropDB({
    "wheat": {
        "base_temp": 5,
        "stages": {
            "germination": 150,
            "vegetative": 900,
            "flowering": 1400,
            "harvest": 1800
        }
    },
    "rice": {
        "base_temp": 10,
        "stages": {
            "germination": 200,
            "vegetative": 1000,
            "flowering": 1600,
            "harvest": 2100
        }
    },
    "maize": {
        "base_temp": 10,
        "stages": {
            "germination": 120,
            "vegetative": 800,
            "flowering": 1300,
            "harvest": 1800
        }
    },
    "chickpea": {
        "base_temp": 5,
        "stages": {
            "germination": 100,
            "vegetative": 700,
            "flowering": 1100,
            "harvest": 1500
        }
    },
    "kidneybeans": {
        "base_temp": 10,
        "stages": {
            "germination": 90,
            "vegetative": 600,
            "flowering": 1000,
            "harvest": 1300
        }
    },
    "pigeonpeas": {
        "base_temp": 10,
        "stages": {
            "germination": 150,
            "vegetative": 1200,
            "flowering": 1800,
            "harvest": 2500
        }
    },
    "mothbeans": {
        "base_temp": 10,
        "stages": {
            "germination": 80,
            "vegetative": 500,
            "flowering": 800,
            "harvest": 1100
        }
    },
    "mungbean": {
        "base_temp": 10,
        "stages": {
            "germination": 80,
            "vegetative": 500,
            "flowering": 800,
            "harvest": 1100
        }
    },
    "blackgram": {
        "base_temp": 10,
        "stages": {
            "germination": 90,
            "vegetative": 550,
            "flowering": 900,
            "harvest": 1200
        }
    },
    "lentil": {
        "base_temp": 5,
        "stages": {
            "germination": 100,
            "vegetative": 700,
            "flowering": 1100,
            "harvest": 1500
        }
    },
    "pomegranate": {
        "base_temp": 12,
        "stages": {
            "germination": 300,
            "vegetative": 2000,
            "flowering": 3500,
            "harvest": 5000
        }
    },
    "banana": {
        "base_temp": 12,
        "stages": {
            "germination": 400,
            "vegetative": 3000,
            "flowering": 5000,
            "harvest": 7000
        }
    },
    "mango": {
        "base_temp": 10,
        "stages": {
            "germination": 500,
            "vegetative": 4000,
            "flowering": 7000,
            "harvest": 10000
        }
    },
    "grapes": {
        "base_temp": 10,
        "stages": {
            "germination": 300,
            "vegetative": 2000,
            "flowering": 3500,
            "harvest": 5000
        }
    },
    "watermelon": {
        "base_temp": 10,
        "stages": {
            "germination": 100,
            "vegetative": 600,
            "flowering": 900,
            "harvest": 1200
        }
    },
    "muskmelon": {
        "base_temp": 10,
        "stages": {
            "germination": 100,
            "vegetative": 600,
            "flowering": 900,
            "harvest": 1200
        }
    },
    "apple": {
        "base_temp": 7,
        "stages": {
            "germination": 400,
            "vegetative": 3000,
            "flowering": 6000,
            "harvest": 9000
        }
    },
    "orange": {
        "base_temp": 10,
        "stages": {
            "germination": 300,
            "vegetative": 2500,
            "flowering": 4500,
            "harvest": 6500
        }
    },
    "papaya": {
        "base_temp": 12,
        "stages": {
            "germination": 200,
            "vegetative": 1500,
            "flowering": 3000,
            "harvest": 4500
        }
    },
    "coconut": {
        "base_temp": 12,
        "stages": {
            "germination": 600,
            "vegetative": 5000,
            "flowering": 8000,
            "harvest": 12000
        }
    },
    "cotton": {
        "base_temp": 15,
        "stages": {
            "germination": 150,
            "vegetative": 900,
            "flowering": 1500,
            "harvest": 2200
        }
    },
    "jute": {
        "base_temp": 15,
        "stages": {
            "germination": 120,
            "vegetative": 800,
            "flowering": 1200,
            "harvest": 1600
        }
    },
    "coffee": {
        "base_temp": 10,
        "stages": {
            "germination": 500,
            "vegetative": 4000,
            "flowering": 7000,
            "harvest": 10000
        }
    }
})

# -----------------------------
# 2. Soil Modifier
# -----------------------------
SOIL_FACTOR = {
    "sandy": 0.85,
    "loamy": 1.0,
    "clayey": 1.1
}

# -----------------------------
# 3. Base GDD
# -----------------------------
def compute_gdd(tmax, tmin, base_temp):
    avg = (tmax + tmin) / 2
    return max(0, avg - base_temp)

# -----------------------------
# 4. Stress Functions
# -----------------------------
def temperature_factor(avg_temp):
    if avg_temp > 35:
        return 1.1
    elif avg_temp < 10:
        return 0.7
    return 1.0

def rainfall_factor(rain_7d):
    if rain_7d < 10:
        return 0.85
    elif rain_7d < 50:
        return 1.0
    elif rain_7d < 120:
        return 0.95
    return 0.8

def compute_stress(window, soil_type):
    if not window:
        return 1.0

    avg_temp = sum([(d["tmax"] + d["tmin"]) / 2 for d in window]) / len(window)
    rain_sum = sum([d["rain"] for d in window])

    tf = temperature_factor(avg_temp)
    rf = rainfall_factor(rain_sum)
    sf = SOIL_FACTOR.get(soil_type, 1.0)

    return tf * rf * sf

# -----------------------------
# 5. GDD Accumulation
# -----------------------------
def accumulate_gdd(weather, crop, soil_type):
    base_temp = crop["base_temp"]
    total_gdd = 0
    history = []

    for i, day in enumerate(weather):
        base_gdd = compute_gdd(day["tmax"], day["tmin"], base_temp)

        window = weather[max(0, i-7):i]
        stress = compute_stress(window, soil_type)

        effective_gdd = base_gdd * stress
        total_gdd += effective_gdd

        history.append({
            "date": day["date"],
            "gdd": total_gdd
        })

    return total_gdd, history

# -----------------------------
# 6. Stage Detection
# -----------------------------
def get_stage(gdd, crop):
    thresholds = crop["stages"]

    if gdd < thresholds["germination"]:
        return "germination"
    elif gdd < thresholds["vegetative"]:
        return "vegetative"
    elif gdd < thresholds["flowering"]:
        return "flowering"
    return "harvest"

# -----------------------------
# 7. Stage Progress
# -----------------------------
def stage_progress(gdd, crop):
    thresholds = crop["stages"]
    prev = 0

    for stage, value in thresholds.items():
        if gdd < value:
            return (gdd - prev) / (value - prev)
        prev = value

    return 1.0

# -----------------------------
# 8. Future Simulation
# -----------------------------
def simulate_future(current_gdd, forecast, crop, soil_type):
    base_temp = crop["base_temp"]
    thresholds = crop["stages"]

    gdd = current_gdd
    results = {}

    for i, day in enumerate(forecast):
        base_gdd = compute_gdd(day["tmax"], day["tmin"], base_temp)

        window = forecast[max(0, i-7):i]
        stress = compute_stress(window, soil_type)

        gdd += base_gdd * stress

        for stage, threshold in thresholds.items():
            if stage not in results and gdd >= threshold:
                results[stage] = day["date"]

    return results

# -----------------------------
# 9. Confidence Range
# -----------------------------
def simulate_variation(current_gdd, forecast, crop, soil_type, temp_shift):
    base_temp = crop["base_temp"]
    thresholds = crop["stages"]

    gdd = current_gdd
    results = {}

    for i, day in enumerate(forecast):
        tmax = day["tmax"] + temp_shift
        tmin = day["tmin"] + temp_shift

        base_gdd = compute_gdd(tmax, tmin, base_temp)

        window = forecast[max(0, i-7):i]
        stress = compute_stress(window, soil_type)

        gdd += base_gdd * stress

        for stage, threshold in thresholds.items():
            if stage not in results and gdd >= threshold:
                results[stage] = day["date"]

    return results

# -----------------------------
# 10. MAIN FUNCTION
# -----------------------------
def run_simulation(crop_name, soil_type, past_weather, forecast_weather):
    crop = CROP_DB[crop_name]

    current_gdd, history = accumulate_gdd(past_weather, crop, soil_type)

    stage = get_stage(current_gdd, crop)
    progress = stage_progress(current_gdd, crop)

    predictions = simulate_future(current_gdd, forecast_weather, crop, soil_type)

    lower = simulate_variation(current_gdd, forecast_weather, crop, soil_type, -2)
    upper = simulate_variation(current_gdd, forecast_weather, crop, soil_type, +2)

    return {
        "current_stage": stage,
        "progress_percent": round(progress * 100, 2),
        "current_gdd": round(current_gdd, 2),
        "predicted_dates": predictions,
        "confidence_lower": lower,
        "confidence_upper": upper,
        "gdd_history": history
    }