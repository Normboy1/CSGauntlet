import React, { useState } from 'react';

interface GradingCriteria {
  correctness: number;
  efficiency: number;
  readability: number;
  style: number;
  innovation: number;
  total: number;
}

interface GradingResult {
  criteria: GradingCriteria;
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

interface TestResult {
  test_id: number;
  passed: boolean;
  expected: any;
  got: any;
  error?: string;
}

interface AIGradingResultsProps {
  gradingResult: GradingResult;
  testResults?: {
    passed: number;
    total: number;
    test_results: TestResult[];
  };
  submissionId?: string;
}

const AIGradingResults: React.FC<AIGradingResultsProps> = ({
  gradingResult,
  testResults,
  submissionId
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'detailed' | 'suggestions' | 'tests'>('overview');

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A+': case 'A': return 'text-green-400 bg-green-900/20';
      case 'B+': case 'B': return 'text-blue-400 bg-blue-900/20';
      case 'C+': case 'C': return 'text-yellow-400 bg-yellow-900/20';
      case 'D': return 'text-orange-400 bg-orange-900/20';
      case 'F': return 'text-red-400 bg-red-900/20';
      default: return 'text-gray-400 bg-gray-900/20';
    }
  };

  const getScoreColor = (score: number, maxScore: number) => {
    const percentage = (score / maxScore) * 100;
    if (percentage >= 90) return 'text-green-400';
    if (percentage >= 80) return 'text-blue-400';
    if (percentage >= 70) return 'text-yellow-400';
    if (percentage >= 60) return 'text-orange-400';
    return 'text-red-400';
  };

  const renderScoreBar = (score: number, maxScore: number, label: string) => {
    const percentage = (score / maxScore) * 100;
    const colorClass = getScoreColor(score, maxScore);
    
    return (
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-300">{label}</span>
          <span className={`text-sm font-bold ${colorClass}`}>
            {score.toFixed(1)}/{maxScore}
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              percentage >= 90 ? 'bg-green-500' :
              percentage >= 80 ? 'bg-blue-500' :
              percentage >= 70 ? 'bg-yellow-500' :
              percentage >= 60 ? 'bg-orange-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
      </div>
    );
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Overall Grade */}
      <div className="text-center">
        <div className={`inline-flex items-center px-6 py-3 rounded-lg text-2xl font-bold ${getGradeColor(gradingResult.overall_grade)}`}>
          {gradingResult.overall_grade}
        </div>
        <div className="mt-2 text-gray-400">
          Overall Grade • {gradingResult.criteria.total.toFixed(1)}/100 points
        </div>
        <div className="text-sm text-green-400 font-semibold">
          +{gradingResult.points_earned} points earned
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-blue-400">{gradingResult.rank_percentile.toFixed(0)}%</div>
          <div className="text-sm text-gray-400">Percentile Rank</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-400">{gradingResult.complexity_analysis}</div>
          <div className="text-sm text-gray-400">Time Complexity</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-purple-400">{gradingResult.memory_efficiency}</div>
          <div className="text-sm text-gray-400">Space Complexity</div>
        </div>
      </div>

