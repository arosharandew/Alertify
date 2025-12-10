# config/categories.py
CATEGORIES = {
    'traffic': {
        'subcategories': [
            'road_accident', 'road_closures', 'traffic_jams',
            'train_delays', 'bus_issues', 'highway_updates'
        ],
        'keywords': ['accident', 'traffic', 'road', 'highway', 'bus', 'train', 'delay', 'collision', 'jam','Accident', 'Traffic', 'Road', 'Highway', 'Bus', 'Train', 'Delay', 'Collision', 'Jam']
    },
    'weather': {
        'subcategories': [
            'rainfall_alerts', 'floods', 'landslides',
            'cyclones', 'earthquakes', 'droughts', 'heatwaves'
        ],
        'keywords': ['rain', 'flood', 'cyclone', 'landslide', 'weather', 'storm', 'temperature', 'hot','Rain', 'Flood', 'Cyclone', 'Landslide', 'Weather', 'Storm', 'Temperature', 'Hot']
    },
    'safety': {
        'subcategories': [
            'fires', 'gas_leaks', 'building_collapses',
            'missing_persons', 'rescue_operations', 'emergency_health_alerts'
        ],
        'keywords': ['fire', 'emergency', 'rescue', 'missing', 'explosion', 'collapse','Fire', 'Emergency', 'Rescue', 'Missing', 'Explosion', 'Collapse']
    },
    'crime': {
        'subcategories': [
            'arrests', 'theft_robbery', 'drugs',
            'police_operations', 'court_legal_updates'
        ],
        'keywords': ['arrest', 'robbery', 'theft', 'drugs', 'police', 'court', 'murder','Arrest', 'Robbery', 'Theft', 'Drugs', 'Police', 'Court', 'Murder']
    },
    'government': {
        'subcategories': [
            'policy_changes', 'taxes', 'public_service_announcements',
            'power_cuts', 'water_supply_updates', 'fuel_updates'
        ],
        'keywords': ['government', 'policy', 'tax', 'minister', 'president', 'official','Government', 'Policy', 'Tax', 'Minister', 'President', 'Official']
    },
    'economy': {
        'subcategories': [
            'market_updates', 'company_news', 'fuel_prices',
            'currency_rates', 'tourism_updates'
        ],
        'keywords': ['economy', 'market', 'price', 'currency', 'business', 'inflation','Economy', 'Market', 'Price', 'Currency', 'Business', 'Inflation']
    },
    'health': {
        'subcategories': [
            'disease_outbreaks', 'dengue_updates',
            'hospital_announcements', 'health_guidelines'
        ],
        'keywords': ['health', 'hospital', 'dengue', 'covid', 'disease', 'medical','Health', 'Hospital', 'Dengue', 'Covid', 'Disease', 'Medical']
    },
    'environment': {
        'subcategories': [
            'wildlife', 'pollution', 'deforestation',
            'river_sea_updates'
        ],
        'keywords': ['environment', 'wildlife', 'pollution', 'forest', 'river', 'animal','Environment', 'Wildlife', 'Pollution', 'Forest', 'River', 'Animal']
    },
    'social': {
        'subcategories': [
            'protests', 'strikes', 'political_gatherings',
            'large_crowds', 'public_demonstrations'
        ],
        'keywords': ['protest', 'strike', 'political', 'demonstration', 'rally','Protest', 'Strike', 'Political', 'Demonstration', 'Rally']
    },
    'community': {
        'subcategories': [
            'concerts', 'festivals', 'exhibitions',
            'sports_events', 'educational_events', 'public_celebrations'
        ],
        'keywords': ['concert', 'festival', 'event', 'sports', 'celebration', 'match','Concert', 'Festival', 'Event', 'Sports', 'Celebration', 'Match']
    }
}