/**
 * DOM utility functions for creating and manipulating elements
 */

/**
 * Creates an element with specified attributes and content
 * @param {string} tag - HTML tag name
 * @param {Object} attributes - Element attributes (className, id, etc.)
 * @param {string|HTMLElement|HTMLElement[]} content - Element content
 * @returns {HTMLElement} Created element
 */
export function createElement(tag, attributes = {}, content = null) {
    const element = document.createElement(tag);
    
    // Set attributes
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'innerHTML') {
            element.innerHTML = value;
        } else if (key === 'textContent') {
            element.textContent = value;
        } else if (key.startsWith('data-')) {
            element.setAttribute(key, value);
        } else {
            element[key] = value;
        }
    });
    
    // Set content
    if (content !== null) {
        if (typeof content === 'string') {
            element.textContent = content;
        } else if (content instanceof HTMLElement) {
            element.appendChild(content);
        } else if (Array.isArray(content)) {
            content.forEach(child => {
                if (child instanceof HTMLElement) {
                    element.appendChild(child);
                }
            });
        }
    }
    
    return element;
}

/**
 * Safely removes an element from the DOM
 * @param {string|HTMLElement} elementOrSelector - Element or CSS selector
 */
export function removeElement(elementOrSelector) {
    const element = typeof elementOrSelector === 'string' 
        ? document.querySelector(elementOrSelector)
        : elementOrSelector;
    
    if (element && element.parentNode) {
        element.remove();
    }
}

/**
 * Adds a CSS class to an element if it doesn't have it
 * @param {HTMLElement} element - Target element
 * @param {string} className - CSS class to add
 */
export function addClass(element, className) {
    if (element && !element.classList.contains(className)) {
        element.classList.add(className);
    }
}

/**
 * Removes a CSS class from an element if it has it
 * @param {HTMLElement} element - Target element
 * @param {string} className - CSS class to remove
 */
export function removeClass(element, className) {
    if (element && element.classList.contains(className)) {
        element.classList.remove(className);
    }
}

/**
 * Toggles a CSS class on an element
 * @param {HTMLElement} element - Target element
 * @param {string} className - CSS class to toggle
 */
export function toggleClass(element, className) {
    if (element) {
        element.classList.toggle(className);
    }
}

/**
 * Shows an element by setting display style
 * @param {HTMLElement} element - Element to show
 * @param {string} displayType - Display type (default: 'block')
 */
export function showElement(element, displayType = 'block') {
    if (element) {
        element.style.display = displayType;
    }
}

/**
 * Hides an element by setting display to none
 * @param {HTMLElement} element - Element to hide
 */
export function hideElement(element) {
    if (element) {
        element.style.display = 'none';
    }
}

/**
 * Checks if an element is visible
 * @param {HTMLElement} element - Element to check
 * @returns {boolean} True if element is visible
 */
export function isElementVisible(element) {
    if (!element) return false;
    
    return element.offsetParent !== null && 
           element.style.display !== 'none' && 
           element.style.visibility !== 'hidden' && 
           !element.hidden;
}

/**
 * Waits for an element to appear in the DOM
 * @param {string} selector - CSS selector
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 * @returns {Promise<HTMLElement>} The found element
 */
export function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }

        const observer = new MutationObserver(() => {
            const element = document.querySelector(selector);
            if (element) {
                observer.disconnect();
                clearTimeout(timeoutId);
                resolve(element);
            }
        });

        const timeoutId = setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Element ${selector} not found within ${timeout}ms`));
        }, timeout);

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

/**
 * Adds an event listener with automatic cleanup
 * @param {HTMLElement} element - Target element
 * @param {string} event - Event type
 * @param {Function} handler - Event handler
 * @param {Object} options - Event listener options
 * @returns {Function} Cleanup function
 */
export function addEventListenerWithCleanup(element, event, handler, options = {}) {
    if (!element) return () => {};
    
    element.addEventListener(event, handler, options);
    
    return () => {
        element.removeEventListener(event, handler, options);
    };
}

/**
 * Debounces a function call
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttles a function call
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Gets the scroll position of the window
 * @returns {Object} Object with x and y scroll positions
 */
export function getScrollPosition() {
    return {
        x: window.pageXOffset || document.documentElement.scrollLeft,
        y: window.pageYOffset || document.documentElement.scrollTop
    };
}

/**
 * Smoothly scrolls to an element
 * @param {HTMLElement|string} elementOrSelector - Element or selector to scroll to
 * @param {Object} options - Scroll behavior options
 */
export function scrollToElement(elementOrSelector, options = {}) {
    const element = typeof elementOrSelector === 'string' 
        ? document.querySelector(elementOrSelector)
        : elementOrSelector;
    
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest',
            ...options
        });
    }
}

/**
 * Creates a simple loading spinner element
 * @param {string} size - Size class (sm, md, lg)
 * @returns {HTMLElement} Spinner element
 */
export function createSpinner(size = 'md') {
    return createElement('div', {
        className: `spinner spinner--${size}`,
        innerHTML: '<div class="spinner__circle"></div>'
    });
}

/**
 * Formats text with basic markdown-like formatting
 * @param {string} text - Text to format
 * @returns {string} Formatted HTML
 */
export function formatText(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

/**
 * Sanitizes HTML by removing potentially dangerous elements
 * @param {string} html - HTML string to sanitize
 * @returns {string} Sanitized HTML
 */
export function sanitizeHTML(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}