/**
 * Content script for TRL questions pages (TRL1-TRL9)
 * Handles AI assistance for individual TRL criteria
 * Maintains original functionality while using modern patterns
 */

(function() {
    'use strict';

    // === UTILITY FUNCTIONS ===

    async function getTech() {
        return await chrome.runtime.sendMessage({type: "GET_TECH"});
    }

    async function getSessionId() {
        return await chrome.runtime.sendMessage({type: "GET_SESSION_ID"});
    }

    function apiFetch(url, init) {
        return chrome.runtime.sendMessage({type: "API_FETCH", url, init});
    }

    // === LOADER FUNCTIONS ===

    function showLoader(msg) {
        let l = document.querySelector("#trlLoader");
        if(!l) {
            l = document.createElement("div");
            l.id = "trlLoader";
            l.className = "trl-loader";
            l.innerHTML = `
                <div class="trl-loader__content">
                    <div class="trl-loader__spinner-container">
                        <div class="trl-loader__spinner"></div>
                        <img src="${chrome.runtime.getURL('assets/icons/logo.png')}" class="trl-loader__logo" alt="Logo" />
                    </div>
                    <p id="trlLoaderText" class="trl-loader__text"></p>
                </div>`;
            document.body.appendChild(l);
        }
        l.querySelector("#trlLoaderText").textContent = msg;
        l.style.display = "flex";
    }

    function hideLoader() {
        const l = document.querySelector("#trlLoader");
        if(l) l.style.display = "none";
    }

    // === NOTIFICATION SYSTEM ===

    function showNotification(message, type = 'success', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;

        const iconMap = {
            success: '✓',
            error: '✕',
            info: 'ℹ'
        };

        notification.innerHTML = `
            <span class="notification__icon">${iconMap[type] || iconMap.info}</span>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'notificationSlideOut 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, duration);
    }

    // === AI BUTTON CREATION ===

    function addAIButtons() {
        const questions = document.querySelectorAll('.trl-group');
        questions.forEach((question, index) => {
            // Create AI button
            const aiButton = document.createElement('button');
            aiButton.innerHTML = 'Assistente IA';
            aiButton.type = 'button';
            aiButton.className = 'ai-assist-button';
            
            // Check if AI is disabled
            const isDisabled = window.aiDisabled || false;
            
            // Apply styles
            aiButton.style = `
                position: absolute;
                right: 10px;
                top: 5px;
                background: ${isDisabled ? '#9ca3af' : 'linear-gradient(135deg, #0c3943 0%, #00c5a4 100%)'};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: ${isDisabled ? 'not-allowed' : 'pointer'};
                font-size: 13px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: ${isDisabled ? '0.6' : '1'};
                box-shadow: ${isDisabled ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.3)'};
                transition: all 0.2s ease;
                z-index: 100;
            `;
            
            // Add hover effects if not disabled
            if (!isDisabled) {
                aiButton.addEventListener('mouseenter', () => {
                    aiButton.style.transform = 'translateY(-1px)';
                    aiButton.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.4)';
                });
                
                aiButton.addEventListener('mouseleave', () => {
                    aiButton.style.transform = 'translateY(0)';
                    aiButton.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.3)';
                });
            }
            
            if (isDisabled) {
                aiButton.disabled = true;
                aiButton.title = 'Documentos não carregados. Por favor, faça upload dos documentos primeiro.';
            }
            
            // Add click handler
            aiButton.onclick = async (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Check if AI is disabled
                if (window.aiDisabled) {
                    showNotification('Por favor, faça upload dos documentos da tecnologia primeiro antes de usar a assistência da IA.', 'info');
                    return;
                }
                
                await processTRLQuestion(question);
            };
            
            // Add button to question
            question.style.position = 'relative';
            question.appendChild(aiButton);
        });
    }

    // === TRL QUESTION PROCESSING ===

    async function processTRLQuestion(question) {
        try {
            const sessionId = await getSessionId();
            if (!sessionId) {
                showNotification("Session não encontrada. Recarregue a página para definir o contexto da tecnologia.", 'error');
                return;
            }
            
            const questionText = question.querySelector('label').innerText.trim().replace(/[.:;]$/, '');
            const commentDiv = question.querySelector('.trl-comment-div');
            const commentLabel = commentDiv ? commentDiv.querySelector('label').innerText.trim().replace(/[.:;]$/, '') : '';
            
            // Get current TRL level from URL
            const trlLevel = window.location.pathname.match(/TRL(\d+)/)[1];
            
            showLoader("Consultando IA...");
            
            const questionContext = `**Avaliação de Critério TRL${trlLevel}:**

${questionText}?

**Formato de Resposta Requerido:**

1. **Resposta Principal:** [SIM/NÃO/DESCONHECIDO]

**Se SIM:**
   2. **${commentLabel}:** [Forneça explicação detalhada]
   3. **Nível de Completude:** [0% | 50% | 100%] com justificativa
      - 0%: Apenas planejado ou iniciado, sem resultados concretos
      - 50%: Parcialmente implementado ou em desenvolvimento ativo
      - 100%: Completamente implementado e validado

**Se NÃO:**
   2. **Justificativa:** [Explique por que o critério não é atendido]

**Se DESCONHECIDO:**
   2. **Motivo:** Não há informações suficientes nos documentos fornecidos para avaliar este critério.

**Contexto:** Esta avaliação refere-se especificamente aos critérios e requisitos do Technology Readiness Level ${trlLevel}.`;

            // Log the prompt to console
            console.log("=== TRL Question Prompt ===");
            console.log(questionContext);
            console.log("===========================");

            const resp = await apiFetch("http://127.0.0.1:8000/answer", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ 
                    question: questionContext, 
                    session_id: sessionId
                })
            });

            if (!resp.ok) {
                hideLoader();
                console.error("API Error:", resp);
                showNotification("Erro ao consultar a API: " + (resp.error || resp.status), 'error');
                return;
            }

            // Parse the JSON response and extract the answer
            let text;
            try {
                const responseData = JSON.parse(resp.text);
                text = responseData.answer || resp.text;
            } catch (e) {
                text = resp.text;
            }
            
            hideLoader();
            
            // Log the response to console
            console.log("=== AI Response ===");
            console.log(text);
            console.log("==================");
            
            // Show the answer in the popup widget
            showAnswer(text, question);
            
        } catch (error) {
            console.error("Error processing TRL question:", error);
            hideLoader();
        }
    }

    // === ANSWER DISPLAY ===

    function showAnswer(text, question) {
        // Remove any existing answer
        const existingAnswer = document.querySelector("#aiAnswer");
        if (existingAnswer) {
            existingAnswer.remove();
        }
        
        // Format the text
        let formattedText = text
            .replace(/^"|"$/g, '')
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        
        const div = document.createElement("div");
        div.id = "aiAnswer";
        div.className = "ai-answer";
        
        div.innerHTML = `
            <div class="ai-answer__header">
                <div class="ai-answer__header-content">
                    <div class="ai-answer__logo-container">
                        <img src="${chrome.runtime.getURL('assets/icons/logo.png')}" class="ai-answer__logo" alt="Logo" />
                    </div>
                    <span class="ai-answer__title">Sugestão da IA</span>
                </div>
                <button id="aiClose" class="ai-answer__close">×</button>
            </div>
            <div class="ai-answer__content">
                <div class="ai-answer__text">${formattedText}</div>
            </div>
        `;
        
        document.body.appendChild(div);
        
        document.querySelector("#aiClose").onclick = () => {
            div.style.animation = 'slideOutToRight 0.3s ease-out forwards';
            setTimeout(() => div.remove(), 300);
        };
    }

    // === AI BUTTON MANAGEMENT ===

    function enableAIButtons() {
        const aiButtons = document.querySelectorAll('.ai-assist-button');
        aiButtons.forEach(btn => {
            btn.disabled = false;
            btn.style.background = 'linear-gradient(135deg, #0c3943 0%, #00c5a4 100%)';
            btn.style.cursor = 'pointer';
            btn.style.opacity = '1';
            btn.title = '';
        });

        window.aiDisabled = false;

        if (typeof chrome !== 'undefined' && chrome.storage) {
            chrome.storage.local.set({aiDisabled: false});
        }

        console.log('AI buttons enabled - documents uploaded successfully');
    }

    function disableAIButtons() {
        const aiButtons = document.querySelectorAll('.ai-assist-button');
        aiButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.background = '#9ca3af';
            btn.style.cursor = 'not-allowed';
            btn.style.opacity = '0.6';
            btn.title = 'Documentos não carregados. Por favor, faça upload dos documentos primeiro.';
        });

        window.aiDisabled = true;

        if (typeof chrome !== 'undefined' && chrome.storage) {
            chrome.storage.local.set({aiDisabled: true});
        }

        console.log('AI buttons disabled - no documents uploaded');
    }

    // Make functions globally accessible
    window.enableAIButtons = enableAIButtons;
    window.disableAIButtons = disableAIButtons;

    // === AI STATE INITIALIZATION ===

    async function initializeAIState() {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            try {
                const result = await chrome.storage.local.get(['aiDisabled']);
                window.aiDisabled = result.aiDisabled || false;
            } catch (error) {
                console.log('Could not read AI state from storage:', error);
                window.aiDisabled = false;
            }
        } else {
            window.aiDisabled = false;
        }
    }

    // === INITIALIZATION ===

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", async () => {
            await initializeAIState();
            addAIButtons();
        });
    } else {
        initializeAIState().then(() => {
            addAIButtons();
        });
    }

})();