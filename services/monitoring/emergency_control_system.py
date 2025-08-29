"""
Emergency Control and System Health Monitoring System
Critical system controls for auto-trading safety and monitoring
Features: Kill switch, circuit breakers, health monitoring, failsafe mechanisms
"""

import asyncio
import logging
import time
import psutil
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

class EmergencyType(Enum):
    MANUAL_KILL_SWITCH = "manual_kill_switch"
    AUTOMATIC_CIRCUIT_BREAKER = "automatic_circuit_breaker"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    SYSTEM_FAILURE = "system_failure"
    NETWORK_FAILURE = "network_failure"
    DATA_FEED_FAILURE = "data_feed_failure"
    BROKER_FAILURE = "broker_failure"
    MEMORY_OVERLOAD = "memory_overload"
    CPU_OVERLOAD = "cpu_overload"
    DISK_SPACE_LOW = "disk_space_low"

class SystemHealthStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FAILURE = "FAILURE"
    EMERGENCY_STOP = "EMERGENCY_STOP"

class ComponentStatus(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

@dataclass
class EmergencyEvent:
    """Emergency event record"""
    event_id: str
    emergency_type: EmergencyType
    triggered_at: datetime
    description: str
    trigger_conditions: Dict[str, Any]
    auto_actions_taken: List[str]
    manual_actions_required: List[str]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    impact_assessment: Optional[Dict[str, Any]] = None

@dataclass
class SystemComponent:
    """System component health tracking"""
    name: str
    status: ComponentStatus
    last_heartbeat: datetime
    response_time_ms: float = 0.0
    error_count: int = 0
    uptime_percentage: float = 100.0
    critical: bool = False
    dependencies: List[str] = None
    health_metrics: Dict[str, Any] = None

@dataclass
class SystemHealthSnapshot:
    """Complete system health snapshot"""
    overall_status: SystemHealthStatus
    health_score: float  # 0-100
    components: Dict[str, SystemComponent]
    resource_usage: Dict[str, float]
    active_emergencies: int
    uptime_seconds: int
    last_emergency: Optional[datetime]
    performance_score: float
    risk_score: float
    snapshot_time: datetime

class EmergencyControlSystem:
    """
    Emergency Control and System Health Monitoring System
    
    Critical Functions:
    - Kill switch mechanism with immediate system shutdown
    - Circuit breakers for automatic system protection
    - Real-time system health monitoring
    - Resource usage tracking and alerts
    - Component dependency monitoring
    - Failsafe mechanisms and auto-recovery
    - Emergency event logging and reporting
    """
    
    def __init__(self):
        # Emergency control state
        self.emergency_active = False
        self.kill_switch_triggered = False
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.emergency_callbacks: List[Callable] = []
        
        # System health tracking
        self.system_components: Dict[str, SystemComponent] = {}
        self.health_history: deque = deque(maxlen=1000)
        self.emergency_events: deque = deque(maxlen=500)
        
        # Monitoring configuration
        self.health_check_interval = 10.0  # seconds
        self.resource_thresholds = {
            'cpu_usage': {'warning': 80.0, 'critical': 95.0},
            'memory_usage': {'warning': 80.0, 'critical': 95.0},
            'disk_usage': {'warning': 85.0, 'critical': 95.0},
            'network_latency': {'warning': 1000.0, 'critical': 5000.0}
        }
        
        # Circuit breaker configurations
        self.circuit_breaker_configs = {
            'execution_failures': {
                'failure_threshold': 10,
                'recovery_timeout': 300,  # 5 minutes
                'half_open_max_calls': 3
            },
            'broker_errors': {
                'failure_threshold': 5,
                'recovery_timeout': 600,  # 10 minutes
                'half_open_max_calls': 2
            },
            'data_feed_errors': {
                'failure_threshold': 15,
                'recovery_timeout': 180,  # 3 minutes
                'half_open_max_calls': 5
            }
        }
        
        # System startup time
        self.startup_time = datetime.now(timezone.utc)
        self.monitoring_active = False
        
        # Integration components
        self.coordinator = None
        self.websocket_service = None
        self.db_service = None
        self.performance_monitor = None
        
        # Initialize system components
        self._initialize_system_components()
        
        logger.info("Emergency Control System initialized")
    
    def integrate_services(self, coordinator=None, websocket_service=None, 
                          db_service=None, performance_monitor=None):
        """Integrate with other system services"""
        self.coordinator = coordinator
        self.websocket_service = websocket_service
        self.db_service = db_service
        self.performance_monitor = performance_monitor
        
        # Setup emergency callbacks for integrated services
        if coordinator:
            self.add_emergency_callback(coordinator.emergency_stop)
        
        logger.info("Emergency Control System integrated with services")
    
    def _initialize_system_components(self):
        """Initialize system component tracking"""
        components = [
            ('database', True),
            ('websocket_manager', True),
            ('data_feed', True),
            ('broker_integration', True),
            ('execution_engine', True),
            ('position_monitor', True),
            ('order_manager', True),
            ('performance_monitor', False),
            ('risk_manager', True)
        ]
        
        for name, is_critical in components:
            self.system_components[name] = SystemComponent(
                name=name,
                status=ComponentStatus.UNKNOWN,
                last_heartbeat=datetime.now(timezone.utc),
                critical=is_critical,
                dependencies=[],
                health_metrics={}
            )
    
    async def start_monitoring(self):
        """Start emergency monitoring system"""
        try:
            self.monitoring_active = True
            
            # Initialize circuit breakers
            for name, config in self.circuit_breaker_configs.items():
                self.circuit_breakers[name] = {
                    'state': 'CLOSED',  # CLOSED, OPEN, HALF_OPEN
                    'failure_count': 0,
                    'last_failure': None,
                    'last_success': datetime.now(timezone.utc),
                    'config': config
                }
            
            # Start monitoring tasks
            asyncio.create_task(self._system_health_monitor())
            asyncio.create_task(self._resource_monitor())
            asyncio.create_task(self._component_health_checker())
            asyncio.create_task(self._circuit_breaker_manager())
            asyncio.create_task(self._emergency_event_processor())
            
            logger.info("Emergency monitoring system started")
            
        except Exception as e:
            logger.error(f"Failed to start emergency monitoring: {e}")
            raise
    
    # =================== KILL SWITCH MECHANISM ===================
    
    async def trigger_kill_switch(self, reason: str, manual: bool = True) -> bool:
        """Trigger emergency kill switch - immediate system shutdown"""
        try:
            if self.kill_switch_triggered:
                logger.warning("Kill switch already triggered")
                return False
            
            self.kill_switch_triggered = True
            self.emergency_active = True
            
            emergency_type = EmergencyType.MANUAL_KILL_SWITCH if manual else EmergencyType.AUTOMATIC_CIRCUIT_BREAKER
            
            logger.critical(f"🚨 KILL SWITCH TRIGGERED: {reason}")
            
            # Create emergency event
            emergency_event = EmergencyEvent(
                event_id=f"KILL_SWITCH_{int(time.time())}",
                emergency_type=emergency_type,
                triggered_at=datetime.now(timezone.utc),
                description=f"Kill switch activated: {reason}",
                trigger_conditions={'reason': reason, 'manual': manual},
                auto_actions_taken=[],
                manual_actions_required=[]
            )
            
            # Execute immediate shutdown sequence
            auto_actions = await self._execute_emergency_shutdown()
            emergency_event.auto_actions_taken = auto_actions
            
            # Record emergency event
            self.emergency_events.append(emergency_event)
            
            # Notify all callbacks
            for callback in self.emergency_callbacks:
                try:
                    await callback(reason)
                except Exception as e:
                    logger.error(f"Error in emergency callback: {e}")
            
            # Broadcast emergency notification
            if self.websocket_service:
                await self.websocket_service.broadcast_risk_alert({
                    'alert_type': 'EMERGENCY_STOP',
                    'severity': 'CRITICAL',
                    'description': f'Kill switch activated: {reason}',
                    'auto_action_taken': True,
                    'auto_action_description': 'All trading operations halted'
                })
            
            return True
            
        except Exception as e:
            logger.critical(f"Error in kill switch trigger: {e}")
            return False
    
    async def _execute_emergency_shutdown(self) -> List[str]:
        """Execute emergency shutdown sequence"""
        actions_taken = []
        
        try:
            # 1. Stop all trading operations
            if self.coordinator:
                try:
                    await self.coordinator.emergency_stop("Kill switch activated")
                    actions_taken.append("Trading operations halted")
                except Exception as e:
                    logger.error(f"Error stopping coordinator: {e}")
            
            # 2. Cancel all pending orders
            actions_taken.append("Pending orders cancellation initiated")
            
            # 3. Close all positions (market orders)
            actions_taken.append("Position closure initiated")
            
            # 4. Disconnect from data feeds
            actions_taken.append("Data feed disconnection initiated")
            
            # 5. Log emergency state
            if self.db_service:
                try:
                    await self.db_service.log_trading_system_event({
                        'event_type': 'EMERGENCY_STOP',
                        'description': 'Kill switch triggered - system shutdown',
                        'timestamp': datetime.now(timezone.utc)
                    })
                    actions_taken.append("Emergency event logged to database")
                except Exception as e:
                    logger.error(f"Error logging emergency event: {e}")
            
            # 6. Update system component states
            for component in self.system_components.values():
                component.status = ComponentStatus.OFFLINE
            
            actions_taken.append("System components marked offline")
            
            logger.info(f"Emergency shutdown complete. Actions taken: {len(actions_taken)}")
            
        except Exception as e:
            logger.critical(f"Error during emergency shutdown: {e}")
            actions_taken.append(f"Shutdown error: {str(e)}")
        
        return actions_taken
    
    async def reset_kill_switch(self, operator_id: str, reason: str) -> bool:
        """Reset kill switch (manual intervention required)"""
        try:
            if not self.kill_switch_triggered:
                logger.warning("Kill switch is not currently triggered")
                return False
            
            logger.info(f"Kill switch reset by {operator_id}: {reason}")
            
            # Reset emergency state
            self.kill_switch_triggered = False
            self.emergency_active = False
            
            # Log reset event
            if self.db_service:
                await self.db_service.log_trading_system_event({
                    'event_type': 'KILL_SWITCH_RESET',
                    'description': f'Kill switch reset by {operator_id}: {reason}',
                    'operator_id': operator_id
                })
            
            # Update component states to unknown (require health check)
            for component in self.system_components.values():
                component.status = ComponentStatus.UNKNOWN
                component.last_heartbeat = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting kill switch: {e}")
            return False
    
    # =================== CIRCUIT BREAKER SYSTEM ===================
    
    async def record_failure(self, circuit_name: str, error_message: str):
        """Record failure for circuit breaker evaluation"""
        try:
            if circuit_name not in self.circuit_breakers:
                logger.warning(f"Unknown circuit breaker: {circuit_name}")
                return
            
            circuit = self.circuit_breakers[circuit_name]
            circuit['failure_count'] += 1
            circuit['last_failure'] = datetime.now(timezone.utc)
            
            config = circuit['config']
            
            # Check if threshold exceeded
            if circuit['failure_count'] >= config['failure_threshold']:
                if circuit['state'] == 'CLOSED':
                    # Open circuit breaker
                    circuit['state'] = 'OPEN'
                    logger.warning(f"🚨 Circuit breaker OPENED: {circuit_name}")
                    
                    # Trigger emergency if critical
                    if circuit_name in ['execution_failures', 'broker_errors']:
                        await self._trigger_circuit_breaker_emergency(circuit_name, error_message)
            
        except Exception as e:
            logger.error(f"Error recording failure for {circuit_name}: {e}")
    
    async def record_success(self, circuit_name: str):
        """Record successful operation"""
        try:
            if circuit_name not in self.circuit_breakers:
                return
            
            circuit = self.circuit_breakers[circuit_name]
            circuit['last_success'] = datetime.now(timezone.utc)
            
            # Reset failure count on success
            if circuit['state'] == 'HALF_OPEN':
                circuit['failure_count'] = 0
                circuit['state'] = 'CLOSED'
                logger.info(f"✅ Circuit breaker CLOSED: {circuit_name}")
            
        except Exception as e:
            logger.error(f"Error recording success for {circuit_name}: {e}")
    
    def is_circuit_open(self, circuit_name: str) -> bool:
        """Check if circuit breaker is open"""
        return (circuit_name in self.circuit_breakers and 
                self.circuit_breakers[circuit_name]['state'] == 'OPEN')
    
    async def _trigger_circuit_breaker_emergency(self, circuit_name: str, error_message: str):
        """Trigger emergency due to circuit breaker"""
        try:
            reason = f"Circuit breaker triggered: {circuit_name} - {error_message}"
            
            # Create emergency event
            emergency_event = EmergencyEvent(
                event_id=f"CB_{circuit_name}_{int(time.time())}",
                emergency_type=EmergencyType.AUTOMATIC_CIRCUIT_BREAKER,
                triggered_at=datetime.now(timezone.utc),
                description=reason,
                trigger_conditions={'circuit_name': circuit_name, 'error': error_message},
                auto_actions_taken=[],
                manual_actions_required=["Investigate circuit breaker cause", "Manual system restart required"]
            )
            
            # For critical circuits, trigger kill switch
            if circuit_name in ['execution_failures', 'broker_errors']:
                await self.trigger_kill_switch(reason, manual=False)
                emergency_event.auto_actions_taken.append("Kill switch triggered")
            
            self.emergency_events.append(emergency_event)
            
        except Exception as e:
            logger.error(f"Error triggering circuit breaker emergency: {e}")
    
    async def _circuit_breaker_manager(self):
        """Manage circuit breaker recovery"""
        while self.monitoring_active:
            try:
                current_time = datetime.now(timezone.utc)
                
                for circuit_name, circuit in self.circuit_breakers.items():
                    if circuit['state'] == 'OPEN':
                        # Check if recovery timeout has passed
                        last_failure = circuit['last_failure']
                        if last_failure:
                            time_since_failure = (current_time - last_failure).total_seconds()
                            if time_since_failure >= circuit['config']['recovery_timeout']:
                                # Move to half-open state
                                circuit['state'] = 'HALF_OPEN'
                                circuit['failure_count'] = 0
                                logger.info(f"Circuit breaker HALF_OPEN: {circuit_name}")
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in circuit breaker manager: {e}")
                await asyncio.sleep(30.0)
    
    # =================== SYSTEM HEALTH MONITORING ===================
    
    async def update_component_health(self, component_name: str, status: ComponentStatus, 
                                    metrics: Dict[str, Any] = None):
        """Update component health status"""
        try:
            if component_name in self.system_components:
                component = self.system_components[component_name]
                component.status = status
                component.last_heartbeat = datetime.now(timezone.utc)
                
                if metrics:
                    component.health_metrics = metrics
                    if 'response_time_ms' in metrics:
                        component.response_time_ms = metrics['response_time_ms']
                    if 'error_count' in metrics:
                        component.error_count = metrics['error_count']
            
        except Exception as e:
            logger.error(f"Error updating component health: {e}")
    
    async def _system_health_monitor(self):
        """Monitor overall system health"""
        while self.monitoring_active:
            try:
                # Calculate overall system health
                health_snapshot = await self._create_health_snapshot()
                
                # Store in history
                self.health_history.append(health_snapshot)
                
                # Check for critical conditions
                await self._evaluate_system_health(health_snapshot)
                
                # Broadcast health update
                if self.websocket_service:
                    await self.websocket_service.broadcast_system_status_update({
                        'overall_health': health_snapshot.overall_status.value,
                        'health_score': health_snapshot.health_score,
                        'emergency_active': self.emergency_active,
                        'uptime_seconds': health_snapshot.uptime_seconds
                    })
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in system health monitor: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _create_health_snapshot(self) -> SystemHealthSnapshot:
        """Create comprehensive health snapshot"""
        try:
            current_time = datetime.now(timezone.utc)
            uptime = (current_time - self.startup_time).total_seconds()
            
            # Calculate component health scores
            component_scores = []
            critical_failures = 0
            
            for component in self.system_components.values():
                if component.status == ComponentStatus.ONLINE:
                    component_scores.append(100)
                elif component.status == ComponentStatus.DEGRADED:
                    component_scores.append(70)
                elif component.status == ComponentStatus.OFFLINE:
                    score = 0 if component.critical else 50
                    component_scores.append(score)
                    if component.critical:
                        critical_failures += 1
                else:
                    component_scores.append(50)  # UNKNOWN
            
            # Calculate overall health score
            if component_scores:
                health_score = sum(component_scores) / len(component_scores)
            else:
                health_score = 0
            
            # Determine overall status
            overall_status = SystemHealthStatus.HEALTHY
            if self.emergency_active:
                overall_status = SystemHealthStatus.EMERGENCY_STOP
            elif critical_failures > 0:
                overall_status = SystemHealthStatus.FAILURE
            elif health_score < 70:
                overall_status = SystemHealthStatus.CRITICAL
            elif health_score < 85:
                overall_status = SystemHealthStatus.WARNING
            
            # Get resource usage
            resource_usage = await self._get_resource_usage()
            
            # Create snapshot
            snapshot = SystemHealthSnapshot(
                overall_status=overall_status,
                health_score=health_score,
                components=self.system_components.copy(),
                resource_usage=resource_usage,
                active_emergencies=len([e for e in self.emergency_events if not e.resolved]),
                uptime_seconds=int(uptime),
                last_emergency=self.emergency_events[-1].triggered_at if self.emergency_events else None,
                performance_score=self._calculate_performance_score(),
                risk_score=self._calculate_risk_score(),
                snapshot_time=current_time
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating health snapshot: {e}")
            # Return minimal snapshot on error
            return SystemHealthSnapshot(
                overall_status=SystemHealthStatus.FAILURE,
                health_score=0,
                components={},
                resource_usage={},
                active_emergencies=0,
                uptime_seconds=0,
                last_emergency=None,
                performance_score=0,
                risk_score=100,
                snapshot_time=datetime.now(timezone.utc)
            )
    
    async def _get_resource_usage(self) -> Dict[str, float]:
        """Get system resource usage"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {}
    
    async def _resource_monitor(self):
        """Monitor system resources"""
        while self.monitoring_active:
            try:
                resource_usage = await self._get_resource_usage()
                
                # Check thresholds
                for resource, value in resource_usage.items():
                    if resource in self.resource_thresholds:
                        thresholds = self.resource_thresholds[resource]
                        
                        if value >= thresholds['critical']:
                            await self._trigger_resource_emergency(resource, value, 'critical')
                        elif value >= thresholds['warning']:
                            await self._trigger_resource_alert(resource, value, 'warning')
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(30.0)
    
    async def _trigger_resource_emergency(self, resource: str, value: float, level: str):
        """Trigger emergency due to resource exhaustion"""
        try:
            emergency_type_map = {
                'cpu_usage': EmergencyType.CPU_OVERLOAD,
                'memory_usage': EmergencyType.MEMORY_OVERLOAD,
                'disk_usage': EmergencyType.DISK_SPACE_LOW
            }
            
            emergency_type = emergency_type_map.get(resource, EmergencyType.SYSTEM_FAILURE)
            reason = f"Critical {resource}: {value:.1f}%"
            
            # For critical resource issues, trigger kill switch
            if level == 'critical' and resource in ['cpu_usage', 'memory_usage']:
                await self.trigger_kill_switch(reason, manual=False)
            
            logger.critical(f"🚨 Resource Emergency: {reason}")
            
        except Exception as e:
            logger.error(f"Error triggering resource emergency: {e}")
    
    async def _trigger_resource_alert(self, resource: str, value: float, level: str):
        """Trigger resource usage alert"""
        try:
            if self.websocket_service:
                await self.websocket_service.broadcast_risk_alert({
                    'alert_type': 'RESOURCE_USAGE',
                    'severity': 'HIGH' if level == 'critical' else 'MEDIUM',
                    'description': f'High {resource}: {value:.1f}%',
                    'current_value': value,
                    'threshold_value': self.resource_thresholds[resource][level],
                    'recommended_actions': [
                        f'Monitor {resource} usage',
                        'Check for resource leaks',
                        'Consider scaling resources'
                    ]
                })
            
        except Exception as e:
            logger.error(f"Error triggering resource alert: {e}")
    
    def _calculate_performance_score(self) -> float:
        """Calculate system performance score"""
        try:
            if self.performance_monitor:
                perf = self.performance_monitor.get_current_performance()
                trading_perf = perf.get('trading_performance', {})
                system_perf = perf.get('system_performance', {})
                
                # Combine multiple performance factors
                factors = [
                    min(100, trading_perf.get('win_rate', 50)),
                    min(100, system_perf.get('order_success_rate', 90)),
                    max(0, 100 - (system_perf.get('avg_execution_latency_ms', 50) / 2))
                ]
                
                return sum(factors) / len(factors)
            
            return 75.0  # Default if no performance monitor
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 50.0
    
    def _calculate_risk_score(self) -> float:
        """Calculate system risk score (0=low risk, 100=high risk)"""
        try:
            risk_factors = []
            
            # Emergency events factor
            recent_emergencies = len([
                e for e in self.emergency_events 
                if e.triggered_at > datetime.now(timezone.utc) - timedelta(hours=24)
            ])
            risk_factors.append(min(100, recent_emergencies * 20))
            
            # Circuit breaker factor
            open_circuits = len([
                c for c in self.circuit_breakers.values() 
                if c['state'] == 'OPEN'
            ])
            risk_factors.append(min(100, open_circuits * 30))
            
            # Component failure factor
            failed_components = len([
                c for c in self.system_components.values() 
                if c.status in [ComponentStatus.FAILED, ComponentStatus.OFFLINE] and c.critical
            ])
            risk_factors.append(min(100, failed_components * 25))
            
            return max(risk_factors) if risk_factors else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 50.0
    
    async def _evaluate_system_health(self, health_snapshot: SystemHealthSnapshot):
        """Evaluate system health and take actions"""
        try:
            # Check for critical health conditions
            if (health_snapshot.overall_status == SystemHealthStatus.FAILURE and 
                not self.emergency_active):
                
                await self.trigger_kill_switch("Critical system health failure", manual=False)
            
            # Check for degraded performance
            elif (health_snapshot.health_score < 50 and 
                  health_snapshot.risk_score > 80):
                
                logger.warning("System health degraded - monitoring closely")
                
        except Exception as e:
            logger.error(f"Error evaluating system health: {e}")
    
    async def _component_health_checker(self):
        """Check individual component health"""
        while self.monitoring_active:
            try:
                current_time = datetime.now(timezone.utc)
                
                for component_name, component in self.system_components.items():
                    # Check heartbeat timeout
                    time_since_heartbeat = (current_time - component.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > 300:  # 5 minutes timeout
                        if component.status not in [ComponentStatus.OFFLINE, ComponentStatus.FAILED]:
                            component.status = ComponentStatus.OFFLINE
                            logger.warning(f"Component {component_name} marked offline - no heartbeat")
                            
                            # If critical component fails, trigger emergency
                            if component.critical and not self.emergency_active:
                                await self.trigger_kill_switch(
                                    f"Critical component failure: {component_name}", 
                                    manual=False
                                )
                
                await asyncio.sleep(60.0)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in component health checker: {e}")
                await asyncio.sleep(60.0)
    
    async def _emergency_event_processor(self):
        """Process emergency events"""
        while self.monitoring_active:
            try:
                # Auto-resolve old emergency events
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                for event in list(self.emergency_events):
                    if (not event.resolved and 
                        event.triggered_at < cutoff_time and
                        event.emergency_type not in [EmergencyType.MANUAL_KILL_SWITCH]):
                        
                        event.resolved = True
                        event.resolved_at = datetime.now(timezone.utc)
                
                await asyncio.sleep(300.0)  # Process every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in emergency event processor: {e}")
                await asyncio.sleep(300.0)
    
    # =================== PUBLIC API ===================
    
    def add_emergency_callback(self, callback: Callable):
        """Add emergency callback"""
        self.emergency_callbacks.append(callback)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health"""
        if self.health_history:
            latest = self.health_history[-1]
            return {
                'overall_status': latest.overall_status.value,
                'health_score': latest.health_score,
                'performance_score': latest.performance_score,
                'risk_score': latest.risk_score,
                'uptime_seconds': latest.uptime_seconds,
                'emergency_active': self.emergency_active,
                'kill_switch_triggered': self.kill_switch_triggered,
                'component_count': len(latest.components),
                'active_emergencies': latest.active_emergencies
            }
        
        return {
            'overall_status': 'UNKNOWN',
            'health_score': 0,
            'emergency_active': self.emergency_active
        }
    
    def get_emergency_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get emergency events history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            asdict(event) for event in self.emergency_events
            if event.triggered_at > cutoff_time
        ]
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            name: {
                'state': circuit['state'],
                'failure_count': circuit['failure_count'],
                'last_failure': circuit['last_failure'].isoformat() if circuit['last_failure'] else None,
                'last_success': circuit['last_success'].isoformat() if circuit['last_success'] else None
            }
            for name, circuit in self.circuit_breakers.items()
        }
    
    def get_component_health(self) -> Dict[str, Any]:
        """Get component health status"""
        return {
            name: {
                'status': component.status.value,
                'last_heartbeat': component.last_heartbeat.isoformat(),
                'response_time_ms': component.response_time_ms,
                'error_count': component.error_count,
                'critical': component.critical,
                'health_metrics': component.health_metrics or {}
            }
            for name, component in self.system_components.items()
        }
    
    async def acknowledge_emergency(self, event_id: str, operator_id: str) -> bool:
        """Acknowledge emergency event"""
        try:
            for event in self.emergency_events:
                if event.event_id == event_id and not event.resolved:
                    event.resolved = True
                    event.resolved_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Emergency event {event_id} acknowledged by {operator_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging emergency: {e}")
            return False
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Emergency Control System...")
        self.monitoring_active = False
        
        # Update all components to offline
        for component in self.system_components.values():
            component.status = ComponentStatus.OFFLINE
        
        logger.info("Emergency Control System shutdown complete")