/**
 * Content script for initial questions page
 * Handles technology information parsing and storage
 */

(function() {
    'use strict';

    /**
     * Parses technology information from the span element
     * @param {string} text - Text content to parse
     * @returns {Object|null} Parsed technology info or null if parsing fails
     */
    function parseTechnologyInfo(text) {
        // Clean up text by removing extra whitespace
        const cleaned = text.replace(/\s+/g, " ").trim();
        
        // Match the pattern: Name (ID: number) / Projeto ProjectName / Org.: OrgName
        const match = cleaned.match(/ID:\s*(\d+)\).*?\/ Projeto (.*?) \/ Org\.: (.*)$/);
        
        if (!match) {
            console.warn('Failed to parse technology info:', text);
            return null;
        }
        
        return {
            id: match[1],
            name: cleaned.split("(ID")[0].trim(),
            project: match[2].trim(),
            org: match[3].trim()
        };
    }

    /**
     * Sets technology information in storage
     * @param {Object} techInfo - Technology information to store
     */
    async function setTechInfo(techInfo) {
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
     * Sets up monitoring for technology selection changes
     */
    function setupTechnologyMonitoring() {
        const span = document.querySelector("#select2-itemToSelect-container");
        
        if (!span) {
            console.warn('Technology selection container not found');
            return;
        }

        // Create mutation observer to watch for changes
        const observer = new MutationObserver(() => {
            const text = span.getAttribute("title") || span.textContent;
            const techInfo = parseTechnologyInfo(text);
            
            if (techInfo) {
                console.log('Technology info detected:', techInfo);
                setTechInfo(techInfo).catch(error => {
                    console.error('Failed to set technology info:', error);
                });
            }
        });

        // Observe changes to the span element
        observer.observe(span, {
            characterData: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['title']
        });

        // Parse initial state
        const initialText = span.getAttribute("title") || span.textContent;
        const initialTechInfo = parseTechnologyInfo(initialText);
        
        if (initialTechInfo) {
            console.log('Initial technology info:', initialTechInfo);
            setTechInfo(initialTechInfo).catch(error => {
                console.error('Failed to set initial technology info:', error);
            });
        }
    }

    /**
     * Initializes the content script
     */
    function initialize() {
        console.log('Initial questions page script loaded');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupTechnologyMonitoring);
        } else {
            setupTechnologyMonitoring();
        }
    }

    // Start the script
    initialize();

})();