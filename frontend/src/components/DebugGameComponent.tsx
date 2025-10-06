import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import ChatComponent from './ChatComponent';
import PrismCodeHighlighter from './PrismCodeHighlighter';

interface Bug {
  id: string;
  line: number;
  type: 'syntax' | 'logical' | 'runtime' | 'semantic';
  description: string;
  fix: string;
  points: number;
}

interface DebugChallenge {
  id: string;
  title: string;
  description: string;
  buggyCode: string;
  expectedOutput: string;
  actualOutput: string;
  language: 'javascript' | 'python' | 'java' | 'cpp';
  difficulty: 'easy' | 'medium' | 'hard';
  bugs: Bug[];
  hints: string[];
  totalPoints: number;
}

interface Player {
  id: string;
  username: string;
  score: number;
  bugsFound: number;
  averageTime: number;
  college?: string;
}

interface DebugGameProps {
  gameId: string;
  opponent: Player | null;
  onGameComplete: (result: { winner: string; finalScores: { [key: string]: number }; additionalStats?: Record<string, any> }) => void;
}

const DebugGameComponent: React.FC<DebugGameProps> = ({ gameId, opponent, onGameComplete }) => {
  const { user } = useAuth();
  const [currentChallenge, setCurrentChallenge] = useState<DebugChallenge | null>(null);
  const [challengeIndex, setChallengeIndex] = useState(0);
  const [foundBugs, setFoundBugs] = useState<Set<string>>(new Set());
  const [selectedLine, setSelectedLine] = useState<number | null>(null);
  const [showBugDetails, setShowBugDetails] = useState(false);
  const [currentBug, setCurrentBug] = useState<Bug | null>(null);
  const [fixAttempt, setFixAttempt] = useState('');
  const [timeLeft, setTimeLeft] = useState(480); // 8 minutes total
  const [gameStarted, setGameStarted] = useState(false);
  const [gameComplete, setGameComplete] = useState(false);
  const [player, setPlayer] = useState<Player>({
    id: user?.id || '',
    username: user?.username || '',
    score: 0,
    bugsFound: 0,
    averageTime: 0
  });
  const [opponentData] = useState<Player | null>(opponent);
  const [challenges, setChallenges] = useState<DebugChallenge[]>([]);
  const [challengeStartTime, setChallengeStartTime] = useState<number>(0);
  const [hintsUsed, setHintsUsed] = useState<Set<number>>(new Set());
  const [showHint, setShowHint] = useState(false);
  const [currentHintIndex, setCurrentHintIndex] = useState(0);
  const [streak, setStreak] = useState(0);
  const [maxStreak, setMaxStreak] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const [codeLines, setCodeLines] = useState<string[]>([]);
  const [highlightedLines, setHighlightedLines] = useState<Set<number>>(new Set());
  const [isChatMinimized, setIsChatMinimized] = useState(true);
  const [showChat, setShowChat] = useState(false);

  // Debug challenges will be loaded from backend
  const [debugChallenges, setDebugChallenges] = useState<DebugChallenge[]>([]);

  // Fetch debug challenges from backend
  const fetchDebugChallenges = async () => {
    try {
      const response = await fetch('/api/game/debug/challenges');
      const data = await response.json();
      if (data.success) {
        setDebugChallenges(data.challenges);
      }
    } catch (error) {
      console.error('Failed to fetch debug challenges:', error);
      // Fallback to default challenges if fetch fails
      setDebugChallenges([
        {
          id: '1',
          title: 'Array Sum Function',
          description: 'This function should calculate the sum of all elements in an array, but it has bugs.',
          buggyCode: `function arraySum(arr) {
    let sum = 0;
    for (let i = 0; i <= arr.length; i++) {
        sum += arr[i];
    }
    return sum;
}`,
          expectedOutput: '15',
          actualOutput: 'NaN',
          language: 'javascript',
          difficulty: 'easy',
          bugs: [
            {
              id: 'bug1',
              line: 3,
              type: 'logical',
              description: 'Loop condition should be < instead of <=',
              fix: 'for (let i = 0; i < arr.length; i++)',
              points: 15
            }
          ],
          hints: [
            'Check the loop condition - are you accessing array elements correctly?'
          ],
          totalPoints: 15
        }
      ]);
    }
  };

  const initializeGame = async () => {
    await fetchDebugChallenges();
  };

  useEffect(() => {
    if (debugChallenges.length > 0) {
      // Shuffle challenges and select 3-5 for the game
      const shuffledChallenges = [...debugChallenges].sort(() => Math.random() - 0.5).slice(0, 3);
      setChallenges(shuffledChallenges);
      setCurrentChallenge(shuffledChallenges[0]);
      setChallengeStartTime(Date.now());
      setGameStarted(true);
    }
  }, [debugChallenges]);

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
  }, [gameStarted, currentChallenge]);

  useEffect(() => {
    if (currentChallenge) {
      setCodeLines(currentChallenge.buggyCode.split('\n'));
      setHighlightedLines(new Set(currentChallenge.bugs.map(bug => bug.line)));
    }
  }, [currentChallenge]);


  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          handleTimeUp();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleTimeUp = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    endGame();
  };

  const handleLineClick = (lineNumber: number) => {
    if (!currentChallenge || foundBugs.has(`${currentChallenge.id}-${lineNumber}`)) return;
    
    setSelectedLine(lineNumber);
    
    // Check if this line has a bug
    const bugOnLine = currentChallenge.bugs.find(bug => bug.line === lineNumber);
    
    if (bugOnLine) {
      setCurrentBug(bugOnLine);
      setShowBugDetails(true);
    } else {
      // Wrong line selected - show feedback
      setSelectedLine(null);
      // Could add penalty here
    }
  };

  const handleBugFix = () => {
    if (!currentBug || !currentChallenge) return;
    
    const isCorrectFix = fixAttempt.trim().toLowerCase().includes(currentBug.fix.toLowerCase().trim());
    
    if (isCorrectFix) {
      // Correct fix
      const bugId = `${currentChallenge.id}-${currentBug.line}`;
      setFoundBugs(prev => new Set([...prev, bugId]));
      
      const timeBonus = Math.max(0, Math.floor((480 - (480 - timeLeft)) / 60));
      const streakBonus = Math.floor(streak * 3);
      const hintPenalty = hintsUsed.has(currentBug.line) ? 5 : 0;
      const totalPoints = Math.max(0, currentBug.points + timeBonus + streakBonus - hintPenalty);
      
      setPlayer(prev => ({
        ...prev,
        score: prev.score + totalPoints,
        bugsFound: prev.bugsFound + 1,
        averageTime: (prev.averageTime * prev.bugsFound + (Date.now() - challengeStartTime)) / (prev.bugsFound + 1)
      }));
      
      const newStreak = streak + 1;
      setStreak(newStreak);
      setMaxStreak(Math.max(maxStreak, newStreak));
      
      setShowBugDetails(false);
      setCurrentBug(null);
      setFixAttempt('');
      setSelectedLine(null);
      
      // Check if all bugs found in current challenge
      if (foundBugs.size + 1 >= currentChallenge.bugs.length) {
        setTimeout(() => {
          nextChallenge();
        }, 2000);
      }
    } else {
      // Wrong fix - show feedback
      setStreak(0);
      // Could add penalty here
    }
  };

  const nextChallenge = () => {
    const nextIndex = challengeIndex + 1;
    
    if (nextIndex >= challenges.length) {
      endGame();
      return;
    }

    setChallengeIndex(nextIndex);
    setCurrentChallenge(challenges[nextIndex]);
    setFoundBugs(new Set());
    setHintsUsed(new Set());
    setShowBugDetails(false);
    setCurrentBug(null);
    setFixAttempt('');
    setSelectedLine(null);
    setChallengeStartTime(Date.now());
  };

  const endGame = () => {
    setGameComplete(true);
    setGameStarted(false);
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    const finalScores = {
      [player.id]: player.score,
      [opponentData?.id || 'opponent']: opponentData?.score || Math.floor(Math.random() * player.score * 1.3)
    };

    const winner = Object.entries(finalScores).reduce((a, b) => 
      finalScores[a[0]] > finalScores[b[0]] ? a : b
    )[0];

    // Additional stats for debug game
    const additionalStats = {
      'Bugs Found': `${player.bugsFound}/${debugChallenges.length}`,
      'Success Rate': `${Math.round((player.bugsFound / debugChallenges.length) * 100)}%`,
      'Average Time': `${Math.round(player.averageTime / 1000)}s`,
      'Hints Used': `${debugChallenges.length - hintsRemaining}`
    };

    onGameComplete({ winner, finalScores, additionalStats });
  };

  const useHint = () => {
    if (!currentChallenge || !selectedLine) return;
    
    const bug = currentChallenge.bugs.find(b => b.line === selectedLine);
    if (!bug) return;
    
    setHintsUsed(prev => new Set([...prev, selectedLine]));
    
    const hintIndex = currentChallenge.bugs.findIndex(b => b.line === selectedLine);
    setCurrentHintIndex(hintIndex);
    setShowHint(true);
    
    setTimeout(() => {
      setShowHint(false);
    }, 5000);
  };

  const getBugTypeColor = (type: string) => {
    switch (type) {
      case 'syntax': return 'text-red-400';
      case 'logical': return 'text-yellow-400';
      case 'runtime': return 'text-orange-400';
      case 'semantic': return 'text-purple-400';
      default: return 'text-gray-400';
    }
  };

  const getBugTypeIcon = (type: string) => {
    switch (type) {
      case 'syntax': return '🔴';
      case 'logical': return '🟡';
      case 'runtime': return '🟠';
      case 'semantic': return '🟣';
      default: return '⚪';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const toggleChat = () => {
    if (showChat) {
      setIsChatMinimized(!isChatMinimized);
    } else {
      setShowChat(true);
      setIsChatMinimized(false);
    }
  };

  if (gameComplete) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-8">
        <div className="bg-gray-800 rounded-lg p-8 max-w-2xl w-full">
          <h2 className="text-3xl font-bold text-center mb-6">🐛 Debug Complete!</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-gray-700 rounded-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-center">Your Stats</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Final Score:</span>
                  <span className="font-bold text-green-400">{player.score}</span>
                </div>
                <div className="flex justify-between">
                  <span>Bugs Found:</span>
                  <span className="font-bold text-red-400">{player.bugsFound}</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Streak:</span>
                  <span className="font-bold text-yellow-400">{maxStreak}</span>
                </div>
                <div className="flex justify-between">
                  <span>Challenges:</span>
                  <span className="font-bold text-blue-400">{challengeIndex + 1}/{challenges.length}</span>
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
                  <span className="font-bold text-green-400">{opponentData?.score || 'N/A'}</span>
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
              className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!gameStarted || !currentChallenge) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-400 mx-auto mb-4"></div>
          <p className="text-lg">Loading debug challenges...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex">
      {/* Main Game Area */}
      <div className="flex-1 p-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-4">
                <span className="text-2xl">🐛</span>
                <h1 className="text-2xl font-bold">Debug Mode</h1>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={toggleChat}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                >
                  <span>💬</span>
                  <span>Chat</span>
                </button>
                <span className="text-lg">Challenge {challengeIndex + 1}/{challenges.length}</span>
                <div className={`text-2xl font-bold ${timeLeft <= 60 ? 'text-red-400 animate-pulse' : 'text-green-400'}`}>
                  {formatTime(timeLeft)}
                </div>
              </div>
            </div>
            
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <div className="bg-gray-700 rounded-lg px-4 py-2">
                  <span className="text-sm text-gray-300">Score: </span>
                  <span className="font-bold text-green-400">{player.score}</span>
                </div>
                <div className="bg-gray-700 rounded-lg px-4 py-2">
                  <span className="text-sm text-gray-300">Bugs Found: </span>
                  <span className="font-bold text-red-400">{foundBugs.size}/{currentChallenge.bugs.length}</span>
                </div>
                <div className="bg-gray-700 rounded-lg px-4 py-2">
                  <span className="text-sm text-gray-300">Streak: </span>
                  <span className="font-bold text-yellow-400">{streak}</span>
                </div>
              </div>
              
              <button
                onClick={useHint}
                disabled={!selectedLine || hintsUsed.has(selectedLine)}
                className={`px-4 py-2 rounded text-sm ${
                  selectedLine && !hintsUsed.has(selectedLine)
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                }`}
              >
                Use Hint (-5 pts)
              </button>
            </div>
          </div>

          {/* Challenge Description */}
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{currentChallenge.language === 'javascript' ? '🟨' : '🐍'}</span>
              <h2 className="text-xl font-bold">{currentChallenge.title}</h2>
              <span className={`text-sm font-semibold ${
                currentChallenge.difficulty === 'easy' ? 'text-green-400' :
                currentChallenge.difficulty === 'medium' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {currentChallenge.difficulty.toUpperCase()}
              </span>
            </div>
            <p className="text-gray-300 mb-4">{currentChallenge.description}</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="font-semibold text-green-400 mb-2">Expected Output:</h4>
                <code className="text-green-300">{currentChallenge.expectedOutput}</code>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="font-semibold text-red-400 mb-2">Actual Output:</h4>
                <code className="text-red-300">{currentChallenge.actualOutput}</code>
              </div>
            </div>
          </div>

          {/* Code Display */}
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span>🔍</span>
              Buggy Code - Click on suspicious lines
            </h3>
            
            <div className="bg-gray-900 rounded-lg overflow-x-auto relative">
              {/* Overlay for bug indicators and click handling */}
              <div className="absolute inset-0 z-10">
                {codeLines.map((_, index) => {
                  const lineNumber = index + 1;
                  const hasBug = highlightedLines.has(lineNumber);
                  const isFound = foundBugs.has(`${currentChallenge.id}-${lineNumber}`);
                  const isSelected = selectedLine === lineNumber;
                  
                  return (
                    <div
                      key={lineNumber}
                      onClick={() => handleLineClick(lineNumber)}
                      className={`flex items-center h-7 px-2 cursor-pointer hover:bg-gray-700 hover:bg-opacity-50 transition-colors ${
                        isSelected ? 'bg-blue-600 bg-opacity-40' :
                        isFound ? 'bg-green-600 bg-opacity-30' :
                        hasBug ? 'bg-red-600 bg-opacity-20' : ''
                      }`}
                    >
                      <span className="w-8 mr-4"></span>
                      <span className="flex-1"></span>
                      {isFound && <span className="text-green-400 ml-2">✓</span>}
                      {hasBug && !isFound && <span className="text-red-400 ml-2">🚨</span>}
                    </div>
                  );
                })}
              </div>
              
              {/* Syntax highlighted code */}
              <div className={`relative z-0 ${currentChallenge ? '' : 'hidden'}`}>
                <PrismCodeHighlighter 
                  code={currentChallenge?.buggyCode || ''} 
                  language={currentChallenge?.language || 'javascript'} 
                />
              </div>
            </div>
          </div>

          {/* Bug Details Modal */}
          {showBugDetails && currentBug && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-gray-800 rounded-lg p-8 max-w-2xl w-full mx-4">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{getBugTypeIcon(currentBug.type)}</span>
                  <h3 className="text-xl font-bold">Bug Found!</h3>
                  <span className={`text-sm font-semibold ${getBugTypeColor(currentBug.type)}`}>
                    {currentBug.type.toUpperCase()}
                  </span>
                </div>
                
                <div className="mb-4">
                  <p className="text-gray-300 mb-4">{currentBug.description}</p>
                  <div className="bg-gray-700 rounded-lg p-3">
                    <span className="text-sm text-gray-400">Points: </span>
                    <span className="font-bold text-green-400">{currentBug.points}</span>
                  </div>
                </div>
                
                <div className="mb-6">
                  <label className="block text-sm font-semibold mb-2">
                    Enter your fix:
                  </label>
                  <input
                    type="text"
                    value={fixAttempt}
                    onChange={(e) => setFixAttempt(e.target.value)}
                    className="w-full bg-gray-700 rounded-lg px-4 py-2 text-white"
                    placeholder="Type the corrected code here..."
                  />
                </div>
                
                <div className="flex justify-end gap-4">
                  <button
                    onClick={() => setShowBugDetails(false)}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleBugFix}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    Submit Fix
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Hint Modal */}
          {showHint && currentChallenge && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <span>💡</span>
                  Hint
                </h3>
                <p className="text-gray-300 mb-4">
                  {currentChallenge.hints[currentHintIndex] || 'No hint available'}
                </p>
                <div className="text-center">
                  <button
                    onClick={() => setShowHint(false)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Got it!
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Progress */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-400">Progress</span>
              <span className="text-sm text-gray-400">
                {Math.round((foundBugs.size / currentChallenge.bugs.length) * 100)}% 
                of current challenge
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-red-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(foundBugs.size / currentChallenge.bugs.length) * 100}%` }}
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
            gameMode="debug"
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
          gameMode="debug"
          isMinimized={true}
          onToggleMinimize={toggleChat}
        />
      )}
    </div>
  );
};

export default DebugGameComponent; 