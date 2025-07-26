/**
 * Chrome storage utility functions
 */

/**
 * Gets technology information from storage
 * @returns {Promise<Object>} Technology information object
 */
export async function getTechInfo() {
    try {
        return await chrome.runtime.sendMessage({ type: "GET_TECH" });
    } catch (error) {
        console.error('Error getting tech info:', error);
        return {};
    }
}

/**
 * Sets technology information in storage
 * @param {Object} techInfo - Technology information to store
 * @returns {Promise<void>}
 */
export async function setTechInfo(techInfo) {
    try {
        await chrome.runtime.sendMessage({ 
            type: "SET_TECH", 
            payload: techInfo 
        });
    } catch (error) {
        console.error('Error setting tech info:', error);
        throw error;
    }
}

/**
 * Gets session ID from storage
 * @returns {Promise<string|null>} Session ID or null if not found
 */
export async function getSessionId() {
    try {
        return await chrome.runtime.sendMessage({ type: "GET_SESSION_ID" });
    } catch (error) {
        console.error('Error getting session ID:', error);
        return null;
    }
}

/**
 * Gets AI disabled state from local storage
 * @returns {Promise<boolean>} True if AI is disabled
 */
export async function getAIDisabledState() {
    try {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            const result = await chrome.storage.local.get(['aiDisabled']);
            return result.aiDisabled || false;
        }
        return false;
    } catch (error) {
        console.error('Error getting AI disabled state:', error);
        return false;
    }
}

/**
 * Sets AI disabled state in local storage
 * @param {boolean} disabled - Whether AI should be disabled
 * @returns {Promise<void>}
 */
export async function setAIDisabledState(disabled) {
    try {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            await chrome.storage.local.set({ aiDisabled: disabled });
        }
        // Also set global flag
        window.aiDisabled = disabled;
    } catch (error) {
        console.error('Error setting AI disabled state:', error);
    }
}

/**
 * Clears all extension storage data
 * @returns {Promise<void>}
 */
export async function clearAllStorage() {
    try {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            await chrome.storage.local.clear();
        }
        // Reset global flags
        window.aiDisabled = false;
    } catch (error) {
        console.error('Error clearing storage:', error);
    }
}

/**
 * Gets multiple values from storage
 * @param {string[]} keys - Array of keys to retrieve
 * @returns {Promise<Object>} Object with requested key-value pairs
 */
export async function getStorageValues(keys) {
    try {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            return await chrome.storage.local.get(keys);
        }
        return {};
    } catch (error) {
        console.error('Error getting storage values:', error);
        return {};
    }
}

/**
 * Sets multiple values in storage
 * @param {Object} values - Object with key-value pairs to store
 * @returns {Promise<void>}
 */
export async function setStorageValues(values) {
    try {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            await chrome.storage.local.set(values);
        }
    } catch (error) {
        console.error('Error setting storage values:', error);
        throw error;
    }
}