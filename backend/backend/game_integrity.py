"""
Game Integrity and Anti-Cheating System for CS Gauntlet
Comprehensive anti-cheating measures, code analysis, and game integrity monitoring
"""

import re
import ast
import hashlib
import time
import difflib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict
import statistics
import json

from flask import current_app, request, g
from sqlalchemy import text

from .models import User, Submission, Problem, db
from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity

class CodeAnalyzer:
    """Analyzes code submissions for cheating patterns and security issues"""
    
    def __init__(self):
        """Initialize code analyzer"""
        
        # Suspicious patterns that indicate cheating or malicious code
        self.suspicious_patterns = {
            'network_calls': [
                r'import\s+requests', r'import\s+urllib', r'import\s+socket',
                r'import\s+http', r'from\s+requests', r'from\s+urllib',
                r'requests\.', r'urllib\.', r'socket\.', r'http\.'
            ],
            'file_operations': [
                r'open\s*\(', r'file\s*\(', r'with\s+open',
                r'import\s+os', r'from\s+os', r'os\.',
                r'import\s+sys', r'sys\.', r'__import__'
            ],
            'subprocess_calls': [
                r'import\s+subprocess', r'from\s+subprocess',
                r'subprocess\.', r'os\.system', r'os\.popen',
                r'eval\s*\(', r'exec\s*\(', r'compile\s*\('
            ],
            'time_manipulation': [
                r'import\s+time', r'time\.sleep', r'time\.time',
                r'import\s+datetime', r'datetime\.', r'sleep\s*\('
            ],
            'obfuscation': [
                r'[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*["\'][^"\']{50,}["\']',  # Long string assignments
                r'chr\s*\(\s*\d+\s*\)', r'ord\s*\(',  # Character manipulation
                r'base64\.', r'binascii\.', r'codecs\.'  # Encoding operations
            ]
        }
        
        # Common cheating indicators
        self.cheating_indicators = {
            'copy_paste': [
                r'#.*copied', r'#.*stackoverflow', r'#.*github',
                r'//.*copied', r'//.*stackoverflow', r'//.*github',
                r'/\*.*copied.*\*/', r'/\*.*stackoverflow.*\*/'
            ],
            'template_code': [
                r'TODO:', r'FIXME:', r'YOUR_CODE_HERE',
                r'def\s+solution\s*\(\s*\):', r'class\s+Solution\s*:'
            ]
        }
        
        # Language-specific patterns
        self.language_patterns = {
            'python': {
                'imports': r'^import\s+(\w+)|^from\s+(\w+)',
                'functions': r'def\s+(\w+)\s*\(',
                'classes': r'class\s+(\w+)\s*[:\(]'
            },
            'javascript': {
                'functions': r'function\s+(\w+)\s*\(|(\w+)\s*=\s*function',
                'classes': r'class\s+(\w+)\s*{'
            },
            'java': {
                'classes': r'class\s+(\w+)\s*{',
                'methods': r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\('
            }
        }
    
    def analyze_code(self, code: str, language: str, problem_id: int, user_id: int) -> Dict[str, Any]:
        """Comprehensive code analysis for cheating detection"""
        
        analysis_result = {
            'suspicious_score': 0,
            'security_violations': [],
            'cheating_indicators': [],
            'code_quality': {},
            'similarity_hash': self._generate_similarity_hash(code, language),
            'metadata': {
                'lines_of_code': len(code.splitlines()),
                'character_count': len(code),
                'complexity_score': 0
            }
        }
        
        try:
            # Security analysis
            security_score, violations = self._check_security_violations(code, language)
            analysis_result['suspicious_score'] += security_score
            analysis_result['security_violations'] = violations
            
            # Cheating pattern detection
            cheating_score, indicators = self._detect_cheating_patterns(code, language)
            analysis_result['suspicious_score'] += cheating_score
            analysis_result['cheating_indicators'] = indicators
            
            # Code quality analysis
            quality_analysis = self._analyze_code_quality(code, language)
            analysis_result['code_quality'] = quality_analysis
            analysis_result['suspicious_score'] += quality_analysis.get('suspicious_score', 0)
            
            # Complexity analysis
            complexity = self._calculate_complexity(code, language)
            analysis_result['metadata']['complexity_score'] = complexity
            
            # Check against previous submissions
            similarity_results = self._check_similarity(code, language, problem_id, user_id)
            analysis_result['similarity_results'] = similarity_results
            analysis_result['suspicious_score'] += similarity_results.get('similarity_score', 0)
            
            # Final risk assessment
            analysis_result['risk_level'] = self._calculate_risk_level(analysis_result['suspicious_score'])
            
            return analysis_result
            
        except Exception as e:
            current_app.logger.error(f"Code analysis error: {e}")
            return analysis_result
    
    def _check_security_violations(self, code: str, language: str) -> Tuple[int, List[str]]:
        """Check for security violations in code"""
        
        violations = []
        score = 0
        
        for category, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                    violations.append(f"{category}: {pattern}")
                    
                    # Score based on severity
                    if category in ['network_calls', 'subprocess_calls']:
                        score += 50  # High risk
                    elif category in ['file_operations']:
                        score += 30  # Medium risk
                    else:
                        score += 10  # Low risk
        
        return score, violations
    
    def _detect_cheating_patterns(self, code: str, language: str) -> Tuple[int, List[str]]:
        """Detect common cheating patterns"""
        
        indicators = []
        score = 0
        
        for category, patterns in self.cheating_indicators.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                    indicators.append(f"{category}: {pattern}")
                    score += 20
        
        # Check for extremely short or long solutions
        lines = len(code.splitlines())
        if lines < 3:  # Suspiciously short
            indicators.append("suspicious_length: code too short")
            score += 15
        elif lines > 200:  # Suspiciously long
            indicators.append("suspicious_length: code too long")
            score += 10
        
        return score, indicators
    
    def _analyze_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code quality and detect anomalies"""
        
        quality = {
            'has_comments': bool(re.search(r'#.*|//.*|/\*.*\*/', code)),
            'indentation_consistent': self._check_indentation(code),
            'variable_naming': self._check_variable_naming(code, language),
            'function_count': len(re.findall(r'def\s+\w+\s*\(', code)) if language == 'python' else 0,
            'suspicious_score': 0
        }
        
        # Inconsistent indentation might indicate copy-paste
        if not quality['indentation_consistent']:
            quality['suspicious_score'] += 15
        
        # Too many or too few comments
        comment_lines = len(re.findall(r'^\s*#.*', code, re.MULTILINE))
        total_lines = len(code.splitlines())
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            if comment_ratio > 0.5:  # Too many comments
                quality['suspicious_score'] += 10
            elif comment_ratio == 0 and total_lines > 20:  # No comments in long code
                quality['suspicious_score'] += 5
        
        return quality
    
    def _check_indentation(self, code: str) -> bool:
        """Check if indentation is consistent"""
        
        lines = code.splitlines()
        indent_pattern = None
        
        for line in lines:
            if line.strip() and line.startswith((' ', '\t')):
                leading_whitespace = line[:len(line) - len(line.lstrip())]
                
                if indent_pattern is None:
                    indent_pattern = 'spaces' if ' ' in leading_whitespace else 'tabs'
                else:
                    current_type = 'spaces' if ' ' in leading_whitespace else 'tabs'
                    if current_type != indent_pattern:
                        return False
        
        return True
    
    def _check_variable_naming(self, code: str, language: str) -> Dict[str, Any]:
        """Check variable naming conventions"""
        
        naming = {
            'snake_case_count': 0,
            'camel_case_count': 0,
            'single_letter_count': 0,
            'suspicious_names': []
        }
        
        # Extract variable names (simplified)
        if language == 'python':
            variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        else:
            variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        
        for var in variables:
            if len(var) == 1:
                naming['single_letter_count'] += 1
            elif '_' in var:
                naming['snake_case_count'] += 1
            elif any(c.isupper() for c in var[1:]):
                naming['camel_case_count'] += 1
            
            # Check for suspicious names
            if var.lower() in ['temp', 'tmp', 'var', 'data', 'result', 'output']:
                naming['suspicious_names'].append(var)
        
        return naming
    
    def _calculate_complexity(self, code: str, language: str) -> int:
        """Calculate cyclomatic complexity of code"""
        
        complexity = 1  # Base complexity
        
        # Count decision points
        decision_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'case']
        
        for keyword in decision_keywords:
            matches = re.findall(f'\\b{keyword}\\b', code, re.IGNORECASE)
            complexity += len(matches)
        
        return complexity
    
    def _generate_similarity_hash(self, code: str, language: str) -> str:
        """Generate hash for similarity comparison"""
        
        # Normalize code for comparison
        normalized = self._normalize_code(code, language)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _normalize_code(self, code: str, language: str) -> str:
        """Normalize code by removing comments, whitespace, and variable names"""
        
        # Remove comments
        if language == 'python':
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        elif language in ['javascript', 'java']:
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Remove extra whitespace
        code = re.sub(r'\s+', ' ', code)
        
        # Normalize variable names (replace with generic names)
        variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code)
        unique_vars = list(set(variables))
        
        for i, var in enumerate(unique_vars):
            if not var in ['if', 'else', 'for', 'while', 'def', 'class', 'return', 'print']:
                code = re.sub(f'\\b{re.escape(var)}\\b', f'var{i}', code)
        
        return code.strip().lower()
    
    def _check_similarity(self, code: str, language: str, problem_id: int, user_id: int) -> Dict[str, Any]:
        """Check similarity with other submissions"""
        
        similarity_result = {
            'max_similarity': 0,
            'similar_submissions': [],
            'similarity_score': 0
        }
        
        try:
            # Get recent submissions for the same problem
            recent_submissions = db.session.execute(text("""
                SELECT s.code, s.user_id, s.created_at, u.username
                FROM submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.problem_id = :problem_id 
                AND s.user_id != :user_id
                AND s.created_at > :cutoff_date
                AND s.status = 'accepted'
                ORDER BY s.created_at DESC
                LIMIT 100
            """), {
                'problem_id': problem_id,
                'user_id': user_id,
                'cutoff_date': datetime.utcnow() - timedelta(days=30)
            }).fetchall()
            
            current_normalized = self._normalize_code(code, language)
            
            for submission in recent_submissions:
                other_normalized = self._normalize_code(submission.code, language)
                
                # Calculate similarity
                similarity_ratio = difflib.SequenceMatcher(
                    None, current_normalized, other_normalized
                ).ratio()
                
                if similarity_ratio > 0.8:  # High similarity threshold
                    similarity_result['similar_submissions'].append({
                        'user_id': submission.user_id,
                        'username': submission.username,
                        'similarity': similarity_ratio,
                        'submission_date': submission.created_at.isoformat()
                    })
                    
                    if similarity_ratio > similarity_result['max_similarity']:
                        similarity_result['max_similarity'] = similarity_ratio
            
            # Calculate score based on similarity
            if similarity_result['max_similarity'] > 0.95:
                similarity_result['similarity_score'] = 100  # Extremely high
            elif similarity_result['max_similarity'] > 0.9:
                similarity_result['similarity_score'] = 50
            elif similarity_result['max_similarity'] > 0.8:
                similarity_result['similarity_score'] = 25
            
            return similarity_result
            
        except Exception as e:
            current_app.logger.error(f"Similarity check error: {e}")
            return similarity_result
    
    def _calculate_risk_level(self, suspicious_score: int) -> str:
        """Calculate overall risk level based on suspicious score"""
        
        if suspicious_score >= 100:
            return 'CRITICAL'
        elif suspicious_score >= 70:
            return 'HIGH'
        elif suspicious_score >= 40:
            return 'MEDIUM'
        elif suspicious_score >= 20:
            return 'LOW'
        else:
            return 'CLEAN'

class GameIntegrityMonitor:
    """Monitors game sessions for integrity violations and suspicious behavior"""
    
    def __init__(self, redis_client=None):
        """Initialize game integrity monitor"""
        
        self.redis_client = redis_client
        self.monitor_prefix = "game_integrity:"
        
        # Thresholds for suspicious behavior
        self.thresholds = {
            'submission_frequency': 10,  # Max submissions per minute
            'rapid_solutions': 30,       # Min seconds between correct solutions
            'identical_timings': 3,      # Max number of identical timing patterns
            'browser_switches': 5,       # Max browser/tab switches per game
            'unusual_patterns': 3        # Max unusual behavior patterns
        }
    
    def monitor_submission(self, game_id: str, user_id: int, submission_data: Dict) -> Dict[str, Any]:
        """Monitor a submission for suspicious patterns"""
        
        monitoring_result = {
            'violations': [],
            'suspicious_score': 0,
            'risk_level': 'LOW',
            'should_flag': False
        }
        
        try:
            # Check submission timing
            timing_violations = self._check_submission_timing(game_id, user_id, submission_data)
            monitoring_result['violations'].extend(timing_violations)
            
            # Check submission frequency
            frequency_violations = self._check_submission_frequency(game_id, user_id)
            monitoring_result['violations'].extend(frequency_violations)
            
            # Check for unusual patterns
            pattern_violations = self._check_unusual_patterns(game_id, user_id, submission_data)
            monitoring_result['violations'].extend(pattern_violations)
            
            # Calculate risk score
            monitoring_result['suspicious_score'] = len(monitoring_result['violations']) * 20
            
            # Determine if submission should be flagged
            if monitoring_result['suspicious_score'] >= 60:
                monitoring_result['risk_level'] = 'HIGH'
                monitoring_result['should_flag'] = True
            elif monitoring_result['suspicious_score'] >= 40:
                monitoring_result['risk_level'] = 'MEDIUM'
            
            # Log monitoring result
            if monitoring_result['should_flag']:
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.CHEATING_DETECTED,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message="Suspicious submission behavior detected",
                    details={
                        'game_id': game_id,
                        'violations': monitoring_result['violations'],
                        'suspicious_score': monitoring_result['suspicious_score']
                    },
                    user_id=str(user_id)
                )
            
            return monitoring_result
            
        except Exception as e:
            current_app.logger.error(f"Game integrity monitoring error: {e}")
            return monitoring_result
    
    def _check_submission_timing(self, game_id: str, user_id: int, submission_data: Dict) -> List[str]:
        """Check for suspicious submission timing patterns"""
        
        violations = []
        
        try:
            if not self.redis_client:
                return violations
            
            # Get user's submission history for this game
            timing_key = f"{self.monitor_prefix}timing:{game_id}:{user_id}"
            timing_data = self.redis_client.lrange(timing_key, 0, -1)
            
            current_time = time.time()
            
            # Store current submission timing
            submission_timing = {
                'timestamp': current_time,
                'code_length': len(submission_data.get('code', '')),
                'problem_id': submission_data.get('problem_id')
            }
            
            self.redis_client.lpush(timing_key, json.dumps(submission_timing))
            self.redis_client.expire(timing_key, 3600)  # Expire after 1 hour
            
            # Analyze timing patterns
            if len(timing_data) > 0:
                last_submission = json.loads(timing_data[0])
                time_diff = current_time - last_submission['timestamp']
                
                # Check for too rapid submissions
                if time_diff < self.thresholds['rapid_solutions']:
                    violations.append(f"rapid_submission: {time_diff:.1f} seconds between submissions")
                
                # Check for identical timing patterns
                if len(timing_data) >= 3:
                    time_diffs = []
                    for i in range(min(3, len(timing_data))):
                        if i < len(timing_data) - 1:
                            prev_timing = json.loads(timing_data[i])
                            next_timing = json.loads(timing_data[i + 1])
                            diff = prev_timing['timestamp'] - next_timing['timestamp']
                            time_diffs.append(diff)
                    
                    # Check if timing differences are suspiciously similar
                    if len(time_diffs) >= 2:
                        variance = statistics.variance(time_diffs)
                        if variance < 1.0:  # Very low variance indicates automation
                            violations.append("identical_timing_pattern: submissions show robotic timing")
            
            return violations
            
        except Exception as e:
            current_app.logger.error(f"Timing check error: {e}")
            return violations
    
    def _check_submission_frequency(self, game_id: str, user_id: int) -> List[str]:
        """Check submission frequency for rate limiting violations"""
        
        violations = []
        
        try:
            if not self.redis_client:
                return violations
            
            frequency_key = f"{self.monitor_prefix}frequency:{game_id}:{user_id}"
            current_minute = int(time.time() / 60)
            
            # Increment submission count for current minute
            minute_key = f"{frequency_key}:{current_minute}"
            current_count = self.redis_client.incr(minute_key)
            self.redis_client.expire(minute_key, 120)  # Expire after 2 minutes
            
            if current_count > self.thresholds['submission_frequency']:
                violations.append(f"high_frequency: {current_count} submissions in one minute")
            
            return violations
            
        except Exception as e:
            current_app.logger.error(f"Frequency check error: {e}")
            return violations
    
    def _check_unusual_patterns(self, game_id: str, user_id: int, submission_data: Dict) -> List[str]:
        """Check for unusual behavioral patterns"""
        
        violations = []
        
        try:
            code = submission_data.get('code', '')
            
            # Check for suspiciously perfect solutions
            if len(code.splitlines()) < 5 and len(code) > 100:
                violations.append("condensed_code: suspiciously condensed solution")
            
            # Check for copy-paste indicators (mixed indentation, encoding issues)
            if '\t' in code and '    ' in code:  # Mixed tabs and spaces
                violations.append("mixed_indentation: indicates copy-paste from multiple sources")
            
            # Check for non-ASCII characters that might indicate copy-paste
            if any(ord(char) > 127 for char in code):
                violations.append("non_ascii_chars: contains non-ASCII characters")
            
            return violations
            
        except Exception as e:
            current_app.logger.error(f"Pattern check error: {e}")
            return violations
    
    def track_user_behavior(self, game_id: str, user_id: int, event_type: str, event_data: Dict):
        """Track user behavior during game session"""
        
        try:
            if not self.redis_client:
                return
            
            behavior_key = f"{self.monitor_prefix}behavior:{game_id}:{user_id}"
            
            behavior_event = {
                'timestamp': time.time(),
                'event_type': event_type,
                'data': event_data
            }
            
            self.redis_client.lpush(behavior_key, json.dumps(behavior_event))
            self.redis_client.expire(behavior_key, 3600)  # Expire after 1 hour
            
        except Exception as e:
            current_app.logger.error(f"Behavior tracking error: {e}")

class AntiCheatEngine:
    """Main anti-cheat engine coordinating all integrity checks"""
    
    def __init__(self, redis_client=None):
        """Initialize anti-cheat engine"""
        
        self.code_analyzer = CodeAnalyzer()
        self.integrity_monitor = GameIntegrityMonitor(redis_client)
        self.redis_client = redis_client
        
        # Action thresholds
        self.action_thresholds = {
            'auto_reject': 150,     # Automatically reject submission
            'manual_review': 80,    # Flag for manual review
            'warning': 50,          # Issue warning to user
            'monitor': 25           # Increase monitoring
        }
    
    def process_submission(self, submission_data: Dict) -> Dict[str, Any]:
        """Process a submission through anti-cheat pipeline"""
        
        result = {
            'allowed': True,
            'action': 'ACCEPT',
            'score': 0,
            'violations': [],
            'analysis_details': {},
            'monitoring_details': {}
        }
        
        try:
            code = submission_data.get('code', '')
            language = submission_data.get('language', 'python')
            problem_id = submission_data.get('problem_id')
            user_id = submission_data.get('user_id')
            game_id = submission_data.get('game_id')
            
            # Code analysis
            code_analysis = self.code_analyzer.analyze_code(code, language, problem_id, user_id)
            result['analysis_details'] = code_analysis
            result['score'] += code_analysis.get('suspicious_score', 0)
            result['violations'].extend(code_analysis.get('security_violations', []))
            result['violations'].extend(code_analysis.get('cheating_indicators', []))
            
            # Game integrity monitoring
            if game_id:
                monitoring = self.integrity_monitor.monitor_submission(game_id, user_id, submission_data)
                result['monitoring_details'] = monitoring
                result['score'] += monitoring.get('suspicious_score', 0)
                result['violations'].extend(monitoring.get('violations', []))
            
            # Determine action based on total score
            if result['score'] >= self.action_thresholds['auto_reject']:
                result['allowed'] = False
                result['action'] = 'REJECT'
            elif result['score'] >= self.action_thresholds['manual_review']:
                result['action'] = 'REVIEW'
            elif result['score'] >= self.action_thresholds['warning']:
                result['action'] = 'WARNING'
            elif result['score'] >= self.action_thresholds['monitor']:
                result['action'] = 'MONITOR'
            
            # Log significant violations
            if result['action'] in ['REJECT', 'REVIEW']:
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.CHEATING_DETECTED,
                    severity=AuditSeverity.HIGH if result['action'] == 'REJECT' else AuditSeverity.MEDIUM,
                    success=False,
                    message=f"Anti-cheat action: {result['action']}",
                    details={
                        'score': result['score'],
                        'violations': result['violations'][:5],  # Limit details
                        'action': result['action']
                    },
                    user_id=str(user_id)
                )
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Anti-cheat processing error: {e}")
            # Allow submission on error but log the issue
            result['action'] = 'ERROR'
            return result
    
    def get_user_integrity_report(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Generate integrity report for a user"""
        
        try:
            # Get user's recent submissions
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            submissions = db.session.execute(text("""
                SELECT s.*, p.title as problem_title
                FROM submissions s
                JOIN problems p ON s.problem_id = p.id
                WHERE s.user_id = :user_id
                AND s.created_at > :cutoff_date
                ORDER BY s.created_at DESC
            """), {
                'user_id': user_id,
                'cutoff_date': cutoff_date
            }).fetchall()
            
            report = {
                'user_id': user_id,
                'period_days': days,
                'total_submissions': len(submissions),
                'flagged_submissions': 0,
                'average_score': 0,
                'violations_by_type': defaultdict(int),
                'risk_level': 'LOW',
                'recommendations': []
            }
            
            total_score = 0
            
            for submission in submissions:
                # Re-analyze recent submissions
                analysis = self.code_analyzer.analyze_code(
                    submission.code, 
                    submission.language, 
                    submission.problem_id, 
                    user_id
                )
                
                score = analysis.get('suspicious_score', 0)
                total_score += score
                
                if score >= self.action_thresholds['warning']:
                    report['flagged_submissions'] += 1
                
                # Count violations by type
                for violation in analysis.get('security_violations', []):
                    violation_type = violation.split(':')[0]
                    report['violations_by_type'][violation_type] += 1
                
                for indicator in analysis.get('cheating_indicators', []):
                    indicator_type = indicator.split(':')[0]
                    report['violations_by_type'][indicator_type] += 1
            
            # Calculate averages and risk level
            if report['total_submissions'] > 0:
                report['average_score'] = total_score / report['total_submissions']
                
                if report['average_score'] >= 50:
                    report['risk_level'] = 'HIGH'
                elif report['average_score'] >= 25:
                    report['risk_level'] = 'MEDIUM'
            
            # Generate recommendations
            if report['flagged_submissions'] > 0:
                report['recommendations'].append("Review flagged submissions for policy violations")
            
            if report['violations_by_type'].get('network_calls', 0) > 0:
                report['recommendations'].append("User attempting network operations in code")
            
            if report['violations_by_type'].get('copy_paste', 0) > 2:
                report['recommendations'].append("Possible copy-paste behavior detected")
            
            return report
            
        except Exception as e:
            current_app.logger.error(f"Integrity report error: {e}")
            return {'error': 'Failed to generate report'}

# Integration functions

def init_game_integrity(app, redis_client=None):
    """Initialize game integrity system"""
    
    try:
        anti_cheat_engine = AntiCheatEngine(redis_client)
        
        app.anti_cheat_engine = anti_cheat_engine
        
        app.logger.info("Game integrity and anti-cheat system initialized")
        
        return anti_cheat_engine
        
    except Exception as e:
        app.logger.error(f"Game integrity initialization failed: {e}")
        return None

def check_submission_integrity(submission_data: Dict) -> Dict[str, Any]:
    """Helper function to check submission integrity"""
    
    try:
        if hasattr(current_app, 'anti_cheat_engine'):
            return current_app.anti_cheat_engine.process_submission(submission_data)
        else:
            # Fallback if anti-cheat engine not available
            return {
                'allowed': True,
                'action': 'ACCEPT',
                'score': 0,
                'violations': [],
                'message': 'Anti-cheat system not available'
            }
    except Exception as e:
        current_app.logger.error(f"Integrity check error: {e}")
        return {
            'allowed': True,  # Allow on error
            'action': 'ERROR',
            'score': 0,
            'violations': [],
            'error': str(e)
        }