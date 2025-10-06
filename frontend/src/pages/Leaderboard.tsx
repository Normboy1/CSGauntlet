import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ProfileAvatar from '../components/ProfileAvatar';

interface LeaderboardEntry {
  username: string;
  rating: number;
  rank_title: string;
  games_played: number;
  win_rate: number;
  college: string;
  profilePicture?: string | null;
}

const Leaderboard: React.FC = () => {
  const [leaderboardData, setLeaderboardData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth();

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch('/api/leaderboard', {
          method: 'GET',
          headers: {
            ...(token && { 'Authorization': `Bearer ${token}` })
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (Array.isArray(data)) {
          setLeaderboardData(data);
        } else {
          throw new Error('Invalid data format received');
        }
      } catch (err) {
        console.error('Error fetching leaderboard:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch leaderboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, [token]);

  if (loading) {
  return (
      <div className="min-h-screen bg-black text-white p-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Leaderboard</h1>
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-black text-white p-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Leaderboard</h1>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6 text-center">
            <p className="text-red-400 mb-4">Error loading leaderboard</p>
            <p className="text-gray-400 text-sm">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-4 px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Leaderboard</h1>
        
        {leaderboardData.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">No leaderboard data available</p>
          </div>
        ) : (
          <div className="bg-gray-900/50 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-purple-900/30">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Rank</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Player</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Title</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">College</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Rating</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Games</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-purple-300">Win Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {leaderboardData.map((entry, index) => (
                    <tr key={index} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
                          index === 0 ? 'bg-yellow-500 text-black' :
                          index === 1 ? 'bg-gray-400 text-black' :
                          index === 2 ? 'bg-orange-500 text-black' :
                          'bg-gray-700 text-white'
                        }`}>
                          {index + 1}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <ProfileAvatar
                            profilePicture={entry.profilePicture}
                            username={entry.username}
                            size="sm"
                            className="mr-3"
                          />
                          <span className="font-medium">{entry.username}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          entry.rank_title === 'Creator' ? 'bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-bold border-2 border-yellow-400 shadow-lg' :
                          entry.rank_title === 'Coding Sage' ? 'bg-yellow-500/20 text-yellow-400' :
                          entry.rank_title === 'Code Virtuoso' ? 'bg-purple-500/20 text-purple-400' :
                          entry.rank_title === 'Coding Master' ? 'bg-blue-500/20 text-blue-400' :
                          entry.rank_title === 'Code Ninja' ? 'bg-red-500/20 text-red-400' :
                          entry.rank_title === 'Algorithm Ace' ? 'bg-green-500/20 text-green-400' :
                          entry.rank_title === 'Logic Lord' ? 'bg-indigo-500/20 text-indigo-400' :
                          entry.rank_title === 'Coding Novice' ? 'bg-cyan-500/20 text-cyan-400' :
                          entry.rank_title === 'Vibe Coder' ? 'bg-pink-500/20 text-pink-400' :
                          entry.rank_title === 'Script Kiddie' ? 'bg-orange-500/20 text-orange-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {entry.rank_title}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{entry.college}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-purple-400">
                        {entry.rating === 999999 ? '∞' : entry.rating}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{entry.games_played}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          entry.win_rate >= 70 ? 'bg-green-500/20 text-green-400' :
                          entry.win_rate >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {entry.win_rate.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Leaderboard;
