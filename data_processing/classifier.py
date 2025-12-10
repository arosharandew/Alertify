import re
import json
from typing import Dict, Tuple, List
from dataclasses import dataclass
import requests
from config.categories import CATEGORIES


@dataclass
class ClassificationResult:
    category: str
    subcategory: str
    location: str
    impact: str
    severity: str
    confidence: float


class NewsClassifier:
    def __init__(self, use_llm: bool = False, llm_api_key: str = None):
        self.use_llm = use_llm
        self.llm_api_key = llm_api_key

        # Build keyword patterns from categories
        self.keyword_patterns = self._build_keyword_patterns()

    def _build_keyword_patterns(self) -> Dict:
        """Build comprehensive keyword patterns for classification"""
        patterns = {}

        for category, details in CATEGORIES.items():
            patterns[category] = {
                'subcategories': {},
                'severity_indicators': {
                    'high': ['fatal', 'dead', 'killed', 'emergency', 'disaster',
                             'evacuate', 'urgent', 'critical', 'major', 'severe',
                             'catastrophic', 'death toll', 'massive', 'destroyed'],
                    'medium': ['injured', 'damage', 'delay', 'disruption', 'alert',
                               'moderate', 'significant', 'affected', 'closure',
                               'protest', 'strike', 'arrest', 'investigation'],
                    'low': ['update', 'announcement', 'meeting', 'planned',
                            'information', 'minor', 'small', 'notice', 'schedule',
                            'update', 'advisory', 'reminder']
                }
            }

            # Create subcategory keywords from subcategory names
            for subcat in details['subcategories']:
                # Convert "road_accident" to ["road", "accident"]
                subcat_keywords = subcat.split('_')
                patterns[category]['subcategories'][subcat] = subcat_keywords

        return patterns

    def classify(self, text: str) -> ClassificationResult:
        """Main classification method - uses LLM if available, otherwise keywords"""
        if self.use_llm and self.llm_api_key:
            return self.classify_with_llm(text)
        return self.classify_with_keywords(text)

    def classify_with_keywords(self, text: str) -> ClassificationResult:
        """Classify using keyword matching"""
        text_lower = text.lower()

        # Score categories based on keyword matches
        category_scores = {}
        for category, details in CATEGORIES.items():
            score = 0
            for keyword in details['keywords']:
                if keyword.lower() in text_lower:
                    score += 1
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return self._default_result()

        # Get top category
        top_category = max(category_scores.items(), key=lambda x: x[1])[0]

        # Determine subcategory
        subcategory = self._determine_subcategory(text_lower, top_category)

        # Extract location
        location = self._extract_location(text)

        # Determine severity
        severity = self._determine_severity(text_lower)

        # Generate impact description
        impact = self._generate_impact(text, top_category, severity)

        # Calculate confidence
        confidence = min(category_scores[top_category] / 5, 1.0)

        return ClassificationResult(
            category=top_category,
            subcategory=subcategory,
            location=location,
            impact=impact,
            severity=severity,
            confidence=confidence
        )

    def classify_with_llm(self, text: str) -> ClassificationResult:
        """Use LLM API for classification"""
        try:
            # Using Hugging Face Inference API
            headers = {"Authorization": f"Bearer {self.llm_api_key}"}

            # Prepare prompt
            categories_list = list(CATEGORIES.keys())

            prompt = f"""
            Classify this Sri Lankan news text into one of these categories:

            Categories: {', '.join(categories_list)}

            Text: {text[:500]}

            Return JSON format with these fields:
            - category: one of the main categories
            - subcategory: specific subcategory
            - location: extracted location in Sri Lanka
            - impact: brief impact description
            - severity: "low", "medium", or "high"
            - confidence: confidence score between 0 and 1
            """

            # API call to Hugging Face
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
            response = requests.post(API_URL, headers=headers, json={"inputs": prompt})

            if response.status_code == 200:
                result = response.json()
                # Parse the response
                return self._parse_llm_response(result)
            else:
                print(f"LLM API error: {response.status_code}")
                return self.classify_with_keywords(text)

        except Exception as e:
            print(f"LLM classification failed: {e}")
            return self.classify_with_keywords(text)

    def _parse_llm_response(self, response):
        """Parse LLM response (simplified - adjust based on actual API)"""
        # For now, fall back to keyword classification
        return self.classify_with_keywords("")

    def _determine_subcategory(self, text: str, category: str) -> str:
        """Determine specific subcategory based on text"""
        text_lower = text.lower()

        # Define subcategory patterns for each main category
        subcategory_patterns = {
            'traffic': {
                'road_accident': ['accident', 'crash', 'collision', 'fatal', 'vehicle', 'car'],
                'road_closures': ['closure', 'closed', 'blocked', 'diversion', 'blockade'],
                'traffic_jams': ['jam', 'congestion', 'heavy traffic', 'gridlock', 'bottleneck'],
                'train_delays': ['train', 'railway', 'delay', 'derailment', 'rail', 'locomotive'],
                'bus_issues': ['bus', 'breakdown', 'bus service', 'transport', 'public transport'],
                'highway_updates': ['highway', 'expressway', 'road work', 'construction', 'flyover']
            },
            'weather': {
                'rainfall_alerts': ['rain', 'rainfall', 'shower', 'precipitation', 'drizzle'],
                'floods': ['flood', 'flooding', 'inundated', 'waterlogged', 'submerged'],
                'landslides': ['landslide', 'mudslide', 'earth slip', 'rock fall', 'debris'],
                'cyclones': ['cyclone', 'storm', 'hurricane', 'depression', 'typhoon'],
                'earthquakes': ['earthquake', 'tremor', 'seismic', 'quake', 'epicenter'],
                'droughts': ['drought', 'dry', 'water shortage', 'scarcity', 'arid'],
                'heatwaves': ['heat', 'heatwave', 'hot', 'temperature', 'scorching']
            },
            'safety': {
                'fires': ['fire', 'blaze', 'inferno', 'combustion', 'flames'],
                'gas_leaks': ['gas', 'leak', 'explosion', 'cylinder', 'lpg'],
                'building_collapses': ['building', 'collapse', 'structure', 'demolition'],
                'missing_persons': ['missing', 'person', 'lost', 'disappeared', 'search'],
                'rescue_operations': ['rescue', 'operation', 'evacuation', 'save', 'help'],
                'emergency_health_alerts': ['emergency', 'health', 'alert', 'outbreak', 'epidemic']
            },
            'crime': {
                'arrests': ['arrest', 'arrested', 'detained', 'custody', 'captured'],
                'theft_robbery': ['theft', 'robbery', 'stolen', 'burglary', 'loot'],
                'drugs': ['drug', 'narcotic', 'cocaine', 'heroin', 'meth'],
                'police_operations': ['police', 'operation', 'raid', 'crackdown', 'investigation'],
                'court_legal_updates': ['court', 'legal', 'trial', 'verdict', 'judge']
            }
        }

        if category in subcategory_patterns:
            for subcat, keywords in subcategory_patterns[category].items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return subcat

        # Default to general subcategory
        return f"{category}_general"

    def _extract_location(self, text: str) -> str:
        """Enhanced location extraction"""
        sri_lankan_locations = [
            # Provinces
            'Western Province', 'Central Province', 'Southern Province',
            'Northern Province', 'Eastern Province', 'North Western Province',
            'North Central Province', 'Uva Province', 'Sabaragamuwa Province',

            # Major Cities
            'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Kurunegala',
            'Anuradhapura', 'Polonnaruwa', 'Trincomalee', 'Batticaloa',
            'Matara', 'Ratnapura', 'Badulla', 'Hambantota', 'Kalutara',
            'Mannar', 'Vavuniya', 'Kilinochchi', 'Mullaitivu', 'Ampara',
            'Puttalam', 'Nuwara Eliya', 'Kegalle', 'Moneragala'
        ]

        text_lower = text.lower()

        # Check for exact location matches
        for location in sri_lankan_locations:
            if location.lower() in text_lower:
                return location

        # Check for patterns like "in Colombo", "at Galle"
        location_patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(\w+\s+District)',
            r'(\w+\s+Province)'
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                match = match.strip()
                if match:
                    # Check if it's a known location
                    for location in sri_lankan_locations:
                        if match.lower() == location.lower() or match.lower() in location.lower():
                            return location

        return "Sri Lanka"

    def _determine_severity(self, text: str) -> str:
        """Calculate severity based on keywords"""
        text_lower = text.lower()

        # Severity keywords with weights
        high_keywords = [
            'emergency', 'fatal', 'dead', 'killed', 'disaster', 'death',
            'warning', 'danger', 'major', 'severe', 'catastrophic',
            'evacuate', 'urgent', 'critical', 'massive', 'destroyed',
            'tragic', 'horrific', 'multiple deaths', 'many injured'
        ]

        medium_keywords = [
            'injured', 'damage', 'delay', 'disruption', 'alert',
            'moderate', 'significant', 'affected', 'closure',
            'protest', 'strike', 'arrest', 'investigation', 'incident',
            'accident', 'collision', 'fire', 'flood', 'landslide'
        ]

        low_keywords = [
            'update', 'announcement', 'meeting', 'planned',
            'information', 'minor', 'small', 'notice', 'schedule',
            'advisory', 'reminder', 'maintenance', 'upcoming',
            'expected', 'routine', 'normal'
        ]

        # Count occurrences
        high_count = sum(1 for kw in high_keywords if kw in text_lower)
        medium_count = sum(1 for kw in medium_keywords if kw in text_lower)
        low_count = sum(1 for kw in low_keywords if kw in text_lower)

        # Determine severity
        if high_count >= 2 or (high_count == 1 and medium_count >= 2):
            return 'high'
        elif high_count == 1 or medium_count >= 2:
            return 'medium'
        elif medium_count == 1 or low_count >= 2:
            return 'low'
        else:
            return 'info'

    def _generate_impact(self, text: str, category: str, severity: str) -> str:
        """Generate impact description based on category and severity"""
        impact_templates = {
            'traffic': {
                'high': 'Major traffic disruption with significant delays expected. Alternative routes recommended.',
                'medium': 'Traffic congestion affecting travel times in the area.',
                'low': 'Minor traffic updates. Motorists advised to exercise caution.',
                'info': 'Traffic information update for public awareness.'
            },
            'weather': {
                'high': 'Severe weather conditions posing risks to public safety. Follow official warnings.',
                'medium': 'Weather-related disruptions expected. Stay informed about updates.',
                'low': 'Weather advisory in effect. Minor inconveniences possible.',
                'info': 'Weather information update for planning purposes.'
            },
            'safety': {
                'high': 'Emergency safety situation requiring immediate attention and precautions.',
                'medium': 'Safety concerns reported in the area. Exercise caution.',
                'low': 'Safety advisory issued. Public advised to remain vigilant.',
                'info': 'Safety information update for community awareness.'
            },
            'crime': {
                'high': 'Serious criminal activity reported. Public advised to avoid area.',
                'medium': 'Police operations ongoing. Exercise caution in the vicinity.',
                'low': 'Minor criminal incident reported. Increased police presence.',
                'info': 'Law enforcement update for public information.'
            },
            'government': {
                'high': 'Major government announcement affecting public services.',
                'medium': 'Policy changes announced. Impact on services expected.',
                'low': 'Government service update for public information.',
                'info': 'Public administration update.'
            }
        }

        if category in impact_templates:
            return impact_templates[category].get(severity, 'Information update')

        # Generic impacts
        generic_impacts = {
            'high': 'Serious situation requiring attention. Follow official instructions.',
            'medium': 'Moderate impact expected. Stay informed about developments.',
            'low': 'Minor impact with limited effect on daily activities.',
            'info': 'General information update for public awareness.'
        }

        return generic_impacts.get(severity, 'Information update')

    def _default_result(self) -> ClassificationResult:
        """Return default classification"""
        return ClassificationResult(
            category='general',
            subcategory='general_news',
            location='Sri Lanka',
            impact='General news update for public information',
            severity='info',
            confidence=0.0
        )