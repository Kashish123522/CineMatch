import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock, Heart, Users, Zap, Brain, Globe, Sparkles,
  ChevronRight, RefreshCw, ThumbsUp, ThumbsDown, Eye,
  FastForward, Star, ChevronDown, CheckCircle2, Loader2,
  AlertCircle, Film, BarChart2, Info
} from 'lucide-react';
import { api } from '../api';
import { MovieCardSkeleton } from '../components/SkeletonLoader';
import MovieDetailModal from '../components/MovieDetailModal';
import { useMood } from '../MoodContext';

function LikeBurstOverlay({ burstType }) {
  if (!burstType) return null;
  if (burstType === 'hearts') {
    return (
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
        {[...Array(6)].map((_, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 1, y: 0, x: (i - 2.5) * 28, scale: 0.8 }}
            animate={{ opacity: 0, y: -75 - (i % 3) * 20, scale: 1.4 }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="absolute bottom-6 left-1/2 text-2xl"
          >
            {['💖', '💕', '💗', '❤️', '💞'][i % 5]}
          </motion.span>
        ))}
      </div>
    );
  }
  if (burstType === 'confetti') {
    return (
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
        {[...Array(8)].map((_, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 1, y: 0, x: (i - 3.5) * 26, scale: 0.6 }}
            animate={{
              opacity: 0,
              y: -70 - (i % 4) * 16,
              scale: 1.3,
              rotate: i % 2 === 0 ? 45 : -45,
            }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
            className="absolute bottom-6 left-1/2 text-xl"
          >
            {['✨', '🎉', '🎊', '🌟', '☀️', '⭐'][i % 6]}
          </motion.span>
        ))}
      </div>
    );
  }
  return null;
}

const TIME_OPTIONS = [
  { val: 60, label: '60 mins', desc: 'Quick session' },
  { val: 90, label: '90 mins', desc: 'Standard length' },
  { val: 120, label: '120 mins', desc: 'Feature film' },
  { val: 160, label: '150+ mins', desc: 'Epic marathon' },
  { val: null, label: 'Unlimited', desc: 'No time limit' },
];

const MOOD_OPTIONS = [
  { id: 'funny', label: 'Funny', emoji: '😄' },
  { id: 'thrilling', label: 'Thrilling', emoji: '⚡' },
  { id: 'romantic', label: 'Romantic', emoji: '💖' },
  { id: 'thoughtful', label: 'Thoughtful', emoji: '🧠' },
  { id: 'dark', label: 'Dark / Gritty', emoji: '🌑' },
  { id: 'feel-good', label: 'Feel-Good', emoji: '✨' },
];

const COMPANY_OPTIONS = [
  { id: 'solo', label: 'Solo', desc: 'Tailored solely to my taste' },
  { id: 'date_night', label: 'Date Night', desc: 'Romantic, charming, conversational' },
  { id: 'family', label: 'Family with Kids', desc: 'Filters mature & dark content' },
  { id: 'friends', label: 'Friends', desc: 'Energetic, funny, high-octane' },
];

const INTENSITY_OPTIONS = [
  { id: 'light', label: 'Light & Breezy' },
  { id: 'medium', label: 'Balanced' },
  { id: 'intense', label: 'Intense / Gripping' },
];

const COMPLEXITY_OPTIONS = [
  { id: 'easy', label: 'Easygoing' },
  { id: 'moderate', label: 'Moderate' },
  { id: 'complex', label: 'Complex / Mind-bending' },
];

const LANGUAGE_OPTIONS = [
  { code: 'any', label: 'Any Language' },
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi', note: 'Limited titles available' },
  { code: 'ta', label: 'Tamil', note: 'Limited titles available' },
  { code: 'te', label: 'Telugu', note: 'Limited titles available' },
  { code: 'ja', label: 'Japanese' },
  { code: 'fr', label: 'French' },
  { code: 'es', label: 'Spanish' },
  { code: 'ko', label: 'Korean' },
  { code: 'de', label: 'German' },
];

