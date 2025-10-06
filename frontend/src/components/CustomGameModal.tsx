import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../utils/notifications';

interface CustomGameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGameCreated: (gameId: string) => void;
}

interface GameSettings {
  timeLimit: number;
  maxPlayers: number;
  difficulty: string;
  language: string;
  isPrivate: boolean;
  customRules?: string;
}

const CustomGameModal: React.FC<CustomGameModalProps> = ({ 
  isOpen, 
  onClose, 
  onGameCreated 
}) => {
  const { token } = useAuth();
  const { showNotification } = useNotification();
  const [isCreating, setIsCreating] = useState(false);
  const [gameId, setGameId] = useState('');
  const [settings, setSettings] = useState<GameSettings>({
    timeLimit: 900,
    maxPlayers: 2,
    difficulty: 'medium',
    language: 'python',
    isPrivate: false
  });

  const handleCreateGame = async () => {
    if (!token) {
      showNotification('Please log in to create a game', 'error');
      return;
    }

    setIsCreating(true);
    try {
      const response = await fetch('/api/create_custom_game', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          settings: settings
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create game');
      }

      const data = await response.json();
      if (data.success) {
        showNotification('Custom game created successfully!', 'success');
        onGameCreated(data.game.id);
        onClose();
      } else {
        throw new Error(data.error || 'Failed to create game');
      }
    } catch (error) {
      showNotification('Failed to create custom game', 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleJoinGame = async () => {
    if (!gameId.trim()) {
      showNotification('Please enter a game ID', 'error');
      return;
    }

    if (!token) {
      showNotification('Please log in to join a game', 'error');
      return;
    }

    setIsCreating(true);
    try {
      const response = await fetch('/api/join_custom_game', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          game_id: gameId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to join game');
      }

      const data = await response.json();
      if (data.success) {
        showNotification('Joined game successfully!', 'success');
        onGameCreated(data.game_id);
        onClose();
      } else {
        throw new Error(data.error || 'Failed to join game');
      }
    } catch (error) {
      showNotification('Failed to join game', 'error');
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">Custom Game</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create Game Section */}
          <div className="bg-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-bold text-white mb-4">Create New Game</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Time Limit (minutes)
                </label>
                <select
                  value={settings.timeLimit / 60}
                  onChange={(e) => setSettings({
                    ...settings,
                    timeLimit: parseInt(e.target.value) * 60
                  })}
                  className="w-full bg-gray-600 text-white rounded-lg px-3 py-2"
                >
                  <option value={5}>5 minutes</option>
                  <option value={10}>10 minutes</option>
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Max Players
                </label>
                <select
                  value={settings.maxPlayers}
                  onChange={(e) => setSettings({
                    ...settings,
                    maxPlayers: parseInt(e.target.value)
                  })}
                  className="w-full bg-gray-600 text-white rounded-lg px-3 py-2"
                >
                  <option value={2}>2 players</option>
                  <option value={4}>4 players</option>
                  <option value={8}>8 players</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Difficulty
                </label>
                <select
                  value={settings.difficulty}
                  onChange={(e) => setSettings({
                    ...settings,
                    difficulty: e.target.value
                  })}
                  className="w-full bg-gray-600 text-white rounded-lg px-3 py-2"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Programming Language
                </label>
                <select
                  value={settings.language}
                  onChange={(e) => setSettings({
                    ...settings,
                    language: e.target.value
                  })}
                  className="w-full bg-gray-600 text-white rounded-lg px-3 py-2"
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="private"
                  checked={settings.isPrivate}
                  onChange={(e) => setSettings({
                    ...settings,
                    isPrivate: e.target.checked
                  })}
                  className="mr-2"
                />
                <label htmlFor="private" className="text-sm text-gray-300">
                  Private Game
                </label>
              </div>

              <button
                onClick={handleCreateGame}
                disabled={isCreating}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-bold py-2 px-4 rounded-lg transition-colors"
              >
                {isCreating ? 'Creating...' : 'Create Game'}
              </button>
            </div>
          </div>

          {/* Join Game Section */}
          <div className="bg-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-bold text-white mb-4">Join Existing Game</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Game ID
                </label>
                <input
                  type="text"
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value)}
                  placeholder="Enter game ID..."
                  className="w-full bg-gray-600 text-white rounded-lg px-3 py-2"
                />
              </div>

              <button
                onClick={handleJoinGame}
                disabled={isCreating || !gameId.trim()}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-bold py-2 px-4 rounded-lg transition-colors"
              >
                {isCreating ? 'Joining...' : 'Join Game'}
              </button>
            </div>

            <div className="mt-6 p-4 bg-gray-600 rounded-lg">
              <h4 className="text-sm font-bold text-white mb-2">How to join:</h4>
              <ol className="text-xs text-gray-300 space-y-1">
                <li>1. Ask the game creator for the Game ID</li>
                <li>2. Enter the Game ID above</li>
                <li>3. Click "Join Game"</li>
                <li>4. Wait for the game to start</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomGameModal; 