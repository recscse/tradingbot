"""
Compliance and Regulatory Manager for Indian Stock Market Trading
Handles SEBI regulations, audit trails, and compliance reporting
"""
import logging
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, BrokerConfig, TradeHistory

logger = logging.getLogger('compliance')

class ComplianceEvent(Enum):
    """Types of compliance events"""
    TRADE_EXECUTION = "TRADE_EXECUTION"
    LARGE_ORDER = "LARGE_ORDER"
    POSITION_LIMIT_BREACH = "POSITION_LIMIT_BREACH"
    UNUSUAL_ACTIVITY = "UNUSUAL_ACTIVITY"
    MARGIN_CALL = "MARGIN_CALL"
    STOP_LOSS_TRIGGER = "STOP_LOSS_TRIGGER"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MARKET_MANIPULATION = "MARKET_MANIPULATION"
    INSIDER_TRADING_ALERT = "INSIDER_TRADING_ALERT"
    REGULATORY_BREACH = "REGULATORY_BREACH"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ComplianceRecord:
    """Individual compliance record"""
    id: str
    timestamp: datetime
    user_id: str
    event_type: ComplianceEvent
    risk_level: RiskLevel
    description: str
    data: Dict[str, Any]
    actions_taken: List[str]
    reviewed: bool = False
    reviewer_id: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    notes: str = ""

class SEBIComplianceRules:
    """SEBI (Securities and Exchange Board of India) compliance rules"""
    
    # Position limits (in percentage of total shares outstanding)
    POSITION_LIMITS = {
        'individual': 0.05,  # 5% for individual investors
        'institutional': 0.10,  # 10% for institutional investors
        'fii': 0.24,  # 24% aggregate for FIIs
    }
    
    # Order size limits (in crores INR)
    ORDER_SIZE_LIMITS = {
        'alert_threshold': 1.0,  # Alert for orders above 1 crore
        'large_order': 5.0,  # Large order above 5 crores
        'block_deal': 25.0,  # Block deal above 25 crores
    }
    
    # Time restrictions
    TRADING_HOURS = {
        'equity_start': '09:15',
        'equity_end': '15:30',
        'derivatives_start': '09:15', 
        'derivatives_end': '15:30',
        'pre_open_start': '09:00',
        'pre_open_end': '09:15',
    }
    
    # Price limits and circuit breakers
    PRICE_LIMITS = {
        'upper_circuit': 0.20,  # 20% upper limit
        'lower_circuit': -0.20,  # 20% lower limit
        'derivatives_limit': 0.10,  # 10% for derivatives
    }

