import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface GradingCriteria {
  correctness: number;
  efficiency: number;
  readability: number;
  style: number;
  innovation: number;
}

interface AIGradingResult {
  overall_grade: string;
  total_score: number;
  criteria: GradingCriteria;
  feedback: Record<string, string>;
  suggestions: string[];
  execution_time?: number;
}

interface AIGradingResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  gradingResult: AIGradingResult;
  round: number;
  yourScore: number;
}

const AIGradingResultsModal: React.FC<AIGradingResultsModalProps> = ({
  isOpen,
  onClose,
  gradingResult,
  round,
  yourScore
}) => {
  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A+':
      case 'A':
        return 'text-green-400';
      case 'B+':
      case 'B':
        return 'text-blue-400';
      case 'C+':
      case 'C':
        return 'text-yellow-400';
      case 'D':
        return 'text-orange-400';
      case 'F':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 80) return 'text-blue-400';
    if (score >= 70) return 'text-yellow-400';
    if (score >= 60) return 'text-orange-400';
    return 'text-red-400';
  };

  const criteriaItems = [
    { key: 'correctness', label: 'Correctness', max: 40, icon: CheckCircleIcon },
    { key: 'efficiency', label: 'Efficiency', max: 25, icon: ExclamationTriangleIcon },
    { key: 'readability', label: 'Readability', max: 20, icon: CheckCircleIcon },
    { key: 'style', label: 'Code Style', max: 10, icon: CheckCircleIcon },
    { key: 'innovation', label: 'Innovation', max: 5, icon: CheckCircleIcon }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black bg-opacity-75"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-gray-800 rounded-lg shadow-2xl"
          >
            {/* Header */}
            <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-6 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">AI Grading Results</h2>
                <p className="text-gray-400">Round {round} • Powered by Ollama</p>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Overall Score */}
              <div className="bg-gray-900 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-semibold text-white">Overall Assessment</h3>
                  <div className="text-right">
                    <div className={`text-3xl font-bold ${getGradeColor(gradingResult.overall_grade)}`}>
                      {gradingResult.overall_grade}
                    </div>
                    <div className={`text-lg ${getScoreColor(gradingResult.total_score)}`}>
                      {gradingResult.total_score.toFixed(1)}/100
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-sm text-gray-400 mb-1">Your Total Score</div>
                    <div className="text-2xl font-bold text-indigo-400">{yourScore}</div>
                  </div>
                  {gradingResult.execution_time && (
                    <div className="bg-gray-800 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-1">Grading Time</div>
                      <div className="text-2xl font-bold text-green-400">
                        {gradingResult.execution_time.toFixed(2)}s
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Detailed Criteria */}
              <div className="bg-gray-900 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-white mb-4">Detailed Breakdown</h3>
                <div className="space-y-4">
                  {criteriaItems.map(({ key, label, max, icon: Icon }) => {
                    const score = gradingResult.criteria[key as keyof GradingCriteria];
                    const percentage = (score / max) * 100;
                    
                    return (
                      <div key={key} className="bg-gray-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <Icon className="w-5 h-5 text-indigo-400" />
                            <span className="font-medium text-white">{label}</span>
                          </div>
                          <span className={`font-bold ${getScoreColor(percentage)}`}>
                            {score.toFixed(1)}/{max}
                          </span>
                        </div>
                        
                        {/* Progress Bar */}
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.8, delay: 0.2 }}
                            className={`h-2 rounded-full ${
                              percentage >= 90 ? 'bg-green-500' :
                              percentage >= 80 ? 'bg-blue-500' :
                              percentage >= 70 ? 'bg-yellow-500' :
                              percentage >= 60 ? 'bg-orange-500' : 'bg-red-500'
                            }`}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Feedback */}
              <div className="bg-gray-900 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-white mb-4">AI Feedback</h3>
                <div className="space-y-3">
                  {Object.entries(gradingResult.feedback).map(([category, feedback]) => (
                    <div key={category} className="bg-gray-800 rounded-lg p-4">
                      <div className="font-medium text-indigo-400 capitalize mb-2">
                        {category.replace('_', ' ')}
                      </div>
                      <p className="text-gray-300">{feedback}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suggestions */}
              {gradingResult.suggestions && gradingResult.suggestions.length > 0 && (
                <div className="bg-gray-900 rounded-lg p-6">
                  <h3 className="text-xl font-semibold text-white mb-4">Suggestions for Improvement</h3>
                  <div className="space-y-2">
                    {gradingResult.suggestions.map((suggestion, index) => (
                      <div key={index} className="flex items-start space-x-3">
                        <div className="w-2 h-2 bg-indigo-400 rounded-full mt-2 flex-shrink-0" />
                        <p className="text-gray-300">{suggestion}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Close Button */}
              <div className="flex justify-end">
                <button
                  onClick={onClose}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  Continue Game
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default AIGradingResultsModal;