      {/* Quick Feedback */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-3 text-white">Key Feedback</h3>
        <div className="space-y-2">
          {Object.entries(gradingResult.feedback).slice(0, 2).map(([category, feedback]) => (
            <div key={category} className="text-sm">
              <span className="font-medium text-blue-400 capitalize">{category}:</span>
              <span className="text-gray-300 ml-2">{feedback}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderDetailed = () => (
    <div className="space-y-6">
      {/* Score Breakdown */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">Score Breakdown</h3>
        {renderScoreBar(gradingResult.criteria.correctness, 40, 'Correctness (Test Cases)')}
        {renderScoreBar(gradingResult.criteria.efficiency, 25, 'Efficiency (Time & Space)')}
        {renderScoreBar(gradingResult.criteria.readability, 20, 'Readability (Code Clarity)')}
        {renderScoreBar(gradingResult.criteria.style, 10, 'Style (Conventions)')}
        {renderScoreBar(gradingResult.criteria.innovation, 5, 'Innovation (Creative Solutions)')}
      </div>

      {/* Detailed Feedback */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">Detailed Feedback</h3>
        <div className="space-y-4">
          {Object.entries(gradingResult.feedback).map(([category, feedback]) => (
            <div key={category} className="border-l-4 border-blue-500 pl-4">
              <h4 className="font-medium text-blue-400 capitalize mb-1">{category}</h4>
              <p className="text-gray-300 text-sm">{feedback}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Code Quality Analysis */}
      {(gradingResult.best_practices.length > 0 || gradingResult.code_smells.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {gradingResult.best_practices.length > 0 && (
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
              <h4 className="font-semibold text-green-400 mb-3 flex items-center">
                <span className="mr-2">✓</span>
                Best Practices
              </h4>
              <ul className="space-y-1">
                {gradingResult.best_practices.map((practice, index) => (
                  <li key={index} className="text-sm text-green-300">{practice}</li>
                ))}
              </ul>
            </div>
          )}
          
          {gradingResult.code_smells.length > 0 && (
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
              <h4 className="font-semibold text-red-400 mb-3 flex items-center">
                <span className="mr-2">⚠</span>
                Code Smells
              </h4>
              <ul className="space-y-1">
                {gradingResult.code_smells.map((smell, index) => (
                  <li key={index} className="text-sm text-red-300">{smell}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderSuggestions = () => (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">AI Suggestions for Improvement</h3>
        {gradingResult.suggestions.length > 0 ? (
          <div className="space-y-3">
            {gradingResult.suggestions.map((suggestion, index) => (
              <div key={index} className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold text-white">
                  {index + 1}
                </div>
                <p className="text-gray-300 text-sm flex-1">{suggestion}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 italic">Great job! No specific suggestions at this time.</p>
        )}
      </div>

      {/* Learning Resources */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">Recommended Learning</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="font-medium text-blue-400 mb-2">Algorithm Complexity</h4>
            <p className="text-sm text-gray-300">Learn about Big O notation and optimizing algorithm performance.</p>
          </div>
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="font-medium text-green-400 mb-2">Code Style</h4>
            <p className="text-sm text-gray-300">Master language-specific conventions and clean code principles.</p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTests = () => (
    <div className="space-y-6">
      {testResults && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4 text-white">Test Results</h3>
          <div className="mb-4">
            <div className={`text-lg font-bold ${testResults.passed === testResults.total ? 'text-green-400' : 'text-yellow-400'}`}>
              {testResults.passed} / {testResults.total} tests passed
            </div>
          </div>
          
          <div className="space-y-3">
            {testResults.test_results.map((test, index) => (
              <div key={index} className={`border rounded-lg p-4 ${test.passed ? 'border-green-500/30 bg-green-900/10' : 'border-red-500/30 bg-red-900/10'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">Test {test.test_id + 1}</span>
                  <span className={`px-2 py-1 rounded text-sm font-medium ${test.passed ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                    {test.passed ? 'PASS' : 'FAIL'}
                  </span>
                </div>
                
                <div className="text-sm space-y-1">
                  <div>
                    <span className="text-gray-400">Expected:</span>
                    <span className="text-green-300 ml-2 font-mono">{JSON.stringify(test.expected)}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Got:</span>
                    <span className={`ml-2 font-mono ${test.passed ? 'text-green-300' : 'text-red-300'}`}>
                      {JSON.stringify(test.got)}
                    </span>
                  </div>
                  {test.error && (
                    <div>
                      <span className="text-gray-400">Error:</span>
                      <span className="text-red-300 ml-2 font-mono">{test.error}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto bg-gray-900 text-white rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 px-6 py-4 border-b border-gray-700">
        <h2 className="text-xl font-bold text-white">AI Code Analysis</h2>
        {submissionId && (
          <p className="text-sm text-gray-400">Submission ID: {submissionId}</p>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-8 px-6">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'detailed', label: 'Detailed', icon: '🔍' },
            { id: 'suggestions', label: 'Suggestions', icon: '💡' },
            ...(testResults ? [{ id: 'tests', label: 'Tests', icon: '🧪' }] : [])
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'detailed' && renderDetailed()}
        {activeTab === 'suggestions' && renderSuggestions()}
        {activeTab === 'tests' && renderTests()}
      </div>
    </div>
  );
};

export default AIGradingResults; 