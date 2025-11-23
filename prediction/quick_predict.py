#!/usr/bin/env python3
"""
Quick command-line interface for dust storm predictions
Usage: python quick_predict.py --station 1 --temp 28.5 --humidity 35 ...
"""

import argparse
from src.predict import DustStormPredictor

def main():
    parser = argparse.ArgumentParser(
        description='Quick dust storm prediction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single prediction
  python quick_predict.py --station 1 --temp 28.5 --humidity 35 --wind 22 --pressure 1010 --visibility 5 --snow 0

  # List available stations
  python quick_predict.py --list-stations

  # Show model info
  python quick_predict.py --station 1 --info
        """
    )
    
    parser.add_argument('--station', type=str, help='Station identifier')
    parser.add_argument('--temp', type=float, help='Temperature (°C)')
    parser.add_argument('--humidity', type=float, help='Humidity (%%)')
    parser.add_argument('--wind', type=float, help='Wind speed (m/s)')
    parser.add_argument('--pressure', type=float, help='Pressure (hPa)')
    parser.add_argument('--visibility', type=float, help='Visibility (km)')
    parser.add_argument('--snow', type=float, help='Snow depth (cm)')
    
    parser.add_argument('--list-stations', action='store_true', 
                       help='List available stations with trained models')
    parser.add_argument('--info', action='store_true',
                       help='Show model information for station')
    parser.add_argument('--model-dir', default='saved_models',
                       help='Path to saved models directory (default: saved_models)')
    
    args = parser.parse_args()
    
    try:
        predictor = DustStormPredictor(model_dir=args.model_dir)
        
        # List stations
        if args.list_stations:
            stations = predictor.get_available_stations()
            print(f"\n{'='*60}")
            print(f"Available Stations with Trained Models")
            print(f"{'='*60}")
            print(f"\nFound {len(stations)} stations:")
            for i, station in enumerate(stations, 1):
                info = predictor.get_model_info(station)
                print(f"  {i}. Station {station} - Models: {', '.join(info['available_models'])}")
            print(f"\n{'='*60}\n")
            return
        
        # Show station info
        if args.info:
            if not args.station:
                print("Error: --station required with --info")
                return
            
            info = predictor.get_model_info(args.station)
            print(f"\n{'='*60}")
            print(f"Station {info['station']} - Model Information")
            print(f"{'='*60}")
            print(f"\nModel Directory: {info['model_directory']}")
            print(f"\nAvailable Models:")
            for model in info['available_models']:
                print(f"  ✓ {model}")
            print(f"\n{'='*60}\n")
            return
        
        # Make prediction
        if args.station and args.temp is not None:
            # Check all required features
            required = {
                'temp': args.temp,
                'humidity': args.humidity,
                'wind': args.wind,
                'pressure': args.pressure,
                'visibility': args.visibility,
                'snow': args.snow
            }
            
            missing = [k for k, v in required.items() if v is None]
            if missing:
                print(f"Error: Missing required arguments: {', '.join(f'--{k}' for k in missing)}")
                print("\nAll features are required:")
                print("  --temp        Temperature (°C)")
                print("  --humidity    Humidity (%)")
                print("  --wind        Wind speed (m/s)")
                print("  --pressure    Pressure (hPa)")
                print("  --visibility  Visibility (km)")
                print("  --snow        Snow depth (cm)")
                return
            
            features = {
                'Temperature': args.temp,
                'Humidity': args.humidity,
                'Wind_speed': args.wind,
                'Pressure': args.pressure,
                'Visibility': args.visibility,
                'Snow_depth': args.snow
            }
            
            print(f"\n{'='*60}")
            print(f"Dust Storm Prediction - Station {args.station}")
            print(f"{'='*60}")
            print("\nInput Features:")
            print(f"  Temperature:  {args.temp}°C")
            print(f"  Humidity:     {args.humidity}%")
            print(f"  Wind Speed:   {args.wind} m/s")
            print(f"  Pressure:     {args.pressure} hPa")
            print(f"  Visibility:   {args.visibility} km")
            print(f"  Snow Depth:   {args.snow} cm")
            
            result = predictor.predict_single(station=args.station, features=features)
            
            print(f"\n{'='*60}")
            print("PREDICTION RESULTS")
            print(f"{'='*60}")
            print(f"\n  Overall Probability: {result['probability']:.1%}")
            
            if result['prediction']:
                print(f"  ⚠️  DUST STORM LIKELY")
            else:
                print(f"  ✓  No Dust Storm Expected")
            
            print(f"\n  Individual Model Probabilities:")
            for model, prob in result['model_probabilities'].items():
                bar_length = int(prob * 20)
                bar = '█' * bar_length + '░' * (20 - bar_length)
                print(f"    {model:10s} {bar} {prob:.1%}")
            
            print(f"\n{'='*60}\n")
            return
        
        # No valid command
        parser.print_help()
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Tip: Train models first by running: python src/main.py\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

