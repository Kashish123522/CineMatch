import React from 'react';
import { Film, Dna, Sparkles, User, RefreshCw } from 'lucide-react';
import { useMood } from '../MoodContext';

export default function Navbar({ currentUser, onNavigate, currentPage, onResetUser }) {
  const { currentMood, theme } = useMood();

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md theme-navbar border-b border-white/10 px-4 md:px-8 py-3 transition-colors duration-500">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <button
          onClick={() => onNavigate('landing')}
          className="flex items-center gap-2.5 text-left group cursor-pointer"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-purple-500/20 group-hover:shadow-purple-500/40 transition-shadow">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-extrabold tracking-tight text-lg text-white flex items-center gap-1.5">
              CineMatch
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium hidden sm:block">
              Situational Movie Recommendations
            </p>
          </div>
        </button>

        {/* Navigation links */}
        <div className="flex items-center gap-2 sm:gap-4">
          <button
            onClick={() => onNavigate('landing')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              currentPage === 'landing'
                ? 'bg-white/10 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            Home
          </button>

          <button
            onClick={() => onNavigate('vibe')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              currentPage === 'vibe'
                ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Tonight's Vibe
          </button>

          <button
            onClick={() => onNavigate('dna')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              currentPage === 'dna'
                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <Dna className="w-3.5 h-3.5 text-purple-400" />
            My Movie DNA
          </button>

          {/* Active Mood Pill */}
          {currentMood && currentMood !== 'default' && (
            <div
              title={`Active Mood Theme: ${theme.name}`}
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border transition-all"
              style={{
                backgroundColor: theme.colors.chipBg,
                borderColor: theme.colors.chipBorder,
                color: theme.colors.chipText,
              }}
            >
              <span>{theme.emoji}</span>
              <span>{theme.name} Theme</span>
            </div>
          )}

          {/* User Status pill */}
          {currentUser && (
            <div className="flex items-center gap-2 pl-2 border-l border-white/10 text-xs">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300">
                <User className="w-3.5 h-3.5 text-indigo-400" />
                <span className="font-semibold max-w-[90px] truncate">{currentUser.username}</span>
              </div>
              <button
                onClick={onResetUser}
                title="Switch persona / reset user"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/10 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
