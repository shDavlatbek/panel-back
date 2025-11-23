# ============================================
#   OPTIMIZED MULTI-MODEL DUST STORM FORECASTING (FIXED)
# ============================================

import pandas as pd
import numpy as np
import joblib
import pickle
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import argparse

# ML imports
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Conv1D, MaxPooling1D, Dropout
from tensorflow.keras.optimizers import Adam

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    'data_path': 'src/DustDatafull.xlsx',
    'output_path': 'src/DustForecast_10days.xlsx',
    'model_dir': 'saved_models',
    'forecast_days': 10,
    'test_days': 60,
    'min_samples': 100,
    'random_state': 42,
    'models': {
        'random_forest': {
            'enabled': True,
            'n_estimators': 300,
            'max_depth': 10,
            'class_weight': 'balanced'
        },
        'xgboost': {
            'enabled': True,
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'eval_metric': 'logloss'
        },
        'lstm': {
            'enabled': True,
            'epochs': 50,
            'batch_size': 16,
            'units': 64,
            'dropout': 0.3
        },
        'cnn_lstm': {
            'enabled': True,
            'epochs': 50,
            'batch_size': 16,
            'filters': 32,
            'kernel_size': 1,
            'units': 64,
            'dropout': 0.3
        }
    }
}

# =============================================================================
# LOGGING SETUP (FIXED: Added UTF-8 encoding)
# =============================================================================

def setup_logging():
    """Configure logging with proper encoding"""
    log_file = Path('dust_forecast.log')
    # Clear old log if exists
    if log_file.exists():
        log_file.unlink()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),  # FIX: Added encoding
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# GPU SETUP
# =============================================================================

def setup_gpu():
    """Configure GPU memory growth to prevent OOM errors"""
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logger.info(f"GPU configured: {len(gpus)} device(s) found")
        except RuntimeError as e:
            logger.warning(f"GPU setup failed: {e}")
    else:
        logger.info("No GPU found, using CPU")

# =============================================================================
# DATA LOADING
# =============================================================================

def load_and_prepare_data(config: Dict) -> pd.DataFrame:
    """Load and perform initial data preparation"""
    try:
        data_path = Path(config['data_path'])
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path.absolute()}")
            
        df = pd.read_excel(data_path)
        df.fillna(0, inplace=True)
        df.columns = [c.strip().replace(" ", "_") for c in df.columns]
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(['Stansiya', 'Date']).reset_index(drop=True)
        
        logger.info(f"Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        logger.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        logger.info(f"Stations: {df['Stansiya'].nunique()} unique stations")
        return df
    except Exception as e:
        logger.error(f"Data loading failed: {e}", exc_info=True)
        raise

# =============================================================================
# MODEL PATHS (FIXED: Convert station to string)
# =============================================================================

def get_model_paths(station: Any, model_dir: str) -> Dict[str, Path]:
    """Generate model file paths for a station"""
    try:
        # FIX: Convert station to string for path operations
        station_str = str(station).strip().replace(" ", "_")
        base_dir = Path(model_dir) / station_str
        base_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            'scaler': base_dir / 'scaler.joblib',
            'random_forest': base_dir / 'random_forest.joblib',
            'xgboost': base_dir / 'xgboost.pkl',
            'lstm': base_dir / 'lstm.keras',
            'cnn_lstm': base_dir / 'cnn_lstm.keras'
        }
    except Exception as e:
        logger.error(f"Failed to create model paths for station {station}: {e}")
        raise

# =============================================================================
# MODEL LOADING/TRAINING
# =============================================================================

