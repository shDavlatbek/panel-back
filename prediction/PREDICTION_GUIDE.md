# Dust Storm Prediction Module - Usage Guide

This guide shows how to use the trained models for making predictions outside of the training pipeline.

## Quick Start

```python
from src.predict import DustStormPredictor

# Initialize predictor
predictor = DustStormPredictor(model_dir='saved_models')

# Make a single prediction
result = predictor.predict_single(
    station=1,
    features={
        'Temperature': 28.5,
        'Humidity': 35.0,
        'Wind_speed': 22.0,
        'Pressure': 1010.5,
        'Visibility': 5.0,
        'Snow_depth': 0.0
    }
)

print(f"Probability: {result['probability']:.1%}")
print(f"Prediction: {'Dust Storm' if result['prediction'] else 'No Dust Storm'}")
```

## Installation

Make sure you have the required dependencies:

```bash
pip install -e .
```

## Main Classes and Functions

### `DustStormPredictor` Class

The main class for loading models and making predictions.

#### Initialize

```python
from src.predict import DustStormPredictor

predictor = DustStormPredictor(model_dir='saved_models')
```

#### Methods

##### 1. `predict_single()` - Single Prediction (Recommended)

```python
result = predictor.predict_single(
    station=1,
    features={
        'Temperature': 28.5,
        'Humidity': 35.0,
        'Wind_speed': 22.0,
        'Pressure': 1010.5,
        'Visibility': 5.0,
        'Snow_depth': 0.0
    }
)

# Returns:
# {
#     'station': 1,
#     'probability': 0.75,
#     'prediction': True,
#     'model_probabilities': {
#         'RF': 0.72,
#         'XGB': 0.78,
#         'LSTM': 0.74,
#         'CNNLSTM': 0.76
#     }
# }
```

##### 2. `predict()` - Batch Predictions

```python
import pandas as pd

# With DataFrame
df = pd.DataFrame({
    'Temperature': [25.5, 28.0, 30.5],
    'Humidity': [45.0, 38.0, 32.0],
    'Wind_speed': [15.0, 20.0, 25.0],
    'Pressure': [1013.0, 1011.0, 1009.0],
    'Visibility': [10.0, 7.0, 4.0],
    'Snow_depth': [0.0, 0.0, 0.0]
})

predictions = predictor.predict(
    station=1,
    data=df,
    feature_cols=df.columns.tolist()
)

# With numpy array
import numpy as np
data = np.array([
    [25.5, 45.0, 15.0, 1013.0, 10.0, 0.0],
    [28.0, 38.0, 20.0, 1011.0, 7.0, 0.0]
])

predictions = predictor.predict(station=1, data=data)
```

##### 3. `get_available_stations()` - List Trained Stations

```python
stations = predictor.get_available_stations()
print(f"Available stations: {stations}")
# Output: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
```

##### 4. `get_model_info()` - Get Model Information

```python
info = predictor.get_model_info(station=1)
print(f"Available models: {info['available_models']}")
# Output: ['scaler', 'random_forest', 'xgboost', 'lstm', 'cnn_lstm']
```

### Convenience Functions

#### `predict_dust_storm()` - Quick One-Line Prediction

```python
from src.predict import predict_dust_storm

predictions = predict_dust_storm(
    station=1,
    features={'Temperature': 25.5, 'Humidity': 45, ...}
)
```

#### `batch_predict()` - Multi-Station Batch Prediction

```python
from src.predict import batch_predict
import pandas as pd

df = pd.DataFrame({
    'Station': [1, 1, 2, 2, 3, 3],
    'Temperature': [25.5, 28.0, 26.0, 27.5, 24.0, 26.0],
    'Humidity': [45.0, 38.0, 44.0, 40.0, 50.0, 45.0],
    # ... other features
})

results = batch_predict(df, station_col='Station')
```

## Complete Examples

### Example 1: Real-Time Monitoring

```python
from src.predict import DustStormPredictor
import time

predictor = DustStormPredictor()

# Simulate real-time monitoring
while True:
    # Get current weather data (from your data source)
    current_conditions = {
        'Temperature': get_temperature(),
        'Humidity': get_humidity(),
        'Wind_speed': get_wind_speed(),
        'Pressure': get_pressure(),
        'Visibility': get_visibility(),
        'Snow_depth': get_snow_depth()
    }
    
    # Make prediction
    result = predictor.predict_single(station=1, features=current_conditions)
    
    if result['prediction']:
        print(f"⚠️ ALERT: Dust storm detected! Probability: {result['probability']:.1%}")
        # Send alert
    
    time.sleep(3600)  # Check every hour
```

### Example 2: Batch Forecasting

