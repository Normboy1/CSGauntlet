import React, { useState, useRef } from 'react';
import AIGradingResults from './AIGradingResults';
import PrismCodeHighlighter from './PrismCodeHighlighter';

interface TestResult {
  test_id: number;
  passed: boolean;
  expected: any;
  got: any;
  error?: string;
}

interface Problem {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  example: string;
  constraints: string;
  max_points: number;
  time_limit: number;
}

interface TestResults {
  passed: number;
  total: number;
  test_results: TestResult[];
}

interface GradingResultType {
  criteria: {
    correctness: number;
    efficiency: number;
    readability: number;
    style: number;
    innovation: number;
    total: number;
  };
  feedback: Record<string, string>;
  suggestions: string[];
  code_smells: string[];
  best_practices: string[];
  overall_grade: string;
  rank_percentile: number;
  complexity_analysis: string;
  memory_efficiency: string;
  points_earned: number;
}

interface EnhancedCodeEditorProps {
  problem: Problem;
  onSubmission?: (result: any) => void;
}

const EnhancedCodeEditor: React.FC<EnhancedCodeEditorProps> = ({
  problem,
  onSubmission
}) => {
  const [code, setCode] = useState(`def ${problem.id.replace('-', '_')}():
    # Write your solution here
    pass`);
  const [showEditor, setShowEditor] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [gradingResult, setGradingResult] = useState<GradingResultType | null>(null);
  const [testResults, setTestResults] = useState<TestResults | null>(null);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [language, setLanguage] = useState('python');
  const [showResults, setShowResults] = useState(false);
  const [timeLeft, setTimeLeft] = useState(problem.time_limit);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Timer functionality
  const startTimer = () => {
    if (timerRef.current) return; // Already running
    
    setIsTimerRunning(true);
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          stopTimer();
          handleAutoSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsTimerRunning(false);
  };

  const handleAutoSubmit = () => {
    if (code.trim()) {
      alert('Time\'s up! Auto-submitting your current solution.');
      handleSubmit();
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'text-green-400 bg-green-900/20';
      case 'medium': return 'text-yellow-400 bg-yellow-900/20';
      case 'hard': return 'text-red-400 bg-red-900/20';
      default: return 'text-gray-400 bg-gray-900/20';
    }
  };

  const handleRunCode = async () => {
    if (!code.trim()) {
      alert('Please write some code first!');
      return;
    }

    setIsRunning(true);
    
    try {
      // This would call a simpler endpoint just to run tests without AI grading
      const response = await fetch('/api/code/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          code,
          problem_id: problem.id,
          language
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setTestResults(result.test_results);
        alert(`Tests completed! ${result.test_results.passed}/${result.test_results.total} passed.`);
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (error) {
      alert('Failed to run code. Please try again.');
      console.error('Run error:', error);
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = async () => {
    if (!code.trim()) {
      alert('Please write some code first!');
      return;
    }

    if (!isTimerRunning && timeLeft === problem.time_limit) {
      startTimer();
    }

    setIsSubmitting(true);
    setShowResults(false);

    try {
      const response = await fetch('/api/code/submit_with_grading', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          code,
          problem_id: problem.id,
          language
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setGradingResult(result.grading);
        setTestResults(result.test_results);
        setSubmissionId(result.submission_id);
        setShowResults(true);
        stopTimer();
        
        if (onSubmission) {
          onSubmission(result);
        }
      } else {
        alert(`Submission failed: ${result.error}`);
      }
    } catch (error) {
      alert('Failed to submit code. Please try again.');
      console.error('Submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCode(e.target.value);
    
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const insertTemplate = () => {
    const templates = {
      python: `def ${problem.id.replace('-', '_')}():\n    """\n    ${problem.description}\n    """\n    # Write your solution here\n    pass`,
      javascript: `function ${problem.id.replace('-', '_')}() {\n    // ${problem.description}\n    // Write your solution here\n}`,
      java: `public class Solution {\n    public int ${problem.id.replace('-', '_')}() {\n        // ${problem.description}\n        // Write your solution here\n        return 0;\n    }\n}`
    };
    
    setCode(templates[language as keyof typeof templates] || templates.python);
  };

  React.useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-6 bg-gray-900 text-white">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Problem Description */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-lg p-6 sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">{problem.title}</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getDifficultyColor(problem.difficulty)}`}>
                {problem.difficulty.toUpperCase()}
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-2 text-blue-400">Description</h3>
                <p className="text-gray-300 text-sm leading-relaxed">{problem.description}</p>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2 text-green-400">Example</h3>
                <pre className="bg-gray-900 p-3 rounded text-sm text-green-300 whitespace-pre-wrap">
                  {problem.example}
                </pre>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2 text-yellow-400">Constraints</h3>
                <p className="text-gray-300 text-sm">{problem.constraints}</p>
              </div>

              <div className="pt-4 border-t border-gray-700">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Max Points:</span>
                  <span className="font-bold text-purple-400">{problem.max_points}</span>
                </div>
                <div className="flex justify-between items-center mt-2">
                  <span className="text-sm text-gray-400">Time Limit:</span>
                  <span className={`font-bold font-mono ${timeLeft < 60 ? 'text-red-400' : timeLeft < 300 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {formatTime(timeLeft)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Code Editor */}
        <div className="lg:col-span-2">
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            {/* Editor Header */}
            <div className="bg-gray-700 px-4 py-3 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <h3 className="font-semibold text-white">Code Editor</h3>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="bg-gray-600 text-white px-3 py-1 rounded text-sm"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                </select>
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={insertTemplate}
                  className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm transition-colors"
                >
                  Template
                </button>
                {isTimerRunning && (
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                    <span className="text-sm text-red-400">Timer Active</span>
                  </div>
                )}
              </div>
            </div>

            {/* Code Editor Toggle */}
            <div className="bg-gray-800 px-4 py-2 flex justify-end">
              <button
                onClick={() => setShowEditor(!showEditor)}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors"
              >
                {showEditor ? 'View Highlighted' : 'Edit Code'}
              </button>
            </div>

            {/* Code Textarea / Syntax Highlighter */}
            <div className="relative">
              {showEditor ? (
                <textarea
                  ref={textareaRef}
                  value={code}
                  onChange={handleCodeChange}
                  className="w-full h-80 bg-gray-900 text-green-400 p-4 font-mono text-sm resize-none border-none outline-none"
                  placeholder="Write your solution here..."
                  spellCheck={false}
                />
              ) : (
                <div className="w-full h-80 overflow-auto">
                  <PrismCodeHighlighter 
                    code={code} 
                    language={language} 
                    className="h-full min-h-full"
                  />
                </div>
              )}
            </div>

            {/* Editor Footer */}
            <div className="bg-gray-700 px-4 py-3 flex items-center justify-between">
              <div className="text-sm text-gray-400">
                Lines: {code.split('\n').length} | Characters: {code.length}
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={handleRunCode}
                  disabled={isRunning || isSubmitting}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium transition-colors flex items-center space-x-2"
                >
                  {isRunning ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Running...</span>
                    </>
                  ) : (
                    <>
                      <span>▶</span>
                      <span>Run Tests</span>
                    </>
                  )}
                </button>
                
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || isRunning}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium transition-colors flex items-center space-x-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <span>📤</span>
                      <span>Submit & Grade</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Test Results Preview */}
          {testResults && !showResults && (
            <div className="mt-4 bg-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-2 text-white">Quick Test Results</h3>
              <div className={`text-lg font-bold ${testResults.passed === testResults.total ? 'text-green-400' : 'text-yellow-400'}`}>
                {testResults.passed} / {testResults.total} tests passed
              </div>
              <p className="text-sm text-gray-400 mt-1">
                Submit your solution to get detailed AI grading and feedback!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* AI Grading Results */}
      {showResults && gradingResult && (
        <div className="mt-8">
          <AIGradingResults
            gradingResult={gradingResult}
            testResults={testResults || undefined}
            submissionId={submissionId || undefined}
          />
        </div>
      )}
    </div>
  );
};

export default EnhancedCodeEditor; 