/**
 * API utility functions for the TRL Calculator extension
 */

/**
 * Makes an API request through the extension's background script
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Object>} API response with ok, status, and text properties
 */
export async function apiFetch(url, options = {}) {
    try {
        return await chrome.runtime.sendMessage({
            type: "API_FETCH",
            url,
            init: options
        });
    } catch (error) {
        console.error('API fetch error:', error);
        return {
            ok: false,
            error: error.message || 'Network error occurred'
        };
    }
}

/**
 * Sets the technology context for the current session
 * @param {Object} techInfo - Technology information object
 * @returns {Promise<string|null>} Session ID or null if failed
 */
export async function setTechnologyContext(techInfo) {
    if (!techInfo?.id) {
        console.error('Invalid technology info provided');
        return null;
    }

    try {
        const response = await apiFetch("http://127.0.0.1:8000/set-technology-context", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ technology_id: techInfo.id })
        });

        if (response.ok) {
            const data = JSON.parse(response.text);
            console.log("Technology context set, session_id:", data.session_id);
            return data.session_id;
        } else {
            console.error("Failed to set technology context:", response.status);
            return null;
        }
    } catch (error) {
        console.error("Error setting technology context:", error);
        return null;
    }
}

/**
 * Checks the processing status of documents for a technology
 * @param {string} technologyId - The technology ID
 * @returns {Promise<Object>} Status response
 */
export async function checkProcessingStatus(technologyId) {
    try {
        const response = await apiFetch("http://127.0.0.1:8000/status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ technology_id: technologyId })
        });

        if (response.ok) {
            return JSON.parse(response.text);
        } else {
            throw new Error(`Status check failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Error checking processing status:', error);
        throw error;
    }
}

/**
 * Waits for document processing to complete
 * @param {string} technologyId - The technology ID
 * @param {Function} onStatusUpdate - Callback for status updates
 * @returns {Promise<boolean>} True if ready, false if failed
 */
export async function waitForProcessingComplete(technologyId, onStatusUpdate = null) {
    const maxAttempts = 30; // 1 minute with 2-second intervals
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const status = await checkProcessingStatus(technologyId);
            
            if (onStatusUpdate) {
                onStatusUpdate(status.status);
            }

            if (status.status === "ready") {
                return true;
            }

            if (status.status === "error") {
                console.error('Document processing failed:', status.message);
                return false;
            }

            // Wait 2 seconds before checking again
            await new Promise(resolve => setTimeout(resolve, 2000));
            attempts++;
        } catch (error) {
            console.error('Error waiting for processing:', error);
            return false;
        }
    }

    console.error('Processing timeout - documents may still be processing');
    return false;
}

/**
 * Sends a question to the AI API
 * @param {string} question - The question to ask
 * @param {string} sessionId - The session ID (optional, uses technology_id if not provided)
 * @param {string} technologyId - The technology ID (used when sessionId not provided)
 * @returns {Promise<string>} The AI response
 */
export async function askQuestion(question, sessionId = null, technologyId = null) {
    try {
        const body = sessionId 
            ? { question, session_id: sessionId }
            : { question, technology_id: technologyId };

        const response = await apiFetch("http://127.0.0.1:8000/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            throw new Error(response.error || `API error: ${response.status}`);
        }

        // Parse the JSON response and extract the answer
        try {
            const responseData = JSON.parse(response.text);
            return responseData.answer || response.text;
        } catch (e) {
            // If parsing fails, use the raw text (backward compatibility)
            return response.text;
        }
    } catch (error) {
        console.error('Error asking question:', error);
        throw error;
    }
}

/**
 * Uploads a file in chunks to the API
 * @param {File} file - The file to upload
 * @param {Object} techInfo - Technology information
 * @param {Function} onProgress - Progress callback (current, total)
 * @returns {Promise<void>}
 */
export async function uploadFileInChunks(file, techInfo, onProgress = null) {
    const CHUNK_SIZE = 1024 * 1024 * 3; // 3 MB per chunk
    
    try {
        // Convert file to base64
        const base64Content = await fileToBase64(file);
        
        const totalChunks = Math.ceil(base64Content.length / CHUNK_SIZE);
        
        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, base64Content.length);
            const chunk = base64Content.slice(start, end);
            
            const response = await apiFetch("http://127.0.0.1:8000/upload-files", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    technology_id: techInfo.id,
                    filename: file.name,
                    content_base64: chunk,
                    chunk_index: chunkIndex,
                    final: chunkIndex === totalChunks - 1
                })
            });

            if (!response.ok) {
                throw new Error(response.error || `Upload failed: ${response.status}`);
            }

            if (onProgress) {
                onProgress(chunkIndex + 1, totalChunks);
            }
        }
    } catch (error) {
        console.error('File upload error:', error);
        throw error;
    }
}

/**
 * Lists files for a technology
 * @param {string} technologyId - The technology ID
 * @returns {Promise<Array>} Array of file objects
 */
export async function listFiles(technologyId) {
    try {
        const response = await chrome.runtime.sendMessage({
            type: "LIST_FILES",
            technologyId: technologyId
        });

        if (response.ok && response.data) {
            return response.data.files || [];
        } else {
            throw new Error(response.error || 'Failed to list files');
        }
    } catch (error) {
        console.error('Error listing files:', error);
        throw error;
    }
}

/**
 * Removes a file from a technology
 * @param {string} technologyId - The technology ID
 * @param {string} filename - The filename to remove
 * @returns {Promise<void>}
 */
export async function removeFile(technologyId, filename) {
    try {
        const response = await chrome.runtime.sendMessage({
            type: "REMOVE_FILE",
            technologyId: technologyId,
            filename: filename
        });

        if (!response.ok) {
            throw new Error(response.error || 'Failed to remove file');
        }
    } catch (error) {
        console.error('Error removing file:', error);
        throw error;
    }
}

/**
 * Converts a file to base64 string
 * @param {File} file - The file to convert
 * @returns {Promise<string>} Base64 encoded file content
 */
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            // Extract base64 content (remove data URL prefix)
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}