import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Dna, Check, ChevronRight, ChevronLeft, Sparkles, Film, Globe, Heart, Loader2, RefreshCw } from 'lucide-react';
import MovieCard from '../components/MovieCard';
import MovieDnaChart from '../components/MovieDnaChart';
import { api } from '../api';

const ALL_GENRES = [
  'Science Fiction', 'Action', 'Thriller', 'Drama', 'Animation',
  'Comedy', 'Crime', 'Adventure', 'Fantasy', 'Romance',
  'Mystery', 'Family', 'Horror', 'History',
];

const ALL_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi', note: 'Limited titles available' },
  { code: 'ta', label: 'Tamil', note: 'Limited titles available' },
  { code: 'te', label: 'Telugu', note: 'Limited titles available' },
  { code: 'ja', label: 'Japanese' },
  { code: 'fr', label: 'French' },
  { code: 'es', label: 'Spanish' },
  { code: 'ko', label: 'Korean' },
  { code: 'de', label: 'German' },
  { code: 'any', label: 'Any Language' },
];

const ALL_MOODS = [
  { id: 'thoughtful', label: 'Thoughtful', desc: 'Cerebral, deep, existential' },
  { id: 'feel-good', label: 'Feel-Good', desc: 'Wholesome, heartwarming, comforting' },
  { id: 'thrilling', label: 'Thrilling', desc: 'High stakes, suspense, edge of seat' },
  { id: 'dark', label: 'Dark', desc: 'Gritty, ominous, psychological' },
  { id: 'romantic', label: 'Romantic', desc: 'Intimate, emotional, romantic tension' },
  { id: 'funny', label: 'Funny', desc: 'Witty, laugh-out-loud, comedic timing' },
  { id: 'inspiring', label: 'Inspiring', desc: 'Triumph over adversity, courage' },
];

