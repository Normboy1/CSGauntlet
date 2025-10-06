import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Game from './pages/Game';
import Spectate from './pages/Spectate';
import HomePage from './pages/HomePage';
import Leaderboard from './pages/Leaderboard';
import Profile from './pages/Profile';
import NavBar from './components/NavBar';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './utils/notifications';
import './index.css';

function App() {
  return (
    <NotificationProvider>
      <Router>
        <AuthProvider>
          <div className="min-h-screen bg-black text-white">
            <NavBar />
            <main className="container mx-auto px-4 py-8">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/game/:gameId" element={<Game />} />
                <Route path="/spectate/:gameId" element={<Spectate />} />
                <Route path="/leaderboard" element={<Leaderboard />} />
                <Route path="/profile" element={<Profile />} />
              </Routes>
            </main>
          </div>
        </AuthProvider>
      </Router>
    </NotificationProvider>
  );
}

export default App;
