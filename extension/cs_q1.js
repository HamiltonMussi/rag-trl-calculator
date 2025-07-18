async function getTech() {
    return await chrome.runtime.sendMessage({type: "GET_TECH"});
  }

// === simple loader =========================================
function showLoader(msg){
  let l = document.querySelector("#trlLoader");
  if(!l){
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
function hideLoader(){
  const l = document.querySelector("#trlLoader");
  if(l) l.style.display = "none";
}
  
    // === chunked upload constants + helper =========================
    const CHUNK_SIZE = 1024 * 1024 * 3;   // 3 MB per slice

    // helper – FileReader avoids the huge String.fromCharCode() call‑stack
    function fileToBase64(file){
      return new Promise(res=>{
        const fr = new FileReader();
        fr.onload = () => {
          // Data‑URL:  "data:application/pdf;base64,AAAA..."
          const b64 = fr.result.split(",")[1];
          res(b64);
        };
        fr.readAsDataURL(file);
      });
    }

    async function uploadFile(file, tech){
      // convert file → base‑64 string (without data‑URL header)
      const b64 = await fileToBase64(file);   // <-- converted in one go
  
      let idx = 0;
      for (let off = 0; off < b64.length; off += CHUNK_SIZE){
        const slice = b64.slice(off, off + CHUNK_SIZE);
  
        const res = await apiFetch("http://127.0.0.1:8000/upload-files", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({
            technology_id: tech.id,
            filename: file.name,
            content_base64: slice,
            chunk_index: idx,
            final: (off + CHUNK_SIZE >= b64.length)
          })
        });
  
        if(!res.ok){
          throw new Error(res.error || res.status);
        }
        idx++;
      }
    }
    
  // 4-A  inject upload modal right after DOM ready
  function injectModal() {
    const modal = document.createElement("div");
    modal.innerHTML = `
      <div id="trlModal" style="position:fixed;top:0;left:0;width:100%;height:100%;
          background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999">
        <div style="background:#fff;padding:20px;border-radius:6px;width:400px">
          <h3>Envie os documentos da tecnologia</h3>
          <input type="file" id="fileInput" multiple /><br><br>
          <button id="sendBtn">Enviar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
  
    document.querySelector("#sendBtn").onclick = async () => {
      const files = document.querySelector("#fileInput").files;
      const tech = await getTech();
      showLoader("Enviando documentos…");
      let index = 0;
      for (const f of files){
        showLoader(`Enviando ${++index}/${files.length}…`);
        await uploadFile(f, tech);
      }
      document.querySelector("#trlModal").remove();
      showLoader("Consultando IA…");
      await runQA();          // runQA now awaits; we'll hide loader inside it
    };
  }
  
  // 4-B  extract question + alternatives and query API
  async function runQA(){
    const tech = await getTech();
    const form = document.querySelector("#questionario1_myForm");
    const question = form.parentElement.querySelector("h2").innerText.trim();
    
    // Get only visible radio buttons and their labels
    const radios = [...form.querySelectorAll("input[type=radio]")].filter(radio => {
        const label = form.querySelector(`label[for=${radio.id}]`);
        return label && label.offsetParent !== null; // Check if element is visible
    });
  
    const opts = radios.map(r=>{
      const label = form.querySelector(`label[for=${r.id}]`).innerText.trim();
      return {value:r.value, text:label};
    });
  
    const questionContext = `Analise a seguinte pergunta e suas alternativas:

${question}

Alternativas:
${opts.map(o=>`${o.value}) ${o.text}`).join("\n")}

Responda de forma concisa qual alternativa está correta e por quê. 
Se múltiplas alternativas estiverem corretas, indique a última que estiver correta.`;

    // Log the prompt to console
    console.log("=== General Question Prompt ===");
    console.log(questionContext);
    console.log("==============================");

    // Check processing status and wait if needed
    while (true) {
        const statusResp = await apiFetch("http://127.0.0.1:8000/status", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ technology_id: tech.id })
        });

        if (!statusResp.ok) {
            hideLoader();
            console.error(statusResp);
            alert("Erro ao verificar status: " + (statusResp.error || statusResp.status));
            return;
        }

        const status = JSON.parse(statusResp.text);
        if (status.status === "ready") {
            break;
        }

        // Update loader message and wait before checking again
        showLoader("Processando documento... Por favor, aguarde.");
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds before checking again
    }

    showLoader("Consultando IA...");
    const resp = await apiFetch("http://127.0.0.1:8000/answer", {
      method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ 
            question: questionContext, 
            technology_id: tech.id
        })
    });
    
    if(!resp.ok){
      hideLoader();
      console.error(resp);
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
    showAnswer(text, opts);

    // Set up observer for next question
    setupQuestionObserver();
  }
  
  function setupQuestionObserver() {
    console.log("Setting up question observer...");
    
    // Create a MutationObserver to watch for changes in the DOM
    const observer = new MutationObserver((mutations) => {
        console.log("DOM mutation detected");
        
        // Check if any of the question divs became visible
        const questionIds = ['q12', 'q13', 'q14'];
        for (const id of questionIds) {
            const div = document.getElementById(id);
            if (div) {
                console.log(`Checking div ${id}:`, {
                    exists: true,
                    display: div.style.display,
                    visibility: div.style.visibility,
                    hidden: div.hidden
                });
                
                // Check multiple visibility conditions
                const isVisible = div.style.display !== 'none' && 
                                div.style.visibility !== 'hidden' && 
                                !div.hidden;
                
                if (isVisible) {
                    console.log(`Found visible question: ${id}`);
                    processQuestion(div);
                    observer.disconnect();
                    return;
                }
            }
        }
    });

    // Configure the observer to watch for attribute changes and subtree modifications
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'hidden']
    });
    
    console.log("Observer is now active");
  }

  async function processQuestion(questionDiv) {
    console.log("Processing question:", questionDiv.id);
    try {
        const tech = await getTech();
        const question = questionDiv.querySelector("h2").innerText.trim().replace(/[.:;]$/, '');
        
        // Get only visible radio buttons and their labels
        const radios = [...questionDiv.querySelectorAll("input[type=radio]")].filter(radio => {
            const label = questionDiv.querySelector(`label[for=${radio.id}]`);
            return label && label.offsetParent !== null;
        });
        
        console.log("Question text:", question);
        console.log("Number of visible options:", radios.length);
        
        const opts = radios.map(r => {
            const label = questionDiv.querySelector(`label[for=${r.id}]`).innerText.trim()
            return {value: r.value, text: label};
        });

        const questionContext = `Analise a seguinte pergunta e suas alternativas:

${question}

Alternativas:
${opts.map(o => `${o.value}) ${o.text}`).join("\n")}

Responda de forma concisa qual alternativa está correta e por quê. 
Se múltiplas alternativas estiverem corretas, indique a última que estiver correta.`;

        // Log the prompt to console
        console.log("=== General Question Prompt ===");
        console.log(questionContext);
        console.log("==============================");

        console.log("Sending API request...");
        showLoader("Consultando IA...");
        const resp = await apiFetch("http://127.0.0.1:8000/answer", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                question: questionContext, 
                technology_id: tech.id
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
        showAnswer(text, opts);
    } catch (error) {
        console.error("Error processing question:", error);
        hideLoader();
    }
  }
  
  function showAnswer(text, opts){
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
  
  // kick-off when page loads
  if (document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", injectModal);
  }else injectModal();

  function apiFetch(url, init){
    return chrome.runtime.sendMessage({type:"API_FETCH", url, init});
  }