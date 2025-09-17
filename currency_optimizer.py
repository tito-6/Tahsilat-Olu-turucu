"""
Currency Optimization Module
Centralized currency conversion system to eliminate redundant API calls
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from currency import CurrencyConverter, convert_payment_to_usd

logger = logging.getLogger(__name__)

@dataclass
class ConvertedPayment:
    """Payment data with pre-converted USD amounts"""
    original_payment: object  # Original PaymentData object
    usd_amount: float
    exchange_rate: Optional[float]
    is_converted: bool

class CurrencyOptimizer:
    """
    Centralized currency conversion system that eliminates redundant API calls
    by pre-converting all payments once and caching results globally.
    """
    
    def __init__(self):
        self.converter = CurrencyConverter()
        self.converted_payments: List[ConvertedPayment] = []
        self.rate_cache: Dict[str, float] = {}
        self.conversion_stats = {
            'total_payments': 0,
            'tl_payments': 0,
            'api_calls_made': 0,
            'cache_hits': 0,
            'unique_dates': 0
        }
    
    def pre_convert_payments(self, payments: List) -> List[ConvertedPayment]:
        """
        Pre-convert all payments to USD once, eliminating redundant API calls.
        This is the core optimization that fixes the performance issue.
        """
        logger.info(f"Starting currency optimization for {len(payments)} payments...")
        
        # Reset stats
        self.conversion_stats = {
            'total_payments': len(payments),
            'tl_payments': 0,
            'api_calls_made': 0,
            'cache_hits': 0,
            'unique_dates': 0
        }
        
        # Step 1: Collect all unique dates that need conversion
        unique_dates = self._collect_unique_dates(payments)
        logger.info(f"Found {len(unique_dates)} unique dates requiring conversion")
        
        # Step 2: Batch fetch all required exchange rates
        self._batch_fetch_rates(unique_dates)
        
        # Step 3: Convert all payments using cached rates
        converted_payments = []
        for payment in payments:
            converted = self._convert_single_payment(payment)
            converted_payments.append(converted)
        
        self.converted_payments = converted_payments
        
        # Log optimization results
        self._log_optimization_results()
        
        return converted_payments
    
    def _collect_unique_dates(self, payments: List) -> Set[datetime]:
        """Collect all unique dates that need currency conversion"""
        unique_dates = set()
        
        for payment in payments:
            if hasattr(payment, 'is_tl_payment') and payment.is_tl_payment:
                if hasattr(payment, 'date') and payment.date:
                    # Use one day before payment date (as per current logic)
                    target_date = payment.date - timedelta(days=1)
                    unique_dates.add(target_date)
                    self.conversion_stats['tl_payments'] += 1
        
        self.conversion_stats['unique_dates'] = len(unique_dates)
        return unique_dates
    
    def _batch_fetch_rates(self, unique_dates: Set[datetime]):
        """Batch fetch all required exchange rates to minimize API calls"""
        logger.info(f"Batch fetching rates for {len(unique_dates)} unique dates...")
        
        for date in sorted(unique_dates):
            date_str = date.strftime("%Y-%m-%d")
            
            # Check if we already have this rate
            if date_str in self.rate_cache:
                self.conversion_stats['cache_hits'] += 1
                continue
            
            # Fetch the rate
            try:
                rate = self.converter.get_usd_rate(date)
                if rate:
                    self.rate_cache[date_str] = rate
                    self.conversion_stats['api_calls_made'] += 1
                    logger.debug(f"Fetched rate for {date_str}: {rate}")
                else:
                    logger.warning(f"No rate available for {date_str}")
            except Exception as e:
                logger.error(f"Failed to fetch rate for {date_str}: {e}")
    
    def _convert_single_payment(self, payment) -> ConvertedPayment:
        """Convert a single payment using cached rates"""
        if not (hasattr(payment, 'is_tl_payment') and payment.is_tl_payment):
            # Non-TL payment, no conversion needed
            return ConvertedPayment(
                original_payment=payment,
                usd_amount=payment.amount,
                exchange_rate=None,
                is_converted=False
            )
        
        if not (hasattr(payment, 'date') and payment.date):
            # No date available
            return ConvertedPayment(
                original_payment=payment,
                usd_amount=0.0,
                exchange_rate=None,
                is_converted=False
            )
        
        # Use one day before payment date
        target_date = payment.date - timedelta(days=1)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Get rate from cache
        rate = self.rate_cache.get(date_str)
        
        if rate and rate > 0:
            usd_amount = payment.amount / rate
            return ConvertedPayment(
                original_payment=payment,
                usd_amount=round(usd_amount, 2),
                exchange_rate=rate,
                is_converted=True
            )
        else:
            # Try to get the most recent available rate
            fallback_rate = self._get_fallback_rate()
            if fallback_rate and fallback_rate > 0:
                usd_amount = payment.amount / fallback_rate
                logger.warning(f"No rate for {date_str}, using fallback rate {fallback_rate}")
                return ConvertedPayment(
                    original_payment=payment,
                    usd_amount=round(usd_amount, 2),
                    exchange_rate=fallback_rate,
                    is_converted=True
                )
            else:
                logger.warning(f"No cached rate for {date_str}, using 0 USD")
                return ConvertedPayment(
                    original_payment=payment,
                    usd_amount=0.0,
                    exchange_rate=None,
                    is_converted=False
                )
    
    def _get_fallback_rate(self) -> Optional[float]:
        """Get a fallback rate when the specific date rate is not available"""
        # Try to find any available rate in the cache
        for date_str, rate in self.rate_cache.items():
            if rate and rate > 0:
                return rate
        
        # If no cached rate, try to get a recent rate from the converter
        try:
            from datetime import datetime, timedelta
            today = datetime.now()
            for days_back in range(1, 7):  # Try last 7 days
                check_date = today - timedelta(days=days_back)
                rate = self.converter.get_usd_rate(check_date)
                if rate and rate > 0:
                    return rate
        except Exception as e:
            logger.error(f"Error getting fallback rate: {e}")
        
        # Default fallback rate
        return 41.0
    
    def _log_optimization_results(self):
        """Log the optimization results"""
        stats = self.conversion_stats
        logger.info("=== CURRENCY OPTIMIZATION RESULTS ===")
        logger.info(f"Total payments processed: {stats['total_payments']}")
        logger.info(f"TL payments requiring conversion: {stats['tl_payments']}")
        logger.info(f"Unique dates requiring rates: {stats['unique_dates']}")
        logger.info(f"API calls made: {stats['api_calls_made']}")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        
        if stats['api_calls_made'] > 0:
            efficiency = (stats['cache_hits'] / (stats['api_calls_made'] + stats['cache_hits'])) * 100
            logger.info(f"Cache efficiency: {efficiency:.1f}%")
        
        # Calculate potential savings
        if stats['tl_payments'] > 0:
            potential_calls = stats['tl_payments']  # Without optimization
            actual_calls = stats['api_calls_made']  # With optimization
            savings = potential_calls - actual_calls
            savings_percent = (savings / potential_calls) * 100 if potential_calls > 0 else 0
            logger.info(f"API calls saved: {savings} ({savings_percent:.1f}% reduction)")
    
    def get_converted_payments(self) -> List[ConvertedPayment]:
        """Get the pre-converted payments"""
        return self.converted_payments
    
    def get_rate_for_date(self, date: datetime) -> Optional[float]:
        """Get cached rate for a specific date"""
        target_date = date - timedelta(days=1)
        date_str = target_date.strftime("%Y-%m-%d")
        return self.rate_cache.get(date_str)
    
    def clear_cache(self):
        """Clear the rate cache"""
        self.rate_cache.clear()
        self.converted_payments.clear()
        logger.info("Currency optimizer cache cleared")

# Global optimizer instance
_global_optimizer = None

def get_currency_optimizer() -> CurrencyOptimizer:
    """Get the global currency optimizer instance"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = CurrencyOptimizer()
    return _global_optimizer

def optimize_currency_conversion(payments: List) -> List[ConvertedPayment]:
    """
    Main function to optimize currency conversion for a list of payments.
    This should be called once before running any analysis methods.
    """
    optimizer = get_currency_optimizer()
    return optimizer.pre_convert_payments(payments)

def get_optimized_usd_amount(payment) -> float:
    """
    Get the pre-converted USD amount for a payment.
    This replaces direct calls to convert_payment_to_usd() in analysis methods.
    """
    optimizer = get_currency_optimizer()
    
    # Find the converted payment
    for converted in optimizer.get_converted_payments():
        if converted.original_payment == payment:
            return converted.usd_amount
    
    # Fallback to original conversion if not found
    logger.warning("Payment not found in optimized cache, using fallback conversion")
    if hasattr(payment, 'is_tl_payment') and payment.is_tl_payment:
        usd_amount, _ = convert_payment_to_usd(payment.amount, payment.date)
        return usd_amount
    else:
        return payment.amount
