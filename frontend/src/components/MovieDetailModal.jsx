import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Star, Clock, Calendar, Globe, Film, User, Sparkles, BarChart2, Loader2, ThumbsUp, ThumbsDown, Eye, FastForward } from 'lucide-react';
import { api } from '../api';
import { useMood } from '../MoodContext';

export default function MovieDetailModal({
  movie,
  scoreBreakdown,
  explanation,
  reasonChips,
  onClose,
  onFeedback,
}) {
  const { theme } = useMood();
  const [movieDetail, setMovieDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ratingVal, setRatingVal] = useState(5);
  const [showRatingPicker, setShowRatingPicker] = useState(false);

  const movieId = movie?.movie_id || movie?.id;

  useEffect(() => {
    if (!movieId) return;
    async function loadDetail() {
      try {
        setLoading(true);
        const data = await api.getMovieDetail(movieId);
        setMovieDetail(data);
      } catch (err) {
        console.error('Failed to load movie detail:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDetail();
  }, [movieId]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!movie) return null;

  const bgGradient = movie.gradient || 'from-purple-900 via-indigo-950 to-slate-900';
  const detail = movieDetail || movie;

  const components = scoreBreakdown
    ? [
        { label: 'Profile Taste Similarity', val: scoreBreakdown.profile_similarity, color: 'from-purple-500 to-indigo-500' },
        { label: 'Recent Behaviour Match', val: scoreBreakdown.recent_behavior, color: 'from-indigo-500 to-blue-500' },
        { label: 'Tonight Context Fit', val: scoreBreakdown.context_match, color: 'from-cyan-500 to-teal-500' },
        { label: 'Bayesian Quality Prior', val: scoreBreakdown.quality_prior, color: 'from-amber-500 to-yellow-500' },
        {
          label: 'Collaborative Filter',
          val: scoreBreakdown.collaborative_score,
          color: 'from-emerald-500 to-green-500',
          isSparse: scoreBreakdown.collaborative_score === 0,
        },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-3xl border shadow-2xl overflow-hidden relative text-left my-auto theme-surface transition-all duration-500"
        style={{ borderRadius: theme.cardRadius }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 p-2 rounded-full bg-black/60 text-slate-300 hover:text-white hover:bg-black/90 transition-all border border-white/10 cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Hero Banner with Gradient & Details */}
        <div className={`relative h-64 sm:h-72 w-full bg-gradient-to-br ${bgGradient} flex items-end p-6 overflow-hidden`}>
          {detail.poster_url && (
            <img
              src={detail.poster_url}
              alt={detail.title}
              className="absolute inset-0 w-full h-full object-cover opacity-30 blur-sm scale-105"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent" />

          <div className="relative z-10 flex flex-col sm:flex-row gap-5 items-start sm:items-end w-full">
            {/* Poster Thumbnail */}
            <div
              className={`w-24 sm:w-32 aspect-[2/3] overflow-hidden bg-black/40 border border-white/20 shadow-2xl flex-shrink-0 flex items-center justify-center relative ${
                theme.id === 'dark' ? 'poster-vignette' : ''
              }`}
              style={{ borderRadius: `calc(${theme.cardRadius} * 0.7)` }}
            >
              {detail.poster_url ? (
                <img
                  src={detail.poster_url}
                  alt={detail.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-xl font-black text-white/40 uppercase">
                  {detail.title?.slice(0, 3)}
                </span>
              )}
            </div>

            {/* Title & Metadata */}
            <div className="flex-grow">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span
                  className="px-2.5 py-0.5 rounded-full text-[11px] font-bold border"
                  style={{
                    backgroundColor: theme.colors.chipBg,
                    borderColor: theme.colors.chipBorder,
                    color: theme.colors.chipText,
                  }}
                >
                  {detail.genres && detail.genres[0]}
                </span>
                {detail.vote_average > 0 && (
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-bold flex items-center gap-1">
                    <Star className="w-3 h-3 fill-amber-400" />
                    {detail.vote_average.toFixed(1)} / 10
                  </span>
                )}
                {scoreBreakdown && (
                  <span
                    className="px-2.5 py-0.5 rounded-full text-[11px] font-black border"
                    style={{
                      backgroundColor: `${theme.colors.matchRing}22`,
                      borderColor: `${theme.colors.matchRing}66`,
                      color: theme.colors.matchRing,
                    }}
                  >
                    Match {(scoreBreakdown.final_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>

              <h2 className="theme-title text-2xl sm:text-3xl font-black text-white tracking-tight">
                {detail.title}
              </h2>

              <div className="flex items-center gap-3 text-xs text-slate-300 mt-1 font-medium">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  {detail.year}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  {detail.runtime} mins
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-slate-400" />
                  {detail.original_language?.toUpperCase() || 'EN'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6 max-h-[60vh] overflow-y-auto">
          {/* Explanation Callout */}
          {explanation && (
            <div
              className="p-4 border transition-all"
              style={{
                borderRadius: `calc(${theme.cardRadius} * 0.6)`,
                backgroundColor: theme.colors.chipBg,
                borderColor: theme.colors.chipBorder,
              }}
            >
              <div
                className="flex items-center gap-1.5 text-xs font-bold mb-1"
                style={{ color: theme.colors.accentPrimary }}
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Why CineMatch Picked This
              </div>
              <p className="text-xs sm:text-sm theme-text leading-relaxed font-medium">
                "{explanation}"
              </p>
              {reasonChips && reasonChips.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {reasonChips.map((chip) => (
                    <span
                      key={chip}
                      className="px-2.5 py-0.5 text-[11px] font-semibold border theme-chip shadow-sm"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Overview */}
          <div>
            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-2">Overview</h4>
            <p className="text-sm text-slate-300 leading-relaxed">
              {detail.overview || 'No synopsis available for this title.'}
            </p>
          </div>

          {/* Cast & Director */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            {detail.director && (
              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-slate-400 font-semibold block mb-0.5">Director</span>
                <span className="text-white font-bold">{detail.director}</span>
              </div>
            )}
            {detail.cast && detail.cast.length > 0 && (
              <div className="p-3 rounded-xl bg-slate-800/40 border border-white/5">
                <span className="text-slate-400 font-semibold block mb-0.5">Key Cast</span>
                <span className="text-white font-medium">{detail.cast.slice(0, 3).join(', ')}</span>
              </div>
            )}
          </div>

          {/* Score Breakdown Bar Chart */}
          {components.length > 0 && (
            <div className="p-5 rounded-2xl bg-slate-950/60 border border-white/5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs uppercase font-bold text-slate-300 tracking-wider flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-indigo-400" />
                  Per-Component Score Breakdown
                </h4>
                <span className="text-xs text-purple-400 font-bold">
                  Final: {(scoreBreakdown.final_score * 100).toFixed(0)}%
                </span>
              </div>

              <div className="space-y-3">
                {components.map((comp) => (
                  <div key={comp.label} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400 font-medium">{comp.label}</span>
                      <span className="text-white font-semibold">
                        {comp.isSparse ? '0% (Sparse)' : `${(comp.val * 100).toFixed(0)}%`}
                      </span>
                    </div>
                    <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden p-0.5">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.max(4, comp.val * 100)}%` }}
                        transition={{ duration: 0.6 }}
                        className={`h-full rounded-full bg-gradient-to-r ${comp.color}`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interactive Feedback in Modal */}
          {onFeedback && (
            <div className="pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs text-slate-400 font-medium">Record Feedback:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onFeedback(movieId, 'like')}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-emerald-500/20 hover:text-emerald-300 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors cursor-pointer"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  <span>Like</span>
                </button>
                <button
                  onClick={() => onFeedback(movieId, 'dislike')}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-rose-500/20 hover:text-rose-300 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors cursor-pointer"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                  <span>Dislike</span>
                </button>
                <button
                  onClick={() => onFeedback(movieId, 'watched')}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Watched</span>
                </button>
                <button
                  onClick={() => onFeedback(movieId, 'skip')}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-amber-500/20 hover:text-amber-300 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors cursor-pointer"
                >
                  <FastForward className="w-3.5 h-3.5" />
                  <span>Not Interested</span>
                </button>

                {/* Rating Button */}
                <div className="relative">
                  <button
                    onClick={() => setShowRatingPicker(!showRatingPicker)}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-amber-500/20 hover:text-amber-300 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors cursor-pointer"
                  >
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>Rate</span>
                  </button>

                  {showRatingPicker && (
                    <div className="absolute bottom-full mb-2 right-0 bg-slate-900 border border-white/10 rounded-2xl p-2 shadow-2xl flex items-center gap-1 z-30">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => {
                            onFeedback(movieId, 'rating', star);
                            setShowRatingPicker(false);
                          }}
                          className="p-1 hover:scale-125 transition-transform text-amber-400 cursor-pointer"
                          title={`${star} Star`}
                        >
                          <Star className="w-4 h-4 fill-amber-400" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
