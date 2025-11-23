import sys
import os
import requests

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction.src.predict import DustStormPredictor


def test_prediction_logic():
    print("Testing Prediction Logic...")

    # 1. Initialize Predictor
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(base_dir, "prediction", "saved_models")
    print(f"Model Dir: {model_dir}")

    try:
        predictor = DustStormPredictor(model_dir=model_dir)
        print("Predictor initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize predictor: {e}")
        return

    # 2. Mock Data (similar to what we expect from Open-Meteo)
    features = {
        "Temperature": 25.0,
        "Humidity": 40.0,
        "Wind_speed": 15.0,
        "Pressure": 1013.0,
        "Visibility": 10.0,  # km
        "Snow_depth": 0.0,
    }

    # 3. Predict
    try:
        result = predictor.predict_single(station=1, features=features)
        print("Prediction Result:")
        print(result)
    except Exception as e:
        print(f"Prediction failed: {e}")

    # 4. Test Open-Meteo Connection
    print("\nTesting Open-Meteo Connection...")
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 41.3,  # Tashkent approx
                "longitude": 69.2,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure,visibility,snow_depth",
                "wind_speed_unit": "ms",
            },
            timeout=10,
        )
        if response.status_code == 200:
            print("Open-Meteo API reachable.")
            data = response.json()
            print("Sample Data:", data["current"])
        else:
            print(f"Open-Meteo API returned {response.status_code}")
    except Exception as e:
        print(f"Open-Meteo connection failed: {e}")


if __name__ == "__main__":
    test_prediction_logic()
