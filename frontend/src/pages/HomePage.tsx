import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Section */}
      <div className="relative pt-16 pb-32 flex content-center items-center justify-center">
        <div className="container mx-auto px-4 h-full">
          <div className="flex flex-wrap items-center">
            <div className="w-full lg:w-6/12 px-4 ml-auto mr-auto text-center">
              <h1 className="text-5xl font-bold text-white mb-6">
                CS Gauntlet
              </h1>
              <p className="text-xl text-gray-300 mb-8">
                The ultimate competitive coding platform for college students
              </p>
              <div className="flex justify-center gap-4">
                <Link 
                  to="/login"
                  className="bg-indigo-600 text-white px-8 py-3 rounded-xl hover:bg-indigo-700 transition-colors shadow-lg"
                >
                  Get Started
                </Link>
                <Link 
                  to="/register"
                  className="border border-indigo-600 text-indigo-600 px-8 py-3 rounded-xl hover:bg-indigo-600 hover:text-white transition-colors shadow-lg"
                >
                  Register
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <svg className="h-12 w-12 mx-auto text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path d="M12 14l9-5-9-5-9 5 9 5z" />
              <path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5l4-2.222" />
            </svg>
            <h3 className="text-xl font-semibold text-white mb-2">Competitive Coding</h3>
            <p className="text-gray-400">Practice coding problems in real-time with other students</p>
          </div>
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <svg className="h-12 w-12 mx-auto text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <h3 className="text-xl font-semibold text-white mb-2">Multiplayer Mode</h3>
            <p className="text-gray-400">Compete against other players in ranked matches</p>
          </div>
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <svg className="h-12 w-12 mx-auto text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <h3 className="text-xl font-semibold text-white mb-2">Secure Environment</h3>
            <p className="text-gray-400">Safe and controlled coding environment</p>
          </div>
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <svg className="h-12 w-12 mx-auto text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
            <h3 className="text-xl font-semibold text-white mb-2">Leaderboards</h3>
            <p className="text-gray-400">Track your progress and compete for top rankings</p>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-12">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <h3 className="text-xl font-semibold text-white mb-2">1. Register</h3>
            <p className="text-gray-400">Create your account and set up your profile</p>
          </div>
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <h3 className="text-xl font-semibold text-white mb-2">2. Compete</h3>
            <p className="text-gray-400">Join matches and solve coding challenges</p>
          </div>
          <div className="text-center p-6 bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <h3 className="text-xl font-semibold text-white mb-2">3. Progress</h3>
            <p className="text-gray-400">Track your growth and compete on the leaderboard</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
