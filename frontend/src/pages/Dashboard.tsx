import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import MatchmakingModal from '../components/MatchmakingModal';
import CustomGameModal from '../components/CustomGameModal';
import { useNotification } from '../utils/notifications';

type GameMode = 'classic' | 'custom' | 'blitz' | 'practice' | 'ranked' | 'casual' | 'trivia' | 'debug' | 'electrical';

const Dashboard = () => {
  const [isMatchmaking, setIsMatchmaking] = useState(false);
  const [selectedMode, setSelectedMode] = useState<GameMode | null>(null);
  const [showCustomGameModal, setShowCustomGameModal] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { showNotification } = useNotification();

  const handleMatchmaking = (mode: GameMode) => {
    if (mode === 'custom') {
      setShowCustomGameModal(true);
      return;
    }
    
    setSelectedMode(mode);
    setIsMatchmaking(true);
    // Simulate finding a match after 3-7 seconds
    setTimeout(() => {
      const gameId = Math.random().toString(36).substring(7);
      navigate(`/game/${gameId}?mode=${mode}`);
    }, Math.random() * 4000 + 3000);
  };

  const handleCustomGameCreated = (gameId: string) => {
    navigate(`/game/${gameId}?mode=custom`);
  };

  const gameModes = [
    {
      id: 'classic' as GameMode,
      title: 'Classic',
      description: 'Traditional 1v1 competitive matches with standard rules.',
      gradient: 'from-purple-900 to-purple-700',
      textColor: 'text-purple-900',
      icon: '⚔️'
    },
    {
      id: 'custom' as GameMode,
      title: 'Custom',
      description: 'Create or join custom games with your own rules and settings.',
      gradient: 'from-blue-900 to-blue-700',
      textColor: 'text-blue-900',
      icon: '🎮'
    },
    {
      id: 'blitz' as GameMode,
      title: 'Blitz',
      description: 'Fast-paced matches with shorter time limits and quick rounds.',
      gradient: 'from-red-900 to-red-700',
      textColor: 'text-red-900',
      icon: '⚡'
    },
    {
      id: 'practice' as GameMode,
      title: 'Practice',
      description: 'Train against AI or practice specific skills without ranking changes.',
      gradient: 'from-green-900 to-green-700',
      textColor: 'text-green-900',
      icon: '🎯'
    },
    {
      id: 'ranked' as GameMode,
      title: 'Ranked',
      description: 'Competitive matches that affect your skill rating and ranking.',
      gradient: 'from-yellow-900 to-yellow-700',
      textColor: 'text-yellow-900',
      icon: '🏆'
    },
    {
      id: 'casual' as GameMode,
      title: 'Casual',
      description: 'Relaxed matches for fun without any ranking implications.',
      gradient: 'from-indigo-900 to-indigo-700',
      textColor: 'text-indigo-900',
      icon: '😊'
    },
    {
      id: 'trivia' as GameMode,
      title: 'Trivia',
      description: 'Test your knowledge with programming trivia questions and challenges.',
      gradient: 'from-pink-900 to-pink-700',
      textColor: 'text-pink-900',
      icon: '🧠'
    },
    {
      id: 'debug' as GameMode,
      title: 'Debug Mode',
      description: 'Find and fix bugs in code snippets as fast as possible.',
      gradient: 'from-orange-900 to-orange-700',
      textColor: 'text-orange-900',
      icon: '🐛'
    },
    {
      id: 'electrical' as GameMode,
      title: 'Electrical Engineers Play Box',
      description: 'Build and test electrical circuits in a competitive environment.',
      gradient: 'from-teal-900 to-teal-700',
      textColor: 'text-teal-900',
      icon: '⚡'
    }
  ];

  const getRank = (score: number) => {
    if (score >= 1000) return { name: 'Creator', color: 'text-yellow-400', isGold: true };
    if (score >= 200) return { name: 'Code Guru', color: 'text-purple-400' };
    if (score >= 50) return { name: 'Master', color: 'text-blue-400' };
    if (score >= 10) return { name: 'Novice', color: 'text-green-400' };
    return { name: 'Vibe Coder', color: 'text-pink-400' };
  };

  // Simulated stats (replace with real data from backend/user context)
  const totalScore = 0; // Replace with actual user score
  const rank = getRank(totalScore);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold">CS Gauntlet</h1>
          <div className="flex items-center space-x-4">
            <span className="text-gray-300">Welcome, {user?.username || 'Guest'}</span>
            <button
              onClick={() => {
                logout();
                navigate('/login');
                showNotification('Successfully logged out', 'success');
              }}
              className="bg-red-600 px-4 py-2 rounded-md hover:bg-red-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-4xl font-bold mb-2">Choose Your Battle</h2>
          <p className="text-gray-400 text-lg">Select a game mode to start your coding adventure</p>
        </div>

        {/* Game Modes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {gameModes.map((mode) => (
            <div key={mode.id} className={`bg-gradient-to-br ${mode.gradient} rounded-xl shadow-lg overflow-hidden transform hover:scale-105 transition-all duration-300 hover:shadow-2xl`}>
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="text-3xl mr-3">{mode.icon}</span>
                  <h3 className="text-2xl font-bold">{mode.title}</h3>
                </div>
                <p className="text-gray-200 mb-6 text-sm leading-relaxed">
                  {mode.description}
                </p>
                <button
                  onClick={() => handleMatchmaking(mode.id)}
                  className={`w-full bg-white ${mode.textColor} font-bold py-3 px-4 rounded-lg hover:bg-gray-100 transition-colors duration-200 transform hover:scale-105 active:scale-95`}
                >
                  Play {mode.title}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-indigo-400">0</div>
            <div className="text-gray-400 text-sm">Games Played</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-400">0%</div>
            <div className="text-gray-400 text-sm">Win Rate</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className={`text-2xl font-bold ${rank.color} ${rank.isGold ? 'animate-pulse' : ''}`}>{rank.name}</div>
            <div className="text-gray-400 text-sm">Rank</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-400">{totalScore}</div>
            <div className="text-gray-400 text-sm">Total Score</div>
          </div>
        </div>

        {/* Recent Games Section */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">Recent Games</h2>
          <div className="bg-gray-800 rounded-lg shadow-lg overflow-hidden">
            <div className="p-4">
              <p className="text-gray-400 text-center py-8">
                No recent games found. Start playing to see your history!
              </p>
            </div>
          </div>
        </div>
      </main>

      {isMatchmaking && selectedMode && (
        <MatchmakingModal
          mode={selectedMode}
          onCancel={() => setIsMatchmaking(false)}
        />
      )}

      {showCustomGameModal && (
        <CustomGameModal
          isOpen={showCustomGameModal}
          onClose={() => setShowCustomGameModal(false)}
          onGameCreated={handleCustomGameCreated}
        />
      )}
    </div>
  );
};

export default Dashboard;
