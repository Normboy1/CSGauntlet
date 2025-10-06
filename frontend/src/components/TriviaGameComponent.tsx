import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import ChatComponent from './ChatComponent';

interface TriviaQuestion {
  id: string;
  question: string;
  options: string[];
  correctAnswer: number;
  difficulty: 'easy' | 'medium' | 'hard';
  category: 'algorithms' | 'data-structures' | 'programming-concepts' | 'cs-theory' | 'debugging';
  explanation: string;
  points: number;
}

interface Player {
  id: string;
  username: string;
  score: number;
  correctAnswers: number;
  averageTime: number;
  college?: string;
}

interface TriviaGameProps {
  gameId: string;
  opponent: Player | null;
  onGameComplete: (result: { winner: string; finalScores: { [key: string]: number }; additionalStats?: Record<string, any> }) => void;
}

const TriviaGameComponent: React.FC<TriviaGameProps> = ({ gameId, opponent, onGameComplete }) => {
  const { user } = useAuth();
  const [currentQuestion, setCurrentQuestion] = useState<TriviaQuestion | null>(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [isCorrect, setIsCorrect] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30);
  const [gameStarted, setGameStarted] = useState(false);
  const [gameComplete, setGameComplete] = useState(false);
  const [player, setPlayer] = useState<Player>({
    id: user?.id || '',
    username: user?.username || '',
    score: 0,
    correctAnswers: 0,
    averageTime: 0
  });
  const [opponentData, setOpponentData] = useState<Player | null>(opponent);
  const [questions, setQuestions] = useState<TriviaQuestion[]>([]);
  const [questionStartTime, setQuestionStartTime] = useState<number>(0);
  const [lifelines, setLifelines] = useState({
    fiftyFifty: true,
    skipQuestion: true,
    extraTime: true
  });
  const [streak, setStreak] = useState(0);
  const [maxStreak, setMaxStreak] = useState(0);
  const [roundTime, setRoundTime] = useState(0);
  const [isChatMinimized, setIsChatMinimized] = useState(true);
  const [showChat, setShowChat] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Trivia questions will be loaded from backend
  const [triviaQuestions, setTriviaQuestions] = useState<TriviaQuestion[]>([]);

  // Fetch trivia questions from backend
  const fetchTriviaQuestions = async () => {
    try {
      const response = await fetch('/api/game/trivia/questions');
      const data = await response.json();
      if (data.success) {
        setTriviaQuestions(data.questions);
      }
    } catch (error) {
      console.error('Failed to fetch trivia questions:', error);
      // Fallback to default questions if fetch fails
      setTriviaQuestions([
        {
          id: '1',
          question: 'What is the time complexity of binary search?',
          options: ['O(n)', 'O(log n)', 'O(n log n)', 'O(n²)'],
          correctAnswer: 1,
          difficulty: 'easy',
          category: 'algorithms',
          explanation: 'Binary search eliminates half of the search space in each iteration.',
          points: 10
        }
      ]);
    }
  };

  useEffect(() => {
    initializeGame();
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (gameStarted && !gameComplete) {
      startTimer();
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [gameStarted, currentQuestion]);

  const initializeGame = async () => {
    await fetchTriviaQuestions();
  };

  useEffect(() => {
    if (triviaQuestions.length > 0) {
      // Shuffle questions and select all available for the game
      const shuffledQuestions = [...triviaQuestions].sort(() => Math.random() - 0.5);
      setQuestions(shuffledQuestions);
      setCurrentQuestion(shuffledQuestions[0]);
      setQuestionStartTime(Date.now());
      setGameStarted(true);
    }
  }, [triviaQuestions]);

  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    setTimeLeft(30);
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          handleTimeUp();
          return 0;
        }
        return prev - 1;
      });
      setRoundTime(prev => prev + 1);
    }, 1000);
  };

  const handleTimeUp = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    setStreak(0);
    handleAnswer(null);
  };

  const handleAnswer = (answerIndex: number | null) => {
    if (showResult || !currentQuestion) return;

    const responseTime = Date.now() - questionStartTime;
    const correct = answerIndex === currentQuestion.correctAnswer;
    
    setSelectedAnswer(answerIndex);
    setIsCorrect(correct);
    setShowResult(true);

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    if (correct) {
      const timeBonus = Math.max(0, Math.floor((30 - (30 - timeLeft)) / 5));
      const streakBonus = Math.floor(streak * 2);
      const totalPoints = currentQuestion.points + timeBonus + streakBonus;
      
      setPlayer(prev => ({
        ...prev,
        score: prev.score + totalPoints,
        correctAnswers: prev.correctAnswers + 1,
        averageTime: (prev.averageTime * questionIndex + responseTime) / (questionIndex + 1)
      }));
      
      const newStreak = streak + 1;
      setStreak(newStreak);
      setMaxStreak(Math.max(maxStreak, newStreak));
    } else {
      setStreak(0);
    }

    // Show result for 3 seconds, then next question
    setTimeout(() => {
      nextQuestion();
    }, 3000);
  };

  const nextQuestion = () => {
    const nextIndex = questionIndex + 1;
    
    if (nextIndex >= questions.length) {
      endGame();
      return;
    }

    setQuestionIndex(nextIndex);
    setCurrentQuestion(questions[nextIndex]);
    setSelectedAnswer(null);
    setShowResult(false);
    setQuestionStartTime(Date.now());
    startTimer();
  };

  const endGame = () => {
    setGameComplete(true);
    setGameStarted(false);
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    const finalScores = {
      [player.id]: player.score,
      [opponentData?.id || 'opponent']: opponentData?.score || Math.floor(Math.random() * player.score * 1.2)
    };

    const winner = Object.entries(finalScores).reduce((a, b) => 
      finalScores[a[0]] > finalScores[b[0]] ? a : b
    )[0];

    // Additional stats for trivia game
    const additionalStats = {
      'Correct Answers': `${player.correctAnswers}/${questions.length}`,
      'Accuracy': `${Math.round((player.correctAnswers / questions.length) * 100)}%`,
      'Average Time': `${Math.round(player.averageTime / 1000)}s`,
      'Streak': `${Math.max(...questions.map((_, i) => i < questionIndex ? (player.correctAnswers > i ? i + 1 : 0) : 0))}`
    };

    onGameComplete({ winner, finalScores, additionalStats });
  };

  const useFiftyFifty = () => {
    if (!lifelines.fiftyFifty || !currentQuestion) return;
    
    setLifelines(prev => ({ ...prev, fiftyFifty: false }));
    
    // Remove 2 incorrect answers
    const incorrectAnswers = currentQuestion.options
      .map((_, index) => index)
      .filter(index => index !== currentQuestion.correctAnswer);
    
    const toRemove = incorrectAnswers.slice(0, 2);
    // This would need to be implemented to hide specific options
  };

  const useSkipQuestion = () => {
    if (!lifelines.skipQuestion) return;
    
    setLifelines(prev => ({ ...prev, skipQuestion: false }));
    nextQuestion();
  };

  const useExtraTime = () => {
    if (!lifelines.extraTime) return;
    
    setLifelines(prev => ({ ...prev, extraTime: false }));
    setTimeLeft(prev => prev + 15);
  };

  const toggleChat = () => {
    if (showChat) {
      setIsChatMinimized(!isChatMinimized);
    } else {
      setShowChat(true);
      setIsChatMinimized(false);
    }
  };

  const handleChatClose = () => {
    setShowChat(false);
    setIsChatMinimized(true);
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'hard': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'algorithms': return '🧮';
      case 'data-structures': return '📊';
      case 'programming-concepts': return '💻';
      case 'cs-theory': return '🎓';
      case 'debugging': return '🐛';
      default: return '❓';
    }
  };

  if (gameComplete) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-8">
        <div className="bg-gray-800 rounded-lg p-8 max-w-2xl w-full">
          <h2 className="text-3xl font-bold text-center mb-6">🎉 Game Complete!</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-gray-700 rounded-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-center">Your Stats</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Final Score:</span>
                  <span className="font-bold text-blue-400">{player.score}</span>
                </div>
                <div className="flex justify-between">
                  <span>Correct Answers:</span>
                  <span className="font-bold text-green-400">{player.correctAnswers}/{questions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Accuracy:</span>
                  <span className="font-bold text-purple-400">{Math.round((player.correctAnswers / questions.length) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Streak:</span>
                  <span className="font-bold text-yellow-400">{maxStreak}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-700 rounded-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-center">Opponent Stats</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Name:</span>
                  <span className="font-bold">{opponentData?.username || 'AI Opponent'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Score:</span>
                  <span className="font-bold text-blue-400">{opponentData?.score || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>College:</span>
                  <span className="font-bold">{opponentData?.college || 'Unknown'}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="text-center">
            <button
              onClick={() => window.location.href = '/dashboard'}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!gameStarted || !currentQuestion) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto mb-4"></div>
          <p className="text-lg">Loading trivia questions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex">
      {/* Main Game Area */}
      <div className="flex-1 p-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-4">
                <span className="text-2xl">🧠</span>
                <h1 className="text-2xl font-bold">Trivia Mode</h1>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={toggleChat}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                >
                  <span>💬</span>
                  <span>Chat</span>
                </button>
                <span className="text-lg">Question {questionIndex + 1}/{questions.length}</span>
                <div className={`text-2xl font-bold ${timeLeft <= 10 ? 'text-red-400 animate-pulse' : 'text-blue-400'}`}>
                  {timeLeft}s
                </div>
              </div>
            </div>
            
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <div className="bg-gray-700 rounded-lg px-4 py-2">
                  <span className="text-sm text-gray-300">Score: </span>
                  <span className="font-bold text-blue-400">{player.score}</span>
                </div>
                <div className="bg-gray-700 rounded-lg px-4 py-2">
                  <span className="text-sm text-gray-300">Streak: </span>
                  <span className="font-bold text-yellow-400">{streak}</span>
                </div>
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={useFiftyFifty}
                  disabled={!lifelines.fiftyFifty}
                  className={`px-3 py-1 rounded text-sm ${
                    lifelines.fiftyFifty
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  50/50
                </button>
                <button
                  onClick={useSkipQuestion}
                  disabled={!lifelines.skipQuestion}
                  className={`px-3 py-1 rounded text-sm ${
                    lifelines.skipQuestion
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  Skip
                </button>
                <button
                  onClick={useExtraTime}
                  disabled={!lifelines.extraTime}
                  className={`px-3 py-1 rounded text-sm ${
                    lifelines.extraTime
                      ? 'bg-purple-600 hover:bg-purple-700 text-white'
                      : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  +15s
                </button>
              </div>
            </div>
          </div>

          {/* Question */}
          <div className="bg-gray-800 rounded-lg p-8 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{getCategoryIcon(currentQuestion.category)}</span>
              <span className={`text-sm font-semibold ${getDifficultyColor(currentQuestion.difficulty)}`}>
                {currentQuestion.difficulty.toUpperCase()}
              </span>
              <span className="text-sm text-gray-400">•</span>
              <span className="text-sm text-gray-400">{currentQuestion.category}</span>
              <span className="text-sm text-gray-400">•</span>
              <span className="text-sm text-blue-400">{currentQuestion.points} points</span>
            </div>
            
            <h2 className="text-xl font-semibold mb-6">{currentQuestion.question}</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentQuestion.options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => handleAnswer(index)}
                  disabled={showResult}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    showResult
                      ? index === currentQuestion.correctAnswer
                        ? 'bg-green-600 border-green-500'
                        : selectedAnswer === index
                        ? 'bg-red-600 border-red-500'
                        : 'bg-gray-700 border-gray-600'
                      : 'bg-gray-700 border-gray-600 hover:border-blue-500 hover:bg-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-lg">
                      {String.fromCharCode(65 + index)}
                    </span>
                    <span className="text-left">{option}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Result */}
          {showResult && (
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <div className={`text-center ${isCorrect ? 'text-green-400' : 'text-red-400'}`}>
                <div className="text-4xl mb-2">{isCorrect ? '✅' : '❌'}</div>
                <div className="text-xl font-bold mb-2">
                  {isCorrect ? 'Correct!' : 'Incorrect!'}
                </div>
                <div className="text-sm text-gray-300 mb-4">
                  {currentQuestion.explanation}
                </div>
                {isCorrect && (
                  <div className="text-sm">
                    <span className="text-blue-400">+{currentQuestion.points} points</span>
                    {streak > 0 && <span className="text-yellow-400"> (+{streak * 2} streak bonus)</span>}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Progress Bar */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-400">Progress</span>
              <span className="text-sm text-gray-400">{Math.round((questionIndex / questions.length) * 100)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(questionIndex / questions.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Chat Component */}
      {showChat && (
        <div className="w-80 border-l border-gray-700">
          <ChatComponent
            gameId={gameId}
            gameMode="trivia"
            isMinimized={isChatMinimized}
            onToggleMinimize={toggleChat}
            className="h-full"
          />
        </div>
      )}

      {/* Minimized Chat Button */}
      {!showChat && (
        <ChatComponent
          gameId={gameId}
          gameMode="trivia"
          isMinimized={true}
          onToggleMinimize={toggleChat}
        />
      )}
    </div>
  );
};

export default TriviaGameComponent; 