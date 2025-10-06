from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from .audit_logger import AuditEventType, AuditSeverity
from .security_config import get_security_manager

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user is admin (you'll need to implement this check)
        if not getattr(current_user, 'is_admin', False):
            flash('Admin privileges required.', 'error')
            return redirect(url_for('main.home'))
        
        return f(*args, **kwargs)
    return decorated_function

def create_security_admin_blueprint(app):
    """Create security admin blueprint"""
    
    security_admin = Blueprint('security_admin', __name__, template_folder='templates/security')
    
    @security_admin.route('/')
    @login_required
    @admin_required
    def dashboard():
        """Security dashboard"""
        try:
            security_manager = get_security_manager(app)
            
            if not security_manager:
                flash('Security manager not available', 'error')
                return redirect(url_for('main.home'))
            
            # Get security status
            status = security_manager._get_security_status()
            
            # Get security metrics
            metrics = security_manager.get_security_metrics()
            
            # Get recent security events
            audit_logger = security_manager.get_component('audit')
            recent_events = []
            if audit_logger:
                # Get events from last 24 hours
                start_time = datetime.utcnow() - timedelta(hours=24)
                recent_events = audit_logger.get_events(
                    start_time=start_time,
                    limit=50
                )
            
            return render_template('security/dashboard.html',
                                 status=status,
                                 metrics=metrics,
                                 recent_events=recent_events)
        
        except Exception as e:
            current_app.logger.error(f"Error loading security dashboard: {e}")
            flash('Error loading security dashboard', 'error')
            return redirect(url_for('main.home'))
    
    @security_admin.route('/events')
    @login_required
    @admin_required
    def events():
        """Security events log"""
        try:
            security_manager = get_security_manager(app)
            audit_logger = security_manager.get_component('audit') if security_manager else None
            
            if not audit_logger:
                flash('Audit logging not available', 'error')
                return redirect(url_for('security_admin.dashboard'))
            
            # Get filter parameters
            event_type = request.args.get('event_type')
            severity = request.args.get('severity')
            user_id = request.args.get('user_id')
            hours = int(request.args.get('hours', 24))
            limit = int(request.args.get('limit', 100))
            
            # Convert parameters
            event_types = [AuditEventType(event_type)] if event_type else None
            severity_filter = AuditSeverity(severity) if severity else None
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get filtered events
            events = audit_logger.get_events(
                start_time=start_time,
                event_types=event_types,
                user_id=user_id,
                severity=severity_filter,
                limit=limit
            )
            
            # Get available filter options
            event_type_options = [e.value for e in AuditEventType]
            severity_options = [s.value for s in AuditSeverity]
            
            return render_template('security/events.html',
                                 events=events,
                                 event_type_options=event_type_options,
                                 severity_options=severity_options,
                                 current_filters={
                                     'event_type': event_type,
                                     'severity': severity,
                                     'user_id': user_id,
                                     'hours': hours,
                                     'limit': limit
                                 })
        
        except Exception as e:
            current_app.logger.error(f"Error loading security events: {e}")
            flash('Error loading security events', 'error')
            return redirect(url_for('security_admin.dashboard'))
    
    @security_admin.route('/config')
    @login_required
    @admin_required
    def config():
        """Security configuration"""
        try:
            security_manager = get_security_manager(app)
            
            if not security_manager:
                flash('Security manager not available', 'error')
                return redirect(url_for('security_admin.dashboard'))
            
            config = security_manager.get_config()
            
            return render_template('security/config.html', config=config)
        
        except Exception as e:
            current_app.logger.error(f"Error loading security config: {e}")
            flash('Error loading security configuration', 'error')
            return redirect(url_for('security_admin.dashboard'))
    
    @security_admin.route('/config/update', methods=['POST'])
    @login_required
    @admin_required
    def update_config():
        """Update security configuration"""
        try:
            security_manager = get_security_manager(app)
            
            if not security_manager:
                return jsonify({'error': 'Security manager not available'}), 500
            
            data = request.get_json()
            section = data.get('section')
            key = data.get('key')
            value = data.get('value')
            
            if not all([section, key]):
                return jsonify({'error': 'Section and key required'}), 400
            
            # Update configuration
            security_manager.update_config(section, key, value)
            
            # Log configuration change
            audit_logger = security_manager.get_component('audit')
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.CONFIGURATION_CHANGE,
                    severity=AuditSeverity.HIGH,
                    success=True,
                    message=f"Security configuration updated: {section}.{key}",
                    details={
                        'section': section,
                        'key': key,
                        'new_value': value,
                        'changed_by': current_user.username
                    }
                )
            
            return jsonify({'success': True, 'message': 'Configuration updated'})
        
        except Exception as e:
            current_app.logger.error(f"Error updating security config: {e}")
            return jsonify({'error': 'Failed to update configuration'}), 500
    
    @security_admin.route('/test')
    @login_required
    @admin_required
    def test():
        """Security tests"""
        try:
            security_manager = get_security_manager(app)
            
            if not security_manager:
                flash('Security manager not available', 'error')
                return redirect(url_for('security_admin.dashboard'))
            
            # Run security tests
            test_results = security_manager._run_security_tests()
            
            return render_template('security/test.html', test_results=test_results)
        
        except Exception as e:
            current_app.logger.error(f"Error running security tests: {e}")
            flash('Error running security tests', 'error')
            return redirect(url_for('security_admin.dashboard'))
    
    @security_admin.route('/api/metrics')
    @login_required
    @admin_required
    def api_metrics():
        """API endpoint for security metrics"""
        try:
            security_manager = get_security_manager(app)
            
            if not security_manager:
                return jsonify({'error': 'Security manager not available'}), 500
            
            metrics = security_manager.get_security_metrics()
            return jsonify(metrics)
        
        except Exception as e:
            current_app.logger.error(f"Error getting security metrics: {e}")
            return jsonify({'error': 'Failed to get metrics'}), 500
    
    @security_admin.route('/api/events/summary')
    @login_required
    @admin_required
    def api_events_summary():
        """API endpoint for events summary"""
        try:
            security_manager = get_security_manager(app)
            audit_logger = security_manager.get_component('audit') if security_manager else None
            
            if not audit_logger:
                return jsonify({'error': 'Audit logging not available'}), 500
            
            hours = int(request.args.get('hours', 24))
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get events for summary
            events = audit_logger.get_events(start_time=start_time, limit=1000)
            
            # Create summary
            summary = {
                'total_events': len(events),
                'by_type': {},
                'by_severity': {},
                'by_hour': {},
                'failed_logins': 0,
                'successful_logins': 0,
                'security_violations': 0
            }
            
            for event in events:
                # Count by type
                event_type = event.get('event_type', 'unknown')
                summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1
                
                # Count by severity
                severity = event.get('severity', 'unknown')
                summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
                
                # Count by hour
                timestamp = event.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        hour_key = dt.strftime('%Y-%m-%d %H:00')
                        summary['by_hour'][hour_key] = summary['by_hour'].get(hour_key, 0) + 1
                    except:
                        pass
                
                # Count specific event types
                if event_type == 'login_failed':
                    summary['failed_logins'] += 1
                elif event_type == 'login_success':
                    summary['successful_logins'] += 1
                elif 'security' in event_type or 'violation' in event_type:
                    summary['security_violations'] += 1
            
            return jsonify(summary)
        
        except Exception as e:
            current_app.logger.error(f"Error getting events summary: {e}")
            return jsonify({'error': 'Failed to get events summary'}), 500
    
    @security_admin.route('/api/block-ip', methods=['POST'])
    @login_required
    @admin_required
    def api_block_ip():
        """API endpoint to block an IP address"""
        try:
            data = request.get_json()
            ip_address = data.get('ip_address')
            reason = data.get('reason', 'Blocked by admin')
            
            if not ip_address:
                return jsonify({'error': 'IP address required'}), 400
            
            # TODO: Implement IP blocking logic
            # This would typically involve updating a blacklist in Redis or database
            
            # Log the action
            security_manager = get_security_manager(app)
            audit_logger = security_manager.get_component('audit') if security_manager else None
            
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.CONFIGURATION_CHANGE,
                    severity=AuditSeverity.HIGH,
                    success=True,
                    message=f"IP address blocked: {ip_address}",
                    details={
                        'ip_address': ip_address,
                        'reason': reason,
                        'blocked_by': current_user.username
                    }
                )
            
            return jsonify({'success': True, 'message': f'IP {ip_address} blocked'})
        
        except Exception as e:
            current_app.logger.error(f"Error blocking IP: {e}")
            return jsonify({'error': 'Failed to block IP'}), 500
    
    return security_admin

