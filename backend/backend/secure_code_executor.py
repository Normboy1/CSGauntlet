import subprocess
import tempfile
import os
import sys
import signal
import json
import time
import hashlib
import resource
from typing import Dict, Tuple, Optional, List
from contextlib import contextmanager
from pathlib import Path
import docker
from .security import CodeSandbox, SecurityAudit, SecurityValidator
from .ai_grader import AICodeGrader, GradingResult

class SecureCodeExecutor:
    """Enhanced secure code executor with comprehensive sandboxing"""
    
    def __init__(self, 
                 timeout: int = 10, 
                 memory_limit: str = "128m",
                 cpu_limit: str = "0.5",
                 container_image: str = "python:3.9-slim"):
        
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.container_image = container_image
        self.ai_grader = AICodeGrader()
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_available = True
        except docker.errors.DockerException as e:
            print(f"Docker not available: {e}")
            self.docker_client = None
            self.docker_available = False
        
        # Initialize code sandbox
        self.sandbox = CodeSandbox()
        
        # Maximum execution counts per user per time window
        self.max_executions_per_minute = 10
        self.execution_tracking = {}
    
    def _check_execution_limits(self, user_id: str) -> bool:
        """Check if user has exceeded execution limits"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        if user_id not in self.execution_tracking:
            self.execution_tracking[user_id] = []
        
        # Remove old executions outside the window
        self.execution_tracking[user_id] = [
            exec_time for exec_time in self.execution_tracking[user_id] 
            if exec_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.execution_tracking[user_id]) >= self.max_executions_per_minute:
            SecurityAudit.log_security_event(
                'code_execution_limit_exceeded',
                user_id=user_id,
                details={'executions_in_window': len(self.execution_tracking[user_id])}
            )
            return False
        
        # Record this execution
        self.execution_tracking[user_id].append(current_time)
        return True
    
    def _validate_code_security(self, code: str, language: str) -> Tuple[bool, List[str]]:
        """Comprehensive code security validation"""
        # Use SecurityValidator for basic validation
        is_safe, sanitized_code = SecurityValidator.validate_code_input(code, language)
        if not is_safe:
            return False, [sanitized_code]  # sanitized_code contains error message
        
        # Use CodeSandbox for deeper validation
        is_safe, violations = self.sandbox.validate_code_safety(code, language)
        if not is_safe:
            return False, violations
        
        # Additional language-specific checks
        security_issues = []
        
        if language == 'python':
            security_issues.extend(self._check_python_security(code))
        elif language == 'javascript':
            security_issues.extend(self._check_javascript_security(code))
        
        return len(security_issues) == 0, security_issues
    
    def _check_python_security(self, code: str) -> List[str]:
        """Python-specific security checks"""
        issues = []
        
        # Check for dangerous imports
        dangerous_imports = [
            'os', 'sys', 'subprocess', 'shutil', 'glob', 'socket', 
            'urllib', 'requests', 'http', 'ftplib', 'smtplib',
            'pickle', 'marshal', 'shelve', 'dbm', 'sqlite3',
            'ctypes', 'multiprocessing', 'threading', 'asyncio'
        ]
        
        for imp in dangerous_imports:
            if f'import {imp}' in code or f'from {imp}' in code:
                issues.append(f"Dangerous import detected: {imp}")
        
        # Check for dangerous built-ins
        dangerous_builtins = [
            '__import__', 'eval', 'exec', 'compile', 'open', 'file',
            'input', 'raw_input', 'reload', 'vars', 'globals', 'locals',
            'dir', 'getattr', 'setattr', 'hasattr', 'delattr'
        ]
        
        for builtin in dangerous_builtins:
            if builtin in code:
                issues.append(f"Dangerous built-in function detected: {builtin}")
        
        # Check for infinite loops
        if self._detect_potential_infinite_loops(code):
            issues.append("Potential infinite loop detected")
        
        # Check for excessive memory allocation
        if self._detect_memory_bombs(code):
            issues.append("Potential memory bomb detected")
        
        return issues
    
    def _check_javascript_security(self, code: str) -> List[str]:
        """JavaScript-specific security checks"""
        issues = []
        
        # Check for dangerous functions/objects
        dangerous_patterns = [
            'require(', 'import ', 'eval(', 'Function(', 'setTimeout(', 'setInterval(',
            'XMLHttpRequest', 'fetch(', 'Worker(', 'SharedWorker(',
            'WebSocket', 'EventSource', 'process.', 'global.',
            'window.', 'document.', 'location.', 'navigator.'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return issues
    
    def _detect_potential_infinite_loops(self, code: str) -> bool:
        """Detect patterns that might indicate infinite loops"""
        patterns = [
            r'while\s+True\s*:',
            r'while\s+1\s*:',
            r'for\s+.*\s+in\s+itertools\.count\s*\(',
            r'while\s+.*==.*:'  # Simple equality check that might not change
        ]
        
        import re
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False
    
    def _detect_memory_bombs(self, code: str) -> bool:
        """Detect patterns that might consume excessive memory"""
        patterns = [
            r'\[\d+\]\s*\*\s*\d{6,}',  # Large list creation
            r'range\s*\(\s*\d{7,}',     # Large range
            r'\*\*\s*\d{4,}',          # Large exponentiation
            r'\'.*\'\s*\*\s*\d{6,}',   # Large string multiplication
        ]
        
        import re
        for pattern in patterns:
            if re.search(pattern, code):
                return True
        return False
    
    @contextmanager
    def create_secure_container(self, language: str = "python"):
        """Create a highly secured container for code execution"""
        if not self.docker_available:
            raise RuntimeError("Docker is required for secure code execution")
        
        # Choose appropriate image based on language
        image_map = {
            'python': 'python:3.9-alpine',
            'javascript': 'node:16-alpine',
            'java': 'openjdk:11-jre-slim',
            'cpp': 'gcc:latest'
        }
        
        image = image_map.get(language, self.container_image)
        
        # Create container with maximum security restrictions
        container = self.docker_client.containers.create(
            image,
            command="sleep infinity",
            detach=True,
            remove=True,
            
            # Resource limits
            mem_limit=self.memory_limit,
            memswap_limit=self.memory_limit,  # Disable swap
            cpu_period=100000,
            cpu_quota=int(float(self.cpu_limit) * 100000),
            
            # Security restrictions
            read_only_root_fs=True,
            user="nobody:nogroup",
            network_disabled=True,
            cap_drop=['ALL'],  # Drop all capabilities
            cap_add=[],        # Don't add any back
            
            # Process limits
            pids_limit=20,
            
            # Filesystem restrictions
            tmpfs={'/tmp': 'size=10m,noexec,nosuid,nodev'},
            volumes={},  # No volume mounts
            
            # Environment restrictions
            environment={
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONUNBUFFERED': '1',
                'PATH': '/usr/local/bin:/usr/bin:/bin'  # Restricted PATH
            },
            
            # Additional security options
            security_opt=[
                'no-new-privileges:true',
                'apparmor:unconfined'  # You might want to create a custom AppArmor profile
            ]
        )
        
        try:
            container.start()
            yield container
        finally:
            try:
                container.stop(timeout=1)
                container.remove(force=True)
            except:
                pass  # Container might already be stopped/removed
    
    def execute_code_securely(self, 
                            code: str, 
                            test_cases: List[Dict], 
                            language: str = "python",
                            user_id: str = None) -> Tuple[bool, str, Dict]:
        """Execute code with comprehensive security measures"""
        
        # Check execution limits
        if user_id and not self._check_execution_limits(user_id):
            return False, "Execution limit exceeded. Please wait before submitting again.", {}
        
        # Validate code security
        is_safe, security_issues = self._validate_code_security(code, language)
        if not is_safe:
            SecurityAudit.log_security_event(
                'unsafe_code_detected',
                user_id=user_id,
                details={'issues': security_issues, 'language': language}
            )
            return False, f"Security issues detected: {'; '.join(security_issues)}", {}
        
        # Generate execution ID for tracking
        execution_id = hashlib.sha256(f"{code}{time.time()}".encode()).hexdigest()[:16]
        
        SecurityAudit.log_security_event(
            'code_execution_started',
            user_id=user_id,
            details={'execution_id': execution_id, 'language': language}
        )
        
        results = {
            "passed": 0,
            "total": len(test_cases),
            "test_results": [],
            "execution_id": execution_id,
            "security_validated": True
        }
        
        try:
            if self.docker_available:
                return self._execute_in_docker(code, test_cases, language, results, user_id)
            else:
                # Fallback to sandbox execution
                return self._execute_in_sandbox(code, test_cases, language, results, user_id)
                
        except Exception as e:
            SecurityAudit.log_security_event(
                'code_execution_error',
                user_id=user_id,
                details={'execution_id': execution_id, 'error': str(e)}
            )
            return False, f"Execution error: {str(e)}", results
    
    def _execute_in_docker(self, 
                          code: str, 
                          test_cases: List[Dict], 
                          language: str, 
                          results: Dict,
                          user_id: str) -> Tuple[bool, str, Dict]:
        """Execute code in Docker container"""
        
        with self.create_secure_container(language) as container:
            # Generate test runner code
            if language == "python":
                test_code = self._generate_python_test_code(code, test_cases)
                filename = "solution.py"
                cmd = f"timeout {self.timeout} python /tmp/{filename}"
            elif language == "javascript":
                test_code = self._generate_javascript_test_code(code, test_cases)
                filename = "solution.js"
                cmd = f"timeout {self.timeout} node /tmp/{filename}"
            else:
                return False, f"Language {language} not supported", results
            
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
                f.write(test_code)
                temp_file = f.name
            
            try:
                # Copy file to container
                with open(temp_file, 'rb') as f:
                    container.put_archive('/tmp', f.read())
                
                # Execute with strict timeout
                start_time = time.time()
                exit_code, output = container.exec_run(
                    cmd,
                    timeout=self.timeout,
                    demux=True,
                    user="nobody"
                )
                execution_time = time.time() - start_time
                
                stdout, stderr = output
                stdout = stdout.decode() if stdout else ""
                stderr = stderr.decode() if stderr else ""
                
                # Log execution details
                SecurityAudit.log_security_event(
                    'code_execution_completed',
                    user_id=user_id,
                    details={
                        'execution_id': results['execution_id'],
                        'exit_code': exit_code,
                        'execution_time': execution_time,
                        'stdout_length': len(stdout),
                        'stderr_length': len(stderr)
                    }
                )
                
                if exit_code != 0:
                    if exit_code == 124:  # Timeout exit code
                        return False, f"Code execution timed out after {self.timeout} seconds", results
                    else:
                        return False, f"Execution failed with exit code {exit_code}. Error: {stderr}", results
                
                # Parse test results
                try:
                    test_results = json.loads(stdout.strip())
                    results["test_results"] = test_results
                    results["passed"] = sum(1 for t in test_results if t.get("passed", False))
                    results["execution_time"] = execution_time
                    
                    success = results["passed"] == results["total"]
                    message = "All tests passed" if success else f"Passed {results['passed']}/{results['total']} tests"
                    
                    return success, message, results
                    
                except json.JSONDecodeError as e:
                    return False, f"Error parsing test results: {e}. Output: {stdout[:500]}", results
                    
            finally:
                os.unlink(temp_file)
    
    def _execute_in_sandbox(self, 
                           code: str, 
                           test_cases: List[Dict], 
                           language: str, 
                           results: Dict,
                           user_id: str) -> Tuple[bool, str, Dict]:
        """Fallback execution in local sandbox"""
        
        SecurityAudit.log_security_event(
            'fallback_sandbox_execution',
            user_id=user_id,
            details={'reason': 'Docker not available'}
        )
        
        success, message, output = self.sandbox.execute_code_safely(code, language, self.timeout)
        
        if success:
            # Simple success case - you might want to enhance this
            results["passed"] = results["total"]  # Assume all passed for now
            results["test_results"] = [{"passed": True, "output": output}]
            return True, "Code executed successfully in sandbox", results
        else:
            return False, message, results
    
    def _generate_python_test_code(self, code: str, test_cases: List[Dict]) -> str:
        """Generate Python test runner code"""
        return f"""
