import React from 'react';
import { motion } from 'framer-motion';
import { Star, Clock, Check, ThumbsUp, ThumbsDown, Eye, FastForward } from 'lucide-react';

export default function MovieCard({
  movie,
  selected = false,
  onSelect,
  selectable = false,
  onFeedback,
  showActions = false,
}) {
  const { id, title, year, runtime, genres, moods, vote_average, poster_url, gradient } = movie;

  const bgGradient = gradient || 'from-purple-900 via-indigo-950 to-slate-900';

  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      onClick={() => selectable && onSelect && onSelect(movie)}
      className={`group relative flex flex-col rounded-2xl overflow-hidden border transition-all duration-300 ${
        selected
          ? 'border-purple-500 shadow-lg shadow-purple-500/25 ring-2 ring-purple-500/50'
          : 'border-white/10 hover:border-white/20 bg-slate-900/60'
      } ${selectable ? 'cursor-pointer' : ''}`}
    >
      {/* Poster area or Gradient */}
      <div className={`relative w-full aspect-[2/3] bg-gradient-to-br ${bgGradient} flex items-end p-4 overflow-hidden`}>
        {poster_url ? (
          <img
            src={poster_url}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center opacity-70 group-hover:opacity-90 transition-opacity">
            <span className="text-3xl font-black text-white/30 tracking-wider uppercase mb-1">
              {title.slice(0, 3)}
            </span>
            <span className="text-xs font-semibold text-white/40 tracking-widest uppercase">
              {genres && genres[0]}
            </span>
          </div>
        )}

        {/* Gradient shadow overlay for legibility */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent pointer-events-none" />

        {/* Top Badges */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 z-10">
          {vote_average > 0 && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10 text-[11px] font-bold text-amber-400">
              <Star className="w-3 h-3 fill-amber-400" />
              <span>{vote_average.toFixed(1)}</span>
            </div>
          )}
          {movie.is_watched && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/25 backdrop-blur-md border border-cyan-500/40 text-[10px] font-bold text-cyan-300">
              <Eye className="w-3 h-3" />
              <span>Watched</span>
            </div>
          )}
        </div>

        {/* Selectable hint overlay: 'Seen it' vs 'Haven't seen this' */}
        {selectable && (
          <div className="absolute top-3 right-3 z-10 flex items-center gap-1">
            {selected ? (
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-purple-600 text-white text-[11px] font-bold shadow-lg border border-purple-300/40 animate-in zoom-in-50 duration-200">
                <Check className="w-3.5 h-3.5 stroke-[3]" />
                <span>Seen it</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/75 backdrop-blur-md text-slate-400 group-hover:text-slate-200 group-hover:bg-slate-900/90 text-[10px] font-medium border border-white/10 group-hover:border-purple-500/30 transition-all">
                <span>Haven't seen this</span>
              </div>
            )}
          </div>
        )}

        {/* Bottom overlay info */}
        <div className="relative z-10 w-full">
          <h3 className="font-bold text-base text-white line-clamp-1 group-hover:text-purple-300 transition-colors">
            {title}
          </h3>
          <div className="flex items-center gap-2 text-[11px] text-slate-300 mt-0.5 font-medium">
            <span>{year}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-400" />
              {runtime}m
            </span>
          </div>
        </div>
      </div>

      {/* Tags row */}
      <div className="p-3 bg-slate-900/90 flex flex-col gap-2 flex-grow justify-between">
        <div className="flex flex-wrap gap-1">
          {genres &&
            genres.slice(0, 2).map((g) => (
              <span
                key={g}
                className="px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-[10px] text-slate-300 font-medium"
              >
                {g}
              </span>
            ))}
          {moods && moods[0] && (
            <span className="px-2 py-0.5 rounded-md bg-purple-500/10 border border-purple-500/20 text-[10px] text-purple-300 font-medium">
              {moods[0]}
            </span>
          )}
        </div>

        {/* Feedback actions if enabled */}
        {showActions && onFeedback && (
          <div className="pt-2 border-t border-white/10 flex items-center justify-between text-slate-400">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFeedback(id, 'like');
              }}
              title="Like"
              className="p-1.5 rounded-lg hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFeedback(id, 'dislike');
              }}
              title="Dislike"
              className="p-1.5 rounded-lg hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFeedback(id, 'watched');
              }}
              title="Already Watched"
              className="p-1.5 rounded-lg hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors"
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFeedback(id, 'skip');
              }}
              title="Skip"
              className="p-1.5 rounded-lg hover:text-amber-400 hover:bg-amber-500/10 transition-colors"
            >
              <FastForward className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
