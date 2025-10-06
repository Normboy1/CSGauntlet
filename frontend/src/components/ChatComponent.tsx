import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { io, Socket } from 'socket.io-client';

interface ChatMessage {
  id: string;
  userId: string;
  username: string;
  message: string;
  timestamp: string;
  type: 'message' | 'system' | 'join' | 'leave';
}

interface TypingUser {
  userId: string;
  username: string;
}

interface ChatComponentProps {
  gameId: string;
  gameMode: string;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
  className?: string;
}

const ChatComponent: React.FC<ChatComponentProps> = ({
  gameId,
  gameMode,
  isMinimized = false,
  onToggleMinimize,
  className = ''
}) => {
  const { user } = useAuth();
  const [socket, setSocket] = useState<Socket | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Common emojis for quick reactions
  const quickEmojis = ['👍', '👎', '😄', '😢', '😮', '❤️', '🔥', '💯'];

  // Sound notification function
  const playNotificationSound = () => {
    if (soundEnabled && !isMinimized) {
      // Create a simple notification sound using Web Audio API
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    }
  };

  useEffect(() => {
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    const connectSocket = () => {
      // Initialize socket connection
      const newSocket = io('http://localhost:5010', {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: 1000 * (reconnectAttempts + 1), // Exponential backoff
        timeout: 10000
      });

      setSocket(newSocket);

      // Socket event listeners
      newSocket.on('connect', () => {
        setIsConnected(true);
        setConnectionAttempts(0);
        reconnectAttempts = 0;
        console.log('Connected to chat server');
        
        // Join the game room
        newSocket.emit('join_game_chat', {
          gameId,
          userId: user?.id,
          username: user?.username,
          gameMode
        });
      });

      newSocket.on('disconnect', () => {
        setIsConnected(false);
        console.log('Disconnected from chat server');
      });

      newSocket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        setConnectionAttempts(prev => prev + 1);
        
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          reconnectTimeoutRef.current = setTimeout(() => {
            connectSocket();
          }, 1000 * reconnectAttempts);
        }
      });

      newSocket.on('chat_message', (data: ChatMessage) => {
        setMessages(prev => [...prev, data]);
        
        // Play notification sound for new messages
        if (data.userId !== user?.id) {
          playNotificationSound();
        }
        
        // Increment unread count if chat is minimized and message is not from current user
        if (isMinimized && data.userId !== user?.id) {
          setUnreadCount(prev => prev + 1);
        }
      });

      newSocket.on('chat_history', (data: { messages: ChatMessage[]; users: any[] }) => {
        setMessages(data.messages);
        console.log('Chat history loaded:', data.messages.length, 'messages');
      });

      newSocket.on('user_typing', (data: { userId: string; username: string; isTyping: boolean }) => {
        if (data.userId !== user?.id) {
          setTypingUsers(prev => {
            if (data.isTyping) {
              // Add user to typing list if not already there
              if (!prev.find(u => u.userId === data.userId)) {
                return [...prev, { userId: data.userId, username: data.username }];
              }
            } else {
              // Remove user from typing list
              return prev.filter(u => u.userId !== data.userId);
            }
            return prev;
          });
        }
      });

      newSocket.on('user_joined', (data: { userId: string; username: string }) => {
        const systemMessage: ChatMessage = {
          id: `system-${Date.now()}`,
          userId: 'system',
          username: 'System',
          message: `${data.username} joined the game`,
          timestamp: new Date().toISOString(),
          type: 'join'
        };
        setMessages(prev => [...prev, systemMessage]);
      });

      newSocket.on('user_left', (data: { userId: string; username: string }) => {
        const systemMessage: ChatMessage = {
          id: `system-${Date.now()}`,
          userId: 'system',
          username: 'System',
          message: `${data.username} left the game`,
          timestamp: new Date().toISOString(),
          type: 'leave'
        };
        setMessages(prev => [...prev, systemMessage]);
      });

      newSocket.on('error', (error: { message: string }) => {
        console.error('Socket error:', error.message);
      });

      return newSocket;
    };

    const newSocket = connectSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      newSocket.disconnect();
    };
  }, [gameId, gameMode, user, isMinimized, soundEnabled]);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Reset unread count when chat is opened
    if (!isMinimized) {
      setUnreadCount(0);
    }
  }, [isMinimized]);

  useEffect(() => {
    // Auto-focus input when chat is opened
    if (!isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isMinimized]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = () => {
    if (!socket || !inputMessage.trim() || !user) return;

    const message: ChatMessage = {
      id: `msg-${Date.now()}`,
      userId: user.id,
      username: user.username,
      message: inputMessage.trim(),
      timestamp: new Date().toISOString(),
      type: 'message'
    };

    socket.emit('send_chat_message', {
      gameId,
      message: message.message,
      userId: user.id,
      username: user.username
    });

    setInputMessage('');
    setShowEmojiPicker(false);
    stopTyping();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputMessage(e.target.value);
    handleTyping();
  };

  const handleTyping = () => {
    if (!socket || !user) return;

    if (!isTyping) {
      setIsTyping(true);
      socket.emit('user_typing', {
        gameId,
        userId: user.id,
        username: user.username,
        isTyping: true
      });
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout to stop typing after 2 seconds
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 2000);
  };

  const stopTyping = () => {
    if (socket && user && isTyping) {
      setIsTyping(false);
      socket.emit('user_typing', {
        gameId,
        userId: user.id,
        username: user.username,
        isTyping: false
      });
    }
  };

  const addEmoji = (emoji: string) => {
    setInputMessage(prev => prev + emoji);
    setShowEmojiPicker(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getMessageTypeColor = (type: string) => {
    switch (type) {
      case 'system': return 'text-gray-400';
      case 'join': return 'text-green-400';
      case 'leave': return 'text-red-400';
      default: return 'text-white';
    }
  };

  const getGameModeIcon = (mode: string) => {
    switch (mode) {
      case 'trivia': return '🧠';
      case 'debug': return '🐛';
      case 'electrical': return '⚡';
      case 'classic': return '⚔️';
      default: return '💬';
    }
  };

  const getConnectionStatus = () => {
    if (isConnected) return { color: 'bg-green-400', text: 'Connected' };
    if (connectionAttempts > 0) return { color: 'bg-yellow-400', text: 'Reconnecting...' };
    return { color: 'bg-red-400', text: 'Disconnected' };
  };

  const connectionStatus = getConnectionStatus();

  if (isMinimized) {
    return (
      <div className={`fixed bottom-4 right-4 z-50 ${className}`}>
        <button
          onClick={onToggleMinimize}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-3 shadow-lg transition-colors relative group"
        >
          <span className="text-xl">{getGameModeIcon(gameMode)}</span>
          <span className="ml-2 text-sm font-medium hidden sm:inline">Chat</span>
          {unreadCount > 0 && (
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center animate-pulse">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
          <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${connectionStatus.color}`} />
          
          {/* Tooltip */}
          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            {connectionStatus.text}
          </div>
        </button>
      </div>
    );
  }

  return (
    <div className={`flex flex-col bg-gray-800 rounded-lg shadow-lg ${className}`}>
      {/* Chat Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getGameModeIcon(gameMode)}</span>
          <h3 className="text-lg font-semibold text-white">Game Chat</h3>
          <div className={`w-2 h-2 rounded-full ${connectionStatus.color}`} title={connectionStatus.text} />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-1 rounded transition-colors ${
              soundEnabled ? 'text-green-400 hover:text-green-300' : 'text-gray-400 hover:text-gray-300'
            }`}
            title={soundEnabled ? 'Disable sound' : 'Enable sound'}
          >
            {soundEnabled ? '🔊' : '🔇'}
          </button>
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="text-gray-400 hover:text-white transition-colors"
              title="Minimize chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0" style={{ maxHeight: '400px' }}>
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <span className="text-2xl mb-2 block">💬</span>
            <p className="text-sm">No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex flex-col ${message.userId === user?.id ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg break-words ${
                  message.type === 'message'
                    ? message.userId === user?.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-600 text-white'
                    : 'bg-gray-700 text-center w-full'
                }`}
              >
                {message.type === 'message' && message.userId !== user?.id && (
                  <div className="text-xs text-gray-300 mb-1 font-medium">
                    {message.username}
                  </div>
                )}
                <div className={`text-sm ${getMessageTypeColor(message.type)}`}>
                  {message.message}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Typing Indicator */}
        {typingUsers.length > 0 && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
            <span>
              {typingUsers.length === 1
                ? `${typingUsers[0].username} is typing...`
                : `${typingUsers.length} people are typing...`}
            </span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-700">
        {/* Emoji Picker */}
        {showEmojiPicker && (
          <div className="mb-2 flex flex-wrap gap-2 p-2 bg-gray-700 rounded-lg">
            {quickEmojis.map((emoji, index) => (
              <button
                key={index}
                onClick={() => addEmoji(emoji)}
                className="text-lg hover:bg-gray-600 p-1 rounded transition-colors"
              >
                {emoji}
              </button>
            ))}
          </div>
        )}
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded-lg transition-colors"
            title="Add emoji"
          >
            😊
          </button>
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={!isConnected}
            maxLength={200}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || !isConnected}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        
        {/* Connection Status */}
        {!isConnected && (
          <div className="text-red-400 text-xs mt-2 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {connectionAttempts > 0 ? `Reconnecting... (${connectionAttempts}/5)` : 'Disconnected from chat'}
          </div>
        )}
        
        {/* Character Count */}
        <div className="text-xs text-gray-400 mt-1 text-right">
          {inputMessage.length}/200
        </div>
      </div>
    </div>
  );
};

export default ChatComponent; 