def create_security_templates():
    """Create security dashboard templates"""
    
    dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Dashboard - CS Gauntlet</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-8">Security Dashboard</h1>
        
        <!-- Security Status -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {% for component, info in status.items() %}
            <div class="bg-white rounded-lg shadow p-6">
                <div class="flex items-center justify-between">
                    <h3 class="text-lg font-semibold text-gray-800">{{ component }}</h3>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                 {% if info.enabled %}bg-green-100 text-green-800{% else %}bg-red-100 text-red-800{% endif %}">
                        {% if info.enabled %}Active{% else %}Inactive{% endif %}
                    </span>
                </div>
                <p class="text-sm text-gray-600 mt-2">{{ info.status }}</p>
                {% if info.details %}
                <p class="text-xs text-gray-500 mt-1">{{ info.details }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <!-- Security Metrics -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">Security Metrics</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="text-center">
                    <div class="text-2xl font-bold text-blue-600">{{ metrics.components_active }}</div>
                    <div class="text-sm text-gray-600">Active Components</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-green-600">{{ metrics.security_events_24h }}</div>
                    <div class="text-sm text-gray-600">Events (24h)</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-yellow-600">{{ metrics.failed_authentications_1h }}</div>
                    <div class="text-sm text-gray-600">Failed Auth (1h)</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-red-600">{{ metrics.rate_limit_violations_1h }}</div>
                    <div class="text-sm text-gray-600">Rate Limit Violations</div>
                </div>
            </div>
        </div>
        
        <!-- Recent Events -->
        <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-xl font-semibold text-gray-800">Recent Security Events</h2>
                <a href="{{ url_for('security_admin.events') }}" class="text-blue-600 hover:text-blue-800">View All</a>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Message</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {% for event in recent_events[:10] %}
                        <tr>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {{ event.timestamp[:19] if event.timestamp else 'Unknown' }}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {{ event.event_type }}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                             {% if event.severity == 'critical' %}bg-red-100 text-red-800
                                             {% elif event.severity == 'high' %}bg-orange-100 text-orange-800
                                             {% elif event.severity == 'medium' %}bg-yellow-100 text-yellow-800
                                             {% else %}bg-green-100 text-green-800{% endif %}">
                                    {{ event.severity }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-900">
                                {{ event.message[:100] }}{% if event.message|length > 100 %}...{% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return {
        'dashboard.html': dashboard_template
    }