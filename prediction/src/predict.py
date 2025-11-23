# ============================================
#   DUST STORM PREDICTION MODULE
#   Use trained models for forecasting
# ============================================

import pandas as pd
import numpy as np
import joblib
import pickle
import warnings
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
from datetime import datetime
import tensorflow as tf

warnings.filterwarnings("ignore")

# =============================================================================
# MODEL LOADER
# =============================================================================

class DustStormPredictor:
    """
    Load trained models and make predictions for dust storm forecasting.
    
    Usage:
        predictor = DustStormPredictor(model_dir='saved_models')
        predictions = predictor.predict(station=1, data=new_data_df)
    """
    
    def __init__(self, model_dir: str = 'saved_models'):
        """
        Initialize predictor with model directory.
        
        Args:
            model_dir: Path to directory containing saved models
        """
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_dir.absolute()}")
        
        self.loaded_models = {}  # Cache loaded models
        
    def _get_station_dir(self, station: Any) -> Path:
        """Get the directory path for a station's models"""
        station_str = str(station).strip().replace(" ", "_")
        station_dir = self.model_dir / station_str
        
        if not station_dir.exists():
            raise FileNotFoundError(
                f"No models found for station '{station}'. "
                f"Expected directory: {station_dir.absolute()}"
            )
        return station_dir
    
    def _load_station_models(self, station: Any) -> Dict[str, Any]:
        """Load all models for a specific station"""
        station_key = str(station)
        
        # Return cached models if already loaded
        if station_key in self.loaded_models:
            return self.loaded_models[station_key]
        
        station_dir = self._get_station_dir(station)
        models = {}
        
        # Load scaler (required)
        scaler_path = station_dir / 'scaler.joblib'
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found: {scaler_path}")
        models['scaler'] = joblib.load(scaler_path)
        
        # Load optional models
        model_files = {
            'random_forest': ('random_forest.joblib', joblib.load),
            'xgboost': ('xgboost.pkl', lambda p: pickle.load(open(p, 'rb'))),
            'lstm': ('lstm.keras', tf.keras.models.load_model),
            'cnn_lstm': ('cnn_lstm.keras', tf.keras.models.load_model)
        }
        
        for model_name, (filename, loader) in model_files.items():
            model_path = station_dir / filename
            if model_path.exists():
                try:
                    models[model_name] = loader(model_path)
                except Exception as e:
                    print(f"Warning: Failed to load {model_name} for station {station}: {e}")
        
        # Cache the loaded models
        self.loaded_models[station_key] = models
        return models
    
    def predict(self, 
                station: Any, 
                data: Union[pd.DataFrame, np.ndarray, Dict],
                feature_cols: Optional[List[str]] = None,
                return_probs: bool = True) -> Union[pd.DataFrame, np.ndarray]:
        """
        Make predictions for a given station and input data.
        
        Args:
            station: Station identifier (must match training)
            data: Input features as DataFrame, numpy array, or dict
            feature_cols: List of feature column names (required if data is DataFrame)
            return_probs: If True, return probabilities; if False, return binary predictions
            
        Returns:
            DataFrame with predictions from all models and ensemble mean, or numpy array
            
        Example:
            # With DataFrame
            df = pd.DataFrame({
                'Temperature': [25.5, 26.0],
                'Humidity': [45, 50],
                'Wind_speed': [15, 18],
                # ... other features
            })
            predictions = predictor.predict(station=1, data=df, feature_cols=df.columns.tolist())
            
            # With numpy array
            data_array = np.array([[25.5, 45, 15, ...], [26.0, 50, 18, ...]])
            predictions = predictor.predict(station=1, data=data_array)
            
            # With dict (single prediction)
            data_dict = {'Temperature': 25.5, 'Humidity': 45, 'Wind_speed': 15, ...}
            prediction = predictor.predict(station=1, data=data_dict)
        """
        # Load models for this station
        models = self._load_station_models(station)
        
        # Convert input data to numpy array
        if isinstance(data, pd.DataFrame):
            if feature_cols is None:
                raise ValueError("feature_cols must be provided when data is a DataFrame")
            X = data[feature_cols].values
        elif isinstance(data, dict):
            # Single prediction from dict
            X = np.array([list(data.values())])
        elif isinstance(data, np.ndarray):
            X = data
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")
        
        # Scale features
        X_scaled = models['scaler'].transform(X)
        
        # Get predictions from each model
        predictions = {}
        
        # Random Forest
        if 'random_forest' in models:
            rf_probs = models['random_forest'].predict_proba(X_scaled)[:, 1]
            predictions['RF_Prob'] = rf_probs
        
        # XGBoost
        if 'xgboost' in models:
            xgb_probs = models['xgboost'].predict_proba(X_scaled)[:, 1]
            predictions['XGB_Prob'] = xgb_probs
        
        # LSTM (needs 3D reshape)
        if 'lstm' in models:
            X_lstm = np.expand_dims(X_scaled, axis=1)
            lstm_probs = models['lstm'].predict(X_lstm, verbose=0).flatten()
            predictions['LSTM_Prob'] = lstm_probs
        
        # CNN-LSTM (needs 3D reshape)
        if 'cnn_lstm' in models:
            X_cnn_lstm = np.expand_dims(X_scaled, axis=1)
            cnn_lstm_probs = models['cnn_lstm'].predict(X_cnn_lstm, verbose=0).flatten()
            predictions['CNNLSTM_Prob'] = cnn_lstm_probs
        
        if not predictions:
            raise ValueError(f"No models available for station {station}")
        
        # Calculate ensemble mean
        prob_df = pd.DataFrame(predictions)
        mean_prob = prob_df.mean(axis=1).values
        predictions['Mean_Prob'] = mean_prob
        
        # Binary prediction (threshold = 0.5)
        predictions['Prediction'] = (mean_prob > 0.5).astype(int)
        
        # Return format
        if return_probs:
            result_df = pd.DataFrame(predictions)
            result_df.insert(0, 'Station', station)
            return result_df
        else:
            return predictions['Prediction']
    
    def predict_single(self, station: Any, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Make a single prediction with a cleaner interface.
        
        Args:
            station: Station identifier
            features: Dict mapping feature names to values
            
        Returns:
            Dict with prediction results
            
        Example:
            result = predictor.predict_single(
                station=1,
                features={
                    'Temperature': 25.5,
                    'Humidity': 45,
                    'Wind_speed': 15,
                    'Pressure': 1013.25,
                    'Visibility': 10,
                    'Snow_depth': 0
                }
            )
            print(f"Dust storm probability: {result['probability']:.2%}")
            print(f"Prediction: {'Yes' if result['prediction'] else 'No'}")
        """
        predictions_df = self.predict(station, features, return_probs=True)
        
        result = {
            'station': station,
            'probability': float(predictions_df['Mean_Prob'].iloc[0]),
            'prediction': bool(predictions_df['Prediction'].iloc[0]),
            'model_probabilities': {
                col.replace('_Prob', ''): float(predictions_df[col].iloc[0])
                for col in predictions_df.columns 
                if col.endswith('_Prob')
            }
        }
        
        return result
    
    def get_available_stations(self) -> List[str]:
        """Get list of stations with trained models"""
        stations = []
        for item in self.model_dir.iterdir():
            if item.is_dir() and (item / 'scaler.joblib').exists():
                stations.append(item.name)
        return sorted(stations)
    
    def get_model_info(self, station: Any) -> Dict[str, Any]:
        """Get information about available models for a station"""
        station_dir = self._get_station_dir(station)
        
        model_files = {
            'scaler': 'scaler.joblib',
            'random_forest': 'random_forest.joblib',
            'xgboost': 'xgboost.pkl',
            'lstm': 'lstm.keras',
            'cnn_lstm': 'cnn_lstm.keras'
        }
        
        info = {
            'station': str(station),
            'model_directory': str(station_dir),
            'available_models': []
        }
        
        for model_name, filename in model_files.items():
            model_path = station_dir / filename
            if model_path.exists():
                info['available_models'].append(model_name)
        
        return info


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def predict_dust_storm(station: Any, 
                       features: Union[Dict, pd.DataFrame, np.ndarray],
                       model_dir: str = 'saved_models',
                       feature_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Quick prediction function without creating a predictor object.
    
    Args:
        station: Station identifier
        features: Input features (dict, DataFrame, or array)
        model_dir: Path to saved models directory
        feature_cols: Feature column names (for DataFrame input)
        
    Returns:
        DataFrame with predictions
        
    Example:
        predictions = predict_dust_storm(
            station=1,
            features={'Temperature': 25.5, 'Humidity': 45, ...}
        )
    """
    predictor = DustStormPredictor(model_dir=model_dir)
    return predictor.predict(station, features, feature_cols=feature_cols)


def batch_predict(data: pd.DataFrame, 
                  station_col: str = 'Station',
                  feature_cols: Optional[List[str]] = None,
                  model_dir: str = 'saved_models') -> pd.DataFrame:
    """
    Make predictions for multiple stations in a batch.
    
    Args:
        data: DataFrame with station identifiers and features
        station_col: Name of column containing station identifiers
        feature_cols: List of feature columns (if None, uses all except station_col)
        model_dir: Path to saved models directory
        
    Returns:
        DataFrame with predictions for all stations
        
    Example:
        df = pd.DataFrame({
            'Station': [1, 1, 2, 2],
            'Temperature': [25.5, 26.0, 24.0, 25.5],
            'Humidity': [45, 50, 55, 60],
            # ... other features
        })
        results = batch_predict(df, station_col='Station')
    """
    predictor = DustStormPredictor(model_dir=model_dir)
    
    if feature_cols is None:
        feature_cols = [col for col in data.columns if col != station_col]
    
    all_predictions = []
    
    for station in data[station_col].unique():
        station_data = data[data[station_col] == station].reset_index(drop=True)
        try:
            predictions = predictor.predict(
                station=station,
                data=station_data,
                feature_cols=feature_cols,
                return_probs=True
            )
            all_predictions.append(predictions)
        except Exception as e:
            print(f"Warning: Failed to predict for station {station}: {e}")
    
    if all_predictions:
        return pd.concat(all_predictions, ignore_index=True)
    else:
        raise ValueError("No predictions could be made for any station")


# =============================================================================
# MAIN (EXAMPLE USAGE)
# =============================================================================

if __name__ == '__main__':
    """Example usage of the prediction module"""
    
    print("=" * 60)
    print("DUST STORM PREDICTION MODULE - Example Usage")
    print("=" * 60)
    
    # Initialize predictor
    try:
        predictor = DustStormPredictor(model_dir='saved_models')
        print("\n✓ Predictor initialized successfully")
        
        # Show available stations
        stations = predictor.get_available_stations()
        print(f"\n✓ Available stations: {stations}")
        
        if stations:
            # Pick first station for demo
            demo_station = stations[0]
            print(f"\n--- Demo with station: {demo_station} ---")
            
            # Show model info
            info = predictor.get_model_info(demo_station)
            print(f"\nAvailable models: {info['available_models']}")
            
            # Example 1: Single prediction with dict
            print("\n--- Example 1: Single prediction ---")
            sample_features = {
                'Temperature': 25.5,
                'Humidity': 45.0,
                'Wind_speed': 15.0,
                'Pressure': 1013.25,
                'Visibility': 10.0,
                'Snow_depth': 0.0
            }
            
            result = predictor.predict_single(demo_station, sample_features)
            print(f"Input: {sample_features}")
            print(f"Probability: {result['probability']:.2%}")
            print(f"Prediction: {'Dust Storm' if result['prediction'] else 'No Dust Storm'}")
            print(f"Model probabilities: {result['model_probabilities']}")
            
            # Example 2: Batch prediction with DataFrame
            print("\n--- Example 2: Batch prediction ---")
            batch_data = pd.DataFrame({
                'Temperature': [25.5, 26.0, 27.5],
                'Humidity': [45.0, 50.0, 55.0],
                'Wind_speed': [15.0, 18.0, 20.0],
                'Pressure': [1013.25, 1012.0, 1011.5],
                'Visibility': [10.0, 8.0, 6.0],
                'Snow_depth': [0.0, 0.0, 0.0]
            })
            
            predictions = predictor.predict(
                station=demo_station,
                data=batch_data,
                feature_cols=batch_data.columns.tolist()
            )
            print(predictions[['Station', 'Mean_Prob', 'Prediction']])
            
        else:
            print("\n⚠ No trained models found. Run main.py first to train models.")
            
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease ensure:")
        print("1. You have trained models (run main.py)")
        print("2. The model directory path is correct")
    
    print("\n" + "=" * 60)

