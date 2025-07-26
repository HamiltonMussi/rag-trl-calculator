/**
 * UI component functions for creating consistent interface elements
 */

import { createElement, removeElement, showElement, hideElement } from '../utils/dom.js';

/**
 * Shows a loading overlay with customizable message
 * @param {string} message - Loading message to display
 */
export function showLoader(message = "Carregando...") {
    const existingLoader = document.querySelector("#trlLoader");
    if (existingLoader) {
        document.querySelector("#trlLoaderText").textContent = message;
        showElement(existingLoader, 'flex');
        return;
    }

    const loader = createElement('div', {
        id: 'trlLoader',
        className: 'trl-loader'
    });

    const logoUrl = chrome.runtime.getURL('assets/icons/logo.png');
    
    loader.innerHTML = `
        <div class="trl-loader__content">
            <div class="trl-loader__spinner-container">
                <div class="trl-loader__spinner"></div>
                <img src="${logoUrl}" class="trl-loader__logo" alt="Logo" />
            </div>
            <p id="trlLoaderText" class="trl-loader__text">${message}</p>
        </div>
    `;

    document.body.appendChild(loader);
    
    // Add styles if not already present
    ensureStylesLoaded('trlLoaderStyle', getLoaderStyles());
}

/**
 * Hides the loading overlay
 */
export function hideLoader() {
    const loader = document.querySelector("#trlLoader");
    if (loader) {
        hideElement(loader);
    }
}

/**
 * Shows a notification message
 * @param {string} message - Notification message
 * @param {string} type - Notification type ('success', 'error', 'info')
 * @param {number} duration - Display duration in milliseconds
 */
export function showNotification(message, type = 'success', duration = 3000) {
    const notification = createElement('div', {
        className: `notification notification--${type}`
    });

    const iconMap = {
        success: '✓',
        error: '✕',
        info: 'ℹ'
    };

    notification.innerHTML = `
        <span class="notification__icon">${iconMap[type] || iconMap.info}</span>
        <span>${message}</span>
    `;

    // Add notification styles if not already present
    ensureStylesLoaded('notificationStyles', getNotificationStyles());

    document.body.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        notification.style.animation = 'notificationSlideOut 0.3s ease-out forwards';
        setTimeout(() => {
            removeElement(notification);
        }, 300);
    }, duration);
}

/**
 * Creates an AI assistance button
 * @param {Function} onClick - Click handler function
 * @param {boolean} disabled - Whether the button should be disabled
 * @returns {HTMLElement} The AI button element
 */
export function createAIButton(onClick, disabled = false) {
    const button = createElement('button', {
        className: `ai-assist-button ${disabled ? 'disabled' : ''}`,
        type: 'button',
        disabled: disabled,
        textContent: 'Assistente IA'
    });

    if (disabled) {
        button.title = 'Documentos não carregados. Por favor, faça upload dos documentos primeiro.';
    }

    if (!disabled && onClick) {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            onClick(e);
        });

        // Add hover effects
        button.addEventListener('mouseenter', () => {
            if (!button.disabled) {
                button.style.transform = 'translateY(-1px)';
                button.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.4)';
            }
        });

        button.addEventListener('mouseleave', () => {
            if (!button.disabled) {
                button.style.transform = 'translateY(0)';
                button.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
            }
        });
    }

    return button;
}

/**
 * Shows an AI answer popup
 * @param {string} text - Answer text to display
 * @param {HTMLElement} relatedElement - Related element for context (optional)
 */
export function showAnswer(text, relatedElement = null) {
    // Remove any existing answer
    removeElement("#aiAnswer");

    const formattedText = formatAnswerText(text);
    const logoUrl = chrome.runtime.getURL('assets/icons/logo.png');

    const answerDiv = createElement('div', {
        id: 'aiAnswer',
        className: 'ai-answer'
    });

    answerDiv.innerHTML = `
        <div class="ai-answer__header">
            <div class="ai-answer__header-content">
                <div class="ai-answer__logo-container">
                    <img src="${logoUrl}" class="ai-answer__logo" alt="Logo" />
                </div>
                <span class="ai-answer__title">Sugestão da IA</span>
            </div>
            <button id="aiClose" class="ai-answer__close">×</button>
        </div>
        <div class="ai-answer__content">
            <div class="ai-answer__text">${formattedText}</div>
        </div>
    `;

    document.body.appendChild(answerDiv);

    // Add close functionality
    const closeButton = answerDiv.querySelector('#aiClose');
    closeButton.addEventListener('click', () => {
        answerDiv.style.animation = 'slideOutToRight 0.3s ease-out forwards';
        setTimeout(() => removeElement(answerDiv), 300);
    });

    // Add required styles
    ensureStylesLoaded('aiAnswerStyle', getAnswerStyles());
}

