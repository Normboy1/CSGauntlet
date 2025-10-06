from flask import Flask, jsonify, request, render_template_string
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum

from .audit_logger import AuditEventType, AuditSeverity
from .security_config import get_security_manager

class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityAlert:
    """Security alert structure"""
    id: str
    threat_level: ThreatLevel
    title: str
    description: str
    timestamp: datetime
    source: str
    details: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

class SecurityMonitor:
    """Real-time security monitoring and alerting"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.alerts = deque(maxlen=1000)  # Keep last 1000 alerts
        self.metrics = defaultdict(int)
        self.real_time_events = deque(maxlen=100)  # Last 100 events for real-time display
        self.threat_patterns = {}
        self.monitoring_active = False
        self.monitor_thread = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security monitor with Flask app"""
        self.app = app
        self._setup_monitoring()
        self._start_background_monitoring()
    
    def _setup_monitoring(self):
        """Setup monitoring patterns and thresholds"""
        
        self.threat_patterns = {
            'failed_login_burst': {
                'events': ['login_failed'],
                'threshold': 5,
                'window': 300,  # 5 minutes
                'threat_level': ThreatLevel.HIGH,
                'description': 'Multiple failed login attempts detected'
            },
            'suspicious_code_execution': {
                'events': ['dangerous_code_detected', 'code_execution_blocked'],
                'threshold': 3,
                'window': 600,  # 10 minutes
                'threat_level': ThreatLevel.HIGH,
                'description': 'Suspicious code execution patterns'
            },
            'rate_limit_abuse': {
                'events': ['rate_limit_exceeded'],
                'threshold': 10,
                'window': 300,  # 5 minutes
                'threat_level': ThreatLevel.MEDIUM,
                'description': 'Excessive rate limit violations'
            },
            'file_upload_attacks': {
                'events': ['file_upload_security_failed', 'malicious_file_detected'],
                'threshold': 3,
                'window': 900,  # 15 minutes
                'threat_level': ThreatLevel.HIGH,
                'description': 'Potential file upload attack'
            },
            'cors_violations': {
                'events': ['suspicious_cors_origin', 'unauthorized_origin_blocked'],
                'threshold': 5,
                'window': 600,  # 10 minutes
                'threat_level': ThreatLevel.MEDIUM,
                'description': 'CORS policy violations'
            },
            'privilege_escalation': {
                'events': ['privilege_escalation', 'unauthorized_admin_access'],
                'threshold': 1,
                'window': 60,  # 1 minute
                'threat_level': ThreatLevel.CRITICAL,
                'description': 'Privilege escalation attempt'
            }
        }
    
    def _start_background_monitoring(self):
        """Start background monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._check_threat_patterns()
                self._update_metrics()
                self._cleanup_old_data()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                if self.app:
                    self.app.logger.error(f"Security monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def process_event(self, event_data: Dict[str, Any]):
        """Process a security event for monitoring"""
        
        # Add to real-time events
        self.real_time_events.append({
            **event_data,
            'processed_at': datetime.utcnow().isoformat()
        })
        
        # Update metrics
        event_type = event_data.get('event_type', 'unknown')
        self.metrics[f"events_{event_type}"] += 1
        self.metrics['total_events'] += 1
        
        severity = event_data.get('severity', 'low')
        self.metrics[f"severity_{severity}"] += 1
        
        # Check for immediate threats
        self._check_immediate_threats(event_data)
    
    def _check_immediate_threats(self, event_data: Dict[str, Any]):
        """Check for immediate security threats"""
        
        event_type = event_data.get('event_type')
        severity = event_data.get('severity')
        
        # Critical events trigger immediate alerts
        if severity == 'critical':
            self._create_alert(
                threat_level=ThreatLevel.CRITICAL,
                title=f"Critical Security Event: {event_type}",
                description=event_data.get('message', 'Critical security event detected'),
                source='immediate_threat_detection',
                details=event_data
            )
        
        # Specific event type checks
        if event_type in ['privilege_escalation', 'unauthorized_admin_access']:
            self._create_alert(
                threat_level=ThreatLevel.CRITICAL,
                title="Privilege Escalation Detected",
                description=f"Unauthorized privilege escalation attempt: {event_data.get('message', '')}",
                source='privilege_monitor',
                details=event_data
            )
        
        elif event_type == 'dangerous_code_detected':
            self._create_alert(
                threat_level=ThreatLevel.HIGH,
                title="Dangerous Code Detected",
                description=f"Malicious code pattern detected: {event_data.get('message', '')}",
                source='code_monitor',
                details=event_data
            )
    
    def _check_threat_patterns(self):
        """Check for threat patterns based on event history"""
        
        security_manager = get_security_manager(self.app)
        if not security_manager:
            return
        
        audit_logger = security_manager.get_component('audit')
        if not audit_logger:
            return
        
        # Check each threat pattern
        for pattern_name, pattern_config in self.threat_patterns.items():
            try:
                self._check_pattern(pattern_name, pattern_config, audit_logger)
            except Exception as e:
                if self.app:
                    self.app.logger.error(f"Error checking pattern {pattern_name}: {e}")
    
    def _check_pattern(self, pattern_name: str, pattern_config: Dict, audit_logger):
        """Check a specific threat pattern"""
        
        window_start = datetime.utcnow() - timedelta(seconds=pattern_config['window'])
        
        # Get recent events
        recent_events = audit_logger.get_events(
            start_time=window_start,
            limit=1000
        )
        
        # Count matching events
        matching_events = []
        for event in recent_events:
            if event.get('event_type') in pattern_config['events']:
                matching_events.append(event)
        
        # Check threshold
        if len(matching_events) >= pattern_config['threshold']:
            # Check if we already alerted for this pattern recently
            if not self._has_recent_alert(pattern_name, window_start):
                self._create_alert(
                    threat_level=pattern_config['threat_level'],
                    title=f"Threat Pattern Detected: {pattern_name}",
                    description=pattern_config['description'],
                    source=f'pattern_{pattern_name}',
                    details={
                        'pattern': pattern_name,
                        'event_count': len(matching_events),
                        'threshold': pattern_config['threshold'],
                        'window_minutes': pattern_config['window'] // 60,
                        'matching_events': matching_events[:10]  # Include first 10 events
                    }
                )
    
    def _has_recent_alert(self, pattern_name: str, since: datetime) -> bool:
        """Check if we have a recent alert for this pattern"""
        for alert in self.alerts:
            if (alert.source == f'pattern_{pattern_name}' and 
                alert.timestamp > since and 
                not alert.resolved):
                return True
        return False
    
    def _create_alert(self, 
                     threat_level: ThreatLevel, 
                     title: str, 
                     description: str, 
                     source: str, 
                     details: Dict[str, Any]):
        """Create a new security alert"""
        
        alert = SecurityAlert(
            id=self._generate_alert_id(),
            threat_level=threat_level,
            title=title,
            description=description,
            timestamp=datetime.utcnow(),
            source=source,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        if self.app:
            self.app.logger.warning(f"Security Alert [{threat_level.value.upper()}]: {title}")
        
        # Send notifications for high/critical alerts
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: SecurityAlert):
        """Send alert notification (email, Slack, etc.)"""
        # TODO: Implement notification system
        # This could send emails, Slack messages, etc.
        pass
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _update_metrics(self):
        """Update monitoring metrics"""
        
        # Update timestamp
        self.metrics['last_update'] = time.time()
        
        # Calculate rates
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Count recent events
        recent_events = [
            event for event in self.real_time_events 
            if datetime.fromisoformat(event.get('processed_at', '1970-01-01')).timestamp() > hour_ago
        ]
        
        self.metrics['events_per_hour'] = len(recent_events)
        
        # Count active alerts
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        self.metrics['active_alerts'] = len(active_alerts)
        
        # Count by threat level
        for level in ThreatLevel:
            count = len([a for a in active_alerts if a.threat_level == level])
            self.metrics[f'alerts_{level.value}'] = count
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        
        # Remove old real-time events (keep last 100)
        while len(self.real_time_events) > 100:
            self.real_time_events.popleft()
        
        # Auto-resolve old alerts
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for alert in self.alerts:
            if alert.timestamp < cutoff and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = 'auto_cleanup'
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for security dashboard"""
        
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        recent_alerts = list(self.alerts)[-20:]  # Last 20 alerts
        
        return {
            'metrics': dict(self.metrics),
            'active_alerts': [asdict(alert) for alert in active_alerts],
            'recent_alerts': [asdict(alert) for alert in recent_alerts],
            'real_time_events': list(self.real_time_events)[-20:],  # Last 20 events
            'threat_patterns': self.threat_patterns,
            'monitoring_status': {
                'active': self.monitoring_active,
                'last_update': self.metrics.get('last_update', 0)
            }
        }
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve a security alert"""
        
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = resolved_by
                return True
        
        return False
    
    def get_alert(self, alert_id: str) -> Optional[SecurityAlert]:
        """Get a specific alert by ID"""
        
        for alert in self.alerts:
            if alert.id == alert_id:
                return alert
        
        return None
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

def create_monitoring_blueprint(app: Flask, security_monitor: SecurityMonitor):
    """Create blueprint for monitoring endpoints"""
    
    from flask import Blueprint
    
    monitor_bp = Blueprint('security_monitor', __name__)
    
    @monitor_bp.route('/api/dashboard')
    def dashboard_api():
        """API endpoint for dashboard data"""
        try:
            data = security_monitor.get_dashboard_data()
            return jsonify(data)
        except Exception as e:
            app.logger.error(f"Error getting dashboard data: {e}")
            return jsonify({'error': 'Failed to get dashboard data'}), 500
    
    @monitor_bp.route('/api/alerts/<alert_id>/resolve', methods=['POST'])
    def resolve_alert_api(alert_id: str):
        """API endpoint to resolve an alert"""
        try:
            data = request.get_json() or {}
            resolved_by = data.get('resolved_by', 'unknown')
            
            success = security_monitor.resolve_alert(alert_id, resolved_by)
            
            if success:
                return jsonify({'success': True, 'message': 'Alert resolved'})
            else:
                return jsonify({'error': 'Alert not found or already resolved'}), 404
        
        except Exception as e:
            app.logger.error(f"Error resolving alert: {e}")
            return jsonify({'error': 'Failed to resolve alert'}), 500
    
    @monitor_bp.route('/dashboard')
    def dashboard_view():
        """Dashboard view"""
        
        dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-8">Security Monitoring Dashboard</h1>
        
        <!-- Alert Summary -->
        <div id="alert-summary" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <!-- Populated by JavaScript -->
        </div>
        
        <!-- Active Alerts -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">Active Alerts</h2>
            <div id="active-alerts">
                <!-- Populated by JavaScript -->
            </div>
        </div>
        
        <!-- Real-time Events -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">Real-time Security Events</h2>
            <div id="real-time-events" class="space-y-2">
                <!-- Populated by JavaScript -->
            </div>
        </div>
        
        <!-- Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Event Types</h3>
                <canvas id="event-types-chart"></canvas>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">Threat Levels</h3>
                <canvas id="threat-levels-chart"></canvas>
            </div>
        </div>
    </div>

    <script>
        let dashboardData = {};
        
        async function loadDashboardData() {
            try {
                const response = await fetch('/admin/security/monitor/api/dashboard');
                dashboardData = await response.json();
                updateDashboard();
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }
        
        function updateDashboard() {
            updateAlertSummary();
            updateActiveAlerts();
            updateRealTimeEvents();
            updateCharts();
        }
        
        function updateAlertSummary() {
            const metrics = dashboardData.metrics || {};
            const summaryHtml = `
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-2xl font-bold text-red-600">${metrics.alerts_critical || 0}</div>
                    <div class="text-sm text-gray-600">Critical Alerts</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-2xl font-bold text-orange-600">${metrics.alerts_high || 0}</div>
                    <div class="text-sm text-gray-600">High Alerts</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-2xl font-bold text-yellow-600">${metrics.alerts_medium || 0}</div>
                    <div class="text-sm text-gray-600">Medium Alerts</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="text-2xl font-bold text-blue-600">${metrics.events_per_hour || 0}</div>
                    <div class="text-sm text-gray-600">Events/Hour</div>
                </div>
            `;
            document.getElementById('alert-summary').innerHTML = summaryHtml;
        }
        
        function updateActiveAlerts() {
            const alerts = dashboardData.active_alerts || [];
            if (alerts.length === 0) {
                document.getElementById('active-alerts').innerHTML = 
                    '<p class="text-gray-500">No active alerts</p>';
                return;
            }
            
            const alertsHtml = alerts.map(alert => `
                <div class="border-l-4 ${getThreatLevelColor(alert.threat_level)} bg-gray-50 p-4 mb-2">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="font-semibold text-gray-800">${alert.title}</h4>
                            <p class="text-gray-600 text-sm">${alert.description}</p>
                            <p class="text-gray-500 text-xs">${new Date(alert.timestamp).toLocaleString()}</p>
                        </div>
                        <button onclick="resolveAlert('${alert.id}')" 
                                class="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600">
                            Resolve
                        </button>
                    </div>
                </div>
            `).join('');
            document.getElementById('active-alerts').innerHTML = alertsHtml;
        }
        
        function updateRealTimeEvents() {
            const events = dashboardData.real_time_events || [];
            const eventsHtml = events.slice(-10).map(event => `
                <div class="flex justify-between items-center py-2 border-b border-gray-200">
                    <div>
                        <span class="font-medium">${event.event_type}</span>
                        <span class="text-gray-600 ml-2">${event.message || ''}</span>
                    </div>
                    <span class="text-sm text-gray-500">
                        ${new Date(event.processed_at).toLocaleTimeString()}
                    </span>
                </div>
            `).join('');
            document.getElementById('real-time-events').innerHTML = eventsHtml || 
                '<p class="text-gray-500">No recent events</p>';
        }
        
        function getThreatLevelColor(level) {
            const colors = {
                'critical': 'border-red-500',
                'high': 'border-orange-500', 
                'medium': 'border-yellow-500',
                'low': 'border-green-500'
            };
            return colors[level] || 'border-gray-500';
        }
        
        async function resolveAlert(alertId) {
            try {
                const response = await fetch(`/admin/security/monitor/api/alerts/${alertId}/resolve`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({resolved_by: 'admin'})
                });
                
                if (response.ok) {
                    loadDashboardData(); // Refresh dashboard
                } else {
                    alert('Failed to resolve alert');
                }
            } catch (error) {
                console.error('Error resolving alert:', error);
                alert('Error resolving alert');
            }
        }
        
        function updateCharts() {
            // Implementation for charts would go here
            // Using Chart.js to create event type and threat level charts
        }
        
        // Load initial data and set up refresh
        loadDashboardData();
        setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
        """
        
        return render_template_string(dashboard_template)
    
    return monitor_bp

def setup_security_monitoring(app: Flask) -> SecurityMonitor:
    """Setup security monitoring for the Flask app"""
    
    monitor = SecurityMonitor(app)
    
    # Create monitoring blueprint
    monitor_bp = create_monitoring_blueprint(app, monitor)
    app.register_blueprint(monitor_bp, url_prefix='/admin/security/monitor')
    
    # Store in app extensions
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['security_monitor'] = monitor
    
    return monitor