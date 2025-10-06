import React, { useState, useEffect } from 'react';

interface Player {
  id: string;
  username: string;
  avatar_url?: string;
  college?: string;
}

interface VSAnimationProps {
  player1: Player;
  player2: Player;
  onAnimationComplete: () => void;
  gameMode?: string;
}

const VSAnimation: React.FC<VSAnimationProps> = ({ 
  player1, 
  player2, 
  onAnimationComplete,
  gameMode = 'Classic'
}) => {
  const [animationPhase, setAnimationPhase] = useState(0);
  const [showVS, setShowVS] = useState(false);
  const [showGameMode, setShowGameMode] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimationPhase(1);
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (animationPhase === 1) {
      const timer = setTimeout(() => {
        setShowVS(true);
        setAnimationPhase(2);
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [animationPhase]);

  useEffect(() => {
    if (animationPhase === 2) {
      const timer = setTimeout(() => {
        setShowGameMode(true);
        setAnimationPhase(3);
      }, 1500);

      return () => clearTimeout(timer);
    }
  }, [animationPhase]);

  useEffect(() => {
    if (animationPhase === 3) {
      const timer = setTimeout(() => {
        onAnimationComplete();
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [animationPhase, onAnimationComplete]);

  const getDefaultAvatar = (username: string) => {
    const colors = [
      'bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500',
      'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500'
    ];
    const colorIndex = username.charCodeAt(0) % colors.length;
    return colors[colorIndex];
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div className="text-center">
        {/* Game Mode Display */}
        {showGameMode && (
          <div className="mb-8 animate-fade-in">
            <div className="text-4xl font-bold text-white mb-2">
              {gameMode} Mode
            </div>
            <div className="text-gray-400 text-lg">
              Prepare for battle!
            </div>
          </div>
        )}

        {/* Players Section */}
        <div className="flex items-center justify-center space-x-16 mb-8">
          {/* Player 1 */}
          <div className={`text-center transform transition-all duration-1000 ${
            animationPhase >= 1 ? 'translate-x-0 opacity-100' : '-translate-x-20 opacity-0'
          }`}>
            <div className="relative">
              {player1.avatar_url ? (
                <img
                  src={player1.avatar_url}
                  alt={player1.username}
                  className="w-24 h-24 rounded-full border-4 border-white shadow-lg"
                />
              ) : (
                <div className={`w-24 h-24 rounded-full border-4 border-white shadow-lg flex items-center justify-center ${getDefaultAvatar(player1.username)}`}>
                  <span className="text-2xl font-bold text-white">
                    {player1.username.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-indigo-600 text-white px-3 py-1 rounded-full text-xs font-bold">
                YOU
              </div>
            </div>
            <div className="mt-4">
              <div className="text-xl font-bold text-white">{player1.username}</div>
              <div className="text-sm text-gray-400">{player1.college || 'Unknown College'}</div>
            </div>
          </div>

          {/* VS Text */}
          {showVS && (
            <div className="animate-pulse">
              <div className="text-8xl font-bold text-red-500 animate-bounce">
                VS
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                Battle
              </div>
            </div>
          )}

          {/* Player 2 */}
          <div className={`text-center transform transition-all duration-1000 ${
            animationPhase >= 1 ? 'translate-x-0 opacity-100' : 'translate-x-20 opacity-0'
          }`}>
            <div className="relative">
              {player2.avatar_url ? (
                <img
                  src={player2.avatar_url}
                  alt={player2.username}
                  className="w-24 h-24 rounded-full border-4 border-white shadow-lg"
                />
              ) : (
                <div className={`w-24 h-24 rounded-full border-4 border-white shadow-lg flex items-center justify-center ${getDefaultAvatar(player2.username)}`}>
                  <span className="text-2xl font-bold text-white">
                    {player2.username.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-3 py-1 rounded-full text-xs font-bold">
                OPPONENT
              </div>
            </div>
            <div className="mt-4">
              <div className="text-xl font-bold text-white">{player2.username}</div>
              <div className="text-sm text-gray-400">{player2.college || 'Unknown College'}</div>
            </div>
          </div>
        </div>

        {/* Loading Animation */}
        {animationPhase < 3 && (
          <div className="flex justify-center">
            <div className="flex space-x-2">
              <div className="w-3 h-3 bg-white rounded-full animate-bounce"></div>
              <div className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        )}

        {/* Countdown */}
        {animationPhase === 3 && (
          <div className="text-6xl font-bold text-white animate-pulse">
            Starting in 3...
          </div>
        )}
      </div>
    </div>
  );
};

export default VSAnimation; 