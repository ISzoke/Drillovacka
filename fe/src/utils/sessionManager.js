/**
 * Session Manager for Anonymous Users
 * Handles session ID generation, storage, and API communication
 */

const SESSION_STORAGE_KEY = 'anonymousSessionId';

/**
 * Generate a UUID v4
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Get or create session ID from localStorage
 */
export function getSessionId() {
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  
  if (!sessionId) {
    sessionId = generateUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  
  return sessionId;
}

/**
 * Clear session ID (e.g., on logout or reset)
 */
export function clearSessionId() {
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

/**
 * Check if session ID exists
 */
export function hasSessionId() {
  return !!localStorage.getItem(SESSION_STORAGE_KEY);
}
