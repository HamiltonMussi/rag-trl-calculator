/**
 * File Manager Component
 * Handles file upload, listing, and management functionality
 */

import { createElement, removeElement, showElement, hideElement, addEventListenerWithCleanup } from '../utils/dom.js';
import { getTechInfo } from '../utils/storage.js';
import { uploadFileInChunks, listFiles, removeFile } from '../utils/api.js';
import { showNotification, enableAIButtons, disableAIButtons } from './ui.js';

export class FileManager {
    constructor() {
        this.selectedFiles = [];
        this.existingFiles = [];
        this.isUploading = false;
        this.cleanupFunctions = [];
    }

    /**
     * Opens the file manager modal
     */
    async open() {
        this.createModal();
        await this.loadExistingFiles();
        this.setupEventListeners();
    }

    /**
     * Closes the file manager modal
     */
    close() {
        this.cleanup();
        removeElement("#trlModal");
    }

    /**
     * Creates the file manager modal structure
     */
    createModal() {
        const modal = createElement('div', {
            id: 'trlModal',
            className: 'trl-modal'
        });

        modal.innerHTML = this.getModalHTML();
        document.body.appendChild(modal);
    }

    /**
     * Sets up all event listeners for the modal
     */
    setupEventListeners() {
        const dropZone = document.querySelector("#dropZone");
        const fileInput = document.querySelector("#fileInput");
        const selectFilesBtn = document.querySelector("#selectFilesBtn");
        const actionBtn = document.querySelector("#actionBtn");
        const cancelBtn = document.querySelector("#cancelBtn");

        // File input change
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(fileInput, 'change', () => {
                this.handleFileSelection();
            })
        );

