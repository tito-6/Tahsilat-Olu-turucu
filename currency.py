"""
Currency conversion module for TCMB exchange rates
Handles TL to USD conversion using official TCMB rates
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CurrencyConverter:
    """Handles currency conversion using TCMB exchange rates"""
    
    def __init__(self, cache_file: str = "exchange_rates.json"):
        self.cache_file = cache_file
        self.turkey_tz = pytz.timezone('Europe/Istanbul')
        self.base_url = "https://www.tcmb.gov.tr/kurlar"


        self.rates_page_url = "https://www.tcmb.gov.tr/kurlar/kurlar_tr.html"
        self.rates_cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load exchange rates from local cache"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save exchange rates to local cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.rates_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_tcmb_url(self, date: datetime) -> str:
        """Generate TCMB URL for a specific date"""
        # TCMB uses YYYYMM/DDMMYYYY format
        year_month = date.strftime("%Y%m")
        day_month_year = date.strftime("%d%m%Y")
        return f"{self.base_url}/{year_month}/{day_month_year}.xml"
    
    def _parse_tcmb_xml(self, xml_content: str) -> Optional[float]:
        """Parse TCMB XML to extract USD rate"""
        try:
            soup = BeautifulSoup(xml_content, 'xml')
            # Find USD currency entry
            usd_entry = soup.find('Currency', {'CurrencyCode': 'USD'})
            if usd_entry:
                # Get the selling rate (Satış)
                selling_rate = usd_entry.find('ForexSelling')
                if selling_rate:
                    return float(selling_rate.text)
        except Exception as e:
            logger.error(f"Failed to parse TCMB XML: {e}")
        return None
    
    def get_usd_rate(self, date: datetime) -> Optional[float]:
        """
        Get USD exchange rate for a specific date
        Uses rate from one day before the payment date as requested
        For future dates, uses the most recent available rate
        """
        # Use one day before the payment date
        target_date = date - timedelta(days=1)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Check cache first
        if date_str in self.rates_cache:
            return self.rates_cache[date_str]
        
        # If the date is in the future, use the most recent available rate
        today = datetime.now()
        if target_date > today:
            # Don't log warning for every future date to avoid spam
            return self._get_most_recent_rate()
        
        # Try to fetch from TCMB
        try:
            url = self._get_tcmb_url(target_date)
            response = requests.get(url, timeout=5)  # Reduced timeout
            response.raise_for_status()
            
            rate = self._parse_tcmb_xml(response.text)
            if rate:
                # Cache the rate
                self.rates_cache[date_str] = rate
                self._save_cache()
                logger.info(f"Fetched USD rate for {date_str}: {rate}")
                return rate
            else:
                logger.warning(f"Could not parse USD rate for {date_str}")
                
        except requests.RequestException as e:
            # Don't log 404 errors as they're expected for future dates
            if "404" not in str(e):
                logger.error(f"Failed to fetch exchange rate for {date_str}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching rate for {date_str}: {e}")
        
        # If all else fails, try to get the most recent rate
        return self._get_most_recent_rate()
    
    def _get_most_recent_rate(self) -> Optional[float]:
        """Get the most recent available exchange rate"""
        # Try the last 30 days to find a valid rate
        for days_back in range(1, 31):
            check_date = datetime.now() - timedelta(days=days_back)
            date_str = check_date.strftime("%Y-%m-%d")
            
            # Check cache first
            if date_str in self.rates_cache:
                logger.info(f"Using cached rate from {date_str}")
                return self.rates_cache[date_str]
            
            # Try to fetch from TCMB
            try:
                url = self._get_tcmb_url(check_date)
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                rate = self._parse_tcmb_xml(response.text)
                if rate:
                    # Cache the rate
                    self.rates_cache[date_str] = rate
                    self._save_cache()
                    logger.info(f"Using most recent rate from {date_str}: {rate}")
                    return rate
                    
            except Exception:
                continue
        
        # If no rate found, use a default rate (approximate current rate)
        default_rate = 41.0  # Approximate current USD/TL rate
        logger.warning(f"No exchange rate found, using default rate: {default_rate}")
        return default_rate
    
    def convert_tl_to_usd(self, tl_amount: float, payment_date: datetime) -> Tuple[float, Optional[float]]:
        """
        Convert TL amount to USD using TCMB rate
        Returns (usd_amount, exchange_rate)
        """
        if tl_amount <= 0:
            return 0.0, None
        
        rate = self.get_usd_rate(payment_date)
        if rate is None:
            logger.warning(f"No exchange rate available for {payment_date.strftime('%Y-%m-%d')}")
            return 0.0, None
        
        usd_amount = tl_amount / rate
        return round(usd_amount, 2), rate
    
    def get_cached_rates(self) -> Dict:
        """Get all cached exchange rates"""
        return self.rates_cache.copy()
    
    def clear_cache(self):
        """Clear the exchange rates cache"""
        self.rates_cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("Exchange rates cache cleared")
    
    def validate_rate(self, date: datetime, expected_rate: float) -> bool:
        """Validate if a cached rate matches expected value"""
        date_str = date.strftime("%Y-%m-%d")
        cached_rate = self.rates_cache.get(date_str)
        return cached_rate is not None and abs(cached_rate - expected_rate) < 0.001

# Global converter instance
converter = CurrencyConverter()

def convert_payment_to_usd(tl_amount: float, payment_date: datetime) -> Tuple[float, Optional[float]]:
    """Convenience function for converting payments"""
    return converter.convert_tl_to_usd(tl_amount, payment_date)

def get_usd_rate_for_date(date: datetime) -> Optional[float]:
    """Convenience function for getting USD rate"""
    return converter.get_usd_rate(date)
