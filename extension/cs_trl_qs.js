// Function to add AI button to each TRL question
function addAIButtons() {
    const questions = document.querySelectorAll('.trl-group');
    questions.forEach((question, index) => {
        // Create AI button
        const aiButton = document.createElement('button');
        aiButton.innerHTML = '<i class="fa fa-robot"></i> AI Assist';
        aiButton.type = 'button'; // Prevent form submission
        aiButton.className = 'ai-assist-button'; // Add class for easier selection
        
        // Check if AI is disabled
        const isDisabled = window.aiDisabled || false;
        
        aiButton.style = `
            position: absolute;
            right: 10px;
            top: 10px;
            background: ${isDisabled ? '#9ca3af' : '#3498db'};
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: ${isDisabled ? 'not-allowed' : 'pointer'};
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 5px;
            opacity: ${isDisabled ? '0.6' : '1'};
        `;
        
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
                alert('Por favor, faça upload dos documentos da tecnologia primeiro antes de usar a assistência da IA.');
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
            alert("Session não encontrada. Recarregue a página para definir o contexto da tecnologia.");
            return;
        }
        
        const questionText = question.querySelector('label').innerText.trim().replace(/[.:;]$/, '');
        const commentDiv = question.querySelector('.trl-comment-div');
        const commentLabel = commentDiv ? commentDiv.querySelector('label').innerText.trim().replace(/[.:;]$/, '') : '';
        
        // Get current TRL level from URL
        const trlLevel = window.location.pathname.match(/TRL(\d+)/)[1];
        
        showLoader("Consultando IA...");
        
        // Build the question with context
        const questionContext = `Esta é uma pergunta sobre o nível TRL${trlLevel}. 

Responda de forma estruturada:
1. ${questionText}? (sim/não)
Se sim: 
    2. ${commentLabel}?
    3. Quantifique a realização dessa atividade (0 - 100).
Se não:
    2. Se não, explique brevemente por quê.`;

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
            alert("Erro ao consultar a API: " + (resp.error || resp.status));
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
        top: 0;
        right: 0;
        width: 300px;
        background: #fff;
        border-left: 3px solid #3498db;
        box-shadow: -2px 0 5px rgba(0,0,0,0.1);
        z-index: 9999;
        padding: 15px;
        transform: translateX(0);
        transition: transform 0.3s ease;
        font-family: Arial, sans-serif;
    `;
    
    div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <b style="color: #3498db;">Sugestão da IA</b>
            <button id="aiClose" style="
                background: none;
                border: none;
                color: #666;
                cursor: pointer;
                font-size: 16px;
                padding: 0 5px;
            ">×</button>
        </div>
        <div style="
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 14px;
            line-height: 1.4;
        ">
            ${formattedText}
        </div>`;
    
    document.body.appendChild(div);
    
    // Animate the popup sliding in
    requestAnimationFrame(() => {
        div.style.transform = 'translateX(0)';
    });
    
    document.querySelector("#aiClose").onclick = () => {
        div.style.transform = 'translateX(100%)';
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
        l.style = "position:fixed;top:0;left:0;width:100%;height:100%;"+
                  "background:rgba(255,255,255,0.7);display:flex;align-items:center;"+
                  "justify-content:center;z-index:10000;flex-direction:column;";
        l.innerHTML = `
            <div class="spinner" style="border:6px solid #f3f3f3;border-top:6px solid #3498db;
                 border-radius:50%;width:40px;height:40px;animation:trlspin 1s linear infinite;">
            </div>
            <p id="trlLoaderText" style="margin-top:10px;font-weight:bold;"></p>`;
        document.body.appendChild(l);
        const style = document.createElement("style");
        style.textContent = "@keyframes trlspin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}";
        document.head.appendChild(style);
    }
    l.querySelector("#trlLoaderText").textContent = msg;
    l.style.display = "flex";
}

function hideLoader() {
    const l = document.querySelector("#trlLoader");
    if(l) l.style.display = "none";
} 