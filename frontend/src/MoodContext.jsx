import React, { createContext, useContext, useState, useEffect } from 'react';
import { MOOD_THEMES, getTheme, getRandomMood } from './themes';

const MoodContext = createContext({
  currentMood: 'default',
  setMood: () => {},
  triggerSurpriseMood: () => {},
  theme: MOOD_THEMES.default,
});

export function MoodProvider({ children }) {
  const [currentMood, setCurrentMood] = useState(() => {
    try {
      const saved = localStorage.getItem('cinematch_active_mood');
      return saved && MOOD_THEMES[saved] ? saved : 'default';
    } catch {
      return 'default';
    }
  });

  const setMood = (newMood) => {
    const key = String(newMood).toLowerCase().trim();
    const finalMood = MOOD_THEMES[key] ? key : 'default';
    setCurrentMood(finalMood);
    try {
      localStorage.setItem('cinematch_active_mood', finalMood);
    } catch (e) {
      console.warn('Failed to persist mood preference', e);
    }
  };

  const triggerSurpriseMood = () => {
    const randomMood = getRandomMood();
    setMood(randomMood);
    return randomMood;
  };

  useEffect(() => {
    // Apply data-mood to both root document and root container for immediate CSS cascade
    document.documentElement.setAttribute('data-mood', currentMood);
    const rootEl = document.getElementById('root');
    if (rootEl) {
      rootEl.setAttribute('data-mood', currentMood);
    }
  }, [currentMood]);

  const theme = getTheme(currentMood);

  return (
    <MoodContext.Provider value={{ currentMood, setMood, triggerSurpriseMood, theme }}>
      {children}
    </MoodContext.Provider>
  );
}

export function useMood() {
  return useContext(MoodContext);
}