        // Select files button
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(selectFilesBtn, 'click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.click();
            })
        );

        // Drag and drop
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(dropZone, 'dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drop-zone--dragover');
            })
        );

        this.cleanupFunctions.push(
            addEventListenerWithCleanup(dropZone, 'dragleave', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drop-zone--dragover');
            })
        );

        this.cleanupFunctions.push(
            addEventListenerWithCleanup(dropZone, 'drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drop-zone--dragover');
                const files = Array.from(e.dataTransfer.files);
                this.handleFiles(files);
            })
        );

        // Drop zone click (but not on button)
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(dropZone, 'click', (e) => {
                if (e.target === dropZone && !e.target.closest('#selectFilesBtn')) {
                    fileInput.click();
                }
            })
        );

        // Action button
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(actionBtn, 'click', () => {
                if (this.selectedFiles.length > 0) {
                    this.handleUpload();
                } else {
                    this.handleUseAI();
                }
            })
        );

        // Cancel button
        this.cleanupFunctions.push(
            addEventListenerWithCleanup(cancelBtn, 'click', () => {
                this.handleCancel();
            })
        );
    }

    /**
     * Handles file input selection
     */
    handleFileSelection() {
        const fileInput = document.querySelector("#fileInput");
        const files = Array.from(fileInput.files);
        this.handleFiles(files);
    }

    /**
     * Handles file selection (from input or drag/drop)
     * @param {File[]} files - Selected files
     */
    handleFiles(files) {
        this.selectedFiles = files;
        this.updateFileList();
        this.updateActionButton();
    }

    /**
     * Loads existing files from the server
     */
    async loadExistingFiles() {
        try {
            const tech = await getTechInfo();
            if (!tech?.id) {
                console.log('No technology selected');
                return;
            }

            const files = await listFiles(tech.id);
            this.existingFiles = files.map(file => ({
                ...file,
                isExisting: true
            }));

            this.updateFileList();
            this.updateActionButton();
        } catch (error) {
            console.error('Error loading existing files:', error);
            showNotification('Erro ao carregar arquivos existentes', 'error');
        }
    }

    /**
     * Updates the file list display
     */
    updateFileList() {
        const fileList = document.querySelector("#fileList");
        const fileItems = document.querySelector("#fileItems");
        
        const totalFiles = this.selectedFiles.length + this.existingFiles.length;
        
        if (totalFiles === 0) {
            hideElement(fileList);
            return;
        }
        
        showElement(fileList, 'block');
        fileItems.innerHTML = '';
        
        // Add existing files
        this.existingFiles.forEach(file => {
            const fileItem = this.createFileItem(file, true);
            fileItems.appendChild(fileItem);
        });
        
        // Add selected files
        this.selectedFiles.forEach((file, index) => {
            const fileItem = this.createFileItem({
                ...file,
                filename: file.name,
                isExisting: false
            }, false, index);
            fileItems.appendChild(fileItem);
        });
    }

    /**
     * Creates a file item element
     * @param {Object} file - File object
     * @param {boolean} isExisting - Whether this is an existing file
     * @param {number} index - Index for new files
     * @returns {HTMLElement} File item element
     */
    createFileItem(file, isExisting, index = null) {
        const fileItem = createElement('div', {
            className: 'file-item'
        });

        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        const statusClass = isExisting ? 'file-item__status--uploaded' : 'file-item__status--pending';
        const statusText = isExisting ? '✓ Carregado' : '📤 Para enviar';
        
        let dateInfo = '';
        if (isExisting && file.uploaded_at) {
            const uploadDate = new Date(file.uploaded_at).toLocaleDateString('pt-BR');
            dateInfo = ` • ${uploadDate}`;
        }

        fileItem.innerHTML = `
            <div>
                <div class="file-item__name">
                    ${file.filename} 
                    <span class="file-item__status ${statusClass}">${statusText}</span>
                </div>
                <div class="file-item__size">${fileSize} MB${dateInfo}</div>
            </div>
            <button class="file-item__remove">Remover</button>
        `;

        const removeBtn = fileItem.querySelector('.file-item__remove');
        removeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (isExisting) {
                this.removeExistingFile(file.filename);
            } else {
                this.removeSelectedFile(index);
            }
        });

        return fileItem;
    }

    /**
     * Removes an existing file from the server
     * @param {string} filename - Filename to remove
     */
    async removeExistingFile(filename) {
        try {
            const tech = await getTechInfo();
            await removeFile(tech.id, filename);
            
            // Remove from local array
            this.existingFiles = this.existingFiles.filter(file => file.filename !== filename);
            this.updateFileList();
            this.updateActionButton();
            
            showNotification(`Arquivo "${filename}" removido com sucesso!`, 'success');
        } catch (error) {
            console.error('Error removing existing file:', error);
            showNotification(`Erro ao remover arquivo: ${error.message}`, 'error');
        }
    }

    /**
     * Removes a selected file from the list
     * @param {number} index - Index of file to remove
     */
    removeSelectedFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
        this.updateActionButton();
        
        // Update file input
        try {
            const dt = new DataTransfer();
            this.selectedFiles.forEach(file => dt.items.add(file));
            document.querySelector("#fileInput").files = dt.files;
        } catch (error) {
            console.log('Could not update file input:', error);
        }
    }

    /**
     * Updates the action button state and text
     */
    updateActionButton() {
        const actionBtn = document.querySelector("#actionBtn");
        
        if (this.selectedFiles.length > 0) {
            // New files selected - show upload button
            actionBtn.disabled = false;
            actionBtn.textContent = `Enviar ${this.selectedFiles.length} Novo${this.selectedFiles.length > 1 ? 's' : ''} Documento${this.selectedFiles.length > 1 ? 's' : ''}`;
        } else if (this.existingFiles.length > 0) {
            // No new files but existing files - show AI button
            actionBtn.disabled = false;
            actionBtn.textContent = 'Usar IA';
        } else {
            // No files at all - disabled
            actionBtn.disabled = true;
            actionBtn.textContent = 'Enviar Documentos';
        }
    }

    /**
     * Handles file upload process
     */
    async handleUpload() {
        if (this.selectedFiles.length === 0 || this.isUploading) return;
        
        this.isUploading = true;
        
        try {
            const tech = await getTechInfo();
            
            // Show progress UI
            hideElement(document.querySelector("#dropZone"));
            hideElement(document.querySelector("#fileList"));
            showElement(document.querySelector("#uploadProgress"), 'block');
            hideElement(document.querySelector("#actionBtn"));
            document.querySelector("#cancelBtn").textContent = 'Fechar';
            
            // Upload files
            for (let i = 0; i < this.selectedFiles.length; i++) {
                const file = this.selectedFiles[i];
                this.updateProgress(i, this.selectedFiles.length);
                await uploadFileInChunks(file, tech, (current, total) => {
                    // File-level progress could be shown here
                });
            }
            
            this.updateProgress(this.selectedFiles.length, this.selectedFiles.length);
            
            // Success state
            const progressText = document.querySelector("#progressText");
            const progressBar = document.querySelector("#progressBar");
            progressText.textContent = 'Concluído!';
            progressBar.style.background = '#00c5a4';
            
            // Clear selected files and reload existing files
            this.selectedFiles = [];
            await this.loadExistingFiles();
            
            setTimeout(() => {
                enableAIButtons();
                this.close();
                showNotification('Arquivos enviados com sucesso!', 'success');
            }, 1500);
            
        } catch (error) {
            console.error('Upload error:', error);
            const progressText = document.querySelector("#progressText");
            const progressBar = document.querySelector("#progressBar");
            progressText.textContent = 'Erro no upload';
            progressBar.style.background = '#ef4444';
            showNotification('Erro ao enviar arquivos: ' + error.message, 'error');
        } finally {
            this.isUploading = false;
        }
    }

    /**
     * Handles "Use AI" action
     */
    handleUseAI() {
        enableAIButtons();
        this.close();
        
        // Show loading and trigger AI functionality would go here
        // This would be implemented by the calling code
        setTimeout(() => {
            showNotification('IA habilitada! Agora você pode usar os botões de assistência.', 'success');
        }, 300);
    }

    /**
     * Handles cancel action
     */
    handleCancel() {
        if (this.existingFiles.length === 0) {
            disableAIButtons();
        } else {
            enableAIButtons();
        }
        this.close();
    }

    /**
     * Updates upload progress display
     * @param {number} current - Current progress
     * @param {number} total - Total items
     */
    updateProgress(current, total) {
        const percentage = Math.round((current / total) * 100);
        const progressBar = document.querySelector("#progressBar");
        const progressText = document.querySelector("#progressText");
        
        if (progressBar) progressBar.style.width = `${percentage}%`;
        if (progressText) progressText.textContent = `${percentage}%`;
    }

    /**
     * Cleans up event listeners and resources
     */
    cleanup() {
        this.cleanupFunctions.forEach(cleanup => cleanup());
        this.cleanupFunctions = [];
    }

    /**
     * Returns the modal HTML structure
     * @returns {string} Modal HTML
     */
    getModalHTML() {
        return `
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
        `;
    }
}