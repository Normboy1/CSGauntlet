import React, { useState, useEffect } from 'react';
import SoundEffects from './SoundEffects';

interface GameResultAnimationProps {
  isWinner: boolean;
  playerScore: number;
  opponentScore: number;
  playerName: string;
  opponentName: string;
  gameMode?: string;
  onAnimationComplete?: () => void;
  additionalStats?: Record<string, any>;
}

const GameResultAnimation: React.FC<GameResultAnimationProps> = ({
  isWinner,
  playerScore,
  opponentScore,
  playerName,
  opponentName,
  gameMode = 'Game',
  onAnimationComplete,
  additionalStats = {}
}) => {
  const [animationPhase, setAnimationPhase] = useState<'intro' | 'scores' | 'result' | 'celebration'>('intro');
  const [displayPlayerScore, setDisplayPlayerScore] = useState(0);
  const [displayOpponentScore, setDisplayOpponentScore] = useState(0);
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];

    // Phase 1: Intro (0-1s)
    timers.push(setTimeout(() => setAnimationPhase('scores'), 1000));

    // Phase 2: Score counting animation (1-3s)
    timers.push(setTimeout(() => {
      animateScore(playerScore, setDisplayPlayerScore, 1500);
      animateScore(opponentScore, setDisplayOpponentScore, 1500);
    }, 1200));

    // Phase 3: Result reveal (3-4s)
    timers.push(setTimeout(() => setAnimationPhase('result'), 3000));

    // Phase 4: Celebration (4-6s)
    timers.push(setTimeout(() => {
      setAnimationPhase('celebration');
      if (isWinner) {
        setShowConfetti(true);
      }
    }, 4000));

    // Complete animation (6s)
    timers.push(setTimeout(() => {
      onAnimationComplete?.();
    }, 6000));

    return () => timers.forEach(clearTimeout);
  }, [isWinner, playerScore, opponentScore, onAnimationComplete]);

  const animateScore = (
    targetScore: number, 
    setter: React.Dispatch<React.SetStateAction<number>>, 
    duration: number
  ) => {
    const steps = 60;
    const increment = targetScore / steps;
    const stepDuration = duration / steps;
    let currentScore = 0;

    const timer = setInterval(() => {
      currentScore += increment;
      if (currentScore >= targetScore) {
        setter(targetScore);
        clearInterval(timer);
      } else {
        setter(Math.floor(currentScore));
      }
    }, stepDuration);
  };

  const Confetti = () => (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-50">
      {[...Array(50)].map((_, i) => (
        <div
          key={i}
          className="absolute animate-pulse"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 3}s`,
            animationDuration: `${2 + Math.random() * 3}s`,
          }}
        >
          <div className={`w-2 h-2 rounded-full ${
            ['bg-yellow-400', 'bg-green-400', 'bg-blue-400', 'bg-purple-400', 'bg-red-400'][Math.floor(Math.random() * 5)]
          } animate-bounce`} />
        </div>
      ))}
    </div>
  );

  const ParticleEffect = ({ color, count = 20 }: { color: string; count?: number }) => (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(count)].map((_, i) => (
        <div
          key={i}
          className={`absolute w-1 h-1 ${color} rounded-full animate-ping`}
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 2}s`,
            animationDuration: `${1 + Math.random() * 2}s`,
          }}
        />
      ))}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-95 flex items-center justify-center z-50">
      <SoundEffects isWinner={isWinner} phase={animationPhase} />
      {showConfetti && <Confetti />}
      
      <div className="text-center text-white max-w-4xl mx-auto px-4">
        {/* Phase 1: Intro */}
        {animationPhase === 'intro' && (
          <div className="animate-fade-in">
            <h1 className="text-6xl font-bold mb-4 animate-pulse">
              {gameMode} Complete!
            </h1>
            <div className="text-2xl text-gray-400">
              Calculating results...
            </div>
          </div>
        )}

        {/* Phase 2: Scores */}
        {animationPhase === 'scores' && (
          <div className="animate-slide-up space-y-8">
            <h1 className="text-4xl font-bold mb-8">Final Scores</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Player Score */}
              <div className="bg-gradient-to-br from-purple-600 to-purple-800 rounded-xl p-8 relative overflow-hidden">
                <ParticleEffect color="bg-purple-300" count={15} />
                <div className="relative z-10">
                  <div className="text-sm text-purple-200 mb-2">You</div>
                  <div className="text-2xl font-bold mb-4">{playerName}</div>
                  <div className="text-6xl font-black text-yellow-400 mb-2">
                    {displayPlayerScore}
                  </div>
                  <div className="text-sm text-purple-200">Points</div>
                </div>
              </div>

              {/* Opponent Score */}
              <div className="bg-gradient-to-br from-gray-600 to-gray-800 rounded-xl p-8 relative overflow-hidden">
                <ParticleEffect color="bg-gray-300" count={15} />
                <div className="relative z-10">
                  <div className="text-sm text-gray-200 mb-2">Opponent</div>
                  <div className="text-2xl font-bold mb-4">{opponentName}</div>
                  <div className="text-6xl font-black text-blue-400 mb-2">
                    {displayOpponentScore}
                  </div>
                  <div className="text-sm text-gray-200">Points</div>
                </div>
              </div>
            </div>

            {/* Additional Stats */}
            {Object.keys(additionalStats).length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
                {Object.entries(additionalStats).map(([key, value]) => (
                  <div key={key} className="bg-gray-800 rounded-lg p-4">
                    <div className="text-sm text-gray-400 mb-1">{key}</div>
                    <div className="text-xl font-bold">{value}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Phase 3: Result */}
        {animationPhase === 'result' && (
          <div className={`animate-zoom-in ${isWinner ? 'animate-bounce' : ''}`}>
            <div className={`text-8xl font-black mb-6 ${
              isWinner 
                ? 'text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-600' 
                : 'text-gray-400'
            }`}>
              {isWinner ? 'VICTORY!' : 'DEFEAT'}
            </div>
            
            <div className={`text-2xl mb-8 ${isWinner ? 'text-green-400' : 'text-red-400'}`}>
              {isWinner 
                ? '🎉 Congratulations! You won!' 
                : '💪 Good effort! Better luck next time!'
              }
            </div>

            <div className="text-lg text-gray-300">
              {isWinner 
                ? `You scored ${playerScore} points and defeated ${opponentName}!`
                : `You scored ${playerScore} points. ${opponentName} scored ${opponentScore}.`
              }
            </div>
          </div>
        )}

        {/* Phase 4: Celebration */}
        {animationPhase === 'celebration' && (
          <div className="animate-fade-in">
            {isWinner ? (
              <div className="space-y-6">
                <div className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-600 animate-pulse">
                  🏆 CHAMPION! 🏆
                </div>
                <div className="text-xl text-green-400">
                  Your rank has increased!
                </div>
                <div className="flex justify-center space-x-4 text-4xl animate-bounce">
                  <span>🎉</span>
                  <span>⭐</span>
                  <span>🎊</span>
                  <span>⭐</span>
                  <span>🎉</span>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="text-4xl text-blue-400">
                  Keep practicing to improve!
                </div>
                <div className="text-lg text-gray-300">
                  Every game makes you stronger 💪
                </div>
                <div className="flex justify-center space-x-4 text-2xl">
                  <span>📚</span>
                  <span>💡</span>
                  <span>🚀</span>
                </div>
              </div>
            )}

            <div className="mt-8 text-sm text-gray-400">
              Returning to dashboard...
            </div>
          </div>
        )}
      </div>

      {/* Custom CSS for animations */}
      <style jsx>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes slide-up {
          from { 
            opacity: 0; 
            transform: translateY(50px); 
          }
          to { 
            opacity: 1; 
            transform: translateY(0); 
          }
        }
        
        @keyframes zoom-in {
          from { 
            opacity: 0; 
            transform: scale(0.5); 
          }
          to { 
            opacity: 1; 
            transform: scale(1); 
          }
        }
        
        .animate-fade-in {
          animation: fade-in 0.8s ease-out;
        }
        
        .animate-slide-up {
          animation: slide-up 1s ease-out;
        }
        
        .animate-zoom-in {
          animation: zoom-in 0.6s ease-out;
        }
      `}</style>
    </div>
  );
};

export default GameResultAnimation;