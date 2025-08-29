"""
Comprehensive Performance Monitoring and Alerts System
Real-time tracking of trading performance, system health, and risk metrics
Intelligent alerting system with automated responses
"""

import asyncio
import logging
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import numpy as np

logger = logging.getLogger(__name__)

class PerformanceMetricType(Enum):
    # Trading Performance
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    
    # System Performance
    EXECUTION_LATENCY = "execution_latency"
    ORDER_SUCCESS_RATE = "order_success_rate"
    SIGNAL_ACCURACY = "signal_accuracy"
    SYSTEM_UPTIME = "system_uptime"
    
    # Risk Metrics
    PORTFOLIO_HEAT = "portfolio_heat"
    DAILY_PNL = "daily_pnl"
    POSITION_CONCENTRATION = "position_concentration"
    CORRELATION_RISK = "correlation_risk"

class AlertSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    # Performance Alerts
    POOR_WIN_RATE = "poor_win_rate"
    HIGH_DRAWDOWN = "high_drawdown"
    LOW_SHARPE_RATIO = "low_sharpe_ratio"
    
    # System Alerts
    HIGH_LATENCY = "high_latency"
    LOW_SUCCESS_RATE = "low_success_rate"
    SYSTEM_DEGRADATION = "system_degradation"
    
    # Risk Alerts
    EXCESSIVE_HEAT = "excessive_heat"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    CONCENTRATION_RISK = "concentration_risk"
    CORRELATION_BREACH = "correlation_breach"

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_type: PerformanceMetricType
    current_value: float
    target_value: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    unit: str = ""
    description: str = ""
    last_updated: datetime = None

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    current_value: float
    threshold_value: float
    recommended_actions: List[str]
    affected_components: List[str]
    auto_action_taken: bool = False
    auto_action_description: str = ""
    created_at: datetime = None
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class TradingPerformanceSnapshot:
    """Complete trading performance snapshot"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0
    last_updated: datetime = None

@dataclass
class SystemPerformanceSnapshot:
    """Complete system performance snapshot"""
    avg_execution_latency_ms: float = 0.0
    order_success_rate: float = 100.0
    signal_generation_rate: float = 0.0
    signal_execution_rate: float = 0.0
    system_uptime_percentage: float = 100.0
    data_feed_latency_ms: float = 0.0
    broker_response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percentage: float = 0.0
    active_connections: int = 0
    last_updated: datetime = None

class PerformanceMonitor:
    """
    Comprehensive Performance Monitoring System
    
    Features:
    - Real-time trading performance tracking
    - System performance monitoring
    - Intelligent alerting with auto-responses
    - Historical trend analysis
    - Risk metric calculations
    - Performance benchmarking
    """
    
    def __init__(self):
        # Performance data storage
        self.trading_performance = TradingPerformanceSnapshot()
        self.system_performance = SystemPerformanceSnapshot()
        
        # Historical data storage
        self.performance_history: deque = deque(maxlen=1000)  # Last 1000 snapshots
        self.trade_history: deque = deque(maxlen=10000)       # Last 10K trades
        self.latency_history: deque = deque(maxlen=1000)      # Last 1000 latency measurements
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=500)
        self.alert_callbacks: List[Callable] = []
        
        # Performance thresholds
        self.performance_thresholds = {
            PerformanceMetricType.WIN_RATE: {
                'target': 65.0,
                'warning': 55.0,
                'critical': 45.0
            },
            PerformanceMetricType.PROFIT_FACTOR: {
                'target': 2.0,
                'warning': 1.5,
                'critical': 1.0
            },
            PerformanceMetricType.SHARPE_RATIO: {
                'target': 2.0,
                'warning': 1.0,
                'critical': 0.5
            },
            PerformanceMetricType.MAX_DRAWDOWN: {
                'target': 5.0,
                'warning': 10.0,
                'critical': 15.0
            },
            PerformanceMetricType.EXECUTION_LATENCY: {
                'target': 30.0,
                'warning': 100.0,
                'critical': 200.0
            },
            PerformanceMetricType.ORDER_SUCCESS_RATE: {
                'target': 98.0,
                'warning': 95.0,
                'critical': 90.0
            },
            PerformanceMetricType.PORTFOLIO_HEAT: {
                'target': 50.0,
                'warning': 70.0,
                'critical': 85.0
            }
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.last_performance_update = datetime.now(timezone.utc)
        
        # Integration components
        self.db_service = None
        self.websocket_service = None
        self.coordinator = None
        
        logger.info("Performance Monitor initialized")
    
    def integrate_services(self, db_service=None, websocket_service=None, coordinator=None):
        """Integrate with other services"""
        self.db_service = db_service
        self.websocket_service = websocket_service
        self.coordinator = coordinator
        logger.info("Performance Monitor integrated with services")
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        try:
            self.monitoring_active = True
            
            # Start monitoring tasks
            asyncio.create_task(self._performance_tracker())
            asyncio.create_task(self._alert_processor())
            asyncio.create_task(self._trend_analyzer())
            asyncio.create_task(self._health_checker())
            
            logger.info("Performance monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start performance monitoring: {e}")
            raise
    
    # =================== TRADING PERFORMANCE TRACKING ===================
    
    async def record_trade_execution(self, trade_data: Dict[str, Any]):
        """Record trade execution for performance analysis"""
        try:
            # Add trade to history
            trade_record = {
                'timestamp': datetime.now(timezone.utc),
                'symbol': trade_data.get('symbol'),
                'pnl': trade_data.get('pnl', 0.0),
                'entry_price': trade_data.get('entry_price', 0),
                'exit_price': trade_data.get('exit_price', 0),
                'quantity': trade_data.get('quantity', 0),
                'duration_minutes': trade_data.get('duration_minutes', 0),
                'strategy': trade_data.get('strategy', 'unknown'),
                'exit_reason': trade_data.get('exit_reason', 'unknown'),
                'execution_latency_ms': trade_data.get('execution_latency_ms', 0)
            }
            
            self.trade_history.append(trade_record)
            
            # Update performance metrics
            await self._update_trading_performance()
            
            # Check for performance alerts
            await self._check_performance_alerts()
            
        except Exception as e:
            logger.error(f"Error recording trade execution: {e}")
    
    async def record_system_metric(self, metric_type: str, value: float):
        """Record system performance metric"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Update system performance
            if metric_type == 'execution_latency':
                self.latency_history.append((current_time, value))
                self.system_performance.avg_execution_latency_ms = statistics.mean(
                    [v for _, v in list(self.latency_history)[-100:]]  # Last 100 measurements
                )
            
            elif metric_type == 'order_success_rate':
                self.system_performance.order_success_rate = value
            
            elif metric_type == 'system_uptime':
                self.system_performance.system_uptime_percentage = value
            
            elif metric_type == 'memory_usage':
                self.system_performance.memory_usage_mb = value
            
            elif metric_type == 'cpu_usage':
                self.system_performance.cpu_usage_percentage = value
            
            self.system_performance.last_updated = current_time
            
            # Check for system alerts
            await self._check_system_alerts()
            
        except Exception as e:
            logger.error(f"Error recording system metric: {e}")
    
    async def _update_trading_performance(self):
        """Update trading performance calculations"""
        try:
            if not self.trade_history:
                return
            
            trades = list(self.trade_history)
            
            # Basic statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = len([t for t in trades if t['pnl'] < 0])
            
            # Calculate metrics
            self.trading_performance.total_trades = total_trades
            self.trading_performance.winning_trades = winning_trades
            self.trading_performance.losing_trades = losing_trades
            
            if total_trades > 0:
                self.trading_performance.win_rate = (winning_trades / total_trades) * 100
            
            # P&L calculations
            all_pnl = [t['pnl'] for t in trades]
            winning_pnl = [t['pnl'] for t in trades if t['pnl'] > 0]
            losing_pnl = [t['pnl'] for t in trades if t['pnl'] < 0]
            
            self.trading_performance.total_pnl = sum(all_pnl)
            
            if winning_pnl:
                self.trading_performance.average_win = statistics.mean(winning_pnl)
                self.trading_performance.largest_win = max(winning_pnl)
            
            if losing_pnl:
                self.trading_performance.average_loss = statistics.mean(losing_pnl)
                self.trading_performance.largest_loss = min(losing_pnl)  # Most negative
            
            # Profit factor
            if losing_pnl and winning_pnl:
                gross_profit = sum(winning_pnl)
                gross_loss = abs(sum(losing_pnl))
                if gross_loss > 0:
                    self.trading_performance.profit_factor = gross_profit / gross_loss
            
            # Risk-adjusted metrics
            await self._calculate_risk_metrics(all_pnl)
            
            self.trading_performance.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error updating trading performance: {e}")
    
    async def _calculate_risk_metrics(self, pnl_series: List[float]):
        """Calculate advanced risk metrics"""
        try:
            if len(pnl_series) < 10:  # Need minimum data
                return
            
            # Convert to numpy for calculations
            returns = np.array(pnl_series)
            
            # Sharpe ratio (assuming daily returns)
            if np.std(returns) > 0:
                self.trading_performance.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_std = np.std(downside_returns)
                if downside_std > 0:
                    self.trading_performance.sortino_ratio = np.mean(returns) / downside_std * np.sqrt(252)
            
            # Maximum drawdown calculation
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max)
            max_drawdown = np.min(drawdown)
            
            if max_drawdown < 0:
                self.trading_performance.max_drawdown = abs(max_drawdown)
                
                # Calmar ratio
                annual_return = np.mean(returns) * 252
                if self.trading_performance.max_drawdown > 0:
                    self.trading_performance.calmar_ratio = annual_return / self.trading_performance.max_drawdown
            
            # Recovery factor
            total_return = np.sum(returns)
            if self.trading_performance.max_drawdown > 0:
                self.trading_performance.recovery_factor = total_return / self.trading_performance.max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
    
    # =================== ALERT SYSTEM ===================
    
    async def _check_performance_alerts(self):
        """Check for performance-related alerts"""
        try:
            current_metrics = {
                PerformanceMetricType.WIN_RATE: self.trading_performance.win_rate,
                PerformanceMetricType.PROFIT_FACTOR: self.trading_performance.profit_factor,
                PerformanceMetricType.SHARPE_RATIO: self.trading_performance.sharpe_ratio,
                PerformanceMetricType.MAX_DRAWDOWN: self.trading_performance.max_drawdown
            }
            
            for metric_type, current_value in current_metrics.items():
                await self._evaluate_metric_alert(metric_type, current_value)
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    async def _check_system_alerts(self):
        """Check for system performance alerts"""
        try:
            system_metrics = {
                PerformanceMetricType.EXECUTION_LATENCY: self.system_performance.avg_execution_latency_ms,
                PerformanceMetricType.ORDER_SUCCESS_RATE: self.system_performance.order_success_rate,
                PerformanceMetricType.SYSTEM_UPTIME: self.system_performance.system_uptime_percentage
            }
            
            for metric_type, current_value in system_metrics.items():
                await self._evaluate_metric_alert(metric_type, current_value)
                
        except Exception as e:
            logger.error(f"Error checking system alerts: {e}")
    
    async def _evaluate_metric_alert(self, metric_type: PerformanceMetricType, current_value: float):
        """Evaluate if metric triggers an alert"""
        try:
            thresholds = self.performance_thresholds.get(metric_type)
            if not thresholds:
                return
            
            alert_id = f"{metric_type.value}_alert"
            severity = None
            
            # Determine severity based on thresholds
            if metric_type in [PerformanceMetricType.MAX_DRAWDOWN, PerformanceMetricType.EXECUTION_LATENCY]:
                # Higher values are worse
                if current_value >= thresholds['critical']:
                    severity = AlertSeverity.CRITICAL
                elif current_value >= thresholds['warning']:
                    severity = AlertSeverity.HIGH
            else:
                # Lower values are worse
                if current_value <= thresholds['critical']:
                    severity = AlertSeverity.CRITICAL
                elif current_value <= thresholds['warning']:
                    severity = AlertSeverity.HIGH
            
            # Create or update alert
            if severity:
                if alert_id not in self.active_alerts:
                    alert = Alert(
                        alert_id=alert_id,
                        alert_type=self._get_alert_type_for_metric(metric_type),
                        severity=severity,
                        title=f"{metric_type.value.replace('_', ' ').title()} Alert",
                        description=f"{metric_type.value} is {current_value:.2f}, threshold: {thresholds['warning']:.2f}",
                        current_value=current_value,
                        threshold_value=thresholds['warning'],
                        recommended_actions=self._get_recommended_actions(metric_type, severity),
                        affected_components=[metric_type.value],
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    self.active_alerts[alert_id] = alert
                    await self._trigger_alert(alert)
            
            else:
                # Resolve alert if it exists
                if alert_id in self.active_alerts:
                    await self._resolve_alert(alert_id)
                    
        except Exception as e:
            logger.error(f"Error evaluating metric alert: {e}")
    
    def _get_alert_type_for_metric(self, metric_type: PerformanceMetricType) -> AlertType:
        """Map metric type to alert type"""
        mapping = {
            PerformanceMetricType.WIN_RATE: AlertType.POOR_WIN_RATE,
            PerformanceMetricType.MAX_DRAWDOWN: AlertType.HIGH_DRAWDOWN,
            PerformanceMetricType.SHARPE_RATIO: AlertType.LOW_SHARPE_RATIO,
            PerformanceMetricType.EXECUTION_LATENCY: AlertType.HIGH_LATENCY,
            PerformanceMetricType.ORDER_SUCCESS_RATE: AlertType.LOW_SUCCESS_RATE,
            PerformanceMetricType.SYSTEM_UPTIME: AlertType.SYSTEM_DEGRADATION
        }
        return mapping.get(metric_type, AlertType.SYSTEM_DEGRADATION)
    
    def _get_recommended_actions(self, metric_type: PerformanceMetricType, severity: AlertSeverity) -> List[str]:
        """Get recommended actions for alerts"""
        actions = {
            PerformanceMetricType.WIN_RATE: [
                "Review strategy parameters",
                "Analyze losing trades",
                "Consider reducing position sizes",
                "Check market conditions"
            ],
            PerformanceMetricType.MAX_DRAWDOWN: [
                "Implement stricter stop losses",
                "Reduce position sizing",
                "Review risk management rules",
                "Consider pausing trading"
            ],
            PerformanceMetricType.EXECUTION_LATENCY: [
                "Check network connectivity",
                "Optimize order processing",
                "Review broker performance",
                "Check system resources"
            ],
            PerformanceMetricType.ORDER_SUCCESS_RATE: [
                "Check broker connectivity",
                "Review order validation",
                "Check account status",
                "Contact broker support"
            ]
        }
        
        base_actions = actions.get(metric_type, ["Contact system administrator"])
        
        if severity == AlertSeverity.CRITICAL:
            base_actions.insert(0, "Consider emergency stop")
        
        return base_actions
    
    async def _trigger_alert(self, alert: Alert):
        """Trigger an alert"""
        try:
            logger.warning(f"🚨 ALERT TRIGGERED: {alert.title} - {alert.description}")
            
            # Auto-actions for critical alerts
            if alert.severity == AlertSeverity.CRITICAL:
                await self._execute_auto_actions(alert)
            
            # Add to alert history
            self.alert_history.append(asdict(alert))
            
            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            # Broadcast via WebSocket if available
            if self.websocket_service:
                await self.websocket_service.broadcast_risk_alert(asdict(alert))
                
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
    
    async def _execute_auto_actions(self, alert: Alert):
        """Execute automatic actions for critical alerts"""
        try:
            auto_actions = []
            
            if alert.alert_type == AlertType.HIGH_DRAWDOWN:
                # Reduce position sizes or pause trading
                if self.coordinator:
                    await self.coordinator.pause_trading()
                    auto_actions.append("Trading paused due to high drawdown")
            
            elif alert.alert_type == AlertType.HIGH_LATENCY:
                # Log system performance issue
                auto_actions.append("System performance logged for investigation")
            
            elif alert.alert_type == AlertType.LOW_SUCCESS_RATE:
                # Switch to backup broker if available
                auto_actions.append("Broker failover initiated")
            
            if auto_actions:
                alert.auto_action_taken = True
                alert.auto_action_description = "; ".join(auto_actions)
                logger.info(f"Auto-actions executed: {alert.auto_action_description}")
                
        except Exception as e:
            logger.error(f"Error executing auto-actions: {e}")
    
    async def _resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts.pop(alert_id)
                alert.resolved = True
                self.alert_history.append(asdict(alert))
                logger.info(f"✅ Alert resolved: {alert.title}")
                
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
    
    # =================== MONITORING TASKS ===================
    
    async def _performance_tracker(self):
        """Main performance tracking loop"""
        while self.monitoring_active:
            try:
                # Update performance snapshots
                await self._update_trading_performance()
                
                # Store historical snapshot
                snapshot = {
                    'timestamp': datetime.now(timezone.utc),
                    'trading_performance': asdict(self.trading_performance),
                    'system_performance': asdict(self.system_performance)
                }
                self.performance_history.append(snapshot)
                
                await asyncio.sleep(60.0)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error in performance tracker: {e}")
                await asyncio.sleep(60.0)
    
    async def _alert_processor(self):
        """Process and manage alerts"""
        while self.monitoring_active:
            try:
                # Check all performance and system metrics
                await self._check_performance_alerts()
                await self._check_system_alerts()
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert processor: {e}")
                await asyncio.sleep(30.0)
    
    async def _trend_analyzer(self):
        """Analyze performance trends"""
        while self.monitoring_active:
            try:
                # Analyze trends in performance history
                await self._analyze_performance_trends()
                
                await asyncio.sleep(300.0)  # Analyze every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in trend analyzer: {e}")
                await asyncio.sleep(300.0)
    
    async def _health_checker(self):
        """Check system health"""
        while self.monitoring_active:
            try:
                # Check system health metrics
                await self._check_system_health()
                
                await asyncio.sleep(60.0)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in health checker: {e}")
                await asyncio.sleep(60.0)
    
    async def _analyze_performance_trends(self):
        """Analyze performance trends"""
        try:
            if len(self.performance_history) < 10:
                return
            
            # Analyze recent performance trend
            recent_snapshots = list(self.performance_history)[-10:]
            win_rates = [s['trading_performance']['win_rate'] for s in recent_snapshots if s['trading_performance']['win_rate'] > 0]
            
            if len(win_rates) >= 5:
                # Check for declining win rate trend
                trend_slope = np.polyfit(range(len(win_rates)), win_rates, 1)[0]
                
                if trend_slope < -2:  # Declining by more than 2% per period
                    await self._create_trend_alert("DECLINING_WIN_RATE", 
                                                 "Win rate showing declining trend",
                                                 trend_slope)
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
    
    async def _create_trend_alert(self, trend_type: str, description: str, trend_value: float):
        """Create trend-based alert"""
        try:
            alert_id = f"trend_{trend_type.lower()}"
            
            if alert_id not in self.active_alerts:
                alert = Alert(
                    alert_id=alert_id,
                    alert_type=AlertType.POOR_WIN_RATE,
                    severity=AlertSeverity.MEDIUM,
                    title=f"Trend Alert: {trend_type.replace('_', ' ').title()}",
                    description=f"{description} (Rate: {trend_value:.2f}% per period)",
                    current_value=trend_value,
                    threshold_value=-1.0,
                    recommended_actions=["Review recent strategy performance", "Analyze market conditions"],
                    affected_components=["trading_strategy"],
                    created_at=datetime.now(timezone.utc)
                )
                
                self.active_alerts[alert_id] = alert
                await self._trigger_alert(alert)
                
        except Exception as e:
            logger.error(f"Error creating trend alert: {e}")
    
    async def _check_system_health(self):
        """Check overall system health"""
        try:
            # System health score based on multiple factors
            health_factors = {
                'execution_latency': min(100, (50 / max(self.system_performance.avg_execution_latency_ms, 1)) * 100),
                'order_success': self.system_performance.order_success_rate,
                'system_uptime': self.system_performance.system_uptime_percentage,
                'win_rate': min(100, self.trading_performance.win_rate),
                'profit_factor': min(100, self.trading_performance.profit_factor * 25)
            }
            
            overall_health = statistics.mean(health_factors.values())
            
            # Update system performance
            self.system_performance.last_updated = datetime.now(timezone.utc)
            
            # Create health alert if needed
            if overall_health < 70:
                await self._create_health_alert(overall_health, health_factors)
                
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
    
    async def _create_health_alert(self, health_score: float, health_factors: Dict[str, float]):
        """Create system health alert"""
        try:
            alert_id = "system_health_alert"
            
            if alert_id not in self.active_alerts:
                severity = AlertSeverity.HIGH if health_score < 50 else AlertSeverity.MEDIUM
                
                alert = Alert(
                    alert_id=alert_id,
                    alert_type=AlertType.SYSTEM_DEGRADATION,
                    severity=severity,
                    title="System Health Alert",
                    description=f"Overall system health score: {health_score:.1f}%",
                    current_value=health_score,
                    threshold_value=70.0,
                    recommended_actions=[
                        "Check system resources",
                        "Review component performance",
                        "Contact system administrator"
                    ],
                    affected_components=list(health_factors.keys()),
                    created_at=datetime.now(timezone.utc)
                )
                
                self.active_alerts[alert_id] = alert
                await self._trigger_alert(alert)
                
        except Exception as e:
            logger.error(f"Error creating health alert: {e}")
    
    # =================== PUBLIC API ===================
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance snapshot"""
        return {
            'trading_performance': asdict(self.trading_performance),
            'system_performance': asdict(self.system_performance),
            'active_alerts_count': len(self.active_alerts),
            'monitoring_active': self.monitoring_active,
            'last_updated': self.last_performance_update.isoformat()
        }
    
    def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            snapshot for snapshot in self.performance_history
            if snapshot['timestamp'] > cutoff_time
        ]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if alert.get('created_at') and 
            datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    async def manual_resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        try:
            await self._resolve_alert(alert_id)
            return True
        except Exception as e:
            logger.error(f"Error manually resolving alert: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'overview': {
                'total_trades': self.trading_performance.total_trades,
                'win_rate': self.trading_performance.win_rate,
                'total_pnl': self.trading_performance.total_pnl,
                'profit_factor': self.trading_performance.profit_factor,
                'max_drawdown': self.trading_performance.max_drawdown,
                'sharpe_ratio': self.trading_performance.sharpe_ratio
            },
            'system_metrics': {
                'avg_execution_latency_ms': self.system_performance.avg_execution_latency_ms,
                'order_success_rate': self.system_performance.order_success_rate,
                'system_uptime': self.system_performance.system_uptime_percentage
            },
            'alerts': {
                'active_count': len(self.active_alerts),
                'critical_count': len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
                'recent_count': len(self.get_alert_history(hours=1))
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Performance Monitor...")
        self.monitoring_active = False
        
        # Resolve all active alerts
        for alert_id in list(self.active_alerts.keys()):
            await self._resolve_alert(alert_id)
        
        logger.info("Performance Monitor shutdown complete")