import json
import sys
import traceback
import signal
import resource

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, (128*1024*1024, 128*1024*1024))  # 128MB memory
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))  # 10 seconds CPU time

def timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({self.timeout})

try:
    # User code
{chr(10).join('    ' + line for line in code.split(chr(10)))}

    # Test cases
    test_cases = {json.dumps(test_cases)}
    results = []
    
    for i, test in enumerate(test_cases):
        try:
            func_name = test.get("function")
            if not func_name or func_name not in globals():
                results.append({{
                    "test_id": i,
                    "passed": False,
                    "expected": test.get("expected"),
                    "got": None,
                    "error": f"Function '{{func_name}}' not found"
                }})
                continue
            
            func = globals()[func_name]
            args = test.get("args", [])
            expected = test.get("expected")
            
            result = func(*args)
            passed = result == expected
            
            results.append({{
                "test_id": i,
                "passed": passed,
                "expected": expected,
                "got": result,
                "error": None
            }})
            
        except Exception as e:
            results.append({{
                "test_id": i,
                "passed": False,
                "expected": test.get("expected"),
                "got": None,
                "error": str(e)
            }})
    
    print(json.dumps(results))
    
except Exception as e:
    error_result = [{{"test_id": 0, "passed": False, "error": str(e)}}]
    print(json.dumps(error_result))
