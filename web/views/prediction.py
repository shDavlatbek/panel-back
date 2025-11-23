from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..models import Station
from prediction.src.predict import DustStormPredictor
import requests
import os


class PredictionView(APIView):
    """
    View for handling predictions
    """

    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize predictor with the correct path to saved_models
        # Assuming saved_models is in prediction/saved_models
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels to web, then up one to root, then into prediction/saved_models
        # c:\Users\Xensa\Desktop\panel-back\web\views\prediction.py
        # -> c:\Users\Xensa\Desktop\panel-back\web\views
        # -> c:\Users\Xensa\Desktop\panel-back\web
        # -> c:\Users\Xensa\Desktop\panel-back
        # -> c:\Users\Xensa\Desktop\panel-back\prediction\saved_models

        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        model_dir = os.path.join(base_dir, "prediction", "saved_models")

        try:
            self.predictor = DustStormPredictor(model_dir=model_dir)
        except Exception as e:
            print(f"Error initializing predictor: {e}")
            self.predictor = None

    @swagger_auto_schema(
        tags=["Predictions"],
        operation_description="Get dust storm prediction for a station based on current weather",
        manual_parameters=[
            openapi.Parameter(
                "station_number",
                openapi.IN_PATH,
                description="Station Number",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                description="Prediction data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "result": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "station": openapi.Schema(type=openapi.TYPE_STRING),
                                "prediction": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                "probability": openapi.Schema(type=openapi.TYPE_NUMBER),
                                "current_weather": openapi.Schema(
                                    type=openapi.TYPE_OBJECT
                                ),
                                "model_probabilities": openapi.Schema(
                                    type=openapi.TYPE_OBJECT
                                ),
                            },
                        ),
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: "Station not found",
            500: "Internal Server Error",
        },
    )
    def get(self, request, station_number):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=f"Station {station_number} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
            )

        # Fetch weather data from Open-Meteo
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": station.lat,
                    "longitude": station.lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure,visibility,snow_depth",
                    "wind_speed_unit": "ms",  # Ensure m/s
                },
                timeout=10,
            )
            response.raise_for_status()
            weather_data = response.json()
            current = weather_data.get("current", {})
        except Exception as e:
            return custom_response(
                detail=f"Failed to fetch weather data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
            )

        # Map to model features
        # Model expects: Temperature, Humidity, Wind_speed, Pressure, Visibility, Snow_depth
        # Open-Meteo gives: temperature_2m, relative_humidity_2m, wind_speed_10m, surface_pressure, visibility (m), snow_depth (m)

        try:
            features = {
                "Temperature": current.get("temperature_2m"),
                "Humidity": current.get("relative_humidity_2m"),
                "Wind_speed": current.get("wind_speed_10m"),
                "Pressure": current.get("surface_pressure"),
                "Visibility": current.get("visibility", 0) / 1000.0,  # Convert m to km
                "Snow_depth": current.get("snow_depth", 0)
                * 100.0,  # Convert m to cm (assuming Open-Meteo is m, model is cm)
            }

            # Open-Meteo snow_depth is in meters? Docs say "Snow depth on the ground" in meters usually?
            # Checking Open-Meteo docs: "snow_depth" unit is meters.
            # Model expects cm. So * 100 is correct.

        except Exception as e:
            return custom_response(
                detail=f"Error processing weather data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
            )

        if not self.predictor:
            return custom_response(
                detail="Prediction model not initialized",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
            )

        try:
            # Predict
            # Note: station_number is string in URL, but model might expect int if it uses it for embeddings?
            # PREDICTION_GUIDE says station=1 (int).
            # Station model has number as IntegerField.
            # So we pass int(station.number).

            result = self.predictor.predict_single(
                station=station.number, features=features
            )

            response_data = {
                "station": station.number,
                "prediction": bool(result["prediction"]),  # Ensure native bool
                "probability": float(result["probability"]),
                "current_weather": features,
                "model_probabilities": result.get("model_probabilities", {}),
            }

            return custom_response(data=response_data, status_code=status.HTTP_200_OK)

        except Exception as e:
            return custom_response(
                detail=f"Prediction failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
            )
