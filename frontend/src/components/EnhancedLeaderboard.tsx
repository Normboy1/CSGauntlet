import React, { useState, useEffect } from 'react';

interface LeaderboardEntry {
  user_id: number;
  username: string;
  total_points: number;
  problems_solved: number;
  average_grade: string;
  avg_score: number;
  best_categories: string[];
  streak: number;
  efficiency_rating: number;
  style_rating: number;
  rank?: number;
}

interface EnhancedLeaderboardProps {
  className?: string;
}

const EnhancedLeaderboard: React.FC<EnhancedLeaderboardProps> = ({ className = '' }) => {
  const [leaderboardData, setLeaderboardData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<'all' | 'week' | 'month'>('all');
  const [selectedType, setSelectedType] = useState<'all' | 'algorithms' | 'data_structures'>('all');
  const [sortBy, setSortBy] = useState<'points' | 'grade' | 'efficiency' | 'style'>('points');

  useEffect(() => {
    fetchLeaderboardData();
  }, [selectedPeriod, selectedType]);

  const fetchLeaderboardData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/leaderboard/detailed?period=${selectedPeriod}&type=${selectedType}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      const result = await response.json();
      if (result.success) {
        setLeaderboardData(result.leaderboard);
      }
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A+': case 'A': case 'A-': return 'text-green-400';
      case 'B+': case 'B': case 'B-': return 'text-blue-400';
      case 'C+': case 'C': case 'C-': return 'text-yellow-400';
      case 'D+': case 'D': case 'D-': return 'text-orange-400';
      default: return 'text-red-400';
    }
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1) return { emoji: '🥇', color: 'text-yellow-500', bg: 'bg-yellow-500/20' };
    if (rank === 2) return { emoji: '🥈', color: 'text-gray-400', bg: 'bg-gray-500/20' };
    if (rank === 3) return { emoji: '🥉', color: 'text-orange-400', bg: 'bg-orange-500/20' };
    return { emoji: `#${rank}`, color: 'text-gray-500', bg: 'bg-gray-700' };
  };

  const sortedData = [...leaderboardData].sort((a, b) => {
    switch (sortBy) {
      case 'points':
        return b.total_points - a.total_points;
      case 'grade':
        return b.avg_score - a.avg_score;
      case 'efficiency':
        return b.efficiency_rating - a.efficiency_rating;
      case 'style':
        return b.style_rating - a.style_rating;
      default:
        return b.total_points - a.total_points;
    }
  }).map((entry, index) => ({ ...entry, rank: index + 1 }));

  const renderStarRating = (rating: number) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    
    for (let i = 0; i < fullStars; i++) {
      stars.push('⭐');
    }
    if (hasHalfStar) {
      stars.push('✨');
    }
    while (stars.length < 5) {
      stars.push('☆');
    }
    
    return (
      <div className="flex items-center space-x-1">
        <span className="text-yellow-400">{stars.join('')}</span>
        <span className="text-sm text-gray-400">({rating.toFixed(1)})</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 text-white ${className}`}>
      {/* Header */}
      <div className="bg-gray-800 rounded-t-lg p-6">
        <h1 className="text-2xl font-bold mb-4">🏆 AI-Powered Leaderboard</h1>
        
        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Time Period</label>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value as any)}
              className="bg-gray-700 text-white px-3 py-2 rounded border border-gray-600"
            >
              <option value="all">All Time</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Problem Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as any)}
              className="bg-gray-700 text-white px-3 py-2 rounded border border-gray-600"
            >
              <option value="all">All Types</option>
              <option value="algorithms">Algorithms</option>
              <option value="data_structures">Data Structures</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-gray-700 text-white px-3 py-2 rounded border border-gray-600"
            >
              <option value="points">Total Points</option>
              <option value="grade">Average Grade</option>
              <option value="efficiency">Efficiency Rating</option>
              <option value="style">Style Rating</option>
            </select>
          </div>
        </div>
      </div>

      {/* Leaderboard Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-800 border-b border-gray-700">
            <tr>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-300">Rank</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-300">Player</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Points</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Problems</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Avg Grade</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Efficiency</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Style</th>
              <th className="px-6 py-4 text-center text-sm font-medium text-gray-300">Streak</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-gray-300">Specialties</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((entry, index) => {
              const rankBadge = getRankBadge(entry.rank!);
              return (
                <tr
                  key={entry.user_id}
                  className={`border-b border-gray-700 hover:bg-gray-800/50 transition-colors ${
                    index < 3 ? 'bg-gray-800/30' : ''
                  }`}
                >
                  {/* Rank */}
                  <td className="px-6 py-4">
                    <div className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-bold ${rankBadge.bg} ${rankBadge.color}`}>
                      {rankBadge.emoji}
                    </div>
                  </td>
                  
                  {/* Player */}
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center font-bold">
                        {entry.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium text-white">{entry.username}</div>
                        <div className="text-sm text-gray-400">User #{entry.user_id}</div>
                      </div>
                    </div>
                  </td>
                  
                  {/* Points */}
                  <td className="px-6 py-4 text-center">
                    <div className="font-bold text-lg text-green-400">
                      {entry.total_points.toLocaleString()}
                    </div>
                  </td>
                  
                  {/* Problems */}
                  <td className="px-6 py-4 text-center">
                    <div className="font-semibold text-blue-400">
                      {entry.problems_solved}
                    </div>
                  </td>
                  
                  {/* Average Grade */}
                  <td className="px-6 py-4 text-center">
                    <div className="flex flex-col items-center">
                      <span className={`font-bold text-lg ${getGradeColor(entry.average_grade)}`}>
                        {entry.average_grade}
                      </span>
                      <span className="text-sm text-gray-400">
                        {entry.avg_score.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  
                  {/* Efficiency Rating */}
                  <td className="px-6 py-4 text-center">
                    {renderStarRating(entry.efficiency_rating)}
                  </td>
                  
                  {/* Style Rating */}
                  <td className="px-6 py-4 text-center">
                    {renderStarRating(entry.style_rating)}
                  </td>
                  
                  {/* Streak */}
                  <td className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center space-x-1">
                      <span className="text-orange-400">🔥</span>
                      <span className="font-bold text-orange-400">{entry.streak}</span>
                    </div>
                  </td>
                  
                  {/* Specialties */}
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {entry.best_categories.map((category, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-purple-600/20 text-purple-300 rounded-full text-xs font-medium"
                        >
                          {category}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer Stats */}
      <div className="bg-gray-800 rounded-b-lg p-6 border-t border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-400">
              {sortedData.length}
            </div>
            <div className="text-sm text-gray-400">Total Players</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">
              {sortedData.reduce((sum, entry) => sum + entry.problems_solved, 0)}
            </div>
            <div className="text-sm text-gray-400">Problems Solved</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">
              {sortedData.length > 0 ? (sortedData.reduce((sum, entry) => sum + entry.avg_score, 0) / sortedData.length).toFixed(1) : 0}%
            </div>
            <div className="text-sm text-gray-400">Average Score</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-400">
              {sortedData.length > 0 ? Math.max(...sortedData.map(entry => entry.streak)) : 0}
            </div>
            <div className="text-sm text-gray-400">Highest Streak</div>
          </div>
        </div>
      </div>

      {sortedData.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg">No data available for the selected filters.</div>
          <div className="text-gray-500 text-sm mt-2">Try adjusting your filters or check back later.</div>
        </div>
      )}
    </div>
  );
};

export default EnhancedLeaderboard; 