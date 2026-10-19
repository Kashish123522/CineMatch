import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Dna, Clock, History, ThumbsUp, ThumbsDown, Eye, FastForward, Star, RefreshCw, AlertCircle, Film, Sparkles } from 'lucide-react';
import MovieDnaChart from '../components/MovieDnaChart';
import { DnaSkeleton } from '../components/SkeletonLoader';
import MovieDetailModal from '../components/MovieDetailModal';
import { api } from '../api';
import { useMood } from '../MoodContext';

export default function DnaPage({ currentUser, onNavigateToOnboarding }) {
  const { theme } = useMood();
  const [dna, setDna] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedMovieForModal, setSelectedMovieForModal] = useState(null);

  const loadData = async () => {
    if (!currentUser) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const [dnaData, historyData] = await Promise.all([
        api.getUserDna(currentUser.id),
        api.getUserHistory(currentUser.id),
      ]);
      setDna(dnaData);
      setHistory(historyData || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load Movie DNA');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentUser]);

  const getInteractionBadge = (type, rating) => {
    switch (type.toLowerCase()) {
      case 'like':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <ThumbsUp className="w-3 h-3" /> Liked (+1.0)
          </span>
        );
      case 'dislike':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
            <ThumbsDown className="w-3 h-3" /> Disliked (-1.0)
          </span>
        );
      case 'watched':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            <Eye className="w-3 h-3" /> Watched (+0.6)
          </span>
        );
      case 'skip':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <FastForward className="w-3 h-3" /> Skipped (-0.4)
          </span>
        );
      case 'rating':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <Star className="w-3 h-3 fill-amber-400" /> Rated {rating?.toFixed(1) || '5.0'}★
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-300">
            {type}
          </span>
        );
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="max-w-5xl mx-auto py-10 px-4 space-y-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold mb-2 border"
            style={{
              backgroundColor: theme.colors.chipBg,
              borderColor: theme.colors.chipBorder,
              color: theme.colors.chipText,
            }}
          >
            <Dna className="w-3.5 h-3.5" />
            <span>Personal Profile Intelligence</span>
          </div>
          <h1 className="theme-title text-3xl sm:text-4xl font-black theme-text tracking-tight">
            My Movie DNA
          </h1>
          <p className="text-sm theme-text-sec mt-1">
            Real-time multi-modal taste vector for <strong className="theme-text">{currentUser?.username}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            title="Refresh DNA"
            className="p-2.5 rounded-xl border border-white/10 theme-surface transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer hover:opacity-80"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync</span>
          </button>
          <button
            onClick={onNavigateToOnboarding}
            className="px-4 py-2.5 rounded-xl text-xs font-bold shadow-lg transition-all cursor-pointer hover:scale-105"
            style={{
              background: `linear-gradient(135deg, ${theme.colors.accentPrimary}, ${theme.colors.accentSecondary})`,
              color: theme.colors.accentText,
            }}
          >
            Recalibrate DNA
          </button>
        </div>
      </div>

      {/* Error State */}
      {errorMsg && (
        <div className="p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={loadData}
            className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-xs font-bold transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && <DnaSkeleton />}

      {/* DNA Charts Section */}
      {!loading && dna && <MovieDnaChart dna={dna} />}

      {/* Interaction History Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="theme-title text-xl font-bold theme-text flex items-center gap-2">
            <History className="w-5 h-5" style={{ color: theme.colors.accentPrimary }} />
            <span>Recent Interaction History</span>
            <span
              className="text-xs px-2.5 py-0.5 rounded-full font-semibold border"
              style={{
                backgroundColor: theme.colors.chipBg,
                borderColor: theme.colors.chipBorder,
                color: theme.colors.chipText,
              }}
            >
              {history.length} logged
            </span>
          </h3>
          <span className="text-xs theme-text-muted hidden sm:block">
            Decays exponentially (14-day half-life)
          </span>
        </div>

        {/* Empty State */}
        {!loading && history.length === 0 && (
          <div className="p-10 rounded-3xl theme-surface border border-white/5 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl theme-card mx-auto flex items-center justify-center">
              <Film className="w-6 h-6" style={{ color: theme.colors.accentPrimary }} />
            </div>
            <h4 className="theme-title text-base font-bold theme-text">No interactions recorded yet</h4>
            <p className="text-xs theme-text-muted max-w-sm mx-auto">
              As you like, dislike, rate, or skip movies in the Tonight's Vibe feed, your history will populate and continually train your profile.
            </p>
          </div>
        )}

        {/* History List */}
        {!loading && history.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {history.map((item) => (
              <motion.div
                key={item.id}
                whileHover={{ y: -2 }}
                onClick={() => setSelectedMovieForModal({ id: item.movie_id, title: item.movie_title })}
                className="p-4 theme-card border hover:border-white/20 transition-all flex items-center justify-between gap-3 cursor-pointer group shadow-md"
                style={{ borderRadius: `calc(${theme.cardRadius} * 0.7)` }}
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 group-hover:scale-110 transition-transform"
                    style={{
                      backgroundColor: theme.colors.chipBg,
                      color: theme.colors.accentPrimary,
                    }}
                  >
                    <Film className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <h4 className="theme-title text-sm font-bold theme-text truncate group-hover:opacity-80 transition-opacity">
                      {item.movie_title}
                    </h4>
                    <span className="text-[11px] theme-text-muted block mt-0.5">
                      {formatTimestamp(item.timestamp)}
                    </span>
                  </div>
                </div>

                <div className="flex-shrink-0">
                  {getInteractionBadge(item.interaction_type, item.rating)}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Movie Detail Modal on click */}
      {selectedMovieForModal && (
        <MovieDetailModal
          movie={selectedMovieForModal}
          onClose={() => setSelectedMovieForModal(null)}
        />
      )}
    </div>
  );
}