def load_or_train_model(model_type: str, X_train: np.ndarray, y_train: Optional[np.ndarray], 
                       model_path: Path, config: Dict, X_lstm: Optional[np.ndarray] = None):
    """
    Load existing model or train new one if doesn't exist
    Returns: (model, was_loaded: bool)
    """
    model_path_str = str(model_path.absolute())
    
    if model_path.exists():
        try:
            logger.info(f"  Loading {model_type} from {model_path_str}")
            if model_type == 'scaler':
                return joblib.load(model_path), True
            elif model_type == 'random_forest':
                return joblib.load(model_path), True
            elif model_type == 'xgboost':
                with open(model_path, 'rb') as f:
                    return pickle.load(f), True
            elif model_type in ['lstm', 'cnn_lstm']:
                return load_model(model_path), True
        except Exception as e:
            logger.warning(f"  Failed to load {model_type}: {e}. Retraining...")
    
    # Train new model
    logger.info(f"  Training new {model_type} model...")
    model = None
    
    try:
        if model_type == 'scaler':
            model = StandardScaler()
            model.fit(X_train)
            joblib.dump(model, model_path)
            
        elif model_type == 'random_forest':
            rf_config = config['models']['random_forest']
            model = RandomForestClassifier(
                n_estimators=rf_config['n_estimators'],
                max_depth=rf_config['max_depth'],
                class_weight=rf_config['class_weight'],
                random_state=config['random_state'],
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            joblib.dump(model, model_path)
            
        elif model_type == 'xgboost':
            xgb_config = config['models']['xgboost']
            model = xgb.XGBClassifier(
                n_estimators=xgb_config['n_estimators'],
                max_depth=xgb_config['max_depth'],
                learning_rate=xgb_config['learning_rate'],
                eval_metric=xgb_config['eval_metric'],
                random_state=config['random_state'],
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
                
        elif model_type == 'lstm':
            lstm_config = config['models']['lstm']
            model = Sequential([
                LSTM(lstm_config['units'], input_shape=(X_lstm.shape[1], X_lstm.shape[2])),
                Dropout(lstm_config['dropout']),
                Dense(32, activation='relu'),
                Dense(1, activation='sigmoid')
            ])
            model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
            model.fit(X_lstm, y_train, epochs=lstm_config['epochs'], 
                      batch_size=lstm_config['batch_size'], verbose=0)
            model.save(model_path)
            
        elif model_type == 'cnn_lstm':
            cnn_config = config['models']['cnn_lstm']
            model = Sequential([
                Conv1D(filters=cnn_config['filters'], kernel_size=cnn_config['kernel_size'], 
                       activation='relu', input_shape=(X_lstm.shape[1], X_lstm.shape[2])),
                MaxPooling1D(pool_size=1),
                LSTM(cnn_config['units']),
                Dropout(cnn_config['dropout']),
                Dense(32, activation='relu'),
                Dense(1, activation='sigmoid')
            ])
            model.compile(loss='binary_crossentropy', optimizer=Adam(0.001), metrics=['accuracy'])
            model.fit(X_lstm, y_train, epochs=cnn_config['epochs'], 
                      batch_size=cnn_config['batch_size'], verbose=0)
            model.save(model_path)
        
        logger.info(f"  {model_type} saved to {model_path_str}")
        return model, False
        
    except Exception as e:
        logger.error(f"  Failed to train {model_type}: {e}", exc_info=True)
        raise

# =============================================================================
# DATA PREPARATION
# =============================================================================

def prepare_station_data(df: pd.DataFrame, station: Any, config: Dict) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Split data for a specific station"""
    try:
        # FIX: Ensure station is comparable
        station_value = station.item() if hasattr(station, 'item') else station
        
        st_df = df[df['Stansiya'] == station_value].reset_index(drop=True)
        
        if len(st_df) < config['min_samples']:
            logger.warning(f"Station {station} has only {len(st_df)} samples (< {config['min_samples']}), skipping.")
            return None
        
        # Calculate split points
        forecast_days = config['forecast_days']
        test_days = config['test_days']
        
        forecast_df = st_df.iloc[-forecast_days:]
        test_df = st_df.iloc[-(test_days + forecast_days):-forecast_days]
        train_df = st_df.iloc[:-(test_days + forecast_days)]
        
        logger.info(f"Station {station}: Train={len(train_df)}, Test={len(test_df)}, Forecast={len(forecast_df)}")
        
        if len(train_df) == 0 or len(test_df) == 0 or len(forecast_df) == 0:
            logger.warning(f"Station {station} has insufficient data for splits, skipping.")
            return None
            
        return train_df, test_df, forecast_df
        
    except Exception as e:
        logger.error(f"Failed to prepare data for station {station}: {e}", exc_info=True)
        return None

# =============================================================================
# STATION MODEL TRAINING
# =============================================================================

def train_models_for_station(station: Any, train_df: pd.DataFrame, test_df: pd.DataFrame, 
                             forecast_df: pd.DataFrame, feature_cols: List[str], 
                             target_col: str, config: Dict) -> pd.DataFrame:
    """Train/load models for a single station and generate forecasts"""
    
    # FIX: Convert station to string for consistent naming
    station_name = str(station).strip().replace(" ", "_")
    logger.info(f"Processing station: {station} (name: {station_name})")
    
    model_paths = get_model_paths(station, config['model_dir'])
    
    # 1. Scale features (fit only on training data)
    scaler, _ = load_or_train_model('scaler', train_df[feature_cols].values, None, 
                                    model_paths['scaler'], config)
    
    X_train_scaled = scaler.transform(train_df[feature_cols].values)
    X_forecast_scaled = scaler.transform(forecast_df[feature_cols].values)
    
    # Prepare labels
    y_train = train_df[target_col].values
    
    # Prepare LSTM-shaped data
    X_train_lstm = np.expand_dims(X_train_scaled, axis=1)
    X_forecast_lstm = np.expand_dims(X_forecast_scaled, axis=1)
    
    predictions = {}
    
    # 2. Random Forest
    if config['models']['random_forest']['enabled']:
        rf_model, loaded = load_or_train_model('random_forest', X_train_scaled, y_train, 
                                              model_paths['random_forest'], config)
        predictions['RF_Prob'] = rf_model.predict_proba(X_forecast_scaled)[:, 1]
        logger.info(f"  RF: {'Loaded' if loaded else 'Trained'}")
    
    # 3. XGBoost
    if config['models']['xgboost']['enabled']:
        xgb_model, loaded = load_or_train_model('xgboost', X_train_scaled, y_train, 
                                               model_paths['xgboost'], config)
        predictions['XGB_Prob'] = xgb_model.predict_proba(X_forecast_scaled)[:, 1]
        logger.info(f"  XGB: {'Loaded' if loaded else 'Trained'}")
    
    # 4. LSTM
    if config['models']['lstm']['enabled']:
        lstm_model, loaded = load_or_train_model('lstm', X_train_scaled, y_train, 
                                                model_paths['lstm'], config, X_train_lstm)
        predictions['LSTM_Prob'] = lstm_model.predict(X_forecast_lstm, verbose=0).flatten()
        logger.info(f"  LSTM: {'Loaded' if loaded else 'Trained'}")
    
    # 5. CNN-LSTM
    if config['models']['cnn_lstm']['enabled']:
        cnn_lstm_model, loaded = load_or_train_model('cnn_lstm', X_train_scaled, y_train, 
                                                    model_paths['cnn_lstm'], config, X_train_lstm)
        predictions['CNNLSTM_Prob'] = cnn_lstm_model.predict(X_forecast_lstm, verbose=0).flatten()
        logger.info(f"  CNN-LSTM: {'Loaded' if loaded else 'Trained'}")
    
    # 6. Ensemble
    if predictions:
        prob_df = pd.DataFrame(predictions)
        predictions['Mean_Prob'] = prob_df.mean(axis=1)
        predictions['Forecast_Change'] = (predictions['Mean_Prob'] > 0.5).astype(int)
    else:
        logger.warning("No models enabled, using zeros")
        predictions = {k: np.zeros(len(forecast_df)) for k in 
                      ['RF_Prob', 'XGB_Prob', 'LSTM_Prob', 'CNNLSTM_Prob', 'Mean_Prob', 'Forecast_Change']}
    
    # Compile results
    station_result = pd.DataFrame({
        "Station": station,
        "Date": forecast_df['Date'].values,
        **predictions
    })
    
    logger.info(f"Completed station: {station}")
    return station_result

# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():
    """Main execution pipeline"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--retrain', action='store_true', help='Force retrain all models')
    args = parser.parse_args()
    
    # Setup
    setup_gpu()
    
    # Create model directory
    models_dir = Path(CONFIG['model_dir'])
    models_dir.mkdir(exist_ok=True)
    logger.info(f"Model directory: {models_dir.absolute()}")
    
    # Load data
    df = load_and_prepare_data(CONFIG)
    
    # Identify features and target
    target_col = 'Dust_storm'
    feature_cols = [c for c in df.columns if c not in ['Date', 'Stansiya', target_col]]
    
    if not feature_cols:
        logger.error("No feature columns found!")
        return
    
    # Process stations
    stations = df['Stansiya'].unique()
    logger.info(f"Found {len(stations)} stations to process")
    
    all_results = []
    failed_stations = []
    
    for i, station in enumerate(stations, 1):
        logger.info(f"[{i}/{len(stations)}] Processing station: {station}")
        
        # Prepare data splits
        station_data = prepare_station_data(df, station, CONFIG)
        if station_data is None:
            failed_stations.append(station)
            continue
        
        train_df, test_df, forecast_df = station_data
        
        # Clear old models if retrain flag is set
        if args.retrain:
            try:
                model_paths = get_model_paths(station, CONFIG['model_dir'])
                for path in model_paths.values():
                    if path.exists():
                        path.unlink()
                        logger.info(f"  Deleted old model: {path.name}")
            except Exception as e:
                logger.warning(f"  Failed to delete old models: {e}")
        
        # Train/load models and generate forecasts
        try:
            station_result = train_models_for_station(
                station, train_df, test_df, forecast_df, 
                feature_cols, target_col, CONFIG
            )
            all_results.append(station_result)
        except Exception as e:
            # FIX: Remove emoji from error message
            logger.error(f"Failed to process station {station}: {e}", exc_info=True)
            failed_stations.append(station)
            continue
    
    # Save final results
    if all_results:
        try:
            results = pd.concat(all_results, ignore_index=True)
            results = results.sort_values(['Station', 'Date'])
            
            output_path = Path(CONFIG['output_path'])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            results.to_excel(output_path, index=False)
            
            logger.info("\n" + "="*60)
            logger.info(f"Forecast complete. Results saved to: {output_path.absolute()}")
            logger.info(f"Successfully processed: {len(all_results)} stations")
            logger.info(f"Failed stations: {len(failed_stations)}")
            if failed_stations:
                logger.info(f"Failed station list: {failed_stations}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}", exc_info=True)
    else:
        logger.error("No stations were successfully processed!")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        raise