import { useEffect } from 'react';

interface SoundEffectsProps {
  isWinner: boolean;
  phase: 'intro' | 'scores' | 'result' | 'celebration';
}

const SoundEffects: React.FC<SoundEffectsProps> = ({ isWinner, phase }) => {
  useEffect(() => {
    // We can use Web Audio API to create simple sound effects
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    
    const playTone = (frequency: number, duration: number, delay: number = 0) => {
      setTimeout(() => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + duration);
      }, delay);
    };

    switch (phase) {
      case 'intro':
        // Countdown sound
        playTone(800, 0.1, 0);
        playTone(800, 0.1, 100);
        playTone(800, 0.1, 200);
        break;
        
      case 'scores':
        // Score counting sound
        playTone(600, 0.05, 0);
        break;
        
      case 'result':
        if (isWinner) {
          // Victory fanfare
          playTone(523, 0.2, 0);   // C
          playTone(659, 0.2, 200); // E
          playTone(784, 0.2, 400); // G
          playTone(1047, 0.4, 600); // C
        } else {
          // Defeat sound
          playTone(400, 0.3, 0);
          playTone(350, 0.3, 150);
          playTone(300, 0.5, 300);
        }
        break;
        
      case 'celebration':
        if (isWinner) {
          // Celebration chimes
          playTone(1047, 0.1, 0);
          playTone(1319, 0.1, 100);
          playTone(1568, 0.1, 200);
          playTone(2093, 0.2, 300);
        }
        break;
    }
  }, [phase, isWinner]);

  return null; // This component doesn't render anything
};

export default SoundEffects;