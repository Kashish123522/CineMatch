import React from 'react';
import { motion } from 'framer-motion';
import { Dna, Sparkles, Clock, Compass, ShieldCheck, ChevronRight, UserPlus, Users } from 'lucide-react';

export default function LandingPage({ onStartOnboarding, onStartVibe, currentUser, onSelectPersona }) {
  const personas = [
    { id: 1, name: 'Alex', tag: 'Thoughtful Sci-Fi & Nolan', color: 'from-purple-500 to-indigo-500' },
    { id: 2, name: 'Sarah', tag: 'Intense Action & Crime', color: 'from-rose-500 to-orange-500' },
    { id: 3, name: 'Elena', tag: 'Studio Ghibli & Family', color: 'from-emerald-500 to-teal-500' },
    { id: 4, name: 'Marcus', tag: 'Tarantino & Indie Cinema', color: 'from-amber-500 to-yellow-500' },
  ];

  return (
    <div className="relative overflow-hidden py-12 md:py-20 px-4 md:px-8 max-w-7xl mx-auto">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-purple-600/20 via-indigo-600/15 to-cyan-500/10 blur-[120px] rounded-full pointer-events-none" />

      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-semibold mb-6 shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Zero Doom-Scrolling. Zero Generic Lists.</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-[1.1] mb-6"
        >
          What should <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400">THIS user</span> watch{' '}
          <span className="underline decoration-purple-500/60 decoration-wavy underline-offset-8">RIGHT NOW</span>?
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-base sm:text-lg text-slate-300 font-normal leading-relaxed mb-10 max-w-2xl mx-auto"
        >
          CineMatch builds your personal <strong className="text-white font-semibold">Movie DNA</strong> and recalculates recommendations in real-time based on your available time, current mood, company, and recent interactions.
        </motion.p>

        {/* Primary CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        >
          <button
            onClick={onStartOnboarding}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 text-white font-bold text-base shadow-xl shadow-purple-600/30 hover:shadow-purple-600/50 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2.5 cursor-pointer"
          >
            <Dna className="w-5 h-5 text-white" />
            <span>Build my Movie DNA</span>
            <ChevronRight className="w-4 h-4 text-white/70" />
          </button>

          <button
            onClick={onStartVibe}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 hover:text-white font-semibold text-base border border-white/10 hover:border-white/20 transition-all flex items-center justify-center gap-2.5 cursor-pointer backdrop-blur-md"
          >
            <Sparkles className="w-5 h-5 text-amber-400" />
            <span>Set Tonight's Vibe</span>
          </button>
        </motion.div>

        {/* Quick Persona Switcher for Instant Testing */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 backdrop-blur-md max-w-2xl mx-auto text-left"
        >
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-bold text-slate-300 flex items-center gap-1.5">
              <Users className="w-4 h-4 text-indigo-400" />
              Instant Evaluation Personas
            </span>
            <span className="text-[11px] text-slate-400">Pre-seeded with interaction histories</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {personas.map((p) => (
              <button
                key={p.id}
                onClick={() => onSelectPersona(p.id, p.name)}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  currentUser && currentUser.id === p.id
                    ? 'border-purple-500 bg-purple-500/15 text-white ring-1 ring-purple-500'
                    : 'border-white/5 bg-slate-800/40 text-slate-300 hover:bg-slate-800 hover:border-white/15'
                }`}
              >
                <div className="font-bold text-xs text-white">{p.name}</div>
                <div className="text-[10px] text-slate-400 truncate mt-0.5">{p.tag}</div>
              </button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Feature Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-16 max-w-6xl mx-auto relative z-10">
        <div className="p-5 rounded-2xl bg-slate-900/40 border border-white/5 backdrop-blur-sm">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center mb-3">
            <Dna className="w-4 h-4" />
          </div>
          <h4 className="font-bold text-sm text-white mb-1">Movie DNA Profile</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Multi-modal preference vector capturing genres, moods, actors, and director signatures.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/40 border border-white/5 backdrop-blur-sm">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-3">
            <Clock className="w-4 h-4" />
          </div>
          <h4 className="font-bold text-sm text-white mb-1">Exponential Recency</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            14-day half-life decay. Recent likes adapt immediately without wiping your foundational taste.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/40 border border-white/5 backdrop-blur-sm">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center mb-3">
            <Compass className="w-4 h-4" />
          </div>
          <h4 className="font-bold text-sm text-white mb-1">Situational Context</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Filters for time available, solo vs date night vs family (filters mature themes), and intensity.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/40 border border-white/5 backdrop-blur-sm">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center mb-3">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h4 className="font-bold text-sm text-white mb-1">MMR & Plain Explanations</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Maximal Marginal Relevance avoids 10 clones; natural language explains why each movie was picked.
          </p>
        </div>
      </div>
    </div>
  );
}
