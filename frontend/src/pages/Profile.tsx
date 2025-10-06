import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ProfilePictureUpload from '../components/ProfilePictureUpload';

interface ProfileData {
  username: string;
  email: string;
  college: string;
  userRank: string;
  totalScore: number;
  gamesPlayed: number;
  winRate: number;
  rank: number;
  profilePicture?: string | null;
}

const Profile: React.FC = () => {
  const { user, token, logout } = useAuth();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleProfilePictureUpload = (pictureUrl: string) => {
    // Update the profile data with the new picture URL
    setProfileData(prev => prev ? { ...prev, profilePicture: pictureUrl } : null);
  };

  const handleProfilePictureDelete = () => {
    // Remove the profile picture from the profile data
    setProfileData(prev => prev ? { ...prev, profilePicture: null } : null);
  };

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch('/api/profile', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        setProfileData(data);
      } catch (err) {
        console.error('Error fetching profile:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch profile data');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchProfile();
    }
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Profile</h1>
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
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-center">Profile</h1>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6 text-center">
            <p className="text-red-400 mb-4">Error loading profile</p>
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
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Profile</h1>
        
        {profileData && (
          <div className="bg-gray-900/50 rounded-lg p-8">
            {/* Profile Picture Section */}
            <div className="mb-8 flex justify-center">
              <ProfilePictureUpload
                currentPicture={profileData.profilePicture}
                onUploadSuccess={handleProfilePictureUpload}
                onDeleteSuccess={handleProfilePictureDelete}
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* User Info */}
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-purple-400 mb-4">User Information</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Username</label>
                    <p className="text-white font-medium">{profileData.username}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
                    <p className="text-white">{profileData.email}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">College</label>
                    <p className="text-white">{profileData.college}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">User Rank</label>
                    <p className={`font-semibold ${
                      profileData.userRank === 'Creator' ? 'text-yellow-400' :
                      profileData.userRank === 'Admin' ? 'text-red-400' :
                      'text-green-400'
                    }`}>{profileData.userRank}</p>
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-purple-400 mb-4">Statistics</h2>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-purple-900/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">{profileData.totalScore}</div>
                    <div className="text-sm text-gray-300">Total Score</div>
                  </div>
                  
                  <div className="bg-purple-900/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">{profileData.gamesPlayed}</div>
                    <div className="text-sm text-gray-300">Games Played</div>
                  </div>
                  
                  <div className="bg-purple-900/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">{profileData.winRate.toFixed(1)}%</div>
                    <div className="text-sm text-gray-300">Win Rate</div>
                  </div>
                  
                  <div className="bg-purple-900/30 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">#{profileData.rank}</div>
                    <div className="text-sm text-gray-300">Global Rank</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-8 pt-8 border-t border-gray-700">
              <div className="flex justify-center space-x-4">
                <button
                  onClick={logout}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg transition-colors font-medium"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
