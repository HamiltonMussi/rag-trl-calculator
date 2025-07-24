async function getTech() {
    return await chrome.runtime.sendMessage({type: "GET_TECH"});
  }

// === simple loader =========================================
function showLoader(msg){
  let l = document.querySelector("#trlLoader");
  if(!l){
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
function hideLoader(){
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
          background:rgba(0,0,0,0.75);display:flex;align-items:center;justify-content:center;z-index:9999;
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,Cantarell,sans-serif;">
        <div style="background:#fff;padding:0;border-radius:12px;width:520px;max-width:90vw;
            box-shadow:0 25px 50px -12px rgba(0,0,0,0.25);transform:scale(0.95);
            animation:modalSlideIn 0.3s ease-out forwards;">
          
          <!-- Header -->
          <div style="background:linear-gradient(135deg,#0c3943 0%,#00c5a4 100%);
              color:white;padding:24px 32px;border-radius:12px 12px 0 0;text-align:center;">
            <div style="font-size:24px;font-weight:600;margin-bottom:8px;">
              📄 Gerenciar Documentos
            </div>
            <div style="font-size:14px;opacity:0.9;">
              Visualize, remova e adicione documentos da sua tecnologia
            </div>
          </div>
          
          <!-- Content -->
          <div style="padding:32px;">
            <!-- Drop Zone -->
            <div id="dropZone" style="border:2px dashed #d1d5db;border-radius:8px;padding:40px 20px;
                text-align:center;transition:all 0.3s ease;cursor:pointer;background:#f9fafb;
                margin-bottom:24px;">
              <div style="font-size:48px;margin-bottom:16px;">📁</div>
              <div style="font-size:16px;font-weight:500;color:#374151;margin-bottom:8px;">
                Adicionar Novos Arquivos
              </div>
              <div style="font-size:14px;color:#6b7280;margin-bottom:8px;">
                Arraste e solte aqui ou clique para selecionar
              </div>
              <div style="font-size:12px;color:#ef4444;margin-bottom:16px;">
                ⚠️ Não use espaços ou acentos no nome do arquivo
              </div>
              <input type="file" id="fileInput" multiple accept=".pdf,.doc,.docx,.txt" 
                  style="display:none;" />
              <div id="selectFilesBtn" style="display:inline-block;background:#0c3943;color:white;padding:10px 20px;
                  border-radius:6px;font-size:14px;font-weight:500;cursor:pointer;
                  transition:background 0.2s ease;">
                Selecionar Arquivos
              </div>
            </div>
            
            <!-- File List -->
            <div id="fileList" style="display:none;margin-bottom:24px;">
              <div style="font-size:14px;font-weight:500;color:#374151;margin-bottom:12px;">
                📋 Arquivos Selecionados:
              </div>
              <div id="fileItems" style="max-height:150px;overflow-y:auto;"></div>
            </div>
            
            <!-- Progress -->
            <div id="uploadProgress" style="display:none;margin-bottom:24px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="font-size:14px;font-weight:500;color:#374151;">Enviando...</span>
                <span id="progressText" style="font-size:14px;color:#6b7280;">0%</span>
              </div>
              <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;">
                <div id="progressBar" style="background:linear-gradient(90deg,#0c3943,#00c5a4);
                    height:100%;transition:width 0.3s ease;width:0%;"></div>
              </div>
            </div>
            
            <!-- Actions -->
            <div style="display:flex;gap:12px;justify-content:flex-end;">
              <button id="cancelBtn" style="background:#f3f4f6;color:#374151;border:none;
                  padding:12px 24px;border-radius:6px;font-size:14px;font-weight:500;
                  cursor:pointer;transition:background 0.2s ease;">
                Cancelar
              </button>
              <button id="actionBtn" disabled style="background:#9ca3af;color:white;border:none;
                  padding:12px 24px;border-radius:6px;font-size:14px;font-weight:500;
                  cursor:not-allowed;transition:all 0.2s ease;">
                Enviar Documentos
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- CSS Animations -->
      <style>
        @keyframes modalSlideIn {
          from { transform: scale(0.95); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        #dropZone:hover {
          border-color: #00c5a4 !important;
          background: #fff7d6 !important;
        }
        #dropZone.dragover {
          border-color: #00c5a4 !important;
          background: #fff7d6 !important;
          transform: scale(1.02);
        }
        #actionBtn:not(:disabled) {
          background: linear-gradient(135deg, #0c3943 0%, #00c5a4 100%) !important;
          cursor: pointer !important;
        }
        #actionBtn:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(12, 57, 67, 0.4);
        }
        #cancelBtn:hover {
          background: #e5e7eb !important;
        }
        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: #f9fafb;
          border-radius: 6px;
          margin-bottom: 8px;
          font-size: 14px;
        }
        .file-item:last-child {
          margin-bottom: 0;
        }
        .file-name {
          color: #374151;
          font-weight: 500;
        }
        .file-size {
          color: #6b7280;
          font-size: 12px;
        }
        .file-remove {
          background: #ef4444;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 12px;
          cursor: pointer;
          transition: background 0.2s ease;
        }
        .file-remove:hover {
          background: #dc2626;
        }
      </style>`;
    document.body.appendChild(modal);
  
    // Setup drag and drop functionality
    const dropZone = document.querySelector("#dropZone");
    const fileInput = document.querySelector("#fileInput");
    const fileList = document.querySelector("#fileList");
    const fileItems = document.querySelector("#fileItems");
    const actionBtn = document.querySelector("#actionBtn");
    const cancelBtn = document.querySelector("#cancelBtn");
    const uploadProgress = document.querySelector("#uploadProgress");
    const progressBar = document.querySelector("#progressBar");
    const progressText = document.querySelector("#progressText");
    const selectFilesBtn = document.querySelector("#selectFilesBtn");
    
    let selectedFiles = [];
    let existingFiles = [];
    
    // Load existing files when modal opens
    loadExistingFilesData();
    
    // File input change handler
    fileInput.addEventListener('change', function(e) {
      console.log('File input changed, files:', e.target.files.length);
      handleFileSelection();
    });
    
    // Select files button click handler
    selectFilesBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('Select files button clicked');
      fileInput.click();
    });
    
    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const files = Array.from(e.dataTransfer.files);
      console.log('Files dropped:', files.length);
      handleFiles(files);
    });
    
    // Drop zone click handler (but not on the select button)
    dropZone.addEventListener('click', (e) => {
      if (e.target === dropZone && !e.target.closest('#selectFilesBtn')) {
        console.log('Drop zone clicked');
        fileInput.click();
      }
    });
    
    function handleFileSelection() {
      const files = Array.from(fileInput.files);
      console.log('handleFileSelection called, files found:', files.length);
      handleFiles(files);
    }
    
    function handleFiles(files) {
      console.log('handleFiles called with:', files.length, 'files');
      selectedFiles = files;
      updateFileList();
      updateActionButton();
    }
    
    async function loadExistingFilesData() {
      try {
        const tech = await getTech();
        if (!tech || !tech.id) {
          console.log('No technology selected');
          return;
        }

        const response = await chrome.runtime.sendMessage({
          type: "LIST_FILES",
          technologyId: tech.id
        });

        if (response.ok && response.data) {
          existingFiles = response.data.files.map(file => ({
            ...file,
            isExisting: true
          }));
          updateFileList();
          updateActionButton();
        }
      } catch (error) {
        console.error('Error loading existing files:', error);
      }
      
      // Always call updateActionButton to handle the case when there are no existing files
      updateActionButton();
    }

    function updateFileList() {
      console.log('updateFileList called, selectedFiles.length:', selectedFiles.length, 'existingFiles.length:', existingFiles.length);
      
      const totalFiles = selectedFiles.length + existingFiles.length;
      
      if (totalFiles === 0) {
        fileList.style.display = 'none';
        return;
      }
      
      fileList.style.display = 'block';
      fileItems.innerHTML = '';
      
      // Add existing files first
      existingFiles.forEach((file, index) => {
        console.log(`Adding existing file ${index}: ${file.filename}`);
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        const uploadDate = new Date(file.uploaded_at).toLocaleDateString('pt-BR');
        
        fileItem.innerHTML = `
          <div>
            <div class="file-name">${file.filename} <span style="color:#00c5a4;font-size:11px;">✓ Carregado</span></div>
            <div class="file-size">${fileSize} MB • ${uploadDate}</div>
          </div>
          <button class="file-remove" data-existing-filename="${file.filename}">Remover</button>
        `;
        
        // Add event listener to the remove button for existing files
        const removeBtn = fileItem.querySelector('.file-remove');
        removeBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const filename = this.getAttribute('data-existing-filename');
          console.log('Removing existing file:', filename);
          removeExistingFileFromList(filename);
        });
        
        fileItems.appendChild(fileItem);
      });
      
      // Add newly selected files
      selectedFiles.forEach((file, index) => {
        console.log(`Adding selected file ${index}: ${file.name} (${file.size} bytes)`);
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        fileItem.innerHTML = `
          <div>
            <div class="file-name">${file.name} <span style="color:#0c3943;font-size:11px;">📤 Para enviar</span></div>
            <div class="file-size">${fileSize} MB</div>
          </div>
          <button class="file-remove" data-index="${index}">Remover</button>
        `;
        
        // Add event listener to the remove button for selected files
        const removeBtn = fileItem.querySelector('.file-remove');
        removeBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          const fileIndex = parseInt(this.getAttribute('data-index'));
          console.log('Removing selected file at index:', fileIndex);
          removeFile(fileIndex);
        });
        
        fileItems.appendChild(fileItem);
      });
    }
    
    async function removeExistingFileFromList(filename) {
      // User clicked remove - proceed with removal

      try {
        const tech = await getTech();
        const response = await chrome.runtime.sendMessage({
          type: "REMOVE_FILE",
          technologyId: tech.id,
          filename: filename
        });

        if (response.ok) {
          // Remove from existingFiles array
          existingFiles = existingFiles.filter(file => file.filename !== filename);
          updateFileList();
          updateActionButton();
          
          // Show success message
          showNotification(`Arquivo "${filename}" removido com sucesso!`, 'success');
        } else {
          showNotification(`Erro ao remover arquivo: ${response.error || 'Erro desconhecido'}`, 'error');
        }
      } catch (error) {
        console.error('Error removing existing file:', error);
        showNotification(`Erro ao remover arquivo: ${error.message}`, 'error');
      }
    }

    function updateActionButton() {
      console.log('updateActionButton called, selectedFiles.length:', selectedFiles.length, 'existingFiles.length:', existingFiles.length);
      
      if (selectedFiles.length > 0) {
        // New files selected - show upload button
        actionBtn.disabled = false;
        actionBtn.textContent = `Enviar ${selectedFiles.length} Novo${selectedFiles.length > 1 ? 's' : ''} Documento${selectedFiles.length > 1 ? 's' : ''}`;
        actionBtn.onclick = handleUploadAction;
        console.log('Action button: Upload mode enabled');
      } else if (existingFiles.length > 0) {
        // No new files but existing files - show AI button
        actionBtn.disabled = false;
        actionBtn.textContent = 'Usar IA';
        actionBtn.onclick = handleAIAction;
        console.log('Action button: AI mode enabled');
      } else {
        // No files at all - disabled
        actionBtn.disabled = true;
        actionBtn.textContent = 'Enviar Documentos';
        actionBtn.onclick = null;
        console.log('Action button: Disabled');
      }
    }
    
    function removeFile(index) {
      console.log('removeFile called with index:', index);
      console.log('selectedFiles before removal:', selectedFiles.length);
      
      selectedFiles.splice(index, 1);
      console.log('selectedFiles after removal:', selectedFiles.length);
      
      updateFileList();
      updateActionButton();
      
      // Update file input
      try {
        const dt = new DataTransfer();
        selectedFiles.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
        console.log('File input updated successfully');
      } catch (error) {
        console.log('Could not update file input:', error);
      }
    }
    
    function updateProgress(current, total) {
      const percentage = Math.round((current / total) * 100);
      progressBar.style.width = `${percentage}%`;
      progressText.textContent = `${percentage}%`;
    }
    
    // Make functions globally accessible
    window.disableAIButtons = function disableAIButtons() {
      // Disable AI buttons in current page
      const aiButtons = document.querySelectorAll('.ai-assist-button, button[innerHTML*="AI Assist"]');
      aiButtons.forEach(btn => {
        btn.disabled = true;
        btn.style.background = '#9ca3af';
        btn.style.cursor = 'not-allowed';
        btn.style.opacity = '0.6';
        btn.title = 'Documentos não carregados. Por favor, faça upload dos documentos primeiro.';
      });
      
      // Set a flag to disable AI functionality globally
      window.aiDisabled = true;
      
      // Store in chrome storage for persistence across pages
      if (typeof chrome !== 'undefined' && chrome.storage) {
        chrome.storage.local.set({aiDisabled: true});
      }
      
      console.log('AI buttons disabled - no documents uploaded');
    }
    
    // Function to enable all AI buttons
    window.enableAIButtons = function enableAIButtons() {
      const aiButtons = document.querySelectorAll('.ai-assist-button, button[innerHTML*="AI Assist"]');
      aiButtons.forEach(btn => {
        btn.disabled = false;
        btn.style.background = '#00c5a4';
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

    // Action button handlers
    function handleAIAction() {
      enableAIButtons();
      document.querySelector("#trlModal").remove();
      
      // Trigger AI functionality with existing documents
      setTimeout(() => {
        showLoader("Consultando IA…");
        runQA();
      }, 300);
    }

    async function handleUploadAction() {
      if (selectedFiles.length === 0) return;
      
      const tech = await getTech();
      
      // Hide file selection, show progress
      document.querySelector("#dropZone").style.display = 'none';
      fileList.style.display = 'none';
      uploadProgress.style.display = 'block';
      actionBtn.style.display = 'none';
      cancelBtn.textContent = 'Fechar';
      
      try {
        for (let i = 0; i < selectedFiles.length; i++) {
          const file = selectedFiles[i];
          updateProgress(i, selectedFiles.length);
          await uploadFile(file, tech);
        }
        
        updateProgress(selectedFiles.length, selectedFiles.length);
        
        // Success state
        progressText.textContent = 'Concluído!';
        progressBar.style.background = '#00c5a4';
        
        // Clear selected files and reload existing files to show newly uploaded files
        selectedFiles = [];
        await loadExistingFilesData();
        
        setTimeout(() => {
          // Enable AI buttons after successful upload
          enableAIButtons();
          document.querySelector("#trlModal").remove();
          
          showLoader("Consultando IA…");
          runQA();
        }, 1500);
        
      } catch (error) {
        console.error('Upload error:', error);
        progressText.textContent = 'Erro no upload';
        progressBar.style.background = '#ef4444';
        showNotification('Erro ao enviar arquivos: ' + error.message, 'error');
      }
    }

    cancelBtn.onclick = () => {
      // Only disable AI if there are no existing files
      if (existingFiles.length === 0) {
        disableAIButtons();
      } else {
        // If there are existing files, enable AI
        enableAIButtons();
      }
      document.querySelector("#trlModal").remove();
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
  
    // ========================================
    // UI-CONTEXT FORMATTING ONLY
    // ========================================
    // Frontend handles clean question formatting - backend applies all prompting techniques
    
    const questionContext = `**Pergunta de Múltipla Escolha sobre TRL:**

