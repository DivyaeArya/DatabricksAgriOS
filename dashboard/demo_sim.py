import datetime
from gdd import CROP_DB, simulate_future, get_stage, stage_progress, simulate_variation

def main():
    current_gdd = 1100
    crop_name = "rice"
    crop = CROP_DB[crop_name]
    soil_type = "loamy"

    print(f"--- DEMO SIMULATION ---")
    print(f"Crop: {crop_name.capitalize()}")
    print(f"Current GDD: {current_gdd}")

    current_stage = get_stage(current_gdd, crop)
    progress = stage_progress(current_gdd, crop)

    print(f"Current Stage: {current_stage}")
    print(f"Progress in stage: {round(progress * 100, 2)}%")

    # Generate some fake forecast data for the next 60 days
    base_date = datetime.date.today()
    forecast = []
    for i in range(70):
        # Temp varies, let's say average tmax=32, tmin=24
        day_data = {
            "date": (base_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d"),
            "tmax": 32,
            "tmin": 24,
            "rain": 5
        }
        forecast.append(day_data)

    print("\nRunning simulation for upcoming stages...")
    predictions = simulate_future(current_gdd, forecast, crop, soil_type)
    lower = simulate_variation(current_gdd, forecast, crop, soil_type, -2)
    upper = simulate_variation(current_gdd, forecast, crop, soil_type, +2)

    # We only care about stages that are in the future
    future_stages = ["flowering", "harvest"]
    
    for stage in future_stages:
        if stage in predictions:
            print(f"\nStage: {stage.capitalize()}")
            print(f"  Expected Date: {predictions[stage]}")
            l_date = lower.get(stage, 'N/A')
            u_date = upper.get(stage, 'N/A')
            print(f"  Confidence Range: {l_date} (Pessimistic) to {u_date} (Optimistic)")

if __name__ == "__main__":
    main()