export default function OnboardingPage({ currentUser, onComplete, onNavigateToVibe }) {
  const [step, setStep] = useState(1);
  const [selectedGenres, setSelectedGenres] = useState(['Science Fiction', 'Action']);
  const [selectedLanguages, setSelectedLanguages] = useState(['en']);
  const [selectedMoods, setSelectedMoods] = useState(['thoughtful']);
  const [moviesPool, setMoviesPool] = useState([]);
  const [movieOffset, setMovieOffset] = useState(0);
  const [selectedMovieIds, setSelectedMovieIds] = useState([]);
  const [loadingMovies, setLoadingMovies] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [dnaResult, setDnaResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  // Fetch diverse onboarding anchor movies
  useEffect(() => {
    async function loadMovies() {
      try {
        setLoadingMovies(true);
        const data = await api.getOnboardingMovies(15, 0);
        setMoviesPool(data);
      } catch (err) {
        console.error('Failed to load onboarding movies:', err);
      } finally {
        setLoadingMovies(false);
      }
    }
    loadMovies();
  }, []);

  const handleSkipFreshPosters = async () => {
    try {
      setLoadingMovies(true);
      const nextOffset = movieOffset + 5;
      const currentExcluded = moviesPool.map((m) => m.id).join(',');
      const data = await api.getOnboardingMovies(15, nextOffset, currentExcluded);
      setMoviesPool(data);
      setMovieOffset(nextOffset);
    } catch (err) {
      console.error('Failed to load fresh posters:', err);
    } finally {
      setLoadingMovies(false);
    }
  };

  const toggleGenre = (genre) => {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  };

  const toggleLanguage = (code) => {
    setSelectedLanguages((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const toggleMood = (id) => {
    setSelectedMoods((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const toggleMovie = (movie) => {
    setSelectedMovieIds((prev) =>
      prev.includes(movie.id) ? prev.filter((id) => id !== movie.id) : [...prev, movie.id]
    );
  };

  // Step 4 -> 5: Complete onboarding & Reveal DNA
  const handleFinalize = async () => {
    if (!currentUser) return;
    setSubmitting(true);
    setErrorMsg('');
    try {
      await api.completeOnboarding({
        user_id: currentUser.id,
        liked_movie_ids: selectedMovieIds,
        preferred_genres: selectedGenres,
        preferred_languages: selectedLanguages,
        preferred_moods: selectedMoods,
      });

      // Fetch newly generated DNA
      const dna = await api.getUserDna(currentUser.id);
      setDnaResult(dna);
      setStep(5);
      if (onComplete) onComplete(dna);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to complete onboarding');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-10 px-4">
      {/* Step Indicator */}
      {step < 5 && (
        <div className="mb-10 max-w-xl mx-auto">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-2">
            <span>Step {step} of 4</span>
            <span className="text-purple-400">
              {step === 1 && 'Favorite Genres'}
              {step === 2 && 'Languages'}
              {step === 3 && 'Emotional Moods'}
              {step === 4 && 'Anchor Movies'}
            </span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-400 rounded-full"
              initial={{ width: '25%' }}
              animate={{ width: `${(step / 4) * 100}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
      )}

      {/* Animated Step Carousel */}
      <AnimatePresence mode="wait">
        {/* STEP 1: Genre Bubbles */}
        {step === 1 && (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-400 mx-auto flex items-center justify-center mb-4 border border-purple-500/20">
              <Film className="w-6 h-6" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">
              What genres resonate with you?
            </h2>
            <p className="text-sm text-slate-400 mb-8">
              Tap the genres you enjoy watching most. We'll calibrate your taste boundaries.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-2.5 mb-10 max-w-2xl mx-auto">
              {ALL_GENRES.map((genre) => {
                const active = selectedGenres.includes(genre);
                return (
                  <motion.button
                    key={genre}
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={() => toggleGenre(genre)}
                    className={`px-4 py-2.5 rounded-full text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                      active
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30 border border-purple-400/40'
                        : 'bg-slate-900/80 text-slate-300 border border-white/10 hover:border-white/20 hover:bg-slate-800'
                    }`}
                  >
                    <span>{genre}</span>
                    {active && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </motion.button>
                );
              })}
            </div>

            <button
              onClick={() => setStep(2)}
              disabled={selectedGenres.length === 0}
              className="px-8 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold text-sm shadow-xl shadow-purple-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 inline-flex items-center gap-2 cursor-pointer"
            >
              <span>Next: Languages</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </motion.div>
        )}

        {/* STEP 2: Languages */}
        {step === 2 && (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="text-center max-w-2xl mx-auto"
          >
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 text-cyan-400 mx-auto flex items-center justify-center mb-4 border border-cyan-500/20">
              <Globe className="w-6 h-6" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">
              Preferred languages
            </h2>
            <p className="text-sm text-slate-400 mb-8">
              Select languages you are comfortable with (subtitled or original audio).
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-10">
              {ALL_LANGUAGES.map((lang) => {
                const active = selectedLanguages.includes(lang.code);
                return (
                  <button
                    key={lang.code}
                    onClick={() => toggleLanguage(lang.code)}
                    className={`p-3.5 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                      active
                        ? 'border-cyan-500 bg-cyan-500/15 text-white shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-500'
                        : 'border-white/10 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-bold block">{lang.label}</span>
                      {lang.note && (
                        <span className="text-[10px] text-amber-400 font-normal block mt-0.5">
                          {lang.note}
                        </span>
                      )}
                    </div>
                    {active && <Check className="w-4 h-4 text-cyan-400 stroke-[3] shrink-0 ml-1.5" />}
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setStep(1)}
                className="px-5 py-3 rounded-2xl bg-slate-800 text-slate-300 font-semibold text-sm hover:bg-slate-700 flex items-center gap-1.5 cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="px-8 py-3 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold text-sm shadow-xl shadow-purple-600/30 hover:scale-[1.02] flex items-center gap-2 cursor-pointer"
              >
                <span>Next: Moods</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}

        {/* STEP 3: Moods */}
        {step === 3 && (
          <motion.div
            key="step3"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 mx-auto flex items-center justify-center mb-4 border border-amber-500/20">
              <Heart className="w-6 h-6" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">
              What emotional tones do you crave?
            </h2>
            <p className="text-sm text-slate-400 mb-8">
              Choose the core vibes that make a movie memorable to you.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-10 text-left">
              {ALL_MOODS.map((m) => {
                const active = selectedMoods.includes(m.id);
                return (
                  <button
                    key={m.id}
                    onClick={() => toggleMood(m.id)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                      active
                        ? 'border-purple-500 bg-purple-500/15 text-white ring-1 ring-purple-500 shadow-lg shadow-purple-500/20'
                        : 'border-white/10 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm text-white capitalize">{m.label}</span>
                      {active && <Check className="w-4 h-4 text-purple-400 stroke-[3]" />}
                    </div>
                    <p className="text-xs text-slate-400">{m.desc}</p>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setStep(2)}
                className="px-5 py-3 rounded-2xl bg-slate-800 text-slate-300 font-semibold text-sm hover:bg-slate-700 flex items-center gap-1.5 cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
              <button
                onClick={() => setStep(4)}
                disabled={selectedMoods.length === 0}
                className="px-8 py-3 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold text-sm shadow-xl shadow-purple-600/30 hover:scale-[1.02] disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                <span>Next: Pick Anchor Movies</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}

        {/* STEP 4: Pick Movies Grid */}
        {step === 4 && (
          <motion.div
            key="step4"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="max-w-5xl mx-auto"
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">
                Select movies you've liked or loved
              </h2>
              <p className="text-sm text-slate-400">
                Choose at least 1 or more anchor titles to seed your vector space.
              </p>
              <div className="inline-flex items-center gap-2 mt-3 px-3 py-1 rounded-full bg-slate-800 text-xs font-semibold text-slate-300 border border-slate-700">
                <span>Selected:</span>
                <span className="text-purple-400 font-bold">{selectedMovieIds.length} titles</span>
              </div>
            </div>

            {loadingMovies ? (
              <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
                <span className="text-xs">Loading anchor catalog...</span>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 mb-10">
                {moviesPool.map((movie) => (
                  <MovieCard
                    key={movie.id}
                    movie={movie}
                    selected={selectedMovieIds.includes(movie.id)}
                    selectable={true}
                    onSelect={toggleMovie}
                  />
                ))}
              </div>
            )}

            {/* Skip fresh posters control */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-8 px-1">
              <button
                type="button"
                onClick={handleSkipFreshPosters}
                disabled={loadingMovies}
                className="px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 hover:border-white/20 text-xs font-semibold text-slate-300 hover:text-white transition-all flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loadingMovies ? 'animate-spin' : ''}`} />
                <span>Skip, I haven't watched any of these</span>
              </button>

              <span className="text-[11px] text-slate-400">
                Haven't watched any? Click to load fresh posters, or proceed with your genre & mood DNA.
              </span>
            </div>

            {errorMsg && (
              <p className="text-xs text-rose-400 text-center mb-4 font-semibold">{errorMsg}</p>
            )}

            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => setStep(3)}
                className="px-5 py-3 rounded-2xl bg-slate-800 text-slate-300 font-semibold text-sm hover:bg-slate-700 flex items-center gap-1.5 cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>

              <button
                onClick={handleFinalize}
                disabled={submitting}
                className="px-8 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 text-white font-bold text-sm shadow-xl shadow-purple-600/30 hover:scale-[1.02] disabled:opacity-50 flex items-center gap-2.5 cursor-pointer"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Synthesizing DNA...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>Generate My Movie DNA</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}

        {/* STEP 5: Reveal Screen with Movie DNA Chart */}
        {step === 5 && dnaResult && (
          <motion.div
            key="step5"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-3xl mx-auto text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', damping: 15 }}
              className="w-16 h-16 rounded-full bg-gradient-to-tr from-purple-500 to-cyan-400 p-1 mx-auto mb-4 shadow-xl shadow-purple-500/30"
            >
              <div className="w-full h-full bg-slate-950 rounded-full flex items-center justify-center">
                <Dna className="w-8 h-8 text-purple-400" />
              </div>
            </motion.div>

            <h2 className="text-2xl sm:text-4xl font-black text-white mb-2 tracking-tight">
              Movie DNA Calibrated!
            </h2>
            <p className="text-sm text-slate-400 mb-8 max-w-xl mx-auto">
              Your multidimensional taste vector has been synthesized. You can now get real-time context-aware recommendations whenever you're ready to watch.
            </p>

            <MovieDnaChart dna={dnaResult} className="mb-10 text-left" />

            <button
              onClick={onNavigateToVibe}
              className="px-10 py-4 rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 text-white font-extrabold text-base shadow-2xl shadow-purple-600/40 hover:scale-[1.02] active:scale-[0.98] transition-all inline-flex items-center gap-3 cursor-pointer"
            >
              <Sparkles className="w-5 h-5 text-amber-300" />
              <span>Continue to Tonight's Vibe</span>
              <ChevronRight className="w-5 h-5 text-white/70" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