```python
from src.predict import DustStormPredictor
import pandas as pd

# Load forecast data
forecast_data = pd.read_csv('weather_forecast.csv')

# Make predictions for all stations
predictor = DustStormPredictor()

results = []
for station in forecast_data['Station'].unique():
    station_data = forecast_data[forecast_data['Station'] == station]
    
    predictions = predictor.predict(
        station=station,
        data=station_data,
        feature_cols=['Temperature', 'Humidity', 'Wind_speed', 
                     'Pressure', 'Visibility', 'Snow_depth']
    )
    results.append(predictions)

all_predictions = pd.concat(results)
all_predictions.to_csv('dust_storm_forecast.csv', index=False)
```

### Example 3: REST API Integration

```python
from flask import Flask, request, jsonify
from src.predict import DustStormPredictor

app = Flask(__name__)
predictor = DustStormPredictor()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    
    result = predictor.predict_single(
        station=data['station'],
        features=data['features']
    )
    
    return jsonify(result)

# Run: curl -X POST http://localhost:5000/predict \
#   -H "Content-Type: application/json" \
#   -d '{"station": 1, "features": {"Temperature": 28.5, ...}}'
```

## Feature Requirements

The models expect the following features in this order:

1. **Temperature** - Air temperature (°C)
2. **Humidity** - Relative humidity (%)
3. **Wind_speed** - Wind speed (m/s or km/h)
4. **Pressure** - Atmospheric pressure (hPa)
5. **Visibility** - Visibility distance (km)
6. **Snow_depth** - Snow depth (cm)

⚠️ **Important**: Feature names and order must match the training data!

## Output Format

### `predict_single()` output:

```python
{
    'station': 1,
    'probability': 0.75,          # Overall probability (0-1)
    'prediction': True,            # Binary prediction (True/False)
    'model_probabilities': {       # Individual model probabilities
        'RF': 0.72,
        'XGB': 0.78,
        'LSTM': 0.74,
        'CNNLSTM': 0.76
    }
}
```

### `predict()` output (DataFrame):

| Station | RF_Prob | XGB_Prob | LSTM_Prob | CNNLSTM_Prob | Mean_Prob | Prediction |
|---------|---------|----------|-----------|--------------|-----------|------------|
| 1       | 0.72    | 0.78     | 0.74      | 0.76         | 0.75      | 1          |
| 1       | 0.35    | 0.42     | 0.38      | 0.40         | 0.39      | 0          |

## Troubleshooting

### Error: "Model directory not found"

```python
# Make sure you trained the models first
python src/main.py

# Or specify the correct path
predictor = DustStormPredictor(model_dir='path/to/saved_models')
```

### Error: "No models found for station X"

```python
# Check available stations
stations = predictor.get_available_stations()
print(stations)

# Use one of the available stations
result = predictor.predict_single(station=stations[0], features=...)
```

### Error: "feature_cols must be provided when data is a DataFrame"

```python
# When using DataFrame, specify feature columns
predictions = predictor.predict(
    station=1,
    data=df,
    feature_cols=['Temperature', 'Humidity', 'Wind_speed', 
                 'Pressure', 'Visibility', 'Snow_depth']  # Add this!
)
```

## Running Examples

Try the provided examples:

```bash
python example_usage.py
```

This will demonstrate:
- Single predictions
- Batch predictions
- Multiple stations
- Different input formats
- Model availability checks

## Performance Tips

1. **Reuse predictor object**: Models are cached after first load
```python
predictor = DustStormPredictor()  # Load once
for data in many_predictions:
    predictor.predict_single(...)  # Reuse
```

2. **Batch predictions**: More efficient than single predictions
```python
# Good: Batch predict
predictor.predict(station=1, data=df_with_100_rows)

# Less efficient: Loop
for row in df.iterrows():
    predictor.predict_single(station=1, features=row)
```

3. **Disable TensorFlow warnings**:
```python
import warnings
warnings.filterwarnings("ignore")
```

## Integration Examples

### With Jupyter Notebook

```python
# In Jupyter
from src.predict import DustStormPredictor
import pandas as pd

predictor = DustStormPredictor()

# Interactive prediction
features = {
    'Temperature': 28.5,
    'Humidity': 35.0,
    'Wind_speed': 22.0,
    'Pressure': 1010.5,
    'Visibility': 5.0,
    'Snow_depth': 0.0
}

result = predictor.predict_single(1, features)
display(result)
```

### With Streamlit Dashboard

```python
import streamlit as st
from src.predict import DustStormPredictor

st.title("Dust Storm Predictor")

predictor = DustStormPredictor()

# Input widgets
temperature = st.slider("Temperature (°C)", -10, 50, 25)
humidity = st.slider("Humidity (%)", 0, 100, 50)
wind_speed = st.slider("Wind Speed (m/s)", 0, 50, 15)
# ... more inputs

if st.button("Predict"):
    result = predictor.predict_single(1, {
        'Temperature': temperature,
        'Humidity': humidity,
        'Wind_speed': wind_speed,
        # ...
    })
    
    st.metric("Probability", f"{result['probability']:.1%}")
    if result['prediction']:
        st.error("⚠️ Dust Storm Likely!")
```

## License & Support

For issues or questions, refer to the main project documentation.

