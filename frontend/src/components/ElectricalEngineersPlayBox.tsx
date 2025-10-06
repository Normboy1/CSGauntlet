import React, { useState, useRef, useCallback, useEffect } from 'react';

// Grid configuration
const GRID_SIZE = 20;
const CANVAS_WIDTH = 1200;
const CANVAS_HEIGHT = 800;

// Component types with connection points and prerequisites
const COMPONENT_TYPES = {
  // Power Components (Tier 0 - Always available)
  vcc: {
    label: 'VCC (+5V)',
    symbol: '+',
    width: 30,
    height: 30,
    pins: [
      { id: 'output', x: 0, y: 15, label: '+5V' }
    ],
    color: '#FF0000',
    tier: 0,
    prerequisites: [],
    description: 'Power supply - provides +5V for circuits'
  },
  gnd: {
    label: 'Ground',
    symbol: '⏚',
    width: 30,
    height: 30,
    pins: [
      { id: 'input', x: 0, y: -15, label: 'GND' }
    ],
    color: '#000000',
    tier: 0,
    prerequisites: [],
    description: 'Ground reference point'
  },
  
  // Basic Components (Tier 0)
  resistor: {
    label: 'Resistor',
    symbol: 'R',
    width: 60,
    height: 20,
    pins: [
      { id: 'pin1', x: -30, y: 0, label: '1' },
      { id: 'pin2', x: 30, y: 0, label: '2' }
    ],
    color: '#8B4513',
    tier: 0,
    prerequisites: [],
    description: 'Basic resistor component'
  },
  capacitor: {
    label: 'Capacitor',
    symbol: 'C',
    width: 40,
    height: 30,
    pins: [
      { id: 'pin1', x: -20, y: 0, label: '+' },
      { id: 'pin2', x: 20, y: 0, label: '-' }
    ],
    color: '#4169E1',
    tier: 0,
    prerequisites: [],
    description: 'Basic capacitor component'
  },
  led: {
    label: 'LED',
    symbol: 'D',
    width: 30,
    height: 30,
    pins: [
      { id: 'anode', x: -15, y: 0, label: 'A' },
      { id: 'cathode', x: 15, y: 0, label: 'K' }
    ],
    color: '#FFD700',
    tier: 0,
    prerequisites: [],
    description: 'Light emitting diode'
  },
  
  // Logic Gates (Tier 1 - Requires power)
  and_gate: {
    label: 'AND Gate',
    symbol: '&',
    width: 60,
    height: 40,
    pins: [
      { id: 'input1', x: -30, y: -10, label: 'A' },
      { id: 'input2', x: -30, y: 10, label: 'B' },
      { id: 'output', x: 30, y: 0, label: 'Y' }
    ],
    color: '#32CD32',
    tier: 1,
    prerequisites: ['vcc', 'gnd'],
    description: 'Logic AND gate'
  },
  or_gate: {
    label: 'OR Gate',
    symbol: '≥1',
    width: 60,
    height: 40,
    pins: [
      { id: 'input1', x: -30, y: -10, label: 'A' },
      { id: 'input2', x: -30, y: 10, label: 'B' },
      { id: 'output', x: 30, y: 0, label: 'Y' }
    ],
    color: '#FF6347',
    tier: 1,
    prerequisites: ['vcc', 'gnd'],
    description: 'Logic OR gate'
  },
  not_gate: {
    label: 'NOT Gate',
    symbol: '!',
    width: 40,
    height: 30,
    pins: [
      { id: 'input', x: -20, y: 0, label: 'A' },
      { id: 'output', x: 20, y: 0, label: 'Y' }
    ],
    color: '#9370DB',
    tier: 1,
    prerequisites: ['vcc', 'gnd'],
    description: 'Logic NOT gate (inverter)'
  },
  xor_gate: {
    label: 'XOR Gate',
    symbol: '⊕',
    width: 60,
    height: 40,
    pins: [
      { id: 'input1', x: -30, y: -10, label: 'A' },
      { id: 'input2', x: -30, y: 10, label: 'B' },
      { id: 'output', x: 30, y: 0, label: 'Y' }
    ],
    color: '#FF69B4',
    tier: 1,
    prerequisites: ['vcc', 'gnd'],
    description: 'Logic XOR gate'
  },
  
  // Sequential Logic (Tier 2 - Requires logic gates)
  flip_flop: {
    label: 'D Flip-Flop',
    symbol: 'FF',
    width: 80,
    height: 60,
    pins: [
      { id: 'D', x: -40, y: -20, label: 'D' },
      { id: 'CLK', x: -40, y: 0, label: 'CLK' },
      { id: 'Q', x: 40, y: -20, label: 'Q' },
      { id: 'Qn', x: 40, y: 20, label: 'Q̄' }
    ],
    color: '#20B2AA',
    tier: 2,
    prerequisites: ['vcc', 'gnd', 'and_gate'],
    description: 'D-type flip-flop for memory'
  },
  clock: {
    label: 'Clock Generator',
    symbol: '⏰',
    width: 40,
    height: 30,
    pins: [
      { id: 'output', x: 20, y: 0, label: 'CLK' }
    ],
    color: '#FFB6C1',
    tier: 1,
    prerequisites: ['vcc', 'gnd'],
    description: 'Clock signal generator'
  },
  
  // Complex Components (Tier 3 - Requires flip-flops)
  counter: {
    label: '4-bit Counter',
    symbol: 'CTR',
    width: 80,
    height: 50,
    pins: [
      { id: 'clk_in', x: -40, y: 0, label: 'CLK' },
      { id: 'reset', x: -40, y: 20, label: 'RST' },
      { id: 'q0', x: 40, y: -20, label: 'Q0' },
      { id: 'q1', x: 40, y: -10, label: 'Q1' },
      { id: 'q2', x: 40, y: 10, label: 'Q2' },
      { id: 'q3', x: 40, y: 20, label: 'Q3' }
    ],
    color: '#DA70D6',
    tier: 3,
    prerequisites: ['vcc', 'gnd', 'flip_flop', 'clock'],
    description: '4-bit binary counter'
  }
};

