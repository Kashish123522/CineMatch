import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import VibePage from './pages/VibePage';
import DnaPage from './pages/DnaPage';
import { api } from './api';
import { UserPlus, Sparkles, X } from 'lucide-react';
import { useMood } from './MoodContext';

export default function App() {
  const { currentMood, theme } = useMood();
  const [currentPage, setCurrentPage] = useState('landing');
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('cinematch_user');
      return saved ? JSON.parse(saved) : { id: 1, username: 'alex_scifi' };
    } catch {
      return { id: 1, username: 'alex_scifi' };
    }
  });

  const [showNewUserModal, setShowNewUserModal] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [userModalError, setUserModalError] = useState('');

  // Persist current user in local storage
  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('cinematch_user', JSON.stringify(currentUser));
    }
  }, [currentUser]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUsername.trim()) return;
    setUserModalError('');
    try {
      const user = await api.createUser(newUsername.trim());
      setCurrentUser(user);
      setShowNewUserModal(false);
      setNewUsername('');
      setCurrentPage('onboarding');
    } catch (err) {
      setUserModalError(err.message || 'Username already exists or invalid');
    }
  };

  const handleSelectPersona = (id, username) => {
    const user = { id, username };
    setCurrentUser(user);
    setCurrentPage('vibe');
  };

  const handleStartOnboarding = () => {
    setShowNewUserModal(true);
  };

  return (
    <div
      data-mood={currentMood}
      className="min-h-screen flex flex-col theme-bg theme-text selection:bg-purple-500 selection:text-white transition-colors duration-500"
    >
      {/* Top Navbar */}
      <Navbar
        currentUser={currentUser}
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        onResetUser={() => setShowNewUserModal(true)}
      />

      {/* Main Page Area */}
      <main className="flex-grow">
        {currentPage === 'landing' && (
          <LandingPage
            currentUser={currentUser}
            onStartOnboarding={handleStartOnboarding}
            onStartVibe={() => setCurrentPage('vibe')}
            onSelectPersona={handleSelectPersona}
          />
        )}

        {currentPage === 'onboarding' && (
          <OnboardingPage
            currentUser={currentUser}
            onNavigateToVibe={() => setCurrentPage('vibe')}
          />
        )}

        {currentPage === 'vibe' && (
          <VibePage currentUser={currentUser} />
        )}

        {currentPage === 'dna' && (
          <DnaPage
            currentUser={currentUser}
            onNavigateToOnboarding={() => setCurrentPage('onboarding')}
          />
        )}
      </main>

      {/* User Creation / Persona Modal */}
      {showNewUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-3xl bg-slate-900 border border-white/10 p-6 sm:p-8 shadow-2xl relative">
            <button
              onClick={() => setShowNewUserModal(false)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-full hover:bg-white/5 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center mb-4 border border-purple-500/20">
              <UserPlus className="w-6 h-6" />
            </div>

            <h3 className="text-xl font-bold text-white mb-1">Create CineMatch Profile</h3>
            <p className="text-xs text-slate-400 mb-6">
              Enter a name to synthesize a brand new Movie DNA vector through onboarding.
            </p>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
                  Username
                </label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g. nolan_enthusiast"
                  className="w-full px-4 py-3 rounded-xl bg-slate-800/80 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
                />
              </div>

              {userModalError && (
                <p className="text-xs text-rose-400 font-semibold">{userModalError}</p>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewUserModal(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold text-xs shadow-lg shadow-purple-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
                >
                  Start Onboarding
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 px-4 text-center text-xs text-slate-500">
        <p>CineMatch Recommendation Engine • Context-Aware Movie DNA with MMR Diversity</p>
      </footer>
    </div>
  );
}
