import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useNotification } from '../utils/notifications';

interface GameInfo {
  players: {
    username: string;
    progress: number;
  }[];
  currentRound: number;
  question: {
    title: string;
    description: string;
    examples: string[];
  };
}

const Spectate: React.FC = () => {
  const { gameId: _gameId } = useParams<{ gameId: string }>();
  const [gameInfo, setGameInfo] = useState<GameInfo | null>(null);
  const [timeLeft, setTimeLeft] = useState(300);
  const { showNotification } = useNotification();

  useEffect(() => {
    // Mock game data instead of connecting to WebSocket
    const mockGameInfo: GameInfo = {
      players: [
        { username: 'Player1', progress: 65 },
        { username: 'Player2', progress: 42 }
      ],
      currentRound: 1,
      question: {
        title: 'Two Sum',
        description: 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
        examples: [
          'Input: nums = [2,7,11,15], target = 9\nOutput: [0,1]',
          'Input: nums = [3,2,4], target = 6\nOutput: [1,2]'
        ]
      }
    };
    
    setGameInfo(mockGameInfo);
    showNotification('Connected to game stream', 'success');
    
    // Start countdown timer
    const timer = setInterval(() => {
      setTimeLeft(prev => Math.max(0, prev - 1));
    }, 1000);
    
    // Mock player progress updates
    const progressUpdater = setInterval(() => {
      setGameInfo(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          players: prev.players.map(player => ({
            ...player,
            progress: Math.min(100, player.progress + Math.floor(Math.random() * 5))
          }))
        };
      });
    }, 3000);
    
    // Cleanup function
    return () => {
      clearInterval(timer);
      clearInterval(progressUpdater);
    };
  }, [showNotification]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <div className="text-2xl font-bold">
            Round {gameInfo?.currentRound || 1}/3
          </div>
          <div className="text-xl">
            Time Left: {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Question Panel */}
          <div className="bg-gray-800 rounded-lg p-6">
            {gameInfo?.question && (
              <>
                <h2 className="text-xl font-bold mb-4">{gameInfo.question.title}</h2>
                <div className="prose prose-invert">
                  <p>{gameInfo.question.description}</p>
                  <h3 className="text-lg font-semibold mt-4">Examples:</h3>
                  {gameInfo.question.examples.map((example, index) => (
                    <div key={index} className="bg-gray-700 p-4 rounded-md mt-2">
                      <p>{example}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Player Panels */}
          {gameInfo?.players?.map((player, index) => (
            <div key={index} className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4">{player.username}</h3>
              <div className="w-full bg-gray-700 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${player.progress * 33.33}%` }}
                ></div>
              </div>
              <p className="mt-2 text-sm text-gray-400">
                {player.progress}/3 rounds complete
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Spectate;
