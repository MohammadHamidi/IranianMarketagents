import re
import logging
from typing import List, Dict, Optional

# Safe import handling for Hazm
try:
    import hazm
    HAZM_AVAILABLE = True
except ImportError:
    HAZM_AVAILABLE = False
    logging.warning("Hazm library not available, using fallback methods")

class PersianTextProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if HAZM_AVAILABLE:
            try:
                self.normalizer = hazm.Normalizer()
                self.stemmer = hazm.Stemmer()
                self.lemmatizer = hazm.Lemmatizer()
                self.hazm_ready = True
            except Exception as e:
                self.logger.warning(f"Hazm initialization failed: {e}")
                self.hazm_ready = False
        else:
            self.hazm_ready = False
    
    def normalize_persian_text(self, text: str) -> str:
        """Normalize Persian text with fallback methods"""
        if not text:
            return ""
        
        if self.hazm_ready:
            try:
                return self.normalizer.normalize(text)
            except Exception as e:
                self.logger.warning(f"Hazm normalization failed: {e}")
        
        # Fallback normalization
        # Convert Persian/Arabic digits
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        english_digits = '0123456789'
        
        translation = str.maketrans(
            persian_digits + arabic_digits,
            english_digits + english_digits
        )
        text = text.translate(translation)
        
        # Normalize Unicode characters
        text = text.replace('ي', 'ی')  # Arabic ya to Persian ya
        text = text.replace('ك', 'ک')  # Arabic ka to Persian ka
        text = text.replace('‌', ' ')   # ZWNJ to space
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.lower()
    
    def extract_brand_from_text(self, text: str) -> Optional[str]:
        """Extract brand names from Persian/English text"""
        text = self.normalize_persian_text(text)
        
        brand_mappings = {
            # Persian to English mappings
            'سامسونگ': 'samsung',
            'اپل': 'apple',
            'هواوی': 'huawei',
            'شیائومی': 'xiaomi',
            'ال جی': 'lg',
            'سونی': 'sony',
            'ایسوس': 'asus',
            'لنوو': 'lenovo',
            'اچ پی': 'hp',
            'دل': 'dell'
        }
        
        # Check Persian brand names
        for persian_brand, english_brand in brand_mappings.items():
            if persian_brand in text:
                return english_brand
        
        # Check English brand names
        english_brands = list(brand_mappings.values()) + ['iphone', 'ipad', 'macbook']
        for brand in english_brands:
            if brand in text:
                return brand
        
        return None
    
    def extract_price_from_persian_text(self, text: str) -> Dict[str, Optional[int]]:
        """Extract price from Persian text"""
        normalized_text = self.normalize_persian_text(text)
        
        # Find all numbers
        numbers = re.findall(r'[\d,]+', normalized_text.replace(',', ''))
        
        result = {
            'price_irr': None,
            'price_toman': None
        }
        
        if numbers:
            # Take the largest number (usually the price)
            price = max(int(num.replace(',', '')) for num in numbers if num.replace(',', '').isdigit())
            
            # Determine if Toman or Rial
            if 'تومان' in text or 'تومن' in text:
                result['price_toman'] = price
                result['price_irr'] = price * 10
            elif 'ریال' in text:
                result['price_irr'] = price
                result['price_toman'] = price // 10
            else:
                # Heuristic: if number < 1M, probably Toman
                if price < 1000000:
                    result['price_toman'] = price
                    result['price_irr'] = price * 10
                else:
                    result['price_irr'] = price
                    result['price_toman'] = price // 10
        
        return result