${question}

**Alternativas disponíveis:**
${opts.map((o, index) => `${o.value}) ${o.text}`).join('\n')}

**Formato de Resposta Requerido:**

**Se há informações suficientes:**
1. **Resposta:** [Letra da alternativa correta]
2. **Justificativa:** [Explicação detalhada baseada nos documentos, citando fontes específicas]

**Se não há informações suficientes:**
1. **Resposta:** DESCONHECIDO - Não há informações suficientes nos documentos fornecidos para responder esta pergunta.

**Instrução:** Selecione e justifique a alternativa mais adequada com base nos critérios TRL. Se múltiplas alternativas estiverem tecnicamente corretas, selecione a última (mais avançada) da lista.`;

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
            showNotification("Erro ao verificar status: " + (statusResp.error || statusResp.status), 'error');
            return;
        }

        const status = JSON.parse(statusResp.text);
        if (status.status === "ready") {
            break;
        }

        // Update loader message and wait before checking again
        showLoader("Processando documentos... Por favor, aguarde.");
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
    showAnswer(text, opts);

    // Set up observer for next question
    setupQuestionObserver();
  }
  
  function setupQuestionObserver() {
    console.log("Setting up question observer...");
    
    // Create a MutationObserver to watch for changes in the DOM
    const observer = new MutationObserver(() => {
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
  
  // kick-off when page loads
  if (document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", injectModal);
  }else injectModal();

  function apiFetch(url, init){
    return chrome.runtime.sendMessage({type:"API_FETCH", url, init});
  }


  // Helper function to refresh file manager
  async function loadFiles(technologyId) {
    const filesList = document.querySelector("#filesList");
    if (!filesList) return; // File manager not open
    
    try {
      const response = await chrome.runtime.sendMessage({
        type: "LIST_FILES",
        technologyId: technologyId
      });

      if (response.ok && response.data) {
        const files = response.data.files;
        
        if (files.length === 0) {
          filesList.innerHTML = `
            <div style="text-align: center; color: #666; padding: 20px;">
              <div style="font-size: 24px; margin-bottom: 8px;">📭</div>
              <div style="font-size: 14px;">Nenhum arquivo carregado</div>
              <div style="font-size: 12px; color: #999;">Clique em "Adicionar Mais Arquivos" para começar</div>
            </div>
          `;
        } else {
          filesList.innerHTML = `
            <div style="font-size: 14px; font-weight: 500; color: #374151; margin-bottom: 12px;">
              📋 ${files.length} arquivo${files.length > 1 ? 's' : ''} carregado${files.length > 1 ? 's' : ''}:
            </div>
            <div style="max-height: 200px; overflow-y: auto;" id="filesContainer"></div>
          `;

          const filesContainer = document.querySelector("#filesContainer");
          files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.style = `
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 8px 12px;
              background: #f9fafb;
              border-radius: 6px;
              margin-bottom: 8px;
              font-size: 13px;
            `;

            const fileSize = (file.size / 1024 / 1024).toFixed(2);
            const uploadDate = new Date(file.uploaded_at).toLocaleDateString('pt-BR');
            
            fileItem.innerHTML = `
              <div style="flex: 1;">
                <div style="color: #374151; font-weight: 500;">${file.filename}</div>
                <div style="color: #6b7280; font-size: 11px;">${fileSize} MB • ${uploadDate}</div>
              </div>
              <button class="remove-file-btn" data-filename="${file.filename}" style="
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                cursor: pointer;
                transition: background 0.2s ease;
              ">Remover</button>
            `;
            
            filesContainer.appendChild(fileItem);
          });

          // Add event listeners to remove buttons
          document.querySelectorAll('.remove-file-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
              const filename = e.target.getAttribute('data-filename');
              await removeFileFromQ1(technologyId, filename);
            });
          });
        }
      }
    } catch (error) {
      console.error('Error loading files:', error);
    }
  }

  async function removeFileFromQ1(technologyId, filename) {
    // User clicked remove - proceed with removal

    try {
      const response = await chrome.runtime.sendMessage({
        type: "REMOVE_FILE",
        technologyId: technologyId,
        filename: filename
      });

      if (response.ok) {
        // Reload the files list
        await loadFiles(technologyId);
        
        // Show success message
        showNotification(`Arquivo "${filename}" removido com sucesso!`, 'success');
      } else {
        showNotification(`Erro ao remover arquivo: ${response.error || 'Erro desconhecido'}`, 'error');
      }
    } catch (error) {
      console.error('Error removing file:', error);
      showNotification(`Erro ao remover arquivo: ${error.message}`, 'error');
    }
  }