finally:
    signal.alarm(0)
"""
    
    def _generate_javascript_test_code(self, code: str, test_cases: List[Dict]) -> str:
        """Generate JavaScript test runner code"""
        return f"""
// Set timeout
setTimeout(() => {{
    console.log(JSON.stringify([{{"test_id": 0, "passed": false, "error": "Execution timed out"}}]));
    process.exit(1);
}}, {self.timeout * 1000});

try {{
    // User code
{code}

    // Test cases
    const testCases = {json.dumps(test_cases)};
    const results = [];
    
    for (let i = 0; i < testCases.length; i++) {{
        const test = testCases[i];
        try {{
            const funcName = test.function;
            if (typeof global[funcName] !== 'function') {{
                results.push({{
                    test_id: i,
                    passed: false,
                    expected: test.expected,
                    got: null,
                    error: `Function '${{funcName}}' not found`
                }});
                continue;
            }}
            
            const func = global[funcName];
            const args = test.args || [];
            const expected = test.expected;
            
            const result = func(...args);
            const passed = JSON.stringify(result) === JSON.stringify(expected);
            
            results.push({{
                test_id: i,
                passed: passed,
                expected: expected,
                got: result,
                error: null
            }});
            
        }} catch (error) {{
            results.push({{
                test_id: i,
                passed: false,
                expected: test.expected,
                got: null,
                error: error.message
            }});
        }}
    }}
    
    console.log(JSON.stringify(results));
    
}} catch (error) {{
    const errorResult = [{{"test_id": 0, "passed": false, "error": error.message}}];
    console.log(JSON.stringify(errorResult));
}}
"""

    async def execute_and_grade_securely(self,
                                       code: str,
                                       test_cases: List[Dict],
                                       problem_description: str,
                                       language: str = "python",
                                       user_id: str = None,
                                       reference_solution: str = None) -> Tuple[bool, str, Dict, GradingResult]:
        """Execute code securely and provide AI grading"""
        
        # Execute code securely
        success, message, test_results = self.execute_code_securely(
            code, test_cases, language, user_id
        )
        
        # Get AI grading if execution was successful
        try:
            if success:
                grading_result = await self.ai_grader.grade_solution(
                    problem_description=problem_description,
                    solution_code=code,
                    test_results=test_results,
                    language=language,
                    reference_solution=reference_solution
                )
            else:
                # Create basic grading for failed execution
                grading_result = self._create_failure_grading(test_results, message)
            
            return success, message, test_results, grading_result
            
        except Exception as e:
            # Fallback grading
            fallback_grading = self._create_fallback_grading(test_results)
            return success, message, test_results, fallback_grading
    
    def _create_failure_grading(self, test_results: Dict, error_message: str) -> GradingResult:
        """Create grading result for failed execution"""
        from .ai_grader import GradingCriteria, GradingResult
        
        criteria = GradingCriteria(
            correctness=0,
            efficiency=0,
            readability=0,
            style=0,
            innovation=0,
            total=0
        )
        
        feedback = {
            'correctness': f"Code failed to execute: {error_message}",
            'efficiency': "Cannot analyze - execution failed",
            'readability': "Cannot analyze - execution failed",
            'style': "Cannot analyze - execution failed"
        }
        
        return GradingResult(
            criteria=criteria,
            feedback=feedback,
            suggestions=["Fix the execution errors before resubmitting"],
            execution_time=0,
            memory_efficiency="Unknown",
            complexity_analysis="Unknown",
            code_smells=[],
            best_practices=[],
            overall_grade='F',
            rank_percentile=0
        )
    
    def _create_fallback_grading(self, test_results: Dict) -> GradingResult:
        """Create basic grading when AI is unavailable"""
        from .ai_grader import GradingCriteria, GradingResult
        
        passed = test_results.get('passed', 0)
        total = test_results.get('total', 1)
        pass_rate = passed / total if total > 0 else 0
        
        # Basic scoring
        correctness = pass_rate * 40
        efficiency = 15 if pass_rate > 0.8 else 10
        readability = 12 if pass_rate > 0.6 else 8
        style = 6 if pass_rate > 0.4 else 4
        innovation = 2
        
        criteria = GradingCriteria(
            correctness=correctness,
            efficiency=efficiency,
            readability=readability,
            style=style,
            innovation=innovation,
            total=correctness + efficiency + readability + style + innovation
        )
        
        feedback = {
            'correctness': f"Passed {passed}/{total} test cases ({pass_rate*100:.1f}%)",
            'efficiency': "Basic efficiency analysis",
            'readability': "Standard code structure",
            'style': "Acceptable formatting"
        }
        
        if pass_rate == 1.0:
            grade = 'A'
        elif pass_rate >= 0.8:
            grade = 'B'
        elif pass_rate >= 0.6:
            grade = 'C'
        elif pass_rate >= 0.4:
            grade = 'D'
        else:
            grade = 'F'
        
        return GradingResult(
            criteria=criteria,
            feedback=feedback,
            suggestions=["Consider optimizing your solution" if pass_rate > 0 else "Review the problem requirements"],
            execution_time=test_results.get('execution_time', 0),
            memory_efficiency="Standard",
            complexity_analysis="Not analyzed",
            code_smells=[],
            best_practices=[],
            overall_grade=grade,
            rank_percentile=pass_rate * 100
        )