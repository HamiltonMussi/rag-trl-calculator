/**
 * Content script for questionnaire page (Q1)
 * Handles file management and AI assistance for questionnaire
 * Maintains original functionality while using modern patterns
 */

(function() {
    'use strict';

    // === UTILITY FUNCTIONS ===

    async function getTech() {
        return await chrome.runtime.sendMessage({type: "GET_TECH"});
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

    // === FILE HELPER FUNCTIONS ===

    const CHUNK_SIZE = 1024 * 1024 * 3; // 3 MB per slice

    function fileToBase64(file) {
        return new Promise(res => {
            const fr = new FileReader();
            fr.onload = () => {
                const b64 = fr.result.split(",")[1];
                res(b64);
            };
            fr.readAsDataURL(file);
        });
    }

    async function uploadFile(file, tech) {
        const b64 = await fileToBase64(file);
        let idx = 0;
        for (let off = 0; off < b64.length; off += CHUNK_SIZE) {
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

            if(!res.ok) {
                throw new Error(res.error || res.status);
            }
            idx++;
        }
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
    window.disableAIButtons = disableAIButtons;
    window.enableAIButtons = enableAIButtons;

    // === FILE MODAL CREATION ===

    function injectModal() {
        const modal = document.createElement("div");
        modal.innerHTML = `
            <div id="trlModal" class="trl-modal">
                <div class="trl-modal__content">
                    <div class="trl-modal__header">
                        <div class="trl-modal__title">📄 Gerenciar Documentos</div>
                        <div class="trl-modal__subtitle">Visualize, remova e adicione documentos da sua tecnologia</div>
                    </div>
                    
                    <div class="trl-modal__body">
                        <div id="dropZone" class="drop-zone">
                            <div class="drop-zone__icon">📁</div>
                            <div class="drop-zone__title">Adicionar Novos Arquivos</div>
                            <div class="drop-zone__description">Arraste e solte aqui ou clique para selecionar</div>
                            <div class="drop-zone__warning">⚠️ Não use espaços ou acentos no nome do arquivo</div>
                            <input type="file" id="fileInput" multiple accept=".pdf,.doc,.docx,.txt" style="display:none;" />
                            <button id="selectFilesBtn" class="drop-zone__button">Selecionar Arquivos</button>
                        </div>
                        
                        <div id="fileList" class="file-list" style="display:none;">
                            <div class="file-list__title">📋 Arquivos Selecionados:</div>
                            <div id="fileItems" class="file-list__items"></div>
                        </div>
                        
                        <div id="uploadProgress" class="upload-progress" style="display:none;">
                            <div class="upload-progress__header">
                                <span class="upload-progress__label">Enviando...</span>
                                <span id="progressText" class="upload-progress__text">0%</span>
                            </div>
                            <div class="upload-progress__bar-container">
                                <div id="progressBar" class="upload-progress__bar"></div>
                            </div>
                        </div>
                        
                        <div class="modal-actions">
                            <button id="cancelBtn" class="btn btn--secondary">Cancelar</button>
                            <button id="actionBtn" class="btn btn--primary" disabled>Enviar Documentos</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        setupModalFunctionality();
    }

    // === MODAL FUNCTIONALITY ===

    function setupModalFunctionality() {
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
        
        // Event listeners
        fileInput.addEventListener('change', handleFileSelection);
        selectFilesBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });
        
        // Drag and drop handlers
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drop-zone--dragover');
        });
        
        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drop-zone--dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drop-zone--dragover');
            const files = Array.from(e.dataTransfer.files);
            handleFiles(files);
        });
        
        dropZone.addEventListener('click', (e) => {
            if (e.target === dropZone && !e.target.closest('#selectFilesBtn')) {
                fileInput.click();
            }
        });
        
        actionBtn.addEventListener('click', () => {
            if (selectedFiles.length > 0) {
                handleUploadAction();
            } else {
                handleAIAction();
            }
        });
        
        cancelBtn.addEventListener('click', () => {
            if (existingFiles.length === 0) {
                disableAIButtons();
            } else {
                enableAIButtons();
            }
            document.querySelector("#trlModal").remove();
        });
        
        function handleFileSelection() {
            const files = Array.from(fileInput.files);
            handleFiles(files);
        }
        
        function handleFiles(files) {
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
            
            updateActionButton();
        }

        function updateFileList() {
            const totalFiles = selectedFiles.length + existingFiles.length;
            
            if (totalFiles === 0) {
                fileList.style.display = 'none';
                return;
            }
            
            fileList.style.display = 'block';
            fileItems.innerHTML = '';
            
            // Add existing files first
            existingFiles.forEach((file) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                const uploadDate = new Date(file.uploaded_at).toLocaleDateString('pt-BR');
                
                fileItem.innerHTML = `
                    <div>
                        <div class="file-item__name">${file.filename} <span class="file-item__status file-item__status--uploaded">✓ Carregado</span></div>
                        <div class="file-item__size">${fileSize} MB • ${uploadDate}</div>
                    </div>
                    <button class="file-item__remove" data-existing-filename="${file.filename}">Remover</button>
                `;
                
                const removeBtn = fileItem.querySelector('.file-item__remove');
                removeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const filename = this.getAttribute('data-existing-filename');
                    removeExistingFileFromList(filename);
                });
                
                fileItems.appendChild(fileItem);
            });
            
            // Add newly selected files
            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                fileItem.innerHTML = `
                    <div>
                        <div class="file-item__name">${file.name} <span class="file-item__status file-item__status--pending">📤 Para enviar</span></div>
                        <div class="file-item__size">${fileSize} MB</div>
                    </div>
                    <button class="file-item__remove" data-index="${index}">Remover</button>
                `;
                
                const removeBtn = fileItem.querySelector('.file-item__remove');
                removeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const fileIndex = parseInt(this.getAttribute('data-index'));
                    removeFile(fileIndex);
                });
                
                fileItems.appendChild(fileItem);
            });
        }
        
        async function removeExistingFileFromList(filename) {
            try {
                const tech = await getTech();
                const response = await chrome.runtime.sendMessage({
                    type: "REMOVE_FILE",
                    technologyId: tech.id,
                    filename: filename
                });

                if (response.ok) {
                    existingFiles = existingFiles.filter(file => file.filename !== filename);
                    updateFileList();
                    updateActionButton();
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
            if (selectedFiles.length > 0) {
                actionBtn.disabled = false;
                actionBtn.textContent = `Enviar ${selectedFiles.length} Novo${selectedFiles.length > 1 ? 's' : ''} Documento${selectedFiles.length > 1 ? 's' : ''}`;
            } else if (existingFiles.length > 0) {
                actionBtn.disabled = false;
                actionBtn.textContent = 'Usar IA';
            } else {
                actionBtn.disabled = true;
                actionBtn.textContent = 'Enviar Documentos';
            }
        }
        
        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
            updateActionButton();
            
            try {
                const dt = new DataTransfer();
                selectedFiles.forEach(file => dt.items.add(file));
                fileInput.files = dt.files;
            } catch (error) {
                console.log('Could not update file input:', error);
            }
        }
        
        function updateProgress(current, total) {
            const percentage = Math.round((current / total) * 100);
            progressBar.style.width = `${percentage}%`;
            progressText.textContent = `${percentage}%`;
        }
        
        function handleAIAction() {
            enableAIButtons();
            document.querySelector("#trlModal").remove();
            
            setTimeout(() => {
                showLoader("Consultando IA…");
                runQA();
            }, 300);
        }

        async function handleUploadAction() {
            if (selectedFiles.length === 0) return;
            
            const tech = await getTech();
            
            dropZone.style.display = 'none';
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
                
                progressText.textContent = 'Concluído!';
                progressBar.style.background = '#00c5a4';
                
                selectedFiles = [];
                await loadExistingFilesData();
                
                setTimeout(() => {
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
    }

    // === Q&A PROCESSING ===

    async function runQA() {
        const tech = await getTech();
        const form = document.querySelector("#questionario1_myForm");
        const question = form.parentElement.querySelector("h2").innerText.trim();
        
        const radios = [...form.querySelectorAll("input[type=radio]")].filter(radio => {
            const label = form.querySelector(`label[for=${radio.id}]`);
            return label && label.offsetParent !== null;
        });

        const opts = radios.map(r => {
            const label = form.querySelector(`label[for=${r.id}]`).innerText.trim();
            return {value: r.value, text: label};
        });

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

            showLoader("Processando documentos... Por favor, aguarde.");
            await new Promise(resolve => setTimeout(resolve, 2000));
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
        
        if(!resp.ok) {
            hideLoader();
            console.error(resp);
            showNotification("Erro ao consultar a API: " + (resp.error || resp.status), 'error');
            return;
        }

        let text;
        try {
            const responseData = JSON.parse(resp.text);
            text = responseData.answer || resp.text;
        } catch (e) {
            text = resp.text;
        }

        hideLoader();
        showAnswer(text, opts);
        setupQuestionObserver();
    }

    // === ANSWER DISPLAY ===

    function showAnswer(text, opts) {
        const existingAnswer = document.querySelector("#aiAnswer");
        if (existingAnswer) {
            existingAnswer.remove();
        }
        
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

    // === QUESTION OBSERVER ===

    function setupQuestionObserver() {
        console.log("Setting up question observer...");
        
        const observer = new MutationObserver(() => {
            console.log("DOM mutation detected");
            
            const questionIds = ['q12', 'q13', 'q14'];
            for (const id of questionIds) {
                const div = document.getElementById(id);
                if (div) {
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
            
            const radios = [...questionDiv.querySelectorAll("input[type=radio]")].filter(radio => {
                const label = questionDiv.querySelector(`label[for=${radio.id}]`);
                return label && label.offsetParent !== null;
            });
            
            const opts = radios.map(r => {
                const label = questionDiv.querySelector(`label[for=${r.id}]`).innerText.trim()
                return {value: r.value, text: label};
            });

            const questionContext = `**Pergunta de Múltipla Escolha sobre TRL:**

${question}

**Alternativas disponíveis:**
${opts.map(o => `${o.value}) ${o.text}`).join('\n')}

**Formato de Resposta Requerido:**

**Se há informações suficientes:**
1. **Resposta:** [Letra da alternativa correta]
2. **Justificativa:** [Explicação detalhada baseada nos documentos, citando fontes específicas]

**Se não há informações suficientes:**
1. **Resposta:** DESCONHECIDO - Não há informações suficientes nos documentos fornecidos para responder esta pergunta.

**Instrução:** Selecione e justifique a alternativa mais adequada com base nos critérios TRL. Se múltiplas alternativas estiverem tecnicamente corretas, selecione a última (mais avançada) da lista.`;

            console.log(`=== Specific Question Prompt (${questionDiv.id}) ===`);
            console.log(questionContext);
            console.log("============================================");

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

            let text;
            try {
                const responseData = JSON.parse(resp.text);
                text = responseData.answer || resp.text;
            } catch (e) {
                text = resp.text;
            }

            hideLoader();
            showAnswer(text, opts);
        } catch (error) {
            console.error("Error processing question:", error);
            hideLoader();
        }
    }

    // === INITIALIZATION ===

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectModal);
    } else {
        injectModal();
    }

})();