export default function VibePage({ currentUser }) {
  const { currentMood, setMood: setGlobalMood, triggerSurpriseMood, theme } = useMood();

  // Context state
  const [timeAvailable, setTimeAvailable] = useState(120);
  const [mood, setMood] = useState(() => (currentMood && currentMood !== 'default' ? currentMood : 'thoughtful'));
  const [company, setCompany] = useState('solo');
  const [intensity, setIntensity] = useState('medium');
  const [complexity, setComplexity] = useState('moderate');
  const [language, setLanguage] = useState('any');
  const [unseenOnly, setUnseenOnly] = useState(true);
  const [bursts, setBursts] = useState({});

  // Recommendation state
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedMovieForModal, setSelectedMovieForModal] = useState(null);
  const [activeRatingMovieId, setActiveRatingMovieId] = useState(null);
  const [feedbackToast, setFeedbackToast] = useState({ show: false, message: '', type: 'info' });

  const showToast = (message, type = 'info') => {
    setFeedbackToast({ show: true, message, type });
    setTimeout(() => {
      setFeedbackToast((prev) => ({ ...prev, show: false }));
    }, 3500);
  };

  const handleSelectMood = (newMood) => {
    setMood(newMood);
    setGlobalMood(newMood);
  };

  const handleSurpriseMe = () => {
    const picked = triggerSurpriseMood();
    setMood(picked);
    showToast(`🎲 Surprise! Switched to ${picked.toUpperCase()} vibe!`, 'cyan');
  };

  const handleFetchRecommendations = async (overrideUnseen = null) => {
    if (!currentUser) return;
    setLoading(true);
    setErrorMsg('');
    setHasSearched(true);
    const activeUnseen = overrideUnseen !== null ? overrideUnseen : unseenOnly;
    try {
      const payload = {
        user_id: currentUser.id,
        context: {
          time_available_minutes: timeAvailable,
          mood,
          company,
          intensity,
          complexity,
          language: language === 'any' ? null : language,
          unseen_only: activeUnseen,
        },
        limit: 10,
      };
      const res = await api.getRecommendations(payload);
      setRecommendations(res.recommendations || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (movieId, type, ratingValue = null) => {
    if (!currentUser) return;
    try {
      await api.submitFeedback({
        user_id: currentUser.id,
        movie_id: movieId,
        interaction_type: type,
        rating: ratingValue,
      });

      // Real-time toast feedback
      if (type === 'like') {
        if (theme.id === 'romantic') {
          setBursts((prev) => ({ ...prev, [movieId]: 'hearts' }));
          setTimeout(() => setBursts((prev) => ({ ...prev, [movieId]: null })), 1200);
        } else if (theme.id === 'feel-good') {
          setBursts((prev) => ({ ...prev, [movieId]: 'confetti' }));
          setTimeout(() => setBursts((prev) => ({ ...prev, [movieId]: null })), 1200);
        }
        showToast('Liked! We will surface more titles with this synergy.', 'success');
      } else if (type === 'dislike') {
        showToast('Disliked. Pushed away from your taste profile.', 'rose');
        setRecommendations((prev) => prev.filter((r) => r.movie_id !== movieId));
      } else if (type === 'skip') {
        showToast('Not interested tonight. Skipped.', 'amber');
        setRecommendations((prev) => prev.filter((r) => r.movie_id !== movieId));
      } else if (type === 'watched') {
        showToast('Marked as already watched. Profile updated.', 'cyan');
        setRecommendations((prev) => prev.filter((r) => r.movie_id !== movieId));
      } else if (type === 'rating') {
        showToast(`Rated ${ratingValue}★! Taste profile recalibrated.`, 'amber');
      }

      // Close modal if open on that movie
      if (['dislike', 'skip', 'watched'].includes(type) && selectedMovieForModal?.movie_id === movieId) {
        setSelectedMovieForModal(null);
      }
    } catch (err) {
      showToast('Error recording feedback: ' + err.message, 'rose');
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Real-time Toast Alert */}
      <AnimatePresence>
        {feedbackToast.show && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`fixed top-20 right-4 z-50 px-4 py-3 rounded-2xl border text-xs font-semibold shadow-2xl flex items-center gap-2.5 backdrop-blur-xl ${
              feedbackToast.type === 'rose'
                ? 'bg-rose-950/90 border-rose-500/40 text-rose-200'
                : feedbackToast.type === 'amber'
                ? 'bg-amber-950/90 border-amber-500/40 text-amber-200'
                : feedbackToast.type === 'cyan'
                ? 'bg-cyan-950/90 border-cyan-500/40 text-cyan-200'
                : 'bg-slate-900/90 border-purple-500/40 text-purple-200'
            }`}
          >
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
            <span>{feedbackToast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold mb-3">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Real-Time Situational Matching</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight mb-2">
          Tonight's Vibe
        </h1>
        <p className="text-sm text-slate-400">
          Tell us about this specific session. CineMatch balances your baseline Movie DNA with tonight's situational mood and constraints.
        </p>
      </div>

      {/* Context Selection Form */}
      <div
        className="grid grid-cols-1 md:grid-cols-2 gap-6 theme-surface border p-6 md:p-8 backdrop-blur-xl mb-12 shadow-2xl transition-all duration-500"
        style={{ borderRadius: theme.cardRadius }}
      >
        {/* 1. Time Available */}
        <div>
          <label className="text-xs uppercase font-bold theme-text-sec tracking-wider flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-cyan-400" />
            1. Time Available
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {TIME_OPTIONS.map((t) => (
              <button
                key={String(t.val)}
                onClick={() => setTimeAvailable(t.val)}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  timeAvailable === t.val
                    ? 'border-cyan-500 bg-cyan-500/15 text-white ring-1 ring-cyan-500 shadow-lg shadow-cyan-500/20'
                    : 'border-white/5 bg-slate-800/40 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-bold text-xs">{t.label}</div>
                <div className="text-[10px] text-slate-400">{t.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 2. Mood */}
        <div>
          <label className="text-xs uppercase font-bold theme-text-sec tracking-wider flex items-center gap-2 mb-3">
            <Heart className="w-4 h-4 text-purple-400" />
            2. Current Mood
          </label>
          <div className="flex flex-wrap gap-2">
            {MOOD_OPTIONS.map((m) => {
              const isSelected = mood === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => handleSelectMood(m.id)}
                  className={`px-3.5 py-2 text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer ${
                    isSelected ? 'shadow-lg scale-105' : 'hover:opacity-85'
                  }`}
                  style={{
                    borderRadius: `calc(${theme.cardRadius} * 0.55)`,
                    backgroundColor: isSelected ? theme.colors.accentPrimary : theme.colors.chipBg,
                    borderColor: isSelected ? theme.colors.accentSecondary : theme.colors.chipBorder,
                    color: isSelected ? theme.colors.accentText : theme.colors.chipText,
                  }}
                >
                  <span>{m.emoji}</span>
                  <span>{m.label}</span>
                </button>
              );
            })}

            {/* Surprise Me Option */}
            <button
              type="button"
              onClick={handleSurpriseMe}
              className="px-3.5 py-2 text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer bg-gradient-to-r from-amber-500/20 via-pink-500/20 to-purple-500/20 border-amber-400/40 text-amber-300 hover:scale-105 shadow-sm"
              style={{ borderRadius: `calc(${theme.cardRadius} * 0.55)` }}
              title="Pick a random mood theme"
            >
              <span>🎲</span>
              <span>Surprise Me</span>
            </button>
          </div>
        </div>

        {/* 3. Company */}
        <div>
          <label className="text-xs uppercase font-bold text-slate-400 tracking-wider flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-amber-400" />
            3. Who's Watching?
          </label>
          <div className="grid grid-cols-2 gap-2">
            {COMPANY_OPTIONS.map((c) => (
              <button
                key={c.id}
                onClick={() => setCompany(c.id)}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  company === c.id
                    ? 'border-amber-500 bg-amber-500/15 text-white ring-1 ring-amber-500 shadow-lg shadow-amber-500/20'
                    : 'border-white/5 bg-slate-800/40 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-bold text-xs">{c.label}</div>
                <div className="text-[10px] text-slate-400 mt-0.5 leading-snug">{c.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 4. Intensity & Language */}
        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase font-bold text-slate-400 tracking-wider flex items-center gap-2 mb-2">
              <Zap className="w-3.5 h-3.5 text-rose-400" />
              4. Intensity
            </label>
            <div className="grid grid-cols-3 gap-2">
              {INTENSITY_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setIntensity(opt.id)}
                  className={`p-2 rounded-xl text-center text-xs font-semibold border transition-all cursor-pointer ${
                    intensity === opt.id
                      ? 'border-rose-500 bg-rose-500/15 text-white ring-1 ring-rose-500'
                      : 'border-white/5 bg-slate-800/40 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs uppercase font-bold text-slate-400 tracking-wider flex items-center gap-2 mb-2">
              <Globe className="w-3.5 h-3.5 text-cyan-400" />
              5. Language
            </label>
            <div className="flex flex-wrap gap-2">
              {LANGUAGE_OPTIONS.map((l) => (
                <button
                  key={l.code}
                  onClick={() => setLanguage(l.code)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer flex flex-col items-start ${
                    language === l.code
                      ? 'border-cyan-500 bg-cyan-500/20 text-white shadow-sm shadow-cyan-500/20'
                      : 'border-white/5 bg-slate-800/40 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <span>{l.label}</span>
                  {l.note && (
                    <span className="text-[9px] text-amber-400/90 font-normal leading-tight mt-0.5">
                      {l.note}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs uppercase font-bold text-slate-400 tracking-wider flex items-center gap-2 mb-2">
              <Eye className="w-3.5 h-3.5 text-emerald-400" />
              6. Watch History
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setUnseenOnly(true)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                  unseenOnly
                    ? 'border-emerald-500 bg-emerald-500/15 text-white ring-1 ring-emerald-500 shadow-sm shadow-emerald-500/20'
                    : 'border-white/5 bg-slate-800/40 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <div className="font-bold text-xs flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Something new</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5 leading-tight">Fresh unseen discoveries</div>
              </button>

              <button
                type="button"
                onClick={() => setUnseenOnly(false)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                  !unseenOnly
                    ? 'border-purple-500 bg-purple-500/15 text-white ring-1 ring-purple-500 shadow-sm shadow-purple-500/20'
                    : 'border-white/5 bg-slate-800/40 text-slate-400 hover:bg-slate-800'
                }`}
              >
                <div className="font-bold text-xs flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 text-purple-400" />
                  <span>Rewatch a favourite</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5 leading-tight">Include watched & rated</div>
              </button>
            </div>
          </div>
        </div>

        {/* Action Row */}
        <div className="col-span-1 md:col-span-2 pt-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-slate-400">
            {company === 'family' ? (
              <span className="text-amber-400 font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Family mode: Horror, Crime & Intense content will be filtered out.
              </span>
            ) : (
              <span>MMR diversity re-ranking ensures a balanced, non-repetitive feed.</span>
            )}
          </div>

          <button
            onClick={handleFetchRecommendations}
            disabled={loading}
            className="w-full sm:w-auto px-8 py-4 text-sm font-extrabold shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2.5 cursor-pointer disabled:opacity-50"
            style={{
              borderRadius: theme.cardRadius,
              background: `linear-gradient(135deg, ${theme.colors.accentPrimary}, ${theme.colors.accentSecondary})`,
              color: theme.colors.accentText,
            }}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{theme.loadingMessage}</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Find What to Watch Right Now</span>
                <ChevronRight className="w-4 h-4 opacity-75" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error State */}
      {errorMsg && (
        <div className="p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={handleFetchRecommendations}
            className="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-xs font-bold transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeletons with Mood-Adaptive Message */}
      {loading && (
        <div className="space-y-4">
          <div
            className="p-5 border text-center flex items-center justify-center gap-3.5 backdrop-blur-md theme-surface shadow-xl transition-all duration-500"
            style={{ borderRadius: theme.cardRadius }}
          >
            <span className="text-3xl animate-bounce">{theme.emoji}</span>
            <div className="text-left">
              <p
                className="text-xs font-black uppercase tracking-wider"
                style={{ color: theme.colors.accentPrimary }}
              >
                {theme.name} Vibe Active
              </p>
              <p className="text-sm font-bold theme-text">
                {theme.loadingMessage}
              </p>
            </div>
          </div>
          <MovieCardSkeleton />
          <MovieCardSkeleton />
          <MovieCardSkeleton />
        </div>
      )}

      {/* Empty State */}
      {!loading && hasSearched && recommendations.length === 0 && (
        <div className="p-10 sm:p-14 rounded-3xl bg-slate-900/70 border border-white/10 text-center space-y-4 backdrop-blur-xl shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-purple-500/10 text-purple-400 mx-auto flex items-center justify-center border border-purple-500/20">
            <Film className="w-8 h-8" />
          </div>
          <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            {unseenOnly ? "No unseen movies match your current vibe" : "No matches for this exact combination"}
          </h3>
          <p className="text-xs sm:text-sm text-slate-300 max-w-lg mx-auto leading-relaxed font-medium">
            {unseenOnly
              ? "You've already explored or rated the matching titles in our catalog, or your situation filters are narrow. Try turning off 'Haven't watched before' to revisit great favourites, or expand your runtime limit."
              : "All candidates were filtered out by your current filters. Try expanding your available time or choosing a different mood."}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            {unseenOnly && (
              <button
                onClick={() => {
                  setUnseenOnly(false);
                  handleFetchRecommendations(false);
                }}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-bold shadow-lg shadow-purple-600/30 hover:scale-[1.02] transition-all cursor-pointer flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-amber-300" />
                <span>Turn off "Haven't watched before" (Show Rewatches)</span>
              </button>
            )}
            <button
              onClick={() => {
                setTimeAvailable(null);
                setCompany('solo');
                setLanguage('any');
                handleFetchRecommendations();
              }}
              className="px-5 py-3 rounded-xl bg-slate-800 text-slate-300 border border-white/10 text-xs font-bold hover:bg-slate-700 transition-all cursor-pointer"
            >
              Broaden All Filters
            </button>
          </div>
        </div>
      )}

      {/* Recommendation Feed */}
      {!loading && recommendations.length > 0 && (
        <div className="space-y-6">
          {/* Top of Feed Greeting Banner */}
          <div
            className="theme-card border p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all duration-500 shadow-xl"
            style={{ borderRadius: theme.cardRadius }}
          >
            <div className="flex items-center gap-3.5">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0 shadow-inner"
                style={{
                  backgroundColor: theme.colors.chipBg,
                  border: `1px solid ${theme.colors.chipBorder}`,
                }}
              >
                {theme.emoji}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className="text-[10px] uppercase font-black px-2 py-0.5 rounded-md tracking-wider"
                    style={{
                      backgroundColor: theme.colors.chipBg,
                      color: theme.colors.chipText,
                      border: `1px solid ${theme.colors.chipBorder}`,
                    }}
                  >
                    {theme.name} Vibe
                  </span>
                </div>
                <p className="text-base sm:text-lg font-bold theme-text theme-title mt-0.5">
                  "{theme.greeting}"
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSurpriseMe}
              className="self-start sm:self-auto px-3.5 py-2 text-xs font-bold border transition-all hover:scale-105 cursor-pointer flex items-center gap-1.5 shadow-sm"
              style={{
                borderRadius: `calc(${theme.cardRadius} * 0.5)`,
                backgroundColor: theme.colors.chipBg,
                borderColor: theme.colors.chipBorder,
                color: theme.colors.chipText,
              }}
              title="Randomize mood theme"
            >
              <span>🎲 Surprise Me</span>
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/5">
            <h2 className="text-2xl font-black theme-text theme-title tracking-tight flex items-center gap-2">
              <span>Personalized Recommendations</span>
              <span
                className="text-xs px-2.5 py-0.5 rounded-full font-semibold border"
                style={{
                  backgroundColor: theme.colors.chipBg,
                  borderColor: theme.colors.chipBorder,
                  color: theme.colors.chipText,
                }}
              >
                {recommendations.length} items
              </span>
            </h2>

            {/* Haven't watched before Filter Chip Toggle */}
            <button
              onClick={() => {
                const nextVal = !unseenOnly;
                setUnseenOnly(nextVal);
                handleFetchRecommendations(nextVal);
              }}
              className={`px-3.5 py-2 rounded-xl border text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-sm ${
                unseenOnly
                  ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30 shadow-emerald-500/10'
                  : 'border-white/10 bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700/80'
              }`}
              title="Toggle haven't watched before filter"
            >
              <div className={`w-2 h-2 rounded-full ${unseenOnly ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
              <span>Haven't watched before:</span>
              <span className={`font-bold ${unseenOnly ? 'text-emerald-300' : 'text-slate-400'}`}>
                {unseenOnly ? 'ON' : 'OFF'}
              </span>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <AnimatePresence>
              {recommendations.map((rec, idx) => {
                const bgGradient = rec.gradient || 'from-purple-900 via-indigo-950 to-slate-900';
                const matchPct = Math.round(rec.final_score * 100);

                return (
                  <motion.div
                    key={rec.movie_id}
                    layout
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
                    transition={{ delay: idx * 0.04 }}
                    className="theme-card relative border overflow-hidden p-5 sm:p-6 backdrop-blur-xl shadow-xl transition-all duration-500"
                    style={{
                      borderRadius: theme.cardRadius,
                    }}
                  >
                    {/* Like Burst Particle Effect Overlay */}
                    <LikeBurstOverlay burstType={bursts[rec.movie_id]} />

                    <div className="flex flex-col sm:flex-row gap-5">
                      {/* Poster Thumbnail / Gradient */}
                      <div
                        onClick={() => setSelectedMovieForModal(rec)}
                        className={`w-full sm:w-36 h-48 sm:h-auto bg-gradient-to-br ${bgGradient} flex-shrink-0 relative overflow-hidden flex items-center justify-center cursor-pointer group ${
                          theme.id === 'dark' ? 'poster-vignette' : ''
                        }`}
                        style={{ borderRadius: `calc(${theme.cardRadius} * 0.7)` }}
                      >
                        {rec.poster_url ? (
                          <img
                            src={rec.poster_url}
                            alt={rec.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        ) : (
                          <div className="p-3 text-center">
                            <span className="text-2xl font-black text-white/30 uppercase">
                              {rec.title.slice(0, 3)}
                            </span>
                          </div>
                        )}
                        <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-full bg-black/70 backdrop-blur-md text-[10px] font-bold text-amber-400 flex items-center gap-1 border border-white/10">
                          <Star className="w-3 h-3 fill-amber-400" />
                          <span>{rec.vote_average.toFixed(1)}</span>
                        </div>
                        {rec.is_watched && (
                          <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-full bg-cyan-950/80 backdrop-blur-md text-[10px] font-bold text-cyan-300 flex items-center gap-1 border border-cyan-500/40 z-10 shadow-lg">
                            <Eye className="w-3 h-3" />
                            <span>Watched</span>
                          </div>
                        )}
                      </div>

                      {/* Content Area */}
                      <div className="flex-grow flex flex-col justify-between">
                        <div>
                          {/* Title & Match Score Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2.5 flex-wrap">
                              <span
                                className="text-xs font-black px-2 py-0.5 rounded-md"
                                style={{
                                  backgroundColor: theme.colors.chipBg,
                                  color: theme.colors.chipText,
                                }}
                              >
                                #{idx + 1}
                              </span>
                              <h3
                                onClick={() => setSelectedMovieForModal(rec)}
                                className="theme-title text-xl font-bold theme-text hover:opacity-80 transition-opacity cursor-pointer"
                              >
                                {rec.title}
                              </h3>
                              <span className="text-xs theme-text-muted font-medium">({rec.year})</span>
                              {rec.is_watched && (
                                <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/35 text-[10px] font-extrabold flex items-center gap-1">
                                  <Eye className="w-3 h-3" />
                                  Watched
                                </span>
                              )}
                            </div>

                            <div
                              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-black self-start sm:self-auto shadow-sm transition-all"
                              style={{
                                backgroundColor: `${theme.colors.matchRing}20`,
                                borderColor: `${theme.colors.matchRing}55`,
                                color: theme.colors.matchRing,
                                borderWidth: '1px',
                                borderStyle: 'solid',
                                borderRadius: `calc(${theme.cardRadius} * 0.55)`,
                              }}
                            >
                              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: theme.colors.matchRing }} />
                              <span>{matchPct}% Match</span>
                            </div>
                          </div>

                          {/* Plain-Language Explanation */}
                          <p className="text-xs sm:text-sm theme-text-sec font-medium leading-relaxed mb-3">
                            "{rec.explanation}"
                          </p>

                          {/* Reason Chips */}
                          <div className="flex flex-wrap gap-1.5 mb-4">
                            {rec.reason_chips &&
                              rec.reason_chips.map((chip) => (
                                <span
                                  key={chip}
                                  className="px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 border theme-chip shadow-sm"
                                >
                                  <Sparkles className="w-3 h-3 text-amber-400" />
                                  {chip}
                                </span>
                              ))}
                            <span className="px-2.5 py-1 text-xs font-medium border theme-chip opacity-80">
                              {rec.runtime}m
                            </span>
                            {rec.genres && rec.genres.slice(0, 2).map((g) => (
                              <span
                                key={g}
                                className="px-2 py-0.5 text-[11px] font-medium border theme-chip opacity-75"
                              >
                                {g}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Interactive Feedback Controls */}
                        <div className="pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-1.5 text-xs flex-wrap">
                            {/* Like */}
                            <button
                              onClick={() => handleFeedback(rec.movie_id, 'like')}
                              className={`px-2.5 py-1.5 rounded-xl transition-all flex items-center gap-1.5 border cursor-pointer font-medium hover:scale-105 active:scale-95 ${
                                theme.id === 'thrilling' ? 'like-pulse-edge' : ''
                              }`}
                              style={{
                                backgroundColor: theme.colors.chipBg,
                                borderColor: theme.colors.chipBorder,
                                color: theme.colors.textPrimary,
                              }}
                              title="I like this (+1.0)"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" style={{ color: theme.colors.accentPrimary }} />
                              <span>Like</span>
                            </button>

                            {/* Dislike */}
                            <button
                              onClick={() => handleFeedback(rec.movie_id, 'dislike')}
                              className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-rose-500/20 hover:text-rose-300 text-slate-300 transition-colors flex items-center gap-1.5 border border-slate-700 cursor-pointer font-medium"
                              title="Dislike (-1.0)"
                            >
                              <ThumbsDown className="w-3.5 h-3.5 text-rose-400" />
                              <span>Dislike</span>
                            </button>

                            {/* Watched */}
                            <button
                              onClick={() => handleFeedback(rec.movie_id, 'watched')}
                              className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 transition-colors flex items-center gap-1.5 border border-slate-700 cursor-pointer font-medium"
                              title="Already watched (+0.6)"
                            >
                              <Eye className="w-3.5 h-3.5 text-cyan-400" />
                              <span>Watched</span>
                            </button>

                            {/* Not interested */}
                            <button
                              onClick={() => handleFeedback(rec.movie_id, 'skip')}
                              className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-amber-500/20 hover:text-amber-300 text-slate-300 transition-colors flex items-center gap-1.5 border border-slate-700 cursor-pointer font-medium"
                              title="Not interested (-0.4)"
                            >
                              <FastForward className="w-3.5 h-3.5 text-amber-400" />
                              <span>Not interested</span>
                            </button>

                            {/* Interactive Star Rating */}
                            <div className="relative">
                              <button
                                onClick={() =>
                                  setActiveRatingMovieId(
                                    activeRatingMovieId === rec.movie_id ? null : rec.movie_id
                                  )
                                }
                                className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-amber-500/20 hover:text-amber-300 text-slate-300 transition-colors flex items-center gap-1.5 border border-slate-700 cursor-pointer font-medium"
                                title="Rate (1-5 Stars)"
                              >
                                <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                                <span>Rate</span>
                              </button>

                              {activeRatingMovieId === rec.movie_id && (
                                <div className="absolute bottom-full mb-2 left-0 bg-slate-900 border border-white/15 rounded-2xl p-2 shadow-2xl flex items-center gap-1 z-30 animate-in zoom-in-90">
                                  {[1, 2, 3, 4, 5].map((star) => (
                                    <button
                                      key={star}
                                      onClick={() => {
                                        handleFeedback(rec.movie_id, 'rating', star);
                                        setActiveRatingMovieId(null);
                                      }}
                                      className="p-1.5 hover:scale-125 transition-transform text-amber-400 cursor-pointer"
                                      title={`${star} Star`}
                                    >
                                      <Star className="w-4 h-4 fill-amber-400" />
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Detail button */}
                          <button
                            onClick={() => setSelectedMovieForModal(rec)}
                            className="text-xs text-purple-400 hover:text-purple-300 font-bold flex items-center gap-1.5 cursor-pointer ml-auto"
                          >
                            <BarChart2 className="w-3.5 h-3.5" />
                            <span>Score Breakdown</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Movie Detail Modal */}
      {selectedMovieForModal && (
        <MovieDetailModal
          movie={selectedMovieForModal}
          scoreBreakdown={selectedMovieForModal.score_breakdown}
          explanation={selectedMovieForModal.explanation}
          reasonChips={selectedMovieForModal.reason_chips}
          onClose={() => setSelectedMovieForModal(null)}
          onFeedback={handleFeedback}
        />
      )}
    </div>
  );
}
