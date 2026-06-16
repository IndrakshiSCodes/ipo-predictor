import pandas as pd

existing = pd.read_csv('data/processed/ipo_enriched_final.csv')
new_2025 = pd.read_csv('data/processed/ipo_2025_processed.csv')

# Combine
combined = pd.concat([existing, new_2025], ignore_index=True)
combined = combined.drop_duplicates(subset=['ipo_name', 'listing_date'])
combined = combined.sort_values('listing_date', ascending=False)

combined.to_csv('data/processed/ipo_enriched_final.csv', index=False)
print(f"Total rows now: {len(combined)}")