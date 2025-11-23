#!/usr/bin/env python3
"""
Example: How to use the dust storm prediction module
"""

from src.predict import DustStormPredictor, predict_dust_storm, batch_predict
import pandas as pd
import numpy as np

def example_1_single_prediction():
    """Example 1: Make a single prediction"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Single Prediction")
    print("="*60)
    
    # Initialize predictor
    predictor = DustStormPredictor(model_dir='saved_models')
    
    # Define your input features
    features = {
        'Temperature': 28.5,
        'Humidity': 35.0,
        'Wind_speed': 22.0,
        'Pressure': 1010.5,
        'Visibility': 5.0,
        'Snow_depth': 0.0
    }
    
    # Make prediction for station 1
    result = predictor.predict_single(station=1, features=features)
    
    print(f"\nStation: {result['station']}")
    print(f"Dust Storm Probability: {result['probability']:.1%}")
    print(f"Prediction: {'⚠️ DUST STORM' if result['prediction'] else '✓ No Dust Storm'}")
    print("\nIndividual Model Probabilities:")
    for model, prob in result['model_probabilities'].items():
        print(f"  {model:15s}: {prob:.1%}")


def example_2_dataframe_batch():
    """Example 2: Predict for multiple data points"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Batch Prediction (DataFrame)")
    print("="*60)
    
    predictor = DustStormPredictor(model_dir='saved_models')
    
    # Create sample data for multiple days
    data = pd.DataFrame({
        'Temperature': [25.5, 28.0, 30.5, 27.0, 26.5],
        'Humidity': [45.0, 38.0, 32.0, 40.0, 43.0],
        'Wind_speed': [15.0, 20.0, 25.0, 18.0, 16.0],
        'Pressure': [1013.0, 1011.0, 1009.0, 1012.0, 1013.5],
        'Visibility': [10.0, 7.0, 4.0, 8.0, 9.0],
        'Snow_depth': [0.0, 0.0, 0.0, 0.0, 0.0]
    })
    
    # Make predictions
    predictions = predictor.predict(
        station=1,
        data=data,
        feature_cols=data.columns.tolist()
    )
    
    print("\nPredictions:")
    print(predictions[['Station', 'Mean_Prob', 'Prediction']].to_string(index=False))
    
    # Add date column for clarity
    data['Prediction'] = predictions['Prediction'].values
    data['Probability'] = predictions['Mean_Prob'].values
    print("\nWith Input Features:")
    print(data.to_string(index=False))


def example_3_quick_prediction():
    """Example 3: Quick one-line prediction"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Quick Prediction Function")
    print("="*60)
    
    # Quick prediction without creating predictor object
    features = {
        'Temperature': 29.0,
        'Humidity': 30.0,
        'Wind_speed': 23.0,
        'Pressure': 1008.0,
        'Visibility': 3.0,
        'Snow_depth': 0.0
    }
    
    result = predict_dust_storm(station=1, features=features)
    
    print("\nQuick prediction result:")
    print(result[['Station', 'RF_Prob', 'XGB_Prob', 'LSTM_Prob', 
                  'CNNLSTM_Prob', 'Mean_Prob', 'Prediction']].to_string(index=False))


def example_4_multiple_stations():
    """Example 4: Predict for multiple stations at once"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Multiple Stations Batch Prediction")
    print("="*60)
    
    # Create data with multiple stations
    data = pd.DataFrame({
        'Station': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'Temperature': [25.5, 28.0, 30.5, 26.0, 27.5, 29.0, 24.0, 26.0, 28.0],
        'Humidity': [45.0, 38.0, 32.0, 44.0, 40.0, 35.0, 50.0, 45.0, 40.0],
        'Wind_speed': [15.0, 20.0, 25.0, 16.0, 19.0, 24.0, 14.0, 17.0, 22.0],
        'Pressure': [1013.0, 1011.0, 1009.0, 1012.5, 1011.5, 1010.0, 1013.5, 1012.0, 1010.5],
        'Visibility': [10.0, 7.0, 4.0, 9.0, 8.0, 5.0, 10.0, 9.0, 6.0],
        'Snow_depth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })
    
    # Batch predict for all stations
    results = batch_predict(data, station_col='Station')
    
    print("\nPredictions for multiple stations:")
    print(results[['Station', 'Mean_Prob', 'Prediction']].to_string(index=False))


def example_5_available_stations():
    """Example 5: Check available trained models"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Available Stations and Model Info")
    print("="*60)
    
    predictor = DustStormPredictor(model_dir='saved_models')
    
    # Get all available stations
    stations = predictor.get_available_stations()
    print(f"\nAvailable stations: {stations}")
    
    # Get detailed info for each station
    print("\nModel availability by station:")
    for station in stations[:5]:  # Show first 5 stations
        info = predictor.get_model_info(station)
        print(f"\nStation {station}:")
        print(f"  Models: {', '.join(info['available_models'])}")


def example_6_numpy_array():
    """Example 6: Predict using numpy arrays directly"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Prediction with NumPy Arrays")
    print("="*60)
    
    predictor = DustStormPredictor(model_dir='saved_models')
    
    # Create numpy array (shape: n_samples x n_features)
    # Features: [Temperature, Humidity, Wind_speed, Pressure, Visibility, Snow_depth]
    data_array = np.array([
        [25.5, 45.0, 15.0, 1013.0, 10.0, 0.0],
        [28.0, 38.0, 20.0, 1011.0, 7.0, 0.0],
        [30.5, 32.0, 25.0, 1009.0, 4.0, 0.0]
    ])
    
    predictions = predictor.predict(station=1, data=data_array)
    
    print("\nPredictions from numpy array:")
    print(predictions[['Station', 'Mean_Prob', 'Prediction']].to_string(index=False))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("DUST STORM PREDICTION - Usage Examples")
    print("="*60)
    
    try:
        # Run all examples
        example_1_single_prediction()
        example_2_dataframe_batch()
        example_3_quick_prediction()
        example_4_multiple_stations()
        example_5_available_stations()
        example_6_numpy_array()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n⚠️  Please run 'python src/main.py' first to train the models.")
        print("   The prediction module requires trained models to work.\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

