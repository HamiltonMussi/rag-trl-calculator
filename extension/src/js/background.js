/**
 * Background service worker for the TRL Calculator extension
 * Handles API requests, storage management, and session handling
 */

(function() {
    'use strict';

    class BackgroundService {
        constructor() {
            this.setupMessageListeners();
        }

        /**
         * Sets up message listeners for extension communication
         */
        setupMessageListeners() {
            chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
                this.handleMessage(message, sender, sendResponse);
                return true; // Indicates async response
            });
        }

        /**
         * Handles incoming messages from content scripts
         * @param {Object} message - Message object
         * @param {Object} sender - Sender information
         * @param {Function} sendResponse - Response callback
         */
        async handleMessage(message, sender, sendResponse) {
            try {
                switch (message.type) {
                    case "SET_TECH":
                        await this.handleSetTech(message.payload);
                        sendResponse({ success: true });
                        break;

                    case "GET_TECH":
                        const techInfo = await this.handleGetTech();
                        sendResponse(techInfo);
                        break;

                    case "GET_SESSION_ID":
                        const sessionId = await this.handleGetSessionId();
                        sendResponse(sessionId);
                        break;

                    case "LIST_FILES":
                        const filesResponse = await this.handleListFiles(message.technologyId);
                        sendResponse(filesResponse);
                        break;

                    case "REMOVE_FILE":
                        const removeResponse = await this.handleRemoveFile(message.technologyId, message.filename);
                        sendResponse(removeResponse);
                        break;

                    case "API_FETCH":
                        const apiResponse = await this.handleApiFetch(message.url, message.init);
                        sendResponse(apiResponse);
                        break;

                    default:
                        console.warn('Unknown message type:', message.type);
                        sendResponse({ error: 'Unknown message type' });
                }
            } catch (error) {
                console.error('Error handling message:', error);
                sendResponse({ error: error.message });
            }
        }

        /**
         * Handles setting technology information
         * @param {Object} techInfo - Technology information
         */
        async handleSetTech(techInfo) {
            try {
                // Store technology info in chrome storage
                await chrome.storage.local.set({ techInfo });
                console.log("Technology info set:", techInfo);
                
                // Set technology context when tech info is available
                await this.setTechnologyContext(techInfo);
            } catch (error) {
                console.error('Error setting technology info:', error);
                throw error;
            }
        }

        /**
         * Handles getting technology information
         * @returns {Object} Technology information
         */
        async handleGetTech() {
            try {
                const stored = await chrome.storage.local.get(['techInfo']);
                return stored.techInfo || {};
            } catch (error) {
                console.error('Error getting technology info:', error);
                return {};
            }
        }

        /**
         * Handles getting valid session ID
         * @returns {string|null} Session ID or null
         */
        async handleGetSessionId() {
            try {
                return await this.getValidSessionId();
            } catch (error) {
                console.error('Error getting session ID:', error);
                return null;
            }
        }

        /**
         * Handles listing files for a technology
         * @param {string} technologyId - Technology ID
         * @returns {Object} Response object
         */
        async handleListFiles(technologyId) {
            try {
                const response = await this.makeApiRequest("http://127.0.0.1:8000/list-files", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ technology_id: technologyId })
                });

                if (response.ok) {
                    const data = JSON.parse(response.text);
                    console.log("Files listed successfully:", data);
                    return { ok: true, data };
                } else {
                    console.error("Failed to list files:", response.status);
                    return { ok: false, error: `Failed to list files: ${response.status}` };
                }
            } catch (error) {
                console.error("Error listing files:", error);
                return { ok: false, error: error.toString() };
            }
        }

        /**
         * Handles removing a file
         * @param {string} technologyId - Technology ID
         * @param {string} filename - Filename to remove
         * @returns {Object} Response object
         */
        async handleRemoveFile(technologyId, filename) {
            try {
                const response = await this.makeApiRequest("http://127.0.0.1:8000/remove-file", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ technology_id: technologyId, filename })
                });

                if (response.ok) {
                    const data = JSON.parse(response.text);
                    console.log("File removed successfully:", data);
                    return { ok: true, data };
                } else {
                    console.error("Failed to remove file:", response.status);
                    return { ok: false, error: `Failed to remove file: ${response.status}` };
                }
            } catch (error) {
                console.error("Error removing file:", error);
                return { ok: false, error: error.toString() };
            }
        }

        /**
         * Handles API fetch requests
         * @param {string} url - API URL
         * @param {Object} options - Fetch options
         * @returns {Object} Response object
         */
        async handleApiFetch(url, options) {
            try {
                return await this.makeApiRequest(url, options);
            } catch (error) {
                console.error('API fetch error:', error);
                return { ok: false, error: error.toString() };
            }
        }

        /**
         * Makes an API request with error handling
         * @param {string} url - API URL
         * @param {Object} options - Fetch options
         * @returns {Object} Response object with ok, status, and text properties
         */
        async makeApiRequest(url, options = {}) {
            try {
                const response = await fetch(url, options);
                return {
                    ok: response.ok,
                    status: response.status,
                    text: await response.text()
                };
            } catch (error) {
                console.error('Network request failed:', error);
                return {
                    ok: false,
                    error: error.message || 'Network error occurred'
                };
            }
        }

        /**
         * Sets technology context with the backend
         * @param {Object} techInfo - Technology information
         */
        async setTechnologyContext(techInfo = null) {
            try {
                // Get techInfo from storage if not provided
                if (!techInfo) {
                    const stored = await chrome.storage.local.get(['techInfo']);
                    techInfo = stored.techInfo;
                }

                if (!techInfo?.id) {
                    console.warn('No technology ID available for context setting');
                    return;
                }

                const response = await this.makeApiRequest("http://127.0.0.1:8000/set-technology-context", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ technology_id: techInfo.id })
                });

                if (response.ok) {
                    const data = JSON.parse(response.text);
                    
                    // Store session data in chrome storage
                    await chrome.storage.local.set({
                        sessionId: data.session_id,
                        technologyId: techInfo.id
                    });
                    
                    console.log("Technology context set, session_id:", data.session_id);
                } else {
                    console.error("Failed to set technology context:", response.status);
                }
            } catch (error) {
                console.error("Error setting technology context:", error);
            }
        }

        /**
         * Gets a valid session ID, creating one if necessary
         * @returns {string|null} Session ID or null if failed
         */
        async getValidSessionId() {
            try {
                // Get stored tech info and session data
                const stored = await chrome.storage.local.get(['techInfo', 'sessionId', 'technologyId']);
                const techInfo = stored.techInfo;

                if (!techInfo?.id) {
                    console.log("No technology info found");
                    return null;
                }

                // Check if technology changed or no session exists
                if (stored.technologyId !== techInfo.id || !stored.sessionId) {
                    console.log("Technology changed or no session, creating new session");
                    await this.setTechnologyContext(techInfo);
                    const newStored = await chrome.storage.local.get(['sessionId']);
                    return newStored.sessionId;
                }

                // For now, assume existing session is valid
                console.log("Using existing session:", stored.sessionId);
                return stored.sessionId;

            } catch (error) {
                console.error("Error getting valid session ID:", error);
                return null;
            }
        }
    }

    // Initialize the background service
    new BackgroundService();

})();