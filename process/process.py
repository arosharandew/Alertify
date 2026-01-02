import pandas as pd
import os

# Define file paths
data_dir = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\data"
weather_path = os.path.join(data_dir, "weather.csv")
fuel_path = os.path.join(data_dir, "fuel_prices.csv")
alerts_path = os.path.join(data_dir, "alerts.csv")
output_dir = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\docs\data"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Define output paths
new_weather_path = os.path.join(output_dir, "new_weather.csv")
new_fuel_path = os.path.join(output_dir, "new_fuel.csv")
new_alerts_path = os.path.join(output_dir, "new_alerts.csv")

# Process weather.csv
print("Processing weather.csv...")
try:
    # Read weather.csv
    weather_df = pd.read_csv(weather_path)
    print(f"Original weather data shape: {weather_df.shape}")
    print(f"Original columns: {list(weather_df.columns)}")

    # Remove 'id' column
    if 'id' in weather_df.columns:
        weather_df = weather_df.drop(columns=['id'])
        print("✓ Removed 'id' column from weather data")
    else:
        print("⚠ 'id' column not found in weather data")

    # Save processed weather data
    weather_df.to_csv(new_weather_path, index=False)
    print(f"✓ Saved processed weather data to: {new_weather_path}")
    print(f"New weather data shape: {weather_df.shape}")
    print(f"Remaining columns: {list(weather_df.columns)}")

except FileNotFoundError:
    print(f"✗ Error: weather.csv not found at {weather_path}")
except Exception as e:
    print(f"✗ Error processing weather.csv: {e}")

print("\n" + "=" * 50 + "\n")

# Process fuel_prices.csv
print("Processing fuel_prices.csv...")
try:
    # Read fuel_prices.csv
    fuel_df = pd.read_csv(fuel_path)
    print(f"Original fuel data shape: {fuel_df.shape}")
    print(f"Original columns: {list(fuel_df.columns)}")

    # Define columns to remove
    columns_to_remove = ['id', 'source', 'location', 'scraped_at', 'recorded_at']

    # Remove specified columns
    columns_removed = []
    for col in columns_to_remove:
        if col in fuel_df.columns:
            fuel_df = fuel_df.drop(columns=[col])
            columns_removed.append(col)

    if columns_removed:
        print(f"✓ Removed columns: {columns_removed}")
    else:
        print("⚠ No specified columns found to remove")

    # Save processed fuel data
    fuel_df.to_csv(new_fuel_path, index=False)
    print(f"✓ Saved processed fuel data to: {new_fuel_path}")
    print(f"New fuel data shape: {fuel_df.shape}")
    print(f"Remaining columns: {list(fuel_df.columns)}")

except FileNotFoundError:
    print(f"✗ Error: fuel_prices.csv not found at {fuel_path}")
except Exception as e:
    print(f"✗ Error processing fuel_prices.csv: {e}")

print("\n" + "=" * 50 + "\n")

# Process alerts.csv
print("Processing alerts.csv...")
try:
    # Read alerts.csv
    alerts_df = pd.read_csv(alerts_path)
    print(f"Original alerts data shape: {alerts_df.shape}")
    print(f"Original columns: {list(alerts_df.columns)}")

    # Define columns to remove
    columns_to_remove = ['id', 'source', 'source_id', 'start_time', 'end_time', 'created_at']

    # Remove specified columns
    columns_removed = []
    for col in columns_to_remove:
        if col in alerts_df.columns:
            alerts_df = alerts_df.drop(columns=[col])
            columns_removed.append(col)

    if columns_removed:
        print(f"✓ Removed columns: {columns_removed}")
    else:
        print("⚠ No specified columns found to remove")

    # Remove duplicate rows based on 'title' column (keeping first occurrence)
    original_count = len(alerts_df)

    if 'title' in alerts_df.columns:
        # Keep only the first occurrence of each unique title
        alerts_df = alerts_df.drop_duplicates(subset=['title'], keep='first')
        duplicates_removed = original_count - len(alerts_df)
        print(f"✓ Removed {duplicates_removed} duplicate rows based on 'title' column")

        if duplicates_removed > 0:
            print(f"  - Original rows: {original_count}")
            print(f"  - After deduplication: {len(alerts_df)}")
    else:
        print("⚠ 'title' column not found, skipping duplicate removal")

    # Save processed alerts data
    alerts_df.to_csv(new_alerts_path, index=False)
    print(f"✓ Saved processed alerts data to: {new_alerts_path}")
    print(f"New alerts data shape: {alerts_df.shape}")
    print(f"Remaining columns: {list(alerts_df.columns)}")

except FileNotFoundError:
    print(f"✗ Error: alerts.csv not found at {alerts_path}")
except Exception as e:
    print(f"✗ Error processing alerts.csv: {e}")

print("\n" + "=" * 50)
print("PROCESSING COMPLETE")
print("=" * 50)
print(f"Weather file saved to: {new_weather_path}")
print(f"Fuel file saved to: {new_fuel_path}")
print(f"Alerts file saved to: {new_alerts_path}")