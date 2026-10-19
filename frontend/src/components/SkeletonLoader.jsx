import React from 'react';

export function MovieCardSkeleton() {
  return (
    <div className="rounded-3xl bg-slate-900/60 border border-white/5 overflow-hidden p-5 sm:p-6 animate-pulse">
      <div className="flex flex-col sm:flex-row gap-5">
        {/* Poster Skeleton */}
        <div className="w-full sm:w-36 h-48 sm:h-52 rounded-2xl bg-slate-800/60 flex-shrink-0 relative overflow-hidden">
          <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
        </div>

        {/* Content Skeleton */}
        <div className="flex-grow flex flex-col justify-between py-1 space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-6 w-48 bg-slate-800/80 rounded-lg" />
              <div className="h-6 w-20 bg-slate-800/80 rounded-full" />
            </div>

            <div className="h-4 w-full bg-slate-800/50 rounded" />
            <div className="h-4 w-3/4 bg-slate-800/50 rounded" />

            <div className="flex gap-2 pt-1">
              <div className="h-6 w-24 bg-purple-500/10 rounded-lg" />
              <div className="h-6 w-32 bg-purple-500/10 rounded-lg" />
              <div className="h-6 w-20 bg-slate-800/60 rounded-lg" />
            </div>
          </div>

          {/* Action buttons skeleton */}
          <div className="pt-3 border-t border-white/5 flex items-center justify-between">
            <div className="flex gap-2">
              <div className="h-8 w-16 bg-slate-800 rounded-lg" />
              <div className="h-8 w-16 bg-slate-800 rounded-lg" />
              <div className="h-8 w-20 bg-slate-800 rounded-lg" />
            </div>
            <div className="h-4 w-28 bg-slate-800 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function DnaSkeleton() {
  return (
    <div className="rounded-3xl bg-slate-900/60 border border-white/5 p-6 md:p-8 animate-pulse space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-2xl bg-slate-800" />
        <div className="space-y-2">
          <div className="h-5 w-40 bg-slate-800 rounded" />
          <div className="h-3 w-60 bg-slate-800/60 rounded" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 py-4">
        <div className="space-y-3">
          <div className="h-3 w-28 bg-slate-800 rounded" />
          <div className="h-6 w-full bg-slate-800/60 rounded" />
          <div className="h-6 w-full bg-slate-800/60 rounded" />
          <div className="h-6 w-full bg-slate-800/60 rounded" />
        </div>
        <div className="space-y-4">
          <div className="h-3 w-28 bg-slate-800 rounded" />
          <div className="flex gap-2">
            <div className="h-7 w-20 bg-slate-800 rounded-xl" />
            <div className="h-7 w-20 bg-slate-800 rounded-xl" />
            <div className="h-7 w-20 bg-slate-800 rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  );
}
