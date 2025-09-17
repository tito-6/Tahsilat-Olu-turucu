"""
Local storage module for JSON persistence
Handles data storage, retrieval, and daily snapshots
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import shutil

from data_import import PaymentData

logger = logging.getLogger(__name__)

class PaymentStorage:
    """Handles local storage of payment data in JSON format"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.main_file = self.data_dir / "payments.json"
        self.snapshots_dir = self.data_dir / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        
        self.payments: List[PaymentData] = []
        self.load_data()
    
    def load_data(self) -> None:
        """Load payment data from main JSON file"""
        if self.main_file.exists():
            try:
                with open(self.main_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.payments = []
                for item in data.get('payments', []):
                    try:
                        payment = PaymentData.from_dict(item)
                        self.payments.append(payment)
                    except Exception as e:
                        logger.warning(f"Failed to load payment record: {e}")
                        continue
                
                logger.info(f"Loaded {len(self.payments)} payment records")
            except Exception as e:
                logger.error(f"Failed to load data: {e}")
                self.payments = []
        else:
            logger.info("No existing data file found, starting fresh")
            self.payments = []
    
    def save_data(self) -> None:
        """Save payment data to main JSON file"""
        try:
            data = {
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'total_payments': len(self.payments),
                    'version': '1.0'
                },
                'payments': [payment.to_dict() for payment in self.payments]
            }
            
            with open(self.main_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self.payments)} payment records")
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    def add_payments(self, new_payments: List[PaymentData]) -> None:
        """Add new payment records"""
        self.payments.extend(new_payments)
        self.save_data()
        logger.info(f"Added {len(new_payments)} new payment records")
    
    def update_payment(self, index: int, updated_payment: PaymentData) -> bool:
        """Update a specific payment record"""
        if 0 <= index < len(self.payments):
            self.payments[index] = updated_payment
            self.save_data()
            logger.info(f"Updated payment record at index {index}")
            return True
        return False
    
    def delete_payment(self, index: int) -> bool:
        """Delete a specific payment record"""
        if 0 <= index < len(self.payments):
            deleted_payment = self.payments.pop(index)
            self.save_data()
            logger.info(f"Deleted payment record: {deleted_payment.customer_name}")
            return True
        return False
    
    def get_all_payments(self) -> List[PaymentData]:
        """Get all payment records"""
        return self.payments.copy()
    
    def remove_payment(self, payment_to_remove: PaymentData) -> bool:
        """Remove a specific payment from storage"""
        try:
            # Find and remove the payment
            for i, payment in enumerate(self.payments):
                if (payment.customer_name == payment_to_remove.customer_name and
                    payment.date == payment_to_remove.date and
                    abs(payment.amount - payment_to_remove.amount) < 0.01):
                    
                    self.payments.pop(i)
                    self._save_data()
                    logger.info(f"Removed payment: {payment.customer_name} - {payment.amount}")
                    return True
            
            logger.warning("Payment not found for removal")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove payment: {e}")
            return False
    
    def get_payments_by_date_range(self, start_date: datetime, end_date: datetime) -> List[PaymentData]:
        """Get payments within a date range"""
        filtered_payments = []
        for payment in self.payments:
            if payment.date and start_date <= payment.date <= end_date:
                filtered_payments.append(payment)
        return filtered_payments
    
    def get_payments_by_project(self, project_name: str) -> List[PaymentData]:
        """Get payments for a specific project"""
        return [p for p in self.payments if p.project_name == project_name]
    
    def get_payments_by_customer(self, customer_name: str) -> List[PaymentData]:
        """Get payments for a specific customer"""
        return [p for p in self.payments if p.customer_name == customer_name]
    
    def get_payments_by_channel(self, channel: str) -> List[PaymentData]:
        """Get payments for a specific payment channel"""
        return [p for p in self.payments if p.payment_channel == channel]
    
    def get_unique_projects(self) -> List[str]:
        """Get list of unique project names"""
        projects = set(p.project_name for p in self.payments if p.project_name)
        return sorted(list(projects))
    
    def get_unique_customers(self) -> List[str]:
        """Get list of unique customer names"""
        customers = set(p.customer_name for p in self.payments if p.customer_name)
        return sorted(list(customers))
    
    def get_unique_channels(self) -> List[str]:
        """Get list of unique payment channels"""
        channels = set(p.payment_channel for p in self.payments if p.payment_channel)
        return sorted(list(channels))
    
    def create_daily_snapshot(self) -> str:
        """Create a daily snapshot of the data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = self.snapshots_dir / f"snapshot_{timestamp}.json"
        
        try:
            data = {
                'metadata': {
                    'snapshot_date': datetime.now().isoformat(),
                    'total_payments': len(self.payments),
                    'version': '1.0'
                },
                'payments': [payment.to_dict() for payment in self.payments]
            }
            
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created daily snapshot: {snapshot_file}")
            return str(snapshot_file)
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise
    
    def restore_from_snapshot(self, snapshot_file: str) -> bool:
        """Restore data from a snapshot"""
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Backup current data
            backup_file = self.main_file.with_suffix('.backup')
            if self.main_file.exists():
                shutil.copy2(self.main_file, backup_file)
            
            # Restore from snapshot
            self.payments = []
            for item in data.get('payments', []):
                try:
                    payment = PaymentData.from_dict(item)
                    self.payments.append(payment)
                except Exception as e:
                    logger.warning(f"Failed to restore payment record: {e}")
                    continue
            
            self.save_data()
            logger.info(f"Restored data from snapshot: {snapshot_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore from snapshot: {e}")
            return False
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots"""
        snapshots = []
        for snapshot_file in self.snapshots_dir.glob("snapshot_*.json"):
            try:
                stat = snapshot_file.stat()
                snapshots.append({
                    'file': str(snapshot_file),
                    'name': snapshot_file.stem,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'size': stat.st_size
                })
            except Exception as e:
                logger.warning(f"Failed to get info for snapshot {snapshot_file}: {e}")
        
        # Sort by creation time (newest first)
        snapshots.sort(key=lambda x: x['created'], reverse=True)
        return snapshots
    
    def cleanup_old_snapshots(self, keep_days: int = 30) -> int:
        """Remove snapshots older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0
        
        for snapshot_file in self.snapshots_dir.glob("snapshot_*.json"):
            try:
                stat = snapshot_file.stat()
                if datetime.fromtimestamp(stat.st_ctime) < cutoff_date:
                    snapshot_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old snapshot: {snapshot_file}")
            except Exception as e:
                logger.warning(f"Failed to remove snapshot {snapshot_file}: {e}")
        
        logger.info(f"Cleaned up {removed_count} old snapshots")
        return removed_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data statistics"""
        if not self.payments:
            return {
                'total_payments': 0,
                'total_amount_tl': 0,
                'total_amount_usd': 0,
                'projects': 0,
                'customers': 0,
                'channels': 0,
                'date_range': None
            }
        
        total_tl = sum(p.amount for p in self.payments if p.is_tl_payment)
        total_usd = sum(p.amount for p in self.payments if not p.is_tl_payment)
        
        dates = [p.date for p in self.payments if p.date]
        date_range = None
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            date_range = {
                'start': min_date.isoformat(),
                'end': max_date.isoformat()
            }
        
        return {
            'total_payments': len(self.payments),
            'total_amount_tl': total_tl,
            'total_amount_usd': total_usd,
            'projects': len(self.get_unique_projects()),
            'customers': len(self.get_unique_customers()),
            'channels': len(self.get_unique_channels()),
            'date_range': date_range
        }
    
    def export_data(self, file_path: str, format: str = 'json') -> None:
        """Export data to external file"""
        if format.lower() == 'json':
            self.save_data()
            shutil.copy2(self.main_file, file_path)
        elif format.lower() == 'csv':
            import pandas as pd
            data = [payment.to_dict() for payment in self.payments]
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported data to {file_path}")
    
    def clear_all_data(self) -> None:
        """Clear all stored payment data"""
        try:
            # Clear in-memory data
            self.payments = []
            
            # Remove main data file
            if self.main_file.exists():
                self.main_file.unlink()
            
            # Remove all snapshots
            if self.snapshots_dir.exists():
                shutil.rmtree(self.snapshots_dir)
                self.snapshots_dir.mkdir(exist_ok=True)
            
            logger.info("All payment data cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            raise

# Global storage instance
storage = PaymentStorage()

def get_storage() -> PaymentStorage:
    """Get the global storage instance"""
    return storage