class ComplianceManager:
    """Main compliance management system"""
    
    def __init__(self):
        self.compliance_dir = Path("logs/compliance")
        self.compliance_dir.mkdir(parents=True, exist_ok=True)
        self.records: List[ComplianceRecord] = []
        self.sebi_rules = SEBIComplianceRules()
        
    async def log_compliance_event(self, 
                                  user_id: str,
                                  event_type: ComplianceEvent,
                                  risk_level: RiskLevel,
                                  description: str,
                                  data: Dict[str, Any]) -> str:
        """Log a compliance event"""
        record = ComplianceRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            event_type=event_type,
            risk_level=risk_level,
            description=description,
            data=data,
            actions_taken=[]
        )
        
        self.records.append(record)
        
        # Log to compliance audit file
        await self._write_compliance_log(record)
        
        # Take immediate action for critical events
        if risk_level == RiskLevel.CRITICAL:
            await self._handle_critical_event(record)
            
        logger.info(f"Compliance event logged: {event_type.value} for user {user_id}")
        return record.id
        
    async def _write_compliance_log(self, record: ComplianceRecord):
        """Write compliance record to audit file"""
        log_file = self.compliance_dir / f"compliance_{datetime.now().strftime('%Y%m%d')}.json"
        
        log_entry = {
            **asdict(record),
            'timestamp': record.timestamp.isoformat(),
            'event_type': record.event_type.value,
            'risk_level': record.risk_level.value
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    async def _handle_critical_event(self, record: ComplianceRecord):
        """Handle critical compliance events immediately"""
        actions = []
        
        if record.event_type == ComplianceEvent.POSITION_LIMIT_BREACH:
            # Block further trades for this symbol/user
            actions.append("BLOCK_TRADING_FOR_SYMBOL")
            await self._notify_compliance_team(record)
            
        elif record.event_type == ComplianceEvent.MARKET_MANIPULATION:
            # Suspend user account immediately
            actions.append("SUSPEND_USER_ACCOUNT")
            await self._notify_regulator(record)
            
        elif record.event_type == ComplianceEvent.INSIDER_TRADING_ALERT:
            # Flag account for review
            actions.append("FLAG_ACCOUNT_FOR_REVIEW")
            await self._notify_compliance_team(record)
            
        record.actions_taken = actions
        
    async def _notify_compliance_team(self, record: ComplianceRecord):
        """Notify compliance team of critical events"""
        notification = {
            'type': 'COMPLIANCE_ALERT',
            'severity': 'HIGH',
            'event_id': record.id,
            'user_id': record.user_id,
            'event_type': record.event_type.value,
            'description': record.description,
            'timestamp': record.timestamp.isoformat(),
            'requires_immediate_action': True
        }
        
        # In production, this would send email/SMS/Slack notifications
        logger.critical(f"COMPLIANCE ALERT: {json.dumps(notification, indent=2)}")
        
    async def _notify_regulator(self, record: ComplianceRecord):
        """Notify regulatory authorities for severe violations"""
        report = {
            'type': 'REGULATORY_REPORT',
            'severity': 'CRITICAL',
            'event_id': record.id,
            'user_id': record.user_id,
            'event_type': record.event_type.value,
            'description': record.description,
            'data': record.data,
            'timestamp': record.timestamp.isoformat(),
            'requires_regulatory_action': True
        }
        
        # Save to regulatory reports directory
        report_file = self.compliance_dir / "regulatory_reports" / f"report_{record.id}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.critical(f"REGULATORY REPORT GENERATED: {report_file}")

class TradeComplianceChecker:
    """Real-time trade compliance validation"""
    
    def __init__(self, compliance_manager: ComplianceManager):
        self.compliance_manager = compliance_manager
        self.sebi_rules = SEBIComplianceRules()
        
    async def validate_trade(self, 
                           user_id: str,
                           symbol: str,
                           order_type: str,
                           quantity: int,
                           price: float,
                           broker: str) -> Dict[str, Any]:
        """Validate trade against compliance rules"""
        validation_result = {
            'allowed': True,
            'warnings': [],
            'blocks': [],
            'compliance_checks': []
        }
        
        order_value = quantity * price
        
        # Check order size limits
        if order_value > self.sebi_rules.ORDER_SIZE_LIMITS['block_deal'] * 10000000:  # Convert crores to rupees
            validation_result['blocks'].append("Order exceeds block deal threshold")
            validation_result['allowed'] = False
            
            await self.compliance_manager.log_compliance_event(
                user_id=user_id,
                event_type=ComplianceEvent.LARGE_ORDER,
                risk_level=RiskLevel.CRITICAL,
                description=f"Block deal order: {symbol} worth ₹{order_value:,.2f}",
                data={
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'order_value': order_value,
                    'broker': broker
                }
            )
            
        elif order_value > self.sebi_rules.ORDER_SIZE_LIMITS['large_order'] * 10000000:
            validation_result['warnings'].append("Large order detected")
            
            await self.compliance_manager.log_compliance_event(
                user_id=user_id,
                event_type=ComplianceEvent.LARGE_ORDER,
                risk_level=RiskLevel.HIGH,
                description=f"Large order: {symbol} worth ₹{order_value:,.2f}",
                data={
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'order_value': order_value,
                    'broker': broker
                }
            )
            
        # Check trading hours
        now = datetime.now().time()
        if not self._is_within_trading_hours(now):
            validation_result['blocks'].append("Order placed outside trading hours")
            validation_result['allowed'] = False
            
        # Check position limits (simplified - would need real position data)
        await self._check_position_limits(user_id, symbol, quantity, validation_result)
        
        # Check for unusual activity patterns
        await self._check_unusual_activity(user_id, symbol, order_value, validation_result)
        
        validation_result['compliance_checks'] = [
            'Order size validation',
            'Trading hours check',
            'Position limits check',
            'Unusual activity detection'
        ]
        
        return validation_result
        
    def _is_within_trading_hours(self, current_time) -> bool:
        """Check if current time is within trading hours"""
        trading_start = datetime.strptime(self.sebi_rules.TRADING_HOURS['equity_start'], '%H:%M').time()
        trading_end = datetime.strptime(self.sebi_rules.TRADING_HOURS['equity_end'], '%H:%M').time()
        
        return trading_start <= current_time <= trading_end
        
    async def _check_position_limits(self, user_id: str, symbol: str, quantity: int, validation_result: Dict):
        """Check position limits compliance"""
        # This would integrate with real position tracking system
        # For now, implement basic checks
        
        # Example: Check if quantity exceeds individual position limits
        # This is a simplified check - real implementation would calculate
        # percentage of total outstanding shares
        
        if quantity > 100000:  # Example threshold
            validation_result['warnings'].append("Position approaching individual limits")
            
            await self.compliance_manager.log_compliance_event(
                user_id=user_id,
                event_type=ComplianceEvent.POSITION_LIMIT_BREACH,
                risk_level=RiskLevel.MEDIUM,
                description=f"Large position in {symbol}: {quantity} shares",
                data={
                    'symbol': symbol,
                    'quantity': quantity,
                    'limit_type': 'individual_position'
                }
            )
            
    async def _check_unusual_activity(self, user_id: str, symbol: str, order_value: float, validation_result: Dict):
        """Check for unusual trading activity patterns"""
        # This would analyze historical trading patterns
        # For now, implement basic velocity checks
        
        # Check if this is unusually large compared to user's typical orders
        if order_value > 1000000:  # ₹10 lakhs threshold
            validation_result['warnings'].append("Order significantly larger than typical")
            
            await self.compliance_manager.log_compliance_event(
                user_id=user_id,
                event_type=ComplianceEvent.UNUSUAL_ACTIVITY,
                risk_level=RiskLevel.MEDIUM,
                description=f"Unusually large order for user: {symbol} worth ₹{order_value:,.2f}",
                data={
                    'symbol': symbol,
                    'order_value': order_value,
                    'pattern': 'large_order_for_user'
                }
            )

class ComplianceReportGenerator:
    """Generate compliance reports for regulatory filing"""
    
    def __init__(self, compliance_manager: ComplianceManager):
        self.compliance_manager = compliance_manager
        
    async def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily compliance report"""
        report_date = date.strftime('%Y-%m-%d')
        
        # Read compliance logs for the date
        log_file = self.compliance_manager.compliance_dir / f"compliance_{date.strftime('%Y%m%d')}.json"
        
        if not log_file.exists():
            return {'date': report_date, 'events': [], 'summary': {}}
            
        events = []
        with open(log_file, 'r') as f:
            for line in f:
                events.append(json.loads(line))
                
        # Generate summary
        summary = {
            'total_events': len(events),
            'by_risk_level': {},
            'by_event_type': {},
            'critical_events': 0,
            'actions_taken': 0
        }
        
        for event in events:
            risk_level = event['risk_level']
            event_type = event['event_type']
            
            summary['by_risk_level'][risk_level] = summary['by_risk_level'].get(risk_level, 0) + 1
            summary['by_event_type'][event_type] = summary['by_event_type'].get(event_type, 0) + 1
            
            if risk_level == 'CRITICAL':
                summary['critical_events'] += 1
                
            if event['actions_taken']:
                summary['actions_taken'] += 1
                
        report = {
            'date': report_date,
            'events': events,
            'summary': summary,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save report
        report_file = self.compliance_manager.compliance_dir / "reports" / f"daily_report_{report_date}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Daily compliance report generated: {report_file}")
        return report
        
    async def generate_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Generate monthly compliance summary"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
            
        # Collect all events for the month
        all_events = []
        current_date = start_date
        
        while current_date < end_date:
            log_file = self.compliance_manager.compliance_dir / f"compliance_{current_date.strftime('%Y%m%d')}.json"
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        all_events.append(json.loads(line))
                        
            current_date += timedelta(days=1)
            
        # Generate comprehensive summary
        summary = {
            'month': f"{year}-{month:02d}",
            'total_events': len(all_events),
            'daily_average': len(all_events) / (end_date - start_date).days,
            'by_risk_level': {},
            'by_event_type': {},
            'trends': {},
            'recommendations': []
        }
        
        # Analyze trends and patterns
        for event in all_events:
            risk_level = event['risk_level']
            event_type = event['event_type']
            
            summary['by_risk_level'][risk_level] = summary['by_risk_level'].get(risk_level, 0) + 1
            summary['by_event_type'][event_type] = summary['by_event_type'].get(event_type, 0) + 1
            
        # Add recommendations based on patterns
        if summary['by_risk_level'].get('CRITICAL', 0) > 5:
            summary['recommendations'].append("Review risk management procedures - high number of critical events")
            
        if summary['by_event_type'].get('LARGE_ORDER', 0) > 50:
            summary['recommendations'].append("Consider implementing additional order size controls")
            
        report = {
            'summary': summary,
            'total_events': len(all_events),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save monthly report
        report_file = self.compliance_manager.compliance_dir / "reports" / f"monthly_summary_{year}_{month:02d}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Monthly compliance summary generated: {report_file}")
        return report

# Global compliance manager instance
_compliance_manager = None

def get_compliance_manager() -> ComplianceManager:
    """Get or create the global compliance manager instance"""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager()
    return _compliance_manager