/**
 * Creates a button element with consistent styling
 * @param {string} text - Button text
 * @param {string} variant - Button variant ('primary', 'secondary')
 * @param {Function} onClick - Click handler
 * @param {Object} options - Additional options
 * @returns {HTMLElement} Button element
 */
export function createButton(text, variant = 'primary', onClick = null, options = {}) {
    const button = createElement('button', {
        className: `btn btn--${variant} ${options.className || ''}`,
        textContent: text,
        disabled: options.disabled || false,
        type: options.type || 'button'
    });

    if (onClick) {
        button.addEventListener('click', onClick);
    }

    return button;
}

/**
 * Creates a file item element for display in file lists
 * @param {Object} file - File object with name, size, etc.
 * @param {Function} onRemove - Remove handler function
 * @returns {HTMLElement} File item element
 */
export function createFileItem(file, onRemove = null) {
    const fileItem = createElement('div', {
        className: 'file-item'
    });

    const fileSize = file.size ? (file.size / 1024 / 1024).toFixed(2) : '0.00';
    const uploadDate = file.uploaded_at 
        ? new Date(file.uploaded_at).toLocaleDateString('pt-BR')
        : '';

    const statusClass = file.isExisting ? 'file-item__status--uploaded' : 'file-item__status--pending';
    const statusText = file.isExisting ? '✓ Carregado' : '📤 Para enviar';

    fileItem.innerHTML = `
        <div>
            <div class="file-item__name">
                ${file.filename || file.name} 
                <span class="file-item__status ${statusClass}">${statusText}</span>
            </div>
            <div class="file-item__size">${fileSize} MB${uploadDate ? ` • ${uploadDate}` : ''}</div>
        </div>
        ${onRemove ? '<button class="file-item__remove">Remover</button>' : ''}
    `;

    if (onRemove) {
        const removeButton = fileItem.querySelector('.file-item__remove');
        removeButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            onRemove(file);
        });
    }

    return fileItem;
}

/**
 * Enables AI buttons globally
 */
export function enableAIButtons() {
    const aiButtons = document.querySelectorAll('.ai-assist-button');
    aiButtons.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('disabled');
        btn.style.opacity = '1';
        btn.title = '';
    });

    window.aiDisabled = false;

    if (typeof chrome !== 'undefined' && chrome.storage) {
        chrome.storage.local.set({ aiDisabled: false });
    }

    console.log('AI buttons enabled - documents uploaded successfully');
}

/**
 * Disables AI buttons globally
 */
export function disableAIButtons() {
    const aiButtons = document.querySelectorAll('.ai-assist-button');
    aiButtons.forEach(btn => {
        btn.disabled = true;
        btn.classList.add('disabled');
        btn.style.opacity = '0.6';
        btn.title = 'Documentos não carregados. Por favor, faça upload dos documentos primeiro.';
    });

    window.aiDisabled = true;

    if (typeof chrome !== 'undefined' && chrome.storage) {
        chrome.storage.local.set({ aiDisabled: true });
    }

    console.log('AI buttons disabled - no documents uploaded');
}

// Helper functions

/**
 * Formats answer text with basic markdown-like formatting
 * @param {string} text - Text to format
 * @returns {string} Formatted HTML
 */
function formatAnswerText(text) {
    return text
        .replace(/^"|"$/g, '') // Remove surrounding quotes
        .replace(/\\n/g, '\n') // Replace escaped newlines
        .replace(/\\"/g, '"') // Replace escaped quotes
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
        .replace(/\n/g, '<br>'); // Line breaks
}

/**
 * Ensures required styles are loaded in the document
 * @param {string} id - Style element ID
 * @param {string} css - CSS content
 */
function ensureStylesLoaded(id, css) {
    if (!document.querySelector(`#${id}`)) {
        const style = createElement('style', { id, textContent: css });
        document.head.appendChild(style);
    }
}

/**
 * Returns CSS for loader component
 * @returns {string} CSS string
 */
function getLoaderStyles() {
    return `
        @keyframes trlspin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes fadeInScale {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
    `;
}

/**
 * Returns CSS for notification component
 * @returns {string} CSS string
 */
function getNotificationStyles() {
    return `
        @keyframes notificationSlideIn {
            from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        @keyframes notificationSlideOut {
            from { opacity: 1; transform: translateX(-50%) translateY(0); }
            to { opacity: 0; transform: translateX(-50%) translateY(-20px); }
        }
    `;
}

/**
 * Returns CSS for answer component
 * @returns {string} CSS string
 */
function getAnswerStyles() {
    return `
        @keyframes slideInFromRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutToRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
}