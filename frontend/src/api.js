/**
 * CineMatch - Frontend API Client
 * Interfaces with FastAPI backend services with automatic JSON parsing and error handling.
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errMsg = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errMsg = errorData.detail || errMsg;
      } catch {
        // fallback
      }
      throw new Error(errMsg);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

export const api = {
  // Users
  createUser: (username) =>
    request('/users', {
      method: 'POST',
      body: JSON.stringify({ username }),
    }),

  // Onboarding
  getOnboardingMovies: (limit = 15, offset = 0, excludeIds = '') => {
    let q = `/onboarding/movies?limit=${limit}&offset=${offset}`;
    if (excludeIds) q += `&exclude_ids=${encodeURIComponent(excludeIds)}`;
    return request(q);
  },

  completeOnboarding: (data) =>
    request('/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Movie DNA
  getUserDna: (userId) =>
    request(`/users/${userId}/dna`),

  // Recommendations
  getRecommendations: (data) =>
    request('/recommendations', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Feedback
  submitFeedback: (data) =>
    request('/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Movie Detail
  getMovieDetail: (movieId) =>
    request(`/movies/${movieId}`),

  // Interaction History
  getUserHistory: (userId) =>
    request(`/users/${userId}/history`),
};
