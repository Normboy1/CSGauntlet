import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import VSAnimation from '../components/VSAnimation';
import GameResultAnimation from '../components/GameResultAnimation';
import { useNotification } from '../utils/notifications';
import ElectricalEngineersPlayBox from '../components/ElectricalEngineersPlayBox';
import TriviaGameComponent from '../components/TriviaGameComponent';
import DebugGameComponent from '../components/DebugGameComponent';

interface Player {
  id: string;
  username: string;
  avatar_url?: string;
  college?: string;
}

const Game: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const [searchParams] = useSearchParams();
  const gameMode = searchParams.get('mode') || 'classic';
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showNotification } = useNotification();

  const [showVSAnimation, setShowVSAnimation] = useState(true);
  const [gameStarted, setGameStarted] = useState(false);
  const [opponent, setOpponent] = useState<Player | null>(null);
  const [showResultAnimation, setShowResultAnimation] = useState(false);
  const [gameResult, setGameResult] = useState<{
    winner: string;
    finalScores: { [key: string]: number };
    additionalStats?: Record<string, any>;
  } | null>(null);

  useEffect(() => {
    // Simulate finding an opponent
    const mockOpponents = [
      { id: '2', username: 'CodeMaster', college: 'MIT' },
      { id: '3', username: 'AlgoWizard', college: 'Stanford' },
      { id: '4', username: 'DebugKing', college: 'Berkeley' },
      { id: '5', username: 'SyntaxQueen', college: 'CMU' },
      { id: '6', username: 'LogicLord', college: 'Georgia Tech' }
    ];

    const randomOpponent = mockOpponents[Math.floor(Math.random() * mockOpponents.length)];
    setOpponent(randomOpponent);
  }, []);

  const handleVSAnimationComplete = () => {
    setShowVSAnimation(false);
    setGameStarted(true);
    showNotification(`Game started! Mode: ${gameMode}`, 'success');
  };

  const handleGameComplete = (result: { winner: string; finalScores: { [key: string]: number }; additionalStats?: Record<string, any> }) => {
    setGameResult(result);
    setShowResultAnimation(true);
    setGameStarted(false);
  };

  const handleAnimationComplete = () => {
    setShowResultAnimation(false);
    navigate('/dashboard');
  };

  const getGameModeDisplayName = (mode: string) => {
    const modeNames: { [key: string]: string } = {
      classic: 'Classic',
      custom: 'Custom',
      blitz: 'Blitz',
      practice: 'Practice',
      ranked: 'Ranked',
      casual: 'Casual',
      trivia: 'Trivia',
      debug: 'Debug Mode',
      electrical: 'Electrical Engineers Play Box'
    };
    return modeNames[mode] || 'Classic';
  };

  // Adapter function to create trivia/debug player objects
  const createTriviaPlayer = (player: Player) => ({
    id: player.id,
    username: player.username,
    score: 0,
    correctAnswers: 0,
    averageTime: 0,
    college: player.college
  });

  const createDebugPlayer = (player: Player) => ({
    id: player.id,
    username: player.username,
    score: 0,
    bugsFound: 0,
    averageTime: 0,
    college: player.college
  });

  if (!user || !opponent) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading game...</p>
        </div>
      </div>
    );
  }

  if (showVSAnimation) {
    return (
      <VSAnimation
        player1={user}
        player2={opponent}
        onAnimationComplete={handleVSAnimationComplete}
        gameMode={getGameModeDisplayName(gameMode)}
      />
    );
  }

  // Route to appropriate game component based on mode
  if (gameMode === 'electrical') {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <ElectricalEngineersPlayBox />
      </div>
    );
  }

  if (gameMode === 'trivia') {
    return (
      <TriviaGameComponent
        gameId={gameId || ''}
        opponent={createTriviaPlayer(opponent)}
        onGameComplete={handleGameComplete}
      />
    );
  }

  if (gameMode === 'debug') {
    return (
      <DebugGameComponent
        gameId={gameId || ''}
        opponent={createDebugPlayer(opponent)}
        onGameComplete={handleGameComplete}
      />
    );
  }

  // Default game mode (classic, custom, blitz, practice, ranked, casual)
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Game Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="text-gray-400 hover:text-white transition-colors"
              >
                ← Back to Dashboard
              </button>
              <div className="text-sm text-gray-400">
                Game ID: {gameId}
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <div className="text-center">
                <div className="text-sm text-gray-400">Mode</div>
                <div className="font-bold">{getGameModeDisplayName(gameMode)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Time</div>
                <div className="font-bold text-green-400">15:00</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Game Content */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {gameStarted && (
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-8">Game Started!</h1>
            <div className="bg-gray-800 rounded-lg p-8 max-w-2xl mx-auto">
              <h2 className="text-2xl font-bold mb-4">Problem</h2>
              <div className="text-left bg-gray-700 rounded-lg p-6 mb-6">
                <h3 className="text-xl font-bold mb-4">Two Sum</h3>
                <p className="text-gray-300 mb-4">
                  Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.
                </p>
                <p className="text-gray-300 mb-4">
                  You may assume that each input would have exactly one solution, and you may not use the same element twice.
                </p>
                <div className="bg-gray-600 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-2">Example:</div>
                  <div className="text-green-400">Input: nums = [2,7,11,15], target = 9</div>
                  <div className="text-green-400">Output: [0,1]</div>
                  <div className="text-gray-400 text-sm mt-2">Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].</div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-700 rounded-lg p-6">
                  <h3 className="text-lg font-bold mb-4">Code Editor</h3>
                  <textarea
                    className="w-full h-64 bg-gray-800 text-green-400 p-4 rounded-lg font-mono text-sm resize-none"
                    placeholder="Write your solution here..."
                    defaultValue={`def twoSum(nums, target):
    # Your solution here
    pass`}
                  />
                </div>
                
                <div className="bg-gray-700 rounded-lg p-6">
                  <h3 className="text-lg font-bold mb-4">Test Cases</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center p-2 bg-gray-600 rounded">
                      <span>Test 1</span>
                      <span className="text-yellow-400">Pending</span>
                    </div>
                    <div className="flex justify-between items-center p-2 bg-gray-600 rounded">
                      <span>Test 2</span>
                      <span className="text-yellow-400">Pending</span>
                    </div>
                    <div className="flex justify-between items-center p-2 bg-gray-600 rounded">
                      <span>Test 3</span>
                      <span className="text-yellow-400">Pending</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="mt-6 flex justify-center space-x-4">
                <button className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg font-bold transition-colors">
                  Run Tests
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-bold transition-colors">
                  Submit Solution
                </button>
              </div>

              {/* Test Animation Buttons - For demonstration */}
              <div className="mt-8 pt-6 border-t border-gray-600">
                <div className="text-sm text-gray-400 mb-3">Test Animations:</div>
                <div className="flex justify-center space-x-4">
                  <button 
                    onClick={() => handleGameComplete({
                      winner: user?.id || '',
                      finalScores: { [user?.id || '']: 2500, [opponent?.id || '']: 1800 },
                      additionalStats: { 
                        'Time': '12:34', 
                        'Accuracy': '85%', 
                        'Problems Solved': '8/10',
                        'Streak': '5'
                      }
                    })}
                    className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded font-medium transition-colors text-sm"
                  >
                    🏆 Test Win
                  </button>
                  <button 
                    onClick={() => handleGameComplete({
                      winner: opponent?.id || '',
                      finalScores: { [user?.id || '']: 1600, [opponent?.id || '']: 2200 },
                      additionalStats: { 
                        'Time': '15:00', 
                        'Accuracy': '72%', 
                        'Problems Solved': '6/10',
                        'Streak': '3'
                      }
                    })}
                    className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded font-medium transition-colors text-sm"
                  >
                    💪 Test Loss
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Game Result Animation */}
      {showResultAnimation && gameResult && user && opponent && (
        <GameResultAnimation
          isWinner={gameResult.winner === user.id}
          playerScore={gameResult.finalScores[user.id] || 0}
          opponentScore={gameResult.finalScores[opponent.id] || 0}
          playerName={user.username}
          opponentName={opponent.username}
          gameMode={getGameModeDisplayName(gameMode)}
          onAnimationComplete={handleAnimationComplete}
          additionalStats={gameResult.additionalStats}
        />
      )}
    </div>
  );
};

export default Game;
