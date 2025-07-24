// Function to add AI button to each TRL question
function addAIButtons() {
    const questions = document.querySelectorAll('.trl-group');
    questions.forEach((question, index) => {
        // Create AI button
        const aiButton = document.createElement('button');
        aiButton.innerHTML = 'Assistente IA';
        aiButton.type = 'button'; // Prevent form submission
        aiButton.className = 'ai-assist-button'; // Add class for easier selection
        
        // Check if AI is disabled
        const isDisabled = window.aiDisabled || false;
        
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
            e.preventDefault(); // Prevent default button behavior
            e.stopPropagation(); // Stop event bubbling
            
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
        
        // ========================================
        // UI-CONTEXT FORMATTING ONLY  
        // ========================================
        // Frontend provides clean TRL-specific context - backend applies all prompting techniques
        
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
            text = responseData.answer || resp.text; // Fallback to raw text if answer field doesn't exist
        } catch (e) {
            // If parsing fails, use the raw text (backward compatibility)
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

function showAnswer(text, question) {
    // Remove any existing answer
    const existingAnswer = document.querySelector("#aiAnswer");
    if (existingAnswer) {
        existingAnswer.remove();
    }
    
    // Format the text
    let formattedText = text
        // Remove surrounding quotes if present
        .replace(/^"|"$/g, '')
        // Replace escaped newlines with actual newlines
        .replace(/\\n/g, '\n')
        // Replace escaped quotes
        .replace(/\\"/g, '"')
        // Replace asterisks with bold tags
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Replace single asterisks with emphasis
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Preserve actual newlines
        .replace(/\n/g, '<br>');
    
    const div = document.createElement("div");
    div.id = "aiAnswer"; // Add ID for easy removal
    div.style = `
        position: fixed;
        top: 20px;
        right: 20px;
        width: 380px;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        z-index: 9999;
        transform: translateX(0);
        transition: all 0.3s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        overflow: hidden;
        animation: slideInFromRight 0.3s ease-out;
    `;
    
    // Add keyframe animation
    if (!document.querySelector('#aiAnswerStyle')) {
        const style = document.createElement("style");
        style.id = 'aiAnswerStyle';
        style.textContent = `
            @keyframes slideInFromRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutToRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    div.innerHTML = `
        <!-- Header -->
        <div style="
            background: linear-gradient(135deg, #0c3943 0%, #00c5a4 100%);
            color: white;
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="
                    width: 28px;
                    height: 28px;
                    background: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                ">
                    <img src="${chrome.runtime.getURL('icons/logo.png')}" style="
                        width: 20px;
                        height: 20px;
                        object-fit: contain;
                    " alt="Company Logo" />
                </div>
                <span style="font-size: 16px; font-weight: 600;">Sugestão da IA</span>
            </div>
            <button id="aiClose" style="
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 18px;
                padding: 4px;
                border-radius: 4px;
                transition: background 0.2s ease;
                opacity: 0.9;
            " onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='none'">×</button>
        </div>
        
        <!-- Content -->
        <div style="padding: 24px;">
            <div style="
                background: #fff7d6;
                padding: 16px;
                border-radius: 8px;
                font-size: 14px;
                line-height: 1.6;
                color: #0c3943;
                border: 1px solid #00c5a4;
            ">
                ${formattedText}
            </div>
        </div>`;
    
    document.body.appendChild(div);
    
    document.querySelector("#aiClose").onclick = () => {
        div.style.animation = 'slideOutToRight 0.3s ease-out forwards';
        setTimeout(() => div.remove(), 300);
    };
}

// Initialize AI state from storage
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

// Initialize when the page loads
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

// Helper function to get technology info
async function getTech() {
    return await chrome.runtime.sendMessage({type: "GET_TECH"});
}

// Helper function to get session ID
async function getSessionId() {
    return await chrome.runtime.sendMessage({type: "GET_SESSION_ID"});
}

// Helper function for API calls
function apiFetch(url, init) {
    return chrome.runtime.sendMessage({type: "API_FETCH", url, init});
}

// Loader functions
function showLoader(msg) {
    let l = document.querySelector("#trlLoader");
    if(!l) {
        l = document.createElement("div");
        l.id = "trlLoader";
        l.style = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          backdrop-filter: blur(4px);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        `;
        l.innerHTML = `
            <div style="
              background: white;
              padding: 32px;
              border-radius: 16px;
              box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
              display: flex;
              flex-direction: column;
              align-items: center;
              min-width: 280px;
              animation: fadeInScale 0.3s ease-out;
            ">
              <div style="
                position: relative;
                width: 80px;
                height: 80px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                <div style="
                  width: 80px;
                  height: 80px;
                  border: 4px solid #e5e7eb;
                  border-top: 4px solid #00c5a4;
                  border-radius: 50%;
                  animation: trlspin 1s linear infinite;
                  position: absolute;
                  top: 0;
                  left: 0;
                "></div>
                <img src="${chrome.runtime.getURL('icons/logo.png')}" style="
                  width: 48px;
                  height: 48px;
                  object-fit: contain;
                  z-index: 1;
                  position: absolute;
                  top: 50%;
                  left: 50%;
                  transform: translate(-40%, -40%);
                  margin: 0;
                  padding: 0;
                  display: block;
                " alt="Company Logo" />
              </div>
              <p id="trlLoaderText" style="
                margin: 0;
                font-weight: 500;
                font-size: 16px;
                color: #0c3943;
                text-align: center;
              "></p>
            </div>`;
        document.body.appendChild(l);
        
        // Add enhanced animations
        if (!document.querySelector('#trlLoaderStyle')) {
          const style = document.createElement("style");
          style.id = 'trlLoaderStyle';
          style.textContent = `
            @keyframes trlspin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
            @keyframes fadeInScale {
              from { opacity: 0; transform: scale(0.9); }
              to { opacity: 1; transform: scale(1); }
            }
          `;
          document.head.appendChild(style);
        }
    }
    l.querySelector("#trlLoaderText").textContent = msg;
    l.style.display = "flex";
}

function hideLoader() {
    const l = document.querySelector("#trlLoader");
    if(l) l.style.display = "none";
}

// === Modern notification system ===
function showNotification(message, type = 'success', duration = 3000) {
  const notification = document.createElement('div');
  notification.style = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: ${type === 'success' ? '#00c5a4' : type === 'error' ? '#ef4444' : '#0c3943'};
    color: white;
    padding: 16px 24px;
    border-radius: 12px;
    z-index: 10001;
    font-size: 14px;
    font-weight: 500;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
    animation: notificationSlideIn 0.3s ease-out;
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 400px;
  `;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  notification.innerHTML = `
    <span style="font-size: 16px;">${icon}</span>
    <span>${message}</span>
  `;
  
  // Add notification styles if not already present
  if (!document.querySelector('#notificationStyles')) {
    const style = document.createElement("style");
    style.id = 'notificationStyles';
    style.textContent = `
      @keyframes notificationSlideIn {
        from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
      }
      @keyframes notificationSlideOut {
        from { opacity: 1; transform: translateX(-50%) translateY(0); }
        to { opacity: 0; transform: translateX(-50%) translateY(-20px); }
      }
    `;
    document.head.appendChild(style);
  }
  
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