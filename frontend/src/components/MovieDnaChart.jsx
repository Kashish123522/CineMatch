import React from 'react';
import { motion } from 'framer-motion';
import { Dna, Compass, Clock, Zap, Sparkles, Film, Heart } from 'lucide-react';
import { useMood } from '../MoodContext';

export function derivePersonalityTitle(top_genres = [], top_moods = []) {
  const gNames = top_genres.map((g) => (typeof g === 'string' ? g : g.genre || '').toLowerCase());
  const mNames = top_moods.map((m) => (typeof m === 'string' ? m : m.mood || '').toLowerCase());

  if (gNames.includes('science fiction') && (mNames.includes('thoughtful') || mNames.includes('thrilling'))) return 'The Cosmic Visionary';
  if (gNames.includes('action') && mNames.includes('thrilling')) return 'The Adrenaline Hunter';
  if (gNames.includes('comedy') && (mNames.includes('funny') || mNames.includes('feel-good'))) return 'The Joyful Maverick';
  if (gNames.includes('romance') || mNames.includes('romantic')) return 'The Passionate Auteur';
  if (mNames.includes('dark') || gNames.includes('horror') || gNames.includes('crime')) return 'The Noir Detective';
  if (gNames.includes('animation') || gNames.includes('family')) return 'The Wholesome Dreamer';
  if (gNames.includes('drama')) return 'The Empathetic Storyteller';
  return 'The Cinematic Explorer';
}

export default function MovieDnaChart({ dna, className = '' }) {
  const { theme } = useMood();
  if (!dna) return null;

  const {
    top_genres = [],
    top_moods = [],
    top_languages = [],
    top_directors_actors = [],
    typical_runtime_minutes = 120,
    typical_intensity = 'Medium / Thoughtful',
    recent_trend = 'Seed profile from onboarding',
  } = dna;

  const personalityTitle = derivePersonalityTitle(top_genres, top_moods);

  const genreGradients = [
    'from-purple-500 to-indigo-500',
    'from-indigo-500 to-cyan-500',
    'from-cyan-500 to-emerald-500',
    'from-pink-500 to-rose-500',
  ];

  return (
    <div
      className={`theme-card border backdrop-blur-xl p-6 md:p-8 shadow-2xl relative overflow-hidden transition-all duration-500 ${className}`}
      style={{ borderRadius: theme.cardRadius }}
    >
      {/* Background glow decoration */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-80 h-80 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-cyan-400 p-0.5 shadow-lg shadow-purple-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
              <Dna className="w-6 h-6 text-purple-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-extrabold px-3 py-0.5 rounded-full bg-gradient-to-r from-purple-500/20 via-pink-500/20 to-amber-500/20 border border-purple-500/30 text-purple-300">
                ✨ Archetype: {personalityTitle}
              </span>
            </div>
            <h3 className="theme-title text-xl font-black tracking-tight theme-text flex items-center gap-2">
              Your Movie DNA
              <span
                className="text-xs px-2 py-0.5 rounded-full font-medium border"
                style={{
                  backgroundColor: theme.colors.chipBg,
                  borderColor: theme.colors.chipBorder,
                  color: theme.colors.chipText,
                }}
              >
                Active Taste Vector
              </span>
            </h3>
            <p className="text-xs theme-text-muted">
              Adapts dynamically on every like, skip, and watch session
            </p>
          </div>
        </div>

        {/* Typical Profile Badges */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>~{typical_runtime_minutes} mins</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>{typical_intensity}</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Genres, Moods, Talent */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 py-6 relative z-10">
        {/* Left: Top Genres Breakdown */}
        <div>
          <h4 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-4 flex items-center gap-2">
            <Film className="w-4 h-4 text-purple-400" />
            Primary Genre Affinities
          </h4>
          <div className="space-y-3.5">
            {top_genres.length > 0 ? (
              top_genres.map((g, idx) => (
                <div key={g.genre} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-200">{g.genre}</span>
                    <span className="text-slate-400">{g.percentage || Math.round(g.affinity * 100)}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden p-0.5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(12, g.percentage || g.affinity * 100)}%` }}
                      transition={{ duration: 0.8, delay: idx * 0.1, ease: 'easeOut' }}
                      className={`h-full rounded-full bg-gradient-to-r ${genreGradients[idx % genreGradients.length]}`}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 italic">No genre data calibrated yet.</p>
            )}
          </div>
        </div>

        {/* Right: Moods & Talent */}
        <div className="space-y-6">
          {/* Mood Signature */}
          <div>
            <h4 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              Emotional Tone & Mood Signature
            </h4>
            <div className="flex flex-wrap gap-2">
              {top_moods.length > 0 ? (
                top_moods.map((m) => (
                  <span
                    key={m.mood}
                    className="px-3 py-1 rounded-xl bg-purple-900/30 border border-purple-500/30 text-purple-200 text-xs font-medium flex items-center gap-1.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
                    {m.mood}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500">General</span>
              )}
            </div>
          </div>

          {/* Key Directors & Talent */}
          {top_directors_actors.length > 0 && (
            <div>
              <h4 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center gap-2">
                <Heart className="w-4 h-4 text-rose-400" />
                Affinity Talent
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {top_directors_actors.map((talent) => (
                  <span
                    key={talent}
                    className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 text-[11px] font-medium border border-slate-700"
                  >
                    {talent}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom: Recent Trend Banner */}
      <div className="mt-2 pt-4 border-t border-white/10 flex items-start gap-3 relative z-10 bg-slate-950/40 rounded-2xl p-4 border border-white/5">
        <Compass className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
        <div>
          <div className="text-[11px] uppercase font-bold tracking-wider text-indigo-400">
            Dynamic Taste Shift (Exponential Recency Decay)
          </div>
          <p className="text-xs text-slate-300 mt-0.5 font-medium leading-relaxed">
            {recent_trend}
          </p>
        </div>
      </div>
    </div>
  );
}
