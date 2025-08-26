#!/usr/bin/env python3
"""
Iranian Product Matcher - Core ML/Rule-based Product Deduplication
Handles Persian text, product specifications, and vendor variations
"""

import re
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from neo4j import GraphDatabase
import redis
from fuzzywuzzy import fuzz, process
import hazm  # Persian text processing
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    listing_id: str
    product_id: Optional[str]
    match_confidence: float
    match_type: str  # 'exact', 'fuzzy', 'new_product'
    matched_attributes: List[str]
    canonical_product: Dict[str, Any]

class PersianTextProcessor:
    """Handle Persian text normalization and processing"""
    
    def __init__(self):
        self.normalizer = hazm.Normalizer()
        self.stemmer = hazm.Stemmer()
        self.lemmatizer = hazm.Lemmatizer()
        
        # Common Persian stop words
        self.stop_words = {
            'و', 'در', 'از', 'به', 'با', 'برای', 'که', 'این', 'آن', 'را', 'های', 'هر',
            'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده',
            'اینچ', 'سانتی', 'متر', 'گرم', 'کیلو', 'مگا', 'گیگا', 'ترا'
        }
        
        # Brand name variations
        self.brand_variations = {
            'سامسونگ': ['samsung', 'سامسونگ', 'سامسنگ'],
            'اپل': ['apple', 'اپل', 'اپپل', 'آپل', 'iphone', 'ipad', 'macbook'],
            'هواوی': ['huawei', 'هواوی', 'هواوای'],
            'شیائومی': ['xiaomi', 'شیائومی', 'شیامی', 'می'],
            'ال جی': ['lg', 'ال جی', 'الجی'],
            'سونی': ['sony', 'سونی', 'سوني'],
            'ایسوس': ['asus', 'ایسوس', 'اسوس'],
            'لنوو': ['lenovo', 'لنوو', 'لنووا'],
            'اچ پی': ['hp', 'اچ پی', 'اچپی', 'hewlett'],
            'دل': ['dell', 'دل'],
            'ام اس آی': ['msi', 'ام اس آی', 'ام‌اس‌آی'],
            'ایسر': ['acer', 'ایسر', 'اسر']
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize Persian text"""
        if not text:
            return ""
        
        # Basic normalization
        text = self.normalizer.normalize(text)
        
        # Convert Persian/Arabic digits to English
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        english_digits = '0123456789'
        
        translation_table = str.maketrans(
            persian_digits + arabic_digits,
            english_digits + english_digits
        )
        text = text.translate(translation_table)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.lower()
    
    def extract_features(self, text: str) -> Dict[str, Any]:
        """Extract key features from Persian product text"""
        normalized = self.normalize_text(text)
        
        features = {
            'brand': self._extract_brand(normalized),
            'model': self._extract_model(normalized),
            'storage': self._extract_storage(normalized),
            'color': self._extract_color(normalized),
            'ram': self._extract_ram(normalized),
            'screen_size': self._extract_screen_size(normalized),
            'processor': self._extract_processor(normalized),
            'keywords': self._extract_keywords(normalized)
        }
        
        return {k: v for k, v in features.items() if v}
    
    def _extract_brand(self, text: str) -> Optional[str]:
        """Extract brand from text"""
        for canonical_brand, variations in self.brand_variations.items():
            for variation in variations:
                if variation in text:
                    return canonical_brand
        return None
    
    def _extract_model(self, text: str) -> Optional[str]:
        """Extract model information"""
        # Common model patterns
        patterns = [
            r'galaxy\s+([a-z0-9\s+]+)',
            r'iphone\s+(\d+\s*[a-z]*)',
            r'macbook\s+([a-z0-9\s]+)',
            r'note\s+(\d+)',
            r'([a-z]+\d+[a-z]*)',  # Generic model pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_storage(self, text: str) -> Optional[str]:
        """Extract storage capacity"""
        patterns = [
            r'(\d+)\s*gb',
            r'(\d+)\s*tera',
            r'(\d+)\s*tb',
            r'(\d+)\s*گیگابایت',
            r'(\d+)\s*ترابایت'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                size = int(match.group(1))
                if 'tera' in pattern or 'tb' in pattern:
                    size *= 1024
                return f"{size}gb"
        
        return None
    
    def _extract_ram(self, text: str) -> Optional[str]:
        """Extract RAM capacity"""
        patterns = [
            r'(\d+)\s*gb\s*ram',
            r'ram\s*(\d+)\s*gb',
            r'(\d+)\s*گیگ\s*رم',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}gb"
        
        return None
    
    def _extract_color(self, text: str) -> Optional[str]:
        """Extract color information"""
        color_map = {
            'مشکی': 'black', 'سیاه': 'black',
            'سفید': 'white', 'سپید': 'white',
            'آبی': 'blue', 'ابی': 'blue',
            'قرمز': 'red', 'سرخ': 'red',
            'زرد': 'yellow', 'طلایی': 'gold',
            'نقره': 'silver', 'نقره‌ای': 'silver',
            'صورتی': 'pink', 'بنفش': 'purple',
            'سبز': 'green', 'خاکستری': 'gray',
            'نارنجی': 'orange'
        }
        
        for persian_color, english_color in color_map.items():
            if persian_color in text or english_color in text:
                return english_color
        
        return None
    
    def _extract_screen_size(self, text: str) -> Optional[str]:
        """Extract screen size"""
        patterns = [
            r'(\d+\.?\d*)\s*اینچ',
            r'(\d+\.?\d*)\s*inch',
            r'(\d+\.?\d*)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}inch"
        
        return None
    
    def _extract_processor(self, text: str) -> Optional[str]:
        """Extract processor information"""
        processors = [
            'snapdragon', 'exynos', 'kirin', 'mediatek', 'apple', 'intel', 'amd',
            'core i3', 'core i5', 'core i7', 'core i9', 'ryzen', 'm1', 'm2'
        ]
        
        for proc in processors:
            if proc in text:
                return proc
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        words = text.split()
        keywords = []
        
        for word in words:
            # Skip stop words and very short words
            if len(word) > 2 and word not in self.stop_words:
                # Add stemmed version
                stemmed = self.stemmer.stem(word)
                if stemmed not in keywords:
                    keywords.append(stemmed)
        
        return keywords[:10]  # Limit to top 10 keywords

class ProductMatcher:
    """Core product matching logic using ML and rule-based approaches"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.redis_client = redis.from_url("redis://localhost:6379/2")
        self.text_processor = PersianTextProcessor()
        
        # TF-IDF vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Matching thresholds
        self.thresholds = {
            'exact_match': 0.95,
            'high_confidence': 0.85,
            'medium_confidence': 0.70,
            'low_confidence': 0.50
        }
    
    def process_scraped_product(self, product_data: Dict, vendor: str) -> MatchResult:
        """Main entry point for processing scraped products"""
        
        # Create unique listing ID
        listing_id = self._generate_listing_id(product_data, vendor)
        
        # Extract features
        features = self._extract_product_features(product_data)
        
        # Try to find matching existing product
        match_result = self._find_matching_product(features, vendor)
        
        if match_result:
            # Update existing product
            self._update_existing_product(match_result, listing_id, product_data, vendor)
        else:
            # Create new canonical product
            match_result = self._create_new_product(listing_id, product_data, vendor, features)
        
        # Store listing
        self._store_product_listing(listing_id, product_data, vendor, match_result)
        
        return match_result
    
    def _generate_listing_id(self, product_data: Dict, vendor: str) -> str:
        """Generate unique listing ID"""
        key_data = f"{vendor}_{product_data.get('title', '')}_{product_data.get('product_url', '')}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _extract_product_features(self, product_data: Dict) -> Dict[str, Any]:
        """Extract and normalize product features"""
        title = product_data.get('title', '') + ' ' + product_data.get('title_persian', '')
        
        # Use text processor to extract features
        features = self.text_processor.extract_features(title)
        
        # Add structured data if available
        if 'specifications' in product_data:
            specs = product_data['specifications']
            if isinstance(specs, str):
                specs = json.loads(specs) if specs else {}
            
            features.update({
                'storage_gb': specs.get('storage_gb'),
                'ram_gb': specs.get('ram_gb'),
                'screen_inches': specs.get('screen_inches'),
                'camera_mp': specs.get('camera_mp')
            })
        
        # Add price and availability
        features['price_toman'] = product_data.get('price_toman')
        features['availability'] = product_data.get('availability', True)
        
        return features
    
    def _find_matching_product(self, features: Dict, vendor: str) -> Optional[MatchResult]:
        """Find matching product using multiple strategies"""
        
        # Strategy 1: Exact feature matching
        exact_match = self._find_exact_match(features)
        if exact_match:
            return exact_match
        
        # Strategy 2: Fuzzy matching based on brand + model + key specs
        fuzzy_match = self._find_fuzzy_match(features)
        if fuzzy_match and fuzzy_match.match_confidence >= self.thresholds['high_confidence']:
            return fuzzy_match
        
        # Strategy 3: Text similarity using TF-IDF
        text_match = self._find_text_similarity_match(features)
        if text_match and text_match.match_confidence >= self.thresholds['medium_confidence']:
            return text_match
        
        return None
    
    def _find_exact_match(self, features: Dict) -> Optional[MatchResult]:
        """Find products with identical key features"""
        
        with self.neo4j_driver.session() as session:
            # Look for products with same brand, model, and storage
            query = """
            MATCH (p:Product)
            WHERE p.brand = $brand 
            AND p.model = $model 
            AND p.storage = $storage
            RETURN p.product_id as product_id, 
                   p.canonical_title as title,
                   p.canonical_title_fa as title_fa,
                   p as product
            LIMIT 1
            """
            
            result = session.run(query, 
                brand=features.get('brand'),
                model=features.get('model'), 
                storage=features.get('storage')
            )
            
            record = result.single()
            if record:
                return MatchResult(
                    listing_id="",  # Will be set later
                    product_id=record['product_id'],
                    match_confidence=1.0,
                    match_type='exact',
                    matched_attributes=['brand', 'model', 'storage'],
                    canonical_product=dict(record['product'])
                )
        
        return None
    
    def _find_fuzzy_match(self, features: Dict) -> Optional[MatchResult]:
        """Find products using fuzzy string matching"""
        
        if not features.get('brand'):
            return None
        
        with self.neo4j_driver.session() as session:
            # Get candidate products from same brand
            query = """
            MATCH (p:Product)
            WHERE p.brand = $brand
            RETURN p.product_id as product_id,
                   p.canonical_title as title,
                   p.canonical_title_fa as title_fa,
                   p.model as model,
                   p.storage as storage,
                   p as product
            """
            
            result = session.run(query, brand=features['brand'])
            candidates = list(result)
            
            if not candidates:
                return None
            
            best_match = None
            best_score = 0
            
            for candidate in candidates:
                score = self._calculate_fuzzy_score(features, candidate)
                if score > best_score:
                    best_score = score
                    best_match = candidate
            
            if best_score >= self.thresholds['medium_confidence']:
                matched_attrs = []
                if features.get('model') and candidate.get('model'):
                    if fuzz.ratio(features['model'], candidate['model']) > 80:
                        matched_attrs.append('model')
                if features.get('storage') == candidate.get('storage'):
                    matched_attrs.append('storage')
                
                return MatchResult(
                    listing_id="",
                    product_id=best_match['product_id'],
                    match_confidence=best_score,
                    match_type='fuzzy',
                    matched_attributes=matched_attrs,
                    canonical_product=dict(best_match['product'])
                )
        
        return None
    
    def _find_text_similarity_match(self, features: Dict) -> Optional[MatchResult]:
        """Find products using text similarity (TF-IDF + cosine similarity)"""
        
        keywords = features.get('keywords', [])
        if not keywords:
            return None
        
        query_text = ' '.join(keywords)
        
        with self.neo4j_driver.session() as session:
            # Get products from same category
            category_query = """
            MATCH (p:Product)
            WHERE p.brand = $brand OR $brand IS NULL
            RETURN p.product_id as product_id,
                   p.canonical_title as title,
                   p.canonical_title_fa as title_fa,
                   p.keywords as keywords,
                   p as product
            LIMIT 100
            """
            
            result = session.run(category_query, brand=features.get('brand'))
            candidates = list(result)
            
            if not candidates:
                return None
            
            # Prepare texts for vectorization
            texts = [query_text]
            candidate_texts = []
            
            for candidate in candidates:
                candidate_keywords = candidate.get('keywords', [])
                if isinstance(candidate_keywords, str):
                    candidate_keywords = json.loads(candidate_keywords)
                candidate_text = ' '.join(candidate_keywords) if candidate_keywords else candidate.get('title', '')
                candidate_texts.append(candidate_text)
                texts.append(candidate_text)
            
            # Calculate TF-IDF vectors
            try:
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                query_vector = tfidf_matrix[0:1]
                candidate_vectors = tfidf_matrix[1:]
                
                # Calculate cosine similarities
                similarities = cosine_similarity(query_vector, candidate_vectors)[0]
                
                # Find best match
                best_idx = np.argmax(similarities)
                best_score = similarities[best_idx]
                
                if best_score >= self.thresholds['low_confidence']:
                    best_candidate = candidates[best_idx]
                    
                    return MatchResult(
                        listing_id="",
                        product_id=best_candidate['product_id'],
                        match_confidence=best_score,
                        match_type='text_similarity',
                        matched_attributes=['keywords'],
                        canonical_product=dict(best_candidate['product'])
                    )
            except Exception as e:
                logger.warning(f"TF-IDF similarity calculation failed: {e}")
        
        return None
    
    def _calculate_fuzzy_score(self, features: Dict, candidate: Dict) -> float:
        """Calculate fuzzy matching score between features and candidate"""
        
        scores = []
        
        # Brand match (exact)
        if features.get('brand') == candidate.get('brand'):
            scores.append(1.0)
        else:
            scores.append(0.0)
        
        # Model similarity
        if features.get('model') and candidate.get('model'):
            model_similarity = fuzz.ratio(features['model'], candidate['model']) / 100.0
            scores.append(model_similarity * 0.8)  # Weight model matching
        
        # Storage match
        if features.get('storage') == candidate.get('storage'):
            scores.append(1.0)
        else:
            scores.append(0.0)
        
        # Price range similarity (if available)
        if features.get('price_toman') and candidate.get('price_toman'):
            price_diff = abs(features['price_toman'] - candidate['price_toman'])
            price_similarity = max(0, 1 - (price_diff / features['price_toman']))
            scores.append(price_similarity * 0.6)  # Weight price matching
        
        # Return average score
        return sum(scores) / len(scores) if scores else 0.0
    
    def _create_new_product(self, listing_id: str, product_data: Dict, vendor: str, features: Dict) -> MatchResult:
        """Create new canonical product"""
        
        product_id = f"product_{listing_id[:8]}"
        
        with self.neo4j_driver.session() as session:
            # Create canonical product
            session.run("""
                CREATE (p:Product {
                    product_id: $product_id,
                    canonical_title: $title,
                    canonical_title_fa: $title_fa,
                    brand: $brand,
                    model: $model,
                    category: $category,
                    storage: $storage,
                    ram: $ram,
                    screen_size: $screen_size,
                    processor: $processor,
                    keywords: $keywords,
                    created_at: datetime(),
                    updated_at: datetime()
                })
            """,
                product_id=product_id,
                title=product_data.get('title', ''),
                title_fa=product_data.get('title_persian', ''),
                brand=features.get('brand'),
                model=features.get('model'),
                category=self._determine_category(features),
                storage=features.get('storage'),
                ram=features.get('ram'),
                screen_size=features.get('screen_size'),
                processor=features.get('processor'),
                keywords=json.dumps(features.get('keywords', []))
            )
        
        return MatchResult(
            listing_id=listing_id,
            product_id=product_id,
            match_confidence=1.0,
            match_type='new_product',
            matched_attributes=[],
            canonical_product={
                'product_id': product_id,
                'canonical_title': product_data.get('title', ''),
                'canonical_title_fa': product_data.get('title_persian', '')
            }
        )
    
    def _determine_category(self, features: Dict) -> str:
        """Determine product category based on features"""
        
        if features.get('screen_size'):
            if float(features['screen_size'].replace('inch', '')) < 7:
                return 'mobile'
            elif float(features['screen_size'].replace('inch', '')) < 13:
                return 'tablet'
            else:
                return 'laptop'
        
        # Fallback based on keywords
        keywords = features.get('keywords', [])
        if any(word in ['phone', 'mobile', 'گوشی'] for word in keywords):
            return 'mobile'
        elif any(word in ['tablet', 'تبلت'] for word in keywords):
            return 'tablet'
        elif any(word in ['laptop', 'computer', 'لپ تاپ'] for word in keywords):
            return 'laptop'
        
        return 'electronics'
    
    def _update_existing_product(self, match_result: MatchResult, listing_id: str, product_data: Dict, vendor: str):
        """Update existing product with new listing information"""
        
        # Update last seen timestamp
        with self.neo4j_driver.session() as session:
            session.run("""
                MATCH (p:Product {product_id: $product_id})
                SET p.updated_at = datetime(),
                    p.last_seen = datetime()
            """, product_id=match_result.product_id)
    
    def _store_product_listing(self, listing_id: str, product_data: Dict, vendor: str, match_result: MatchResult):
        """Store product listing in Neo4j"""
        
        with self.neo4j_driver.session() as session:
            # Create listing node
            session.run("""
                MERGE (l:Listing {listing_id: $listing_id})
                SET l.vendor = $vendor,
                    l.title = $title,
                    l.title_fa = $title_fa,
                    l.price_irr = $price_irr,
                    l.price_toman = $price_toman,
                    l.availability = $availability,
                    l.product_url = $product_url,
                    l.image_url = $image_url,
                    l.scraped_at = datetime(),
                    l.last_updated = datetime()
                
                WITH l
                MATCH (p:Product {product_id: $product_id})
                MERGE (p)-[:HAS_LISTING]->(l)
                MERGE (l)-[:REPRESENTS]->(p)
            """,
                listing_id=listing_id,
                vendor=vendor,
                title=product_data.get('title', ''),
                title_fa=product_data.get('title_persian', ''),
                price_irr=product_data.get('price_irr'),
                price_toman=product_data.get('price_toman'),
                availability=product_data.get('availability', True),
                product_url=product_data.get('product_url', ''),
                image_url=product_data.get('image_url', ''),
                product_id=match_result.product_id
            )
    
    def close(self):
        """Clean up resources"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.redis_client:
            self.redis_client.close()

# Main entry point for testing
if __name__ == "__main__":
    # Example usage
    matcher = ProductMatcher(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="iranian_price_secure_2025"
    )
    
    # Example product data
    sample_product = {
        'title': 'Samsung Galaxy S21 128GB',
        'title_persian': 'سامسونگ گلکسی اس ۲۱ ۱۲۸ گیگابایت',
        'price_toman': 25000000,
        'price_irr': 250000000,
        'availability': True,
        'product_url': 'https://digikala.com/product/samsung-s21',
        'image_url': 'https://example.com/image.jpg'
    }
    
    try:
        result = matcher.process_scraped_product(sample_product, 'digikala.com')
        print(f"Match result: {result}")
    finally:
        matcher.close()