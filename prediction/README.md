# Dust Storm Forecasting System

A multi-model machine learning system for predicting dust storms using ensemble methods (Random Forest, XGBoost, LSTM, CNN-LSTM).

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Train Models

```bash
python src/main.py
```

This will:
- Load data from `src/DustDatafull.xlsx`
- Train models for all stations
- Save trained models to `saved_models/`
- Generate forecasts to `src/DustForecast_10days.xlsx`

### 3. Make Predictions

```python
from src.predict import DustStormPredictor

# Initialize predictor
predictor = DustStormPredictor()

# Make a prediction
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

## 📁 Project Structure

```
t1/
├── src/
│   ├── main.py              # Main training pipeline
│   ├── predict.py           # Prediction module (USE THIS!)
│   ├── DustDatafull.xlsx    # Training data
│   └── DustForecast_10days.xlsx  # Output forecasts
├── saved_models/            # Trained models (per station)
│   ├── 1/
│   │   ├── scaler.joblib
│   │   ├── random_forest.joblib
│   │   ├── xgboost.pkl
│   │   ├── lstm.keras
│   │   └── cnn_lstm.keras
│   ├── 2/
│   └── ...
├── example_usage.py         # Examples of using predict.py
├── PREDICTION_GUIDE.md      # Detailed prediction guide
├── pyproject.toml           # Dependencies
└── README.md               # This file
```

## 🎯 Main Features

### Training (`main.py`)
- Multi-station support
- Ensemble of 4 models (RF, XGBoost, LSTM, CNN-LSTM)
- Automatic model caching (trains once, loads thereafter)
- GPU support for TensorFlow models
- Comprehensive logging

### Prediction (`predict.py`)
- **Clean API for external use**
- Load pre-trained models
- Single or batch predictions
- Support for DataFrame, numpy array, or dict inputs
- Model caching for performance

## 📊 Models

| Model | Type | Use Case |
|-------|------|----------|
| Random Forest | Tree-based | Feature importance, interpretability |
| XGBoost | Gradient boosting | High accuracy, handles imbalance |
| LSTM | Recurrent NN | Temporal patterns |
| CNN-LSTM | Hybrid NN | Spatial-temporal features |

**Ensemble**: Average probability from all models

## 🔧 Usage Examples

### Example 1: Single Prediction

```python
from src.predict import DustStormPredictor

predictor = DustStormPredictor()
result = predictor.predict_single(
    station=1,
    features={'Temperature': 28.5, 'Humidity': 35.0, ...}
)
print(result)
```

### Example 2: Batch Prediction

```python
import pandas as pd
from src.predict import DustStormPredictor

predictor = DustStormPredictor()

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
print(predictions)
```

### Example 3: Multiple Stations

```python
from src.predict import batch_predict
import pandas as pd

df = pd.DataFrame({
    'Station': [1, 1, 2, 2, 3, 3],
    'Temperature': [25.5, 28.0, 26.0, 27.5, 24.0, 26.0],
    # ... other features
})

results = batch_predict(df, station_col='Station')
```

### More Examples

Run the examples file:

```bash
python example_usage.py
```

## 📖 Documentation

- **[PREDICTION_GUIDE.md](PREDICTION_GUIDE.md)** - Complete guide for using the prediction module
- **[pyproject.toml](pyproject.toml)** - Project dependencies

## 🔄 Workflow

### For Training/Retraining

```bash
# Initial training
python src/main.py

# Force retrain all models
python src/main.py --retrain
```

### For Prediction (External Use)

```python
# Import the prediction module
from src.predict import DustStormPredictor

# Use pre-trained models
predictor = DustStormPredictor()
predictor.predict_single(station=1, features={...})
```

## 📦 Dependencies

- pandas
- numpy
- scikit-learn
- xgboost
- tensorflow
- openpyxl (for Excel files)
- joblib (for model serialization)

Install all with:
```bash
pip install -e .
```

## ⚙️ Configuration

Edit `CONFIG` in `src/main.py`:

```python
CONFIG = {
    'data_path': 'src/DustDatafull.xlsx',
    'output_path': 'src/DustForecast_10days.xlsx',
    'model_dir': 'saved_models',
    'forecast_days': 10,
    'test_days': 60,
    'models': {
        'random_forest': {'enabled': True, ...},
        'xgboost': {'enabled': True, ...},
        'lstm': {'enabled': True, ...},
        'cnn_lstm': {'enabled': True, ...}
    }
}
```

## 🎓 How It Works

1. **Data Loading**: Load historical dust storm data with weather features
2. **Data Splitting**: Split per station into train/test/forecast sets
3. **Feature Scaling**: StandardScaler fitted on training data
4. **Model Training**: Train 4 models per station (or load if exists)
5. **Ensemble Prediction**: Average probabilities from all models
6. **Output**: Binary prediction (threshold = 0.5) + probabilities

## 🐛 Troubleshooting

### "Model directory not found"
```bash
# Train models first
python src/main.py
```

### "No models found for station X"
```python
# Check available stations
predictor = DustStormPredictor()
print(predictor.get_available_stations())
```

### Import errors
```bash
# Reinstall dependencies
pip install -e .
```

## 📈 Performance Tips

1. **Reuse predictor object** - Models are cached after first load
2. **Use batch predictions** - More efficient than loops
3. **GPU for training** - TensorFlow will auto-detect GPU

## 🔐 File Paths

- Training data: `src/DustDatafull.xlsx`
- Models: `saved_models/{station}/`
- Forecasts: `src/DustForecast_10days.xlsx`
- Logs: `dust_forecast.log`

## 🎯 Key Files

| File | Purpose | Use When |
|------|---------|----------|
| `src/main.py` | Training pipeline | Training/retraining models |
| `src/predict.py` | Prediction API | Making predictions |
| `example_usage.py` | Usage examples | Learning the API |
| `PREDICTION_GUIDE.md` | Documentation | Reference/integration |

## 📊 Input Features

Required features for prediction:

1. **Temperature** - Air temperature (°C)
2. **Humidity** - Relative humidity (%)
3. **Wind_speed** - Wind speed (m/s)
4. **Pressure** - Atmospheric pressure (hPa)
5. **Visibility** - Visibility distance (km)
6. **Snow_depth** - Snow depth (cm)

## 🎨 Output Format

```python
{
    'station': 1,
    'probability': 0.75,        # Ensemble probability
    'prediction': True,          # Binary (True = dust storm)
    'model_probabilities': {
        'RF': 0.72,
        'XGB': 0.78,
        'LSTM': 0.74,
        'CNNLSTM': 0.76
    }
}
```

## 🚦 Status Indicators

- ✓ Training complete
- ✓ Prediction module ready
- ✓ All models cached
- ✓ Documentation complete

## 🔗 Integration Examples

### REST API
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
```

### Streamlit Dashboard
```python
import streamlit as st
from src.predict import DustStormPredictor

st.title("Dust Storm Predictor")
predictor = DustStormPredictor()

# Add sliders for inputs
# Make predictions
# Display results
```

## 📝 License

See project documentation for details.

## 🤝 Contributing

1. Train models: `python src/main.py`
2. Test predictions: `python example_usage.py`
3. Read guide: `PREDICTION_GUIDE.md`

---

**Quick Links:**
- 📘 [Prediction Guide](PREDICTION_GUIDE.md)
- 💻 [Example Usage](example_usage.py)
- 🔧 [Main Training](src/main.py)
- 🎯 [Prediction Module](src/predict.py)

