import React from 'react';

interface MatchmakingModalProps {
  mode: 'classic' | 'custom' | 'blitz' | 'practice' | 'ranked' | 'casual' | 'trivia' | 'debug' | 'electrical';
  onCancel: () => void;
}

const MatchmakingModal: React.FC<MatchmakingModalProps> = ({ mode, onCancel }) => {
  const getModeIcon = (mode: string) => {
    const icons = {
      classic: '⚔️',
      custom: '🎮',
      blitz: '⚡',
      practice: '🎯',
      ranked: '🏆',
      casual: '😊',
      trivia: '🧠',
      debug: '🐛',
      electrical: '⚡'
    };
    return icons[mode as keyof typeof icons] || '🎮';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-8 max-w-md w-full mx-4 animate-fade-in">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <span className="text-3xl mr-3">{getModeIcon(mode)}</span>
            <h3 className="text-2xl font-bold text-white">
              Finding {mode.charAt(0).toUpperCase() + mode.slice(1)} Match
            </h3>
          </div>
          
          <div className="relative w-24 h-24 mx-auto mb-4">
            <div 
              className="w-full h-full border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"
              style={{ animationDuration: '2s' }}
            />
            <div 
              className="absolute top-2 left-2 right-2 bottom-2 border-4 border-purple-500 rounded-full border-t-transparent animate-spin"
              style={{ animationDuration: '1.5s', animationDirection: 'reverse' }}
            />
          </div>

          <p className="text-gray-300 mb-6">
            Searching for opponents...
          </p>

          <button
            onClick={onCancel}
            className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors hover:scale-105 active:scale-95"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default MatchmakingModal;