// Engineering challenge definitions
const CHALLENGES = [
  {
    id: 'basic_led',
    title: 'Light an LED',
    description: 'Create a simple circuit to light an LED using power, resistor, and ground',
    timeLimit: 180,
    requiredComponents: ['vcc', 'resistor', 'led', 'gnd'],
    verification: (components: PlacedComponent[], connections: Connection[]) => {
      const hasVcc = components.some(c => c.type === 'vcc');
      const hasLed = components.some(c => c.type === 'led');
      const hasResistor = components.some(c => c.type === 'resistor');
      const hasGnd = components.some(c => c.type === 'gnd');
      return hasVcc && hasLed && hasResistor && hasGnd;
    }
  },
  {
    id: 'logic_gate_circuit',
    title: 'Build Logic Circuit',
    description: 'Create a logic circuit using AND, OR, and NOT gates with proper power connections',
    timeLimit: 300,
    requiredComponents: ['vcc', 'gnd', 'and_gate', 'or_gate', 'not_gate'],
    verification: (components: PlacedComponent[], connections: Connection[]) => {
      const hasVcc = components.some(c => c.type === 'vcc');
      const hasGnd = components.some(c => c.type === 'gnd');
      const hasAnd = components.some(c => c.type === 'and_gate');
      const hasOr = components.some(c => c.type === 'or_gate');
      const hasNot = components.some(c => c.type === 'not_gate');
      return hasVcc && hasGnd && hasAnd && hasOr && hasNot;
    }
  },
  {
    id: 'counter_circuit',
    title: 'Build 2-Bit Counter',
    description: 'Design a 2-bit binary counter using flip-flops and clock generator',
    timeLimit: 480,
    requiredComponents: ['vcc', 'gnd', 'flip_flop', 'clock', 'not_gate'],
    verification: (components: PlacedComponent[], connections: Connection[]) => {
      const hasVcc = components.some(c => c.type === 'vcc');
      const hasGnd = components.some(c => c.type === 'gnd');
      const hasFlipFlops = components.filter(c => c.type === 'flip_flop').length >= 2;
      const hasClock = components.some(c => c.type === 'clock');
      const hasNot = components.some(c => c.type === 'not_gate');
      return hasVcc && hasGnd && hasFlipFlops && hasClock && hasNot;
    }
  }
];

