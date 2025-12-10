import pandas as pd
import os

# Define file paths
news_path = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\data\news.csv"
tweets_path = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\data\tweets.csv"
output_dir = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\dashboard\data"
output_path = os.path.join(output_dir, "combined_newsdata.csv")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Read the CSV files
print("Reading news.csv...")
news_df = pd.read_csv(news_path)
print(f"News data shape: {news_df.shape}")

print("Reading tweets.csv...")
tweets_df = pd.read_csv(tweets_path)
print(f"Tweets data shape: {tweets_df.shape}")

# Process news data
print("Processing news data...")
# Select and rename columns from news data
news_processed = news_df[['title', 'summary', 'location', 'category', 'subcategory', 'impact', 'severity', 'timestamp']].copy()

# Add source column to identify the source
news_processed['source_type'] = 'news'

# Process tweets data
print("Processing tweets data...")
# Select and rename columns from tweets data
# For tweets, 'text' will be used as 'title' in the combined dataset
# Create missing columns with appropriate values
tweets_processed = tweets_df[['text', 'location', 'category', 'severity', 'timestamp']].copy()

# Rename 'text' to 'title'
tweets_processed.rename(columns={'text': 'title'}, inplace=True)

# Add missing columns with appropriate values
tweets_processed['summary'] = ''  # Empty summary for tweets
tweets_processed['subcategory'] = ''  # Empty subcategory for tweets
tweets_processed['impact'] = ''  # Empty impact for tweets

# Reorder columns to match news data
tweets_processed = tweets_processed[['title', 'summary', 'location', 'category', 'subcategory', 'impact', 'severity', 'timestamp']]

# Add source column to identify the source
tweets_processed['source_type'] = 'tweet'

# Combine both datasets
print("Combining datasets...")
combined_df = pd.concat([news_processed, tweets_processed], ignore_index=True)

# Sort by timestamp (if needed)
combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], errors='coerce')
combined_df = combined_df.sort_values('timestamp')

# Reset index
combined_df = combined_df.reset_index(drop=True)

# Remove duplicate titles (keep the first occurrence)
print("\nRemoving duplicate titles...")
original_count = len(combined_df)

# Create a normalized version of title for comparison (lowercase, stripped)
combined_df['title_normalized'] = combined_df['title'].astype(str).str.lower().str.strip()

# Remove rows with duplicate normalized titles, keeping the first occurrence
combined_df = combined_df.drop_duplicates(subset=['title_normalized'], keep='first')

# Remove the temporary normalized title column
combined_df = combined_df.drop(columns=['title_normalized'])

# Reset index after deduplication
combined_df = combined_df.reset_index(drop=True)

# Calculate duplicates removed
duplicates_removed = original_count - len(combined_df)

# Save to CSV
print(f"Saving combined data to: {output_path}")
combined_df.to_csv(output_path, index=False)

print(f"\nProcessing complete!")
print(f"Original combined records: {original_count}")
print(f"Duplicate titles removed: {duplicates_removed}")
print(f"Final combined records: {len(combined_df)}")
print(f"News records: {len(news_processed)}")
print(f"Tweet records: {len(tweets_processed)}")

# Display sample of the combined data
print("\nSample of combined data:")
print(combined_df.head())

# Display column information
print("\nFinal columns in combined dataset:")
print(list(combined_df.columns))

# Show some statistics about duplicates if any were found
if duplicates_removed > 0:
    print(f"\nNote: Removed {duplicates_removed} duplicate titles ({duplicates_removed/original_count*100:.2f}% of total)")