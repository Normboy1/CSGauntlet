import logging
import os
import json
import time
import ast
import re
import asyncio
import aiohttp
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class GradingCriteria:
    """Criteria for evaluating code solutions"""
    correctness: float = 0.0  # 0-40 points
    efficiency: float = 0.0   # 0-25 points
    readability: float = 0.0  # 0-20 points
    style: float = 0.0        # 0-10 points
    innovation: float = 0.0   # 0-5 points
    total: float = 0.0

@dataclass
class GradingResult:
    """Result of AI grading with detailed feedback"""
    criteria: GradingCriteria
    feedback: Dict[str, str]
    suggestions: List[str]
    execution_time: float
    memory_efficiency: str
    complexity_analysis: str
    code_smells: List[str]
    best_practices: List[str]
    overall_grade: str  # A+, A, B+, B, C+, C, D, F
    rank_percentile: float  # 0-100

class AICodeGrader:
    """Advanced AI-powered code grading system with Ollama support"""
    
    def __init__(self, ai_provider: str = "ollama", ollama_url: str = "http://localhost:11434", 
                 ollama_model: str = "codellama:7b", openai_api_key: str = None, openai_model: str = "gpt-4"):
        self.ai_provider = ai_provider.lower()
        
        # Ollama configuration
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        
        # OpenAI configuration (fallback)
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.openai_client = None
        
        # Initialize based on provider
        if self.ai_provider == "ollama":
            logger.info(f"Initializing AI Grader with Ollama: {ollama_model} at {ollama_url}")
        elif self.ai_provider == "openai" and openai_api_key:
            logger.info(f"Initializing AI Grader with OpenAI: {openai_model}")
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.error("OpenAI library not installed. Install with: pip install openai")
                self.ai_provider = "fallback"
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.ai_provider = "fallback"
        else:
            logger.info("Using fallback analysis (no AI provider configured)")
            self.ai_provider = "fallback"
        
        # Grade thresholds
        self.grade_thresholds = {
            'A+': 95, 'A': 90, 'B+': 85, 'B': 80,
            'C+': 75, 'C': 70, 'D': 60, 'F': 0
        }
        
        # Common code quality patterns
        self.quality_patterns = {
            'good': [
                r'def\s+\w+\([^)]*\):',  # Proper function definition
                r'""".*?"""',            # Docstrings
                r'#\s+\w+',             # Comments
                r'if\s+__name__\s*==\s*["\']__main__["\']:',  # Main guard
            ],
            'bad': [
                r'eval\(',              # Dangerous eval
                r'exec\(',              # Dangerous exec
                r'global\s+\w+',        # Global variables
                r'[a-z]+[A-Z]',         # camelCase (prefer snake_case)
            ]
        }

    async def grade_solution(
        self, 
        problem_description: str,
        solution_code: str,
        test_results: Dict,
        language: str = "python",
        reference_solution: Optional[str] = None
    ) -> GradingResult:
        """Grade a coding solution comprehensively"""
        
        start_time = time.time()
        
        # 1. Analyze correctness based on test results
        correctness_score = self._analyze_correctness(test_results)
        
        # 2. Analyze code quality with AI
        quality_analysis = await self._analyze_code_quality(
            problem_description, solution_code, language
        )
        
        # 3. Analyze efficiency
        efficiency_analysis = self._analyze_efficiency(solution_code, language)
        
        # 4. Compare with reference solution if available
        comparative_analysis = None
        if reference_solution:
            comparative_analysis = await self._compare_solutions(
                problem_description, solution_code, reference_solution
            )
        
        # 5. Calculate final scores
        criteria = self._calculate_scores(
            correctness_score,
            quality_analysis,
            efficiency_analysis,
            comparative_analysis
        )
        
        # 6. Generate comprehensive feedback
        feedback = await self._generate_feedback(
            problem_description,
            solution_code,
            criteria,
            quality_analysis,
            efficiency_analysis
        )
        
        # 7. Calculate overall grade and rank
        overall_grade = self._calculate_grade(criteria.total)
        rank_percentile = self._calculate_percentile(criteria.total)
        
        execution_time = time.perf_counter() - start_time
        
        return GradingResult(
            criteria=criteria,
            feedback=feedback,
            suggestions=quality_analysis.get('suggestions', []),
            execution_time=execution_time,
            memory_efficiency=efficiency_analysis.get('memory', 'Unknown'),
            complexity_analysis=efficiency_analysis.get('complexity', 'Unknown'),
            code_smells=quality_analysis.get('code_smells', []),
            best_practices=quality_analysis.get('best_practices', []),
            overall_grade=overall_grade,
            rank_percentile=rank_percentile
        )

    def _analyze_correctness(self, test_results: Dict) -> float:
        """Analyze correctness based on test results (0-40 points)"""
        if not test_results:
            return 0.0
        
        passed = test_results.get('passed', 0)
        total = test_results.get('total', 1)
        
        if total == 0:
            return 0.0
        
        # Base score from pass rate
        pass_rate = passed / total
        base_score = pass_rate * 35  # Up to 35 points for all tests passing
        
        # Bonus points for edge cases or complex test scenarios
        if pass_rate == 1.0:
            base_score += 5  # Perfect score bonus
        
        return min(40.0, base_score)

    async def _analyze_code_quality(self, problem: str, code: str, language: str) -> Dict:
        """Use AI to analyze code quality and style"""
        prompt = f"""
        Analyze this {language} code solution for a programming problem. Provide a comprehensive quality assessment.

        Problem: {problem}

        Code:
        ```{language}
        {code}
        ```

        Evaluate the code on these criteria and provide scores (0-100):
        1. Readability (variable names, structure, clarity)
        2. Code style (follows language conventions)
        3. Innovation (creative or elegant approaches)
        4. Maintainability (easy to modify and extend)

        Also identify:
        - Code smells (bad practices)
        - Best practices followed
        - Specific suggestions for improvement

        Return your analysis as a JSON object with these keys:
        - readability_score
        - style_score
        - innovation_score
        - maintainability_score
        - code_smells (array of strings)
        - best_practices (array of strings)
        - suggestions (array of strings)
        """

        try:
            if self.ai_provider == "ollama":
                content = await self._query_ollama(prompt, f"You are an expert {language} code reviewer and computer science educator. Provide detailed, constructive feedback.")
            elif self.ai_provider == "openai":
                content = await self._query_openai(prompt, f"You are an expert {language} code reviewer and computer science educator. Provide detailed, constructive feedback.")
            else:
                # Fallback to heuristic analysis
                return self._fallback_quality_analysis(code, language)
            
            # Try to parse JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback parsing if AI doesn't return valid JSON
                return self._parse_ai_response(content)
                
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._fallback_quality_analysis(code, language)

    def _analyze_efficiency(self, code: str, language: str) -> Dict:
        """Analyze code efficiency and complexity"""
        analysis = {
            'complexity': 'O(n)',  # Default
            'memory': 'O(1)',      # Default
            'efficiency_score': 70  # Default
        }
        
        if language.lower() == 'python':
            analysis.update(self._analyze_python_efficiency(code))
        
        return analysis

    def _analyze_python_efficiency(self, code: str) -> Dict:
        """Specific efficiency analysis for Python code"""
        try:
            tree = ast.parse(code)
            
            # Count nested loops
            nested_loops = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    nested_loops += 1
            
            # Detect common inefficient patterns
            inefficient_patterns = []
            if 'list(' in code and 'range(' in code:
                inefficient_patterns.append("Consider using range() directly instead of list(range())")
            
            if nested_loops > 2:
                complexity = f"O(n^{nested_loops})"
                efficiency_score = max(30, 80 - (nested_loops - 1) * 15)
            elif nested_loops == 2:
                complexity = "O(n^2)"
                efficiency_score = 65
            elif nested_loops == 1:
                complexity = "O(n)"
                efficiency_score = 80
            else:
                complexity = "O(1)"
                efficiency_score = 90
            
            # Check for space complexity indicators
            if '.append(' in code or '+=' in code:
                memory = "O(n)"
            elif 'dict(' in code or 'set(' in code:
                memory = "O(n)"
            else:
                memory = "O(1)"
            
            return {
                'complexity': complexity,
                'memory': memory,
                'efficiency_score': efficiency_score,
                'inefficient_patterns': inefficient_patterns
            }
            
        except Exception:
            return {
                'complexity': 'Unable to analyze',
                'memory': 'Unable to analyze',
                'efficiency_score': 60
            }

    async def _compare_solutions(self, problem: str, solution: str, reference: str) -> Dict:
        """Compare solution with reference implementation"""
        prompt = f"""
        Compare these two solutions to the same problem:

        Problem: {problem}

        Solution 1 (User's):
        {solution}

        Solution 2 (Reference):
        {reference}

        Provide a comparison focusing on:
        1. Which approach is better and why
        2. Efficiency differences
        3. Readability differences
        4. Alternative approaches used

        Rate the user's solution compared to the reference (0-100).
        """

        try:
            if self.ai_provider == "ollama":
                content = await self._query_ollama(prompt, "You are a computer science professor comparing student solutions.")
            else:
                response = await self.openai_client.ChatCompletion.acreate(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a computer science professor comparing student solutions."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                content = response.choices[0].message.content
            
            # Extract comparison score (basic implementation)
            score_match = re.search(r'(\d+)(?:/100|\%)', content)
            comparative_score = int(score_match.group(1)) if score_match else 75
            
            return {
                'comparative_score': comparative_score,
                'comparison_notes': content
            }
            
        except Exception as e:
            logger.error(f"Error during solution comparison: {e}")
            return {'comparative_score': 75, 'comparison_notes': 'Unable to compare due to error'}

    def _calculate_scores(
        self, 
        correctness: float, 
        quality: Dict, 
        efficiency: Dict, 
        comparison: Optional[Dict]
    ) -> GradingCriteria:
        """Calculate final scores for all criteria"""
        
        # Correctness (0-40 points)
        correctness_score = correctness
        
        # Efficiency (0-25 points)
        efficiency_score = (efficiency.get('efficiency_score', 70) / 100) * 25
        
        # Readability (0-20 points)
        readability_score = (quality.get('readability_score', 70) / 100) * 20
        
        # Style (0-10 points)
        style_score = (quality.get('style_score', 70) / 100) * 10
        
        # Innovation (0-5 points)
        innovation_score = (quality.get('innovation_score', 50) / 100) * 5
        
        # Apply comparison bonus if available
        if comparison:
            comparative_bonus = (comparison.get('comparative_score', 75) - 75) / 25 * 3
            efficiency_score += max(-5, min(5, comparative_bonus))
        
        total = correctness_score + efficiency_score + readability_score + style_score + innovation_score
        
        return GradingCriteria(
            correctness=round(correctness_score, 1),
            efficiency=round(efficiency_score, 1),
            readability=round(readability_score, 1),
            style=round(style_score, 1),
            innovation=round(innovation_score, 1),
            total=round(min(100, total), 1)
        )

    async def _generate_feedback(
        self, 
        problem: str, 
        code: str, 
        criteria: GradingCriteria,
        quality: Dict,
        efficiency: Dict
    ) -> Dict[str, str]:
        """Generate detailed feedback for each category"""
        
        feedback = {}
        
        # Correctness feedback
        if criteria.correctness >= 35:
            feedback['correctness'] = "Excellent! Your solution correctly handles all test cases."
        elif criteria.correctness >= 25:
            feedback['correctness'] = "Good work! Your solution handles most test cases with minor issues."
        elif criteria.correctness >= 15:
            feedback['correctness'] = "Your solution has the right idea but fails some test cases. Check edge cases."
        else:
            feedback['correctness'] = "Your solution has significant correctness issues. Review the problem requirements."
        
        # Efficiency feedback
        if criteria.efficiency >= 20:
            feedback['efficiency'] = f"Great efficiency! Time complexity: {efficiency.get('complexity', 'Good')}"
        elif criteria.efficiency >= 15:
            feedback['efficiency'] = f"Good efficiency. Time complexity: {efficiency.get('complexity', 'Acceptable')}"
        else:
            feedback['efficiency'] = f"Consider optimizing your solution. Time complexity: {efficiency.get('complexity', 'Could be improved')}"
        
        # Readability feedback
        if criteria.readability >= 16:
            feedback['readability'] = "Excellent code readability! Clear variable names and structure."
        elif criteria.readability >= 12:
            feedback['readability'] = "Good readability with room for minor improvements."
        else:
            feedback['readability'] = "Consider improving variable names and code structure for better readability."
        
        # Style feedback
        if criteria.style >= 8:
            feedback['style'] = "Great adherence to coding style conventions!"
        elif criteria.style >= 6:
            feedback['style'] = "Good style with minor convention issues."
        else:
            feedback['style'] = "Review language-specific style conventions for improvement."
        
        return feedback

    def _calculate_grade(self, total_score: float) -> str:
        """Calculate letter grade from total score"""
        for grade, threshold in self.grade_thresholds.items():
            if total_score >= threshold:
                return grade
        return 'F'

    def _calculate_percentile(self, total_score: float) -> float:
        """Calculate percentile ranking (simulated)"""
        # This would normally be based on historical data
        # For now, we'll use a simple calculation
        return min(100, max(0, total_score))

    def _parse_ai_response(self, content: str) -> Dict:
        """Fallback parser for non-JSON AI responses"""
        # Basic regex parsing for scores
        scores = {}
        
        patterns = {
            'readability_score': r'readability.*?(\d+)',
            'style_score': r'style.*?(\d+)', 
            'innovation_score': r'innovation.*?(\d+)',
            'maintainability_score': r'maintainability.*?(\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content.lower())
            scores[key] = int(match.group(1)) if match else 70
        
        return scores

    def _fallback_quality_analysis(self, code: str, language: str) -> Dict:
        """Fallback analysis when AI is unavailable"""
        # Basic heuristic analysis
        lines = code.split('\n')
        
        readability_score = 70
        style_score = 70
        
        # Simple readability checks
        if any('def ' in line for line in lines):
            readability_score += 10
        if any('#' in line for line in lines):
            readability_score += 5
        
        # Simple style checks
        if language.lower() == 'python':
            if any('_' in line for line in lines):  # snake_case
                style_score += 10
            if not any(re.search(r'[a-z][A-Z]', line) for line in lines):  # no camelCase
                style_score += 5
        
        return {
            'readability_score': min(100, readability_score),
            'style_score': min(100, style_score),
            'innovation_score': 50,
            'maintainability_score': 60,
            'code_smells': [],
            'best_practices': [],
            'suggestions': ['Consider adding more comments for clarity']
        }

    async def _query_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """Query Ollama API for AI responses"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.ollama_model,
                    "prompt": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 1500
                    }
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", 
                                       json=payload, 
                                       timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', '')
                    else:
                        logger.error(f"Ollama API error: {response.status}")
                        return ""
                        
        except asyncio.TimeoutError:
            logger.error("Ollama API timeout")
            return ""
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return ""
    
    async def check_ollama_health(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", 
                                     timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def _query_openai(self, prompt: str, system_prompt: str = "") -> str:
        """Query OpenAI API for AI responses"""
        if not self.openai_client:
            logger.error("OpenAI client not initialized")
            return ""
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error querying OpenAI: {e}")
            return ""

# Usage example
if __name__ == "__main__":
    # This part is for demonstration and testing the grader in isolation
    # In a real Flask app, the grader would be instantiated with app.config values
    # and its async methods would be awaited within an async context.
    
    # Example problem and solution
    sample_problem_description = "Write a Python function to reverse a string."
    sample_solution_code = """def reverse_string(s):
    return s[::-1]
"""
    sample_test_results = {"passed": 3, "total": 3, "test_results": []}
    
    async def run_grading_example():
        # Try Ollama first, fallback to OpenAI if available
        grader = AICodeGrader(
            ai_provider="ollama",
            ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            ollama_model=os.getenv('OLLAMA_MODEL', 'codellama:7b'),
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Check if Ollama is available
        if grader.ai_provider == "ollama":
            ollama_available = await grader.check_ollama_health()
            if not ollama_available:
                logger.warning("Ollama not available, using fallback analysis")
        
        grading_result = await grader.grade_solution(
            problem_description=sample_problem_description,
            solution_code=sample_solution_code,
            test_results=sample_test_results
        )
        
        print("\n--- Grading Result ---")
        print(f"Overall Grade: {grading_result.overall_grade}")
        print(f"Total Score: {grading_result.criteria.total}")
        print(f"Feedback: {grading_result.feedback}")
        print(f"Suggestions: {grading_result.suggestions}")
        print(f"Execution Time: {grading_result.execution_time:.4f} seconds")

    # To run the async example
    try:
        asyncio.run(run_grading_example())
    except Exception as e:
        logger.error(f"Error running grading example: {e}") 