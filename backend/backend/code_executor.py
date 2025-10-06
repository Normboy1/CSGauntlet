import subprocess
import tempfile
import os
import sys
import signal
from typing import Dict, Tuple, Optional
import docker
from contextlib import contextmanager
import json
from .ai_grader import AICodeGrader, GradingResult

class CodeExecutor:
    def __init__(self, timeout: int = 10, container_image: str = "python:3.9-slim-buster", memory_limit: str = "256m"):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            print(f"Error connecting to Docker: {e}. Please ensure Docker is running.")
            self.client = None # Or raise an exception, depending on desired behavior

        self.timeout = timeout
        self.container_image = container_image
        self.memory_limit = memory_limit
        self.ai_grader = AICodeGrader()

    @contextmanager
    def create_container(self):
        """Create a temporary container for code execution"""
        if not self.client:
            logger.error("Docker client not initialized. Cannot create container.")
            raise RuntimeError("Docker client not initialized.")

        container = self.client.containers.create(
            self.container_image,
            command="sleep infinity",
            mem_limit=self.memory_limit,
            network_disabled=True,
            remove=True,
            detach=True,
            read_only_root_fs=True,  # Make filesystem read-only
            user="nobody",           # Run as non-root user
            cap_drop=['ALL'],        # Drop all capabilities
            pids_limit=50            # Limit number of processes
        )
        try:
            yield container
        finally:
            container.stop()
            container.remove()

    def execute_code(self, code: str, test_cases: list) -> Tuple[bool, str, Dict]:
        """
        Execute code in a sandboxed environment and validate against test cases
        Returns: (success, message, results)
        """
        results = {
            "passed": 0,
            "total": len(test_cases),
            "test_results": []
        }

        if not self.client:
            return False, "Docker client not initialized. Cannot execute code.", results

        try:
            with self.create_container() as container:
                # Create a temporary file for the code
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    # Add test cases to the code
                    test_code = self._generate_test_code(code, test_cases)
                    f.write(test_code)
                    f.flush()
                    
                    # Copy the file to the container
                    container.put_archive('/tmp', open(f.name, 'rb').read())
                    
                    # Execute the code with timeout
                    exit_code, output = container.exec_run(
                        f"timeout {self.timeout} python /tmp/{os.path.basename(f.name)}",
                        timeout=self.timeout,
                        stream=False, # Capture all output at once
                        demux=True # Separate stdout and stderr
                    )
                    
                    stdout, stderr = output
                    stdout = stdout.decode() if stdout else ""
                    stderr = stderr.decode() if stderr else ""

                    if exit_code != 0:
                        return False, f"Execution failed with exit code {exit_code}. Stderr: {stderr}", results

                    # Parse results
                    try:
                        test_results = json.loads(stdout)
                        results["test_results"] = test_results
                        results["passed"] = sum(1 for t in test_results if t["passed"])
                    except json.JSONDecodeError:
                        return False, f"Error parsing test results. Stdout: {stdout}, Stderr: {stderr}", results

                os.unlink(f.name)
                
                return (
                    results["passed"] == results["total"],
                    "All tests passed" if results["passed"] == results["total"] else "Some tests failed",
                    results
                )

    async def execute_and_grade_code(
        self, 
        code: str, 
        test_cases: list, 
        problem_description: str,
        language: str = "python",
        reference_solution: str = None
    ) -> Tuple[bool, str, Dict, GradingResult]:
        """
        Execute code and provide comprehensive AI grading
        Returns: (success, message, test_results, grading_result)
        """
        # First execute the code normally
        success, message, test_results = self.execute_code(code, test_cases)
        
        # Then get AI grading
        try:
            grading_result = await self.ai_grader.grade_solution(
                problem_description=problem_description,
                solution_code=code,
                test_results=test_results,
                language=language,
                reference_solution=reference_solution
            )
            
            return success, message, test_results, grading_result
            
        except Exception as e:
            # Fallback to basic grading if AI fails
            print(f"AI grading failed: {e}")
            fallback_grading = self._create_fallback_grading(test_results)
            return success, message, test_results, fallback_grading

    def _create_fallback_grading(self, test_results: Dict) -> GradingResult:
        """Create a basic grading result when AI is unavailable"""
        from .ai_grader import GradingCriteria, GradingResult
        
        passed = test_results.get('passed', 0)
        total = test_results.get('total', 1)
        pass_rate = passed / total if total > 0 else 0
        
        # Basic scoring based on test results
        correctness = pass_rate * 40
        efficiency = 15  # Default
        readability = 12  # Default
        style = 6   # Default
        innovation = 2  # Default
        
        criteria = GradingCriteria(
            correctness=correctness,
            efficiency=efficiency,
            readability=readability,
            style=style,
            innovation=innovation,
            total=correctness + efficiency + readability + style + innovation
        )
        
        feedback = {
            'correctness': f"Passed {passed}/{total} test cases",
            'efficiency': "Unable to analyze efficiency without AI",
            'readability': "Basic code structure detected",
            'style': "Standard formatting"
        }
        
        grade = 'A' if pass_rate == 1.0 else 'B' if pass_rate >= 0.8 else 'C' if pass_rate >= 0.6 else 'D'
        
        return GradingResult(
            criteria=criteria,
            feedback=feedback,
            suggestions=["Consider adding comments for clarity"],
            execution_time=0.1,
            memory_efficiency="Unknown",
            complexity_analysis="Unknown",
            code_smells=[],
            best_practices=[],
            overall_grade=grade,
            rank_percentile=pass_rate * 100
        )

    def _generate_test_code(self, code: str, test_cases: list) -> str:
        """Generate code with test cases. Note: Using globals() for function lookup is generally discouraged for untrusted code, but is mitigated here by Docker sandboxing."""
        test_code = f"""
import json
import sys
from typing import List, Dict, Any

{code}

def run_tests() -> List[Dict[str, Any]]:
    results = []
    test_cases = {json.dumps(test_cases)}
    
    for i, test in enumerate(test_cases):
        try:
            # Get the function name from the first test case
            func_name = test["function"]
            func = globals()[func_name]
            
            # Run the test
            result = func(*test["args"])
            passed = result == test["expected"]
            
            results.append({{
                "test_id": i,
                "passed": passed,
                "expected": test["expected"],
                "got": result,
                "error": None
            }})
        except Exception as e:
            results.append({{
                "test_id": i,
                "passed": False,
                "expected": test["expected"],
                "got": None,
                "error": str(e)
            }})
    
    print(json.dumps(results))
    return results

if __name__ == "__main__":
    run_tests()
"""
        return test_code

    def validate_solution(self, solution: str, problem: Dict) -> Tuple[bool, str, Dict]:
        """
        Validate a solution against a problem's test cases
        Returns: (success, message, results)
        """
        return self.execute_code(solution, problem["test_cases"]) 

    async def validate_and_grade_solution(
        self, 
        solution: str, 
        problem: Dict,
        reference_solution: str = None
    ) -> Tuple[bool, str, Dict, GradingResult]:
        """
        Validate and grade a solution against a problem
        Returns: (success, message, test_results, grading_result)
        """
        return await self.execute_and_grade_code(
            code=solution,
            test_cases=problem["test_cases"],
            problem_description=problem.get("description", ""),
            language=problem.get("language", "python"),
            reference_solution=reference_solution
        ) 