interface Pin {
  id: string;
  x: number;
  y: number;
  label: string;
}

interface PlacedComponent {
  id: string;
  type: string;
  x: number;
  y: number;
  rotation: number;
}

interface Connection {
  id: string;
  fromComponent: string;
  fromPin: string;
  toComponent: string;
  toPin: string;
  points: { x: number; y: number }[];
}

interface Challenge {
  id: string;
  title: string;
  description: string;
  timeLimit: number;
  requiredComponents: string[];
  verification: (components: PlacedComponent[], connections: Connection[]) => boolean;
}

const ElectricalEngineersPlayBox: React.FC = () => {
  const [components, setComponents] = useState<PlacedComponent[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectingFrom, setConnectingFrom] = useState<{componentId: string, pinId: string} | null>(null);
  const [currentChallenge, setCurrentChallenge] = useState<Challenge | null>(null);
  const [challengeStartTime, setChallengeStartTime] = useState<number | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  const [challengeCompleted, setChallengeCompleted] = useState(false);
  const [unlockedTiers, setUnlockedTiers] = useState<Set<number>>(new Set([0])); // Tier 0 always unlocked
  const canvasRef = useRef<HTMLDivElement>(null);

  // Snap to grid function
  const snapToGrid = (value: number) => Math.round(value / GRID_SIZE) * GRID_SIZE;

  // Check if component can be placed based on prerequisites
  const canPlaceComponent = (componentType: string) => {
    const component = COMPONENT_TYPES[componentType as keyof typeof COMPONENT_TYPES];
    if (!component) return false;
    
    // Check if tier is unlocked
    if (!unlockedTiers.has(component.tier)) return false;
    
    // Check prerequisites
    return component.prerequisites.every(prereq => 
      components.some(c => c.type === prereq)
    );
  };

  // Update unlocked tiers based on placed components
  useEffect(() => {
    const newUnlockedTiers = new Set([0]); // Always have tier 0
    
    // Check what components we have
    const placedTypes = new Set(components.map(c => c.type));
    
    // Unlock tiers based on prerequisites
    if (placedTypes.has('vcc') && placedTypes.has('gnd')) {
      newUnlockedTiers.add(1); // Logic gates
    }
    if (placedTypes.has('and_gate') || placedTypes.has('or_gate')) {
      newUnlockedTiers.add(2); // Sequential logic
    }
    if (placedTypes.has('flip_flop') && placedTypes.has('clock')) {
      newUnlockedTiers.add(3); // Complex components
    }
    
    setUnlockedTiers(newUnlockedTiers);
  }, [components]);

  // Timer effect
  useEffect(() => {
    if (challengeStartTime && timeRemaining !== null && timeRemaining > 0 && !challengeCompleted) {
      const timer = setInterval(() => {
        const elapsed = Date.now() - challengeStartTime;
        const remaining = Math.max(0, (currentChallenge?.timeLimit || 0) * 1000 - elapsed);
        setTimeRemaining(remaining);
        
        if (remaining === 0) {
          alert('Time\'s up! Challenge failed!');
          endChallenge();
        }
      }, 100);
      
      return () => clearInterval(timer);
    }
  }, [challengeStartTime, timeRemaining, challengeCompleted, currentChallenge]);

  // Check challenge completion
  useEffect(() => {
    if (currentChallenge && !challengeCompleted) {
      const isComplete = currentChallenge.verification(components, connections);
      if (isComplete) {
        setChallengeCompleted(true);
        const elapsed = Date.now() - (challengeStartTime || Date.now());
        const timeUsed = elapsed / 1000;
        alert(`Challenge completed in ${timeUsed.toFixed(1)} seconds!`);
      }
    }
  }, [components, connections, currentChallenge, challengeCompleted, challengeStartTime]);

  const startChallenge = (challenge: Challenge) => {
    setComponents([]);
    setConnections([]);
    setCurrentChallenge(challenge);
    setChallengeStartTime(Date.now());
    setTimeRemaining(challenge.timeLimit * 1000);
    setChallengeCompleted(false);
    setUnlockedTiers(new Set([0])); // Reset to basic components
  };

  const endChallenge = () => {
    setCurrentChallenge(null);
    setChallengeStartTime(null);
    setTimeRemaining(null);
    setChallengeCompleted(false);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!selectedTool || !canvasRef.current) return;

    // Check if component can be placed
    if (!canPlaceComponent(selectedTool)) {
      const component = COMPONENT_TYPES[selectedTool as keyof typeof COMPONENT_TYPES];
      alert(`Cannot place ${component.label}! Prerequisites: ${component.prerequisites.join(', ') || 'None'}`);
      return;
    }

    const rect = canvasRef.current.getBoundingClientRect();
    const x = snapToGrid(e.clientX - rect.left);
    const y = snapToGrid(e.clientY - rect.top);

    const newComponent: PlacedComponent = {
      id: `${selectedTool}-${Date.now()}`,
      type: selectedTool,
      x,
      y,
      rotation: 0
    };

    setComponents(prev => [...prev, newComponent]);
    setSelectedTool(null);
  };

  const handlePinClick = (componentId: string, pinId: string) => {
    if (!isConnecting) {
      setIsConnecting(true);
      setConnectingFrom({ componentId, pinId });
    } else {
      if (connectingFrom && (connectingFrom.componentId !== componentId || connectingFrom.pinId !== pinId)) {
        const newConnection: Connection = {
          id: `conn-${Date.now()}`,
          fromComponent: connectingFrom.componentId,
          fromPin: connectingFrom.pinId,
          toComponent: componentId,
          toPin: pinId,
          points: []
        };
        setConnections(prev => [...prev, newConnection]);
      }
      setIsConnecting(false);
      setConnectingFrom(null);
    }
  };

  const deleteComponent = (componentId: string) => {
    setComponents(prev => prev.filter(c => c.id !== componentId));
    setConnections(prev => prev.filter(c => 
      c.fromComponent !== componentId && c.toComponent !== componentId
    ));
  };

  const rotateComponent = (componentId: string) => {
    setComponents(prev => prev.map(c => 
      c.id === componentId ? { ...c, rotation: (c.rotation + 90) % 360 } : c
    ));
  };

  const renderGrid = () => {
    const lines = [];
    for (let x = 0; x <= CANVAS_WIDTH; x += GRID_SIZE) {
      lines.push(
        <line key={`v-${x}`} x1={x} y1={0} x2={x} y2={CANVAS_HEIGHT} stroke="#2a2a2a" strokeWidth={1} />
      );
    }
    for (let y = 0; y <= CANVAS_HEIGHT; y += GRID_SIZE) {
      lines.push(
        <line key={`h-${y}`} x1={0} y1={y} x2={CANVAS_WIDTH} y2={y} stroke="#2a2a2a" strokeWidth={1} />
      );
    }
    return lines;
  };

  const renderComponent = (component: PlacedComponent) => {
    const componentType = COMPONENT_TYPES[component.type as keyof typeof COMPONENT_TYPES];
    if (!componentType) return null;

    return (
      <g key={component.id} transform={`translate(${component.x}, ${component.y}) rotate(${component.rotation})`}>
        {/* Component body */}
        <rect
          x={-componentType.width / 2}
          y={-componentType.height / 2}
          width={componentType.width}
          height={componentType.height}
          fill={componentType.color}
          stroke="#ffffff"
          strokeWidth={2}
          className="cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedComponent(component.id);
          }}
          onDoubleClick={(e) => {
            e.stopPropagation();
            rotateComponent(component.id);
          }}
          onContextMenu={(e) => {
            e.preventDefault();
            deleteComponent(component.id);
          }}
        />
        
        {/* Component label */}
        <text
          x={0}
          y={0}
          textAnchor="middle"
          dominantBaseline="central"
          fill="white"
          fontSize="12"
          fontWeight="bold"
          pointerEvents="none"
        >
          {componentType.symbol}
        </text>

        {/* Component pins */}
        {componentType.pins.map(pin => (
          <g key={pin.id}>
            <circle
              cx={pin.x}
              cy={pin.y}
              r={4}
              fill="#ffff00"
              stroke="#000000"
              strokeWidth={1}
              className="cursor-crosshair"
              onClick={(e) => {
                e.stopPropagation();
                handlePinClick(component.id, pin.id);
              }}
            />
            <text
              x={pin.x}
              y={pin.y - 8}
              textAnchor="middle"
              fill="white"
              fontSize="8"
              pointerEvents="none"
            >
              {pin.label}
            </text>
          </g>
        ))}
      </g>
    );
  };

  const renderConnection = (connection: Connection) => {
    const fromComponent = components.find(c => c.id === connection.fromComponent);
    const toComponent = components.find(c => c.id === connection.toComponent);
    
    if (!fromComponent || !toComponent) return null;

    const fromType = COMPONENT_TYPES[fromComponent.type as keyof typeof COMPONENT_TYPES];
    const toType = COMPONENT_TYPES[toComponent.type as keyof typeof COMPONENT_TYPES];
    
    const fromPin = fromType?.pins.find(p => p.id === connection.fromPin);
    const toPin = toType?.pins.find(p => p.id === connection.toPin);
    
    if (!fromPin || !toPin) return null;

    const x1 = fromComponent.x + fromPin.x;
    const y1 = fromComponent.y + fromPin.y;
    const x2 = toComponent.x + toPin.x;
    const y2 = toComponent.y + toPin.y;

    return (
      <line
        key={connection.id}
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="#00ff00"
        strokeWidth={2}
        onClick={(e) => {
          e.stopPropagation();
          setConnections(prev => prev.filter(c => c.id !== connection.id));
        }}
        className="cursor-pointer"
      />
    );
  };

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTierLabel = (tier: number) => {
    switch (tier) {
      case 0: return 'Basic Components';
      case 1: return 'Logic Gates';
      case 2: return 'Sequential Logic';
      case 3: return 'Complex Circuits';
      default: return `Tier ${tier}`;
    }
  };

  // Group components by tier
  const componentsByTier = Object.entries(COMPONENT_TYPES).reduce((acc, [type, config]) => {
    if (!acc[config.tier]) acc[config.tier] = [];
    acc[config.tier].push({ type, config });
    return acc;
  }, {} as Record<number, Array<{ type: string, config: any }>>);

  return (
    <div className="flex h-full w-full bg-gray-900 text-white">
      {/* Toolbox */}
      <div className="w-80 bg-gray-800 p-4 flex flex-col gap-4 border-r border-gray-700">
        <h2 className="text-lg font-bold mb-2">⚡ Circuit Design Lab</h2>
        
        {/* Circuit Status */}
        <div className="mb-4 p-3 bg-gray-700 rounded">
          <h3 className="font-semibold mb-2">🔌 Power Status</h3>
          <div className="space-y-1 text-xs">
            <div className={`flex items-center space-x-2 ${components.some(c => c.type === 'vcc') ? 'text-green-400' : 'text-yellow-400'}`}>
              <span>{components.some(c => c.type === 'vcc') ? '✅' : '🔄'}</span>
              <span>Power Supply (+5V)</span>
            </div>
            <div className={`flex items-center space-x-2 ${components.some(c => c.type === 'gnd') ? 'text-green-400' : 'text-gray-500'}`}>
              <span>{components.some(c => c.type === 'gnd') ? '✅' : '⏳'}</span>
              <span>Ground Reference</span>
            </div>
            <div className={`flex items-center space-x-2 ${components.some(c => c.type === 'flip_flop') ? 'text-green-400' : 'text-gray-500'}`}>
              <span>{components.some(c => c.type === 'flip_flop') ? '✅' : '⏳'}</span>
              <span>Memory Elements</span>
            </div>
          </div>
        </div>

        {/* Engineering Challenges */}
        <div className="mb-4 p-3 bg-gray-700 rounded">
          <h3 className="font-semibold mb-2">🎯 Engineering Challenges</h3>
          {currentChallenge ? (
            <div>
              <div className="text-sm text-green-400 mb-1">{currentChallenge.title}</div>
              <div className="text-xs text-gray-300 mb-2">{currentChallenge.description}</div>
              {timeRemaining !== null && (
                <div className={`text-sm font-mono ${timeRemaining < 30000 ? 'text-red-400' : 'text-yellow-400'}`}>
                  Time: {formatTime(timeRemaining)}
                </div>
              )}
              <button
                onClick={endChallenge}
                className="mt-2 px-2 py-1 bg-red-600 text-xs rounded hover:bg-red-700"
              >
                End Challenge
              </button>
            </div>
          ) : (
            <div className="space-y-1">
              {CHALLENGES.map(challenge => (
                <button
                  key={challenge.id}
                  onClick={() => startChallenge(challenge)}
                  className="w-full text-left p-2 bg-gray-600 rounded text-xs hover:bg-gray-500"
                >
                  <div className="font-semibold">{challenge.title}</div>
                  <div className="text-gray-300">{formatTime(challenge.timeLimit * 1000)}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Components by Tier */}
        <div className="flex-1 overflow-y-auto">
          <div className="space-y-3">
            {Object.entries(componentsByTier)
              .sort(([a], [b]) => parseInt(a) - parseInt(b))
              .map(([tier, components]) => (
                <div key={tier}>
                  <h4 className={`text-sm font-semibold mb-2 ${unlockedTiers.has(parseInt(tier)) ? 'text-blue-400' : 'text-gray-500'}`}>
                    {unlockedTiers.has(parseInt(tier)) ? '🔓' : '🔒'} {getTierLabel(parseInt(tier))}
                  </h4>
                  <div className="space-y-1">
                    {components.map(({ type, config }) => {
                      const canPlace = canPlaceComponent(type);
                      return (
                        <button
                          key={type}
                          onClick={() => setSelectedTool(selectedTool === type ? null : type)}
                          disabled={!canPlace}
                          className={`w-full text-left p-2 rounded transition-colors ${
                            selectedTool === type
                              ? 'bg-blue-600 text-white'
                              : canPlace
                              ? 'bg-gray-700 hover:bg-gray-600'
                              : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                          }`}
                          title={canPlace ? config.description : `Prerequisites: ${config.prerequisites.join(', ') || 'None'}`}
                        >
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-4 h-4 rounded"
                              style={{ backgroundColor: canPlace ? config.color : '#555' }}
                            />
                            <span className="text-sm">{config.label}</span>
                            {!canPlace && <span className="text-xs ml-auto">🔒</span>}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Tools */}
        <div className="mt-4 pt-4 border-t border-gray-700">
          <button
            onClick={() => setIsConnecting(!isConnecting)}
            className={`w-full p-2 rounded mb-2 ${
              isConnecting ? 'bg-green-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {isConnecting ? 'Connecting...' : '🔗 Wire Tool'}
          </button>
          <button
            onClick={() => {
              setComponents([]);
              setConnections([]);
              setUnlockedTiers(new Set([0]));
            }}
            className="w-full p-2 bg-red-600 rounded hover:bg-red-700"
          >
            🗑️ Clear All
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <div
          ref={canvasRef}
          className="w-full h-full overflow-auto cursor-crosshair"
          onClick={handleCanvasClick}
        >
          <svg width={CANVAS_WIDTH} height={CANVAS_HEIGHT} className="absolute top-0 left-0">
            {/* Grid */}
            {renderGrid()}
            
            {/* Connections */}
            {connections.map(renderConnection)}
            
            {/* Components */}
            {components.map(renderComponent)}
          </svg>
        </div>

        {/* Status bar */}
        <div className="absolute bottom-0 left-0 right-0 bg-gray-800 p-2 text-sm">
          <div className="flex justify-between items-center">
            <div>
              Components: {components.length} | Connections: {connections.length}
              {selectedTool && (
                <span className="ml-4 text-blue-400">
                  Selected: {COMPONENT_TYPES[selectedTool as keyof typeof COMPONENT_TYPES]?.label}
                </span>
              )}
            </div>
            <div className="text-gray-400">
              Right-click to delete | Double-click to rotate | Click pins to connect
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ElectricalEngineersPlayBox; 