// File Manager JavaScript for Document Converter

class FileManager {
    constructor() {
        this.currentTab = 'uploads';
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.files = [];
        this.filteredFiles = [];
        this.selectedFiles = new Set();
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.searchQuery = '';
        this.expandedFolders = new Set(); // Track expanded conversion folders
        this.viewMode = 'list'; // 'list' or 'tree'
        this.conversionFolders = null; // Processed folder data for tree view
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadFiles();
    }

    setupEventListeners() {
        // Search
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.searchQuery = e.target.value.toLowerCase();
            this.filterAndSort();
        });

        // Sort
        document.getElementById('sort-select').addEventListener('change', (e) => {
            this.sortBy = e.target.value;
            this.filterAndSort();
        });

        // Pagination
        document.getElementById('prev-btn').addEventListener('click', () => this.previousPage());
        document.getElementById('next-btn').addEventListener('click', () => this.nextPage());
        document.getElementById('prev-mobile').addEventListener('click', () => this.previousPage());
        document.getElementById('next-mobile').addEventListener('click', () => this.nextPage());
    }

    async loadFiles() {
        try {
            this.showLoading();
            const response = await fetch(`/api/files/${this.currentTab}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.files = data.files || [];
            
            // Check if we're viewing outputs (conversion folders) to enable tree view
            if (this.currentTab === 'outputs' && this.files.length > 0) {
                this.processConversionFolders();
            }
            
            this.updateCounts();
            this.filterAndSort();
            
        } catch (error) {
            console.error('Error loading files:', error);
            this.showError('Failed to load files. Please try again.');
            this.files = [];
            this.showEmpty();
        }
    }

    updateCounts() {
        // Update tab counts (this would need actual API calls for other tabs)
        document.getElementById(`${this.currentTab}-count`).textContent = this.files.length;
    }

    filterAndSort() {
        if (this.viewMode === 'tree' && this.conversionFolders) {
            // For tree view, we'll handle filtering in renderTreeView
            this.renderFiles();
            return;
        }
        
        // Filter files based on search query
        this.filteredFiles = this.files.filter(file => {
            if (!this.searchQuery) return true;
            
            return file.name.toLowerCase().includes(this.searchQuery) ||
                   file.type.toLowerCase().includes(this.searchQuery);
        });

        // Sort files
        this.filteredFiles.sort((a, b) => {
            let valueA, valueB;
            
            switch (this.sortBy) {
                case 'name':
                    valueA = a.name.toLowerCase();
                    valueB = b.name.toLowerCase();
                    break;
                case 'size':
                    valueA = a.size;
                    valueB = b.size;
                    break;
                case 'date':
                    valueA = new Date(a.lastModified);
                    valueB = new Date(b.lastModified);
                    break;
                case 'type':
                    valueA = a.type.toLowerCase();
                    valueB = b.type.toLowerCase();
                    break;
                default:
                    return 0;
            }

            if (valueA < valueB) return this.sortOrder === 'asc' ? -1 : 1;
            if (valueA > valueB) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        this.currentPage = 1;
        this.renderFiles();
    }

    renderFiles() {
        if (this.filteredFiles.length === 0 && (!this.conversionFolders || this.conversionFolders.length === 0)) {
            this.showEmpty();
            return;
        }

        this.showTable();
        
        if (this.viewMode === 'tree' && this.conversionFolders) {
            this.renderTreeView();
        } else {
            this.renderListView();
        }
    }

    renderListView() {
        const tbody = document.getElementById('files-tbody');
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredFiles.length);
        const currentFiles = this.filteredFiles.slice(startIndex, endIndex);

        tbody.innerHTML = currentFiles.map(file => this.renderFileRow(file)).join('');
        this.updatePagination();
    }

    renderFileRow(file) {
        const isSelected = this.selectedFiles.has(file.name);
        const fileIcon = this.getFileIcon(file.type);
        const formattedSize = this.formatFileSize(file.size);
        const formattedDate = this.formatDate(file.lastModified);

        return `
            <tr class="${isSelected ? 'bg-blue-50' : ''}">
                <td class="px-6 py-4 whitespace-nowrap">
                    <input type="checkbox" 
                           class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 file-checkbox" 
                           data-filename="${file.name}"
                           ${isSelected ? 'checked' : ''}
                           onchange="fileManager.toggleFileSelection('${file.name}')">
                </td>
                <td class="px-6 py-4">
                    <div class="flex items-center">
                        <i class="${fileIcon} text-gray-400 mr-3 flex-shrink-0"></i>
                        <div class="min-w-0 flex-1">
                            <div class="text-sm font-medium text-gray-900 file-name" title="${file.name}">${file.name}</div>
                            ${file.originalName ? `<div class="text-sm text-gray-500 file-name" title="${file.originalName}">Original: ${file.originalName}</div>` : ''}
                            <div class="block md:hidden text-xs text-gray-500 mt-1">
                                ${formattedSize} • ${file.type} • ${formattedDate}
                            </div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden-mobile">${formattedSize}</td>
                <td class="px-6 py-4 whitespace-nowrap hidden-mobile">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${this.getTypeColor(file.type)}">
                        ${file.type}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden-mobile">${formattedDate}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div class="flex items-center space-x-2">
                        ${this.renderActionButtons(file)}
                    </div>
                </td>
            </tr>
        `;
    }

    renderActionButtons(file) {
        const buttons = [];
        
        // View button (for all file types that can be viewed in browser)
        if (this.isViewable(file.type)) {
            buttons.push(`
                <button onclick="fileManager.viewFile('${file.name}')" 
                        class="btn-icon text-indigo-600 hover:text-indigo-800" 
                        title="View">
                    <i class="fas fa-eye"></i>
                </button>
            `);
        }
        
        // Download button
        buttons.push(`
            <button onclick="fileManager.downloadFile('${file.name}')" 
                    class="btn-icon text-blue-600 hover:text-blue-800" 
                    title="Download">
                <i class="fas fa-download"></i>
            </button>
        `);

        // Preview button (for text/markdown files only)
        if (this.isPreviewable(file.type)) {
            buttons.push(`
                <button onclick="fileManager.previewFile('${file.name}')" 
                        class="btn-icon text-green-600 hover:text-green-800" 
                        title="Preview Text">
                    <i class="fas fa-file-alt"></i>
                </button>
            `);
        }

        // Convert Again button (for uploads tab)
        if (this.currentTab === 'uploads') {
            buttons.push(`
                <button onclick="fileManager.convertAgain('${file.name}')" 
                        class="btn-icon text-purple-600 hover:text-purple-800" 
                        title="Convert Again">
                    <i class="fas fa-sync"></i>
                </button>
            `);
        }

        // Delete button
        buttons.push(`
            <button onclick="fileManager.deleteFile('${file.name}')" 
                    class="btn-icon text-red-600 hover:text-red-800" 
                    title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        `);

        return buttons.join('');
    }

    getFileIcon(type) {
        const typeIcons = {
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'xls': 'fas fa-file-excel',
            'xlsx': 'fas fa-file-excel',
            'ppt': 'fas fa-file-powerpoint',
            'pptx': 'fas fa-file-powerpoint',
            'txt': 'fas fa-file-alt',
            'md': 'fab fa-markdown',
            'json': 'fas fa-file-code',
            'csv': 'fas fa-file-csv',
            'epub': 'fas fa-book',
            'mobi': 'fas fa-book'
        };
        
        return typeIcons[type.toLowerCase()] || 'fas fa-file';
    }

    getTypeColor(type) {
        const typeColors = {
            'pdf': 'bg-red-100 text-red-800',
            'doc': 'bg-blue-100 text-blue-800',
            'docx': 'bg-blue-100 text-blue-800',
            'xls': 'bg-green-100 text-green-800',
            'xlsx': 'bg-green-100 text-green-800',
            'ppt': 'bg-orange-100 text-orange-800',
            'pptx': 'bg-orange-100 text-orange-800',
            'txt': 'bg-gray-100 text-gray-800',
            'md': 'bg-purple-100 text-purple-800',
            'json': 'bg-yellow-100 text-yellow-800'
        };
        
        return typeColors[type.toLowerCase()] || 'bg-gray-100 text-gray-800';
    }

    isPreviewable(type) {
        const previewableTypes = [
            // Text files
            'txt', 'md', 'json', 'csv', 'xml', 'yaml', 'yml', 'html', 'css', 'js', 'py', 'java', 'cpp', 'sql', 'php', 'go', 'rust',
            // Images
            'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'tif',
            // PDFs (basic preview)
            'pdf'
        ];
        return previewableTypes.includes(type.toLowerCase());
    }

    isViewable(type) {
        // Files that can be viewed directly in the browser
        const viewableTypes = [
            // Text files
            'txt', 'md', 'json', 'csv', 'xml', 'yaml', 'yml',
            // Code files
            'py', 'js', 'ts', 'html', 'css', 'sql', 'php', 'java', 'cpp', 'go', 'rust',
            // Documents
            'pdf',
            // Images
            'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'tif'
        ];
        return viewableTypes.includes(type.toLowerCase());
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredFiles.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredFiles.length);

        // Update info text
        document.getElementById('showing-start').textContent = this.filteredFiles.length > 0 ? startIndex + 1 : 0;
        document.getElementById('showing-end').textContent = endIndex;
        document.getElementById('total-files').textContent = this.filteredFiles.length;

        // Update navigation buttons
        document.getElementById('prev-btn').disabled = this.currentPage === 1;
        document.getElementById('next-btn').disabled = this.currentPage === totalPages;
        document.getElementById('prev-mobile').disabled = this.currentPage === 1;
        document.getElementById('next-mobile').disabled = this.currentPage === totalPages;

        // Generate page numbers
        this.generatePageNumbers(totalPages);
    }

    generatePageNumbers(totalPages) {
        const pageNumbers = document.getElementById('page-numbers');
        pageNumbers.innerHTML = '';

        const maxVisiblePages = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const button = document.createElement('button');
            button.className = `relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                i === this.currentPage 
                    ? 'z-10 bg-blue-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                    : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
            }`;
            button.textContent = i;
            button.onclick = () => this.goToPage(i);
            pageNumbers.appendChild(button);
        }
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderFiles();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.filteredFiles.length / this.itemsPerPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderFiles();
        }
    }

    goToPage(page) {
        this.currentPage = page;
        this.renderFiles();
    }

    toggleFileSelection(filename) {
        if (this.selectedFiles.has(filename)) {
            this.selectedFiles.delete(filename);
        } else {
            this.selectedFiles.add(filename);
        }
        
        this.updateBulkActions();
        this.updateSelectAllCheckbox();
    }

    updateBulkActions() {
        const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
        const bulkDownloadBtn = document.getElementById('bulk-download-btn');
        if (this.selectedFiles.size > 0) {
            bulkDeleteBtn.classList.remove('hidden');
            bulkDownloadBtn.classList.remove('hidden');
        } else {
            bulkDeleteBtn.classList.add('hidden');
            bulkDownloadBtn.classList.add('hidden');
        }
    }

    updateSelectAllCheckbox() {
        const selectAllCheckbox = document.getElementById('select-all');
        
        if (this.viewMode === 'tree' && this.conversionFolders) {
            // Tree view - check folder selections
            const totalFolders = this.conversionFolders.length;
            const selectedFolders = this.conversionFolders.filter(folder => 
                this.selectedFiles.has(folder.id)
            ).length;

            if (selectedFolders === 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            } else if (selectedFolders === totalFolders) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            }
        } else {
            // List view - check current page file selections
            const currentPageFiles = this.getCurrentPageFiles();
            const selectedInCurrentPage = currentPageFiles.filter(file => 
                this.selectedFiles.has(file.name)
            ).length;

            if (selectedInCurrentPage === 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            } else if (selectedInCurrentPage === currentPageFiles.length) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            }
        }
    }

    getCurrentPageFiles() {
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredFiles.length);
        return this.filteredFiles.slice(startIndex, endIndex);
    }

    async downloadFile(filename) {
        try {
            // Use the correct API endpoint format - remove 'bucket' from path
            const response = await fetch(`/api/download/${this.currentTab}/${filename}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            // Use only the filename part for download, not the full path
            a.download = filename.split('/').pop();
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showSuccess(`Downloaded ${filename.split('/').pop()}`);
        } catch (error) {
            console.error('Error downloading file:', error);
            this.showError(`Failed to download ${filename.split('/').pop()}`);
        }
    }

    async viewFile(filename) {
        try {
            // Open the file in a new browser tab/window for viewing
            const viewUrl = `/api/view/${this.currentTab}/${filename}`;
            const newWindow = window.open(viewUrl, '_blank');
            
            if (!newWindow) {
                // If popup blocked, show message and provide link
                this.showViewerModal(filename, viewUrl);
            } else {
                this.showSuccess(`Opened ${filename} for viewing`);
            }
        } catch (error) {
            console.error('Error viewing file:', error);
            this.showError(`Failed to view ${filename}`);
        }
    }

    showViewerModal(filename, viewUrl) {
        // Create a modal to show the file when popup is blocked
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                <div class="p-6">
                    <div class="flex items-center mb-4">
                        <i class="fas fa-eye text-indigo-600 text-xl mr-3"></i>
                        <h3 class="text-lg font-medium text-gray-900">View File</h3>
                    </div>
                    <p class="text-gray-600 mb-6">
                        Your browser blocked the popup. Click the link below to view <strong>${filename}</strong>:
                    </p>
                    <div class="flex justify-end space-x-3">
                        <button onclick="this.closest('.fixed').remove()" 
                                class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50">
                            Cancel
                        </button>
                        <a href="${viewUrl}" target="_blank" 
                           onclick="this.closest('.fixed').remove()"
                           class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 inline-block">
                            <i class="fas fa-external-link-alt mr-1"></i>
                            View File
                        </a>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (modal.parentNode) {
                modal.remove();
            }
        }, 10000);
    }

    async previewFile(filename) {
        try {
            const response = await fetch(`/api/preview/${this.currentTab}/${filename}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.showPreview(filename, data.content, data.type, data.file_type);
            } else {
                throw new Error(data.error || 'Failed to preview file');
            }
        } catch (error) {
            console.error('Error previewing file:', error);
            this.showError(`Failed to preview ${filename}: ${error.message}`);
        }
    }

    showPreview(filename, content, contentType = 'text', fileType = null) {
        document.getElementById('preview-title').textContent = filename;
        const previewContent = document.getElementById('preview-content');
        
        if (contentType === 'image') {
            // Display image content
            previewContent.innerHTML = `<img src="data:image/${fileType};base64,${content}" alt="${filename}" class="max-w-full h-auto" />`;
        } else if (contentType === 'text') {
            // Format text content based on file type
            const extension = fileType || filename.split('.').pop().toLowerCase();
            if (extension === 'json') {
                try {
                    const parsed = JSON.parse(content);
                    previewContent.innerHTML = `<pre class="language-json"><code>${JSON.stringify(parsed, null, 2)}</code></pre>`;
                } catch {
                    previewContent.innerHTML = `<pre><code>${content}</code></pre>`;
                }
            } else if (extension === 'md') {
                // Simple markdown rendering (you could use a proper markdown parser)
                previewContent.innerHTML = `<div class="prose max-w-none">${content.replace(/\n/g, '<br>')}</div>`;
            } else {
                previewContent.innerHTML = `<pre><code>${content}</code></pre>`;
            }
        } else {
            // Binary or other file types - show as plain text
            previewContent.innerHTML = `<pre><code>${content}</code></pre>`;
        }
        
        document.getElementById('download-preview-btn').onclick = () => this.downloadFile(filename);
        document.getElementById('preview-modal').classList.remove('hidden');
    }

    async convertAgain(filename) {
        if (confirm(`Convert ${filename} again?`)) {
            try {
                const response = await fetch('/api/convert-again', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ filename, bucket: this.currentTab }),
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                this.showSuccess(`Started conversion for ${filename}`);
                
                // Optionally redirect to main converter page
                // window.location.href = '/static/index.html';
                
            } catch (error) {
                console.error('Error converting file:', error);
                this.showError(`Failed to convert ${filename}`);
            }
        }
    }

    async deleteFile(filename) {
        if (confirm(`Are you sure you want to delete ${filename}?`)) {
            try {
                const response = await fetch(`/api/delete/${this.currentTab}/${filename}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                this.showSuccess(`Deleted ${filename}`);
                await this.loadFiles(); // Reload the file list
                
            } catch (error) {
                console.error('Error deleting file:', error);
                this.showError(`Failed to delete ${filename}`);
            }
        }
    }

    showLoading() {
        document.getElementById('loading-state').classList.remove('hidden');
        document.getElementById('empty-state').classList.add('hidden');
        document.getElementById('files-table').classList.add('hidden');
    }

    showEmpty() {
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
        document.getElementById('files-table').classList.add('hidden');
    }

    showTable() {
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('empty-state').classList.add('hidden');
        document.getElementById('files-table').classList.remove('hidden');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'} mr-2"></i>
                ${message}
            </div>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Folder processing methods
    processConversionFolders() {
        // Group files by their conversion folder (document ID)
        const folderGroups = {};
        
        this.files.forEach(file => {
            // Extract document ID from file path if it's a conversion folder structure
            // Expected format: documentId/filename (not documentId/type/filename)
            const pathParts = file.name.split('/');
            
            if (pathParts.length >= 2) {
                const documentId = pathParts[0];
                
                if (!folderGroups[documentId]) {
                    folderGroups[documentId] = {
                        id: documentId,
                        name: this.getDocumentDisplayName(file, documentId),
                        type: 'folder',
                        files: [],
                        isExpanded: this.expandedFolders.has(documentId),
                        originalFile: null,
                        convertedFiles: [],
                        imageFiles: []
                    };
                }
                
                // Categorize files within the folder based on filename
                const fileName = pathParts.slice(1).join('/');
                const fileData = { ...file, displayName: fileName };
                
                // Categorize based on filename patterns
                if (fileName.includes('original') || fileName.endsWith('.pdf')) {
                    folderGroups[documentId].originalFile = fileData;
                    fileData.category = 'original';
                } else if (fileName.includes('converted') || fileName.includes('metadata') || fileName.endsWith('.md') || fileName.endsWith('.json')) {
                    folderGroups[documentId].convertedFiles.push(fileData);
                    fileData.category = 'converted';
                } else if (fileName.includes('image') || fileName.includes('img') || 
                          fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) {
                    folderGroups[documentId].imageFiles.push(fileData);
                    fileData.category = 'images';
                } else {
                    // Default to converted files
                    folderGroups[documentId].convertedFiles.push(fileData);
                    fileData.category = 'converted';
                }
                
                folderGroups[documentId].files.push(fileData);
            }
        });
        
        // Convert to array and set as processed folders
        this.conversionFolders = Object.values(folderGroups);
        this.viewMode = 'tree';
    }

    getDocumentDisplayName(file, documentId) {
        // For the long document ID, extract a meaningful name
        // Example: "HowtodesignbetterUIComponents30-fullebook-25f8a6f6-5616-423f-a980-fb6bce6c247f"
        // Should become: "HowtodesignbetterUIComponents30-fullebook"
        
        if (documentId.includes('-')) {
            // Find the first UUID-looking part (contains 8 characters followed by dashes)
            const parts = documentId.split('-');
            let nameEnd = 0;
            for (let i = 0; i < parts.length; i++) {
                // If we find a part that looks like a UUID segment (all hex and right length)
                if (parts[i].length === 8 && /^[0-9a-f]+$/.test(parts[i])) {
                    nameEnd = i;
                    break;
                }
            }
            
            if (nameEnd > 0) {
                return parts.slice(0, nameEnd).join('-');
            }
        }
        
        // Fallback to truncating if too long
        return documentId.length > 30 ? documentId.substring(0, 30) + '...' : documentId;
    }

    toggleFolder(folderId) {
        console.log('Toggle folder called for:', folderId);
        if (this.expandedFolders.has(folderId)) {
            this.expandedFolders.delete(folderId);
        } else {
            this.expandedFolders.add(folderId);
        }
        
        // Update the folder expansion state
        if (this.conversionFolders) {
            const folder = this.conversionFolders.find(f => f.id === folderId);
            if (folder) {
                folder.isExpanded = this.expandedFolders.has(folderId);
                console.log('Folder state after toggle:', {
                    id: folder.id,
                    isExpanded: folder.isExpanded,
                    filesCount: folder.files.length,
                    convertedFilesCount: folder.convertedFiles.length
                });
            }
        }
        
        this.renderFiles();
    }

    renderTreeView() {
        const tbody = document.getElementById('files-tbody');
        let html = '';
        
        // Filter folders based on search query
        const filteredFolders = this.conversionFolders.filter(folder => {
            if (!this.searchQuery) return true;
            return folder.name.toLowerCase().includes(this.searchQuery) ||
                   folder.files.some(file => file.name.toLowerCase().includes(this.searchQuery));
        });
        
        filteredFolders.forEach(folder => {
            html += this.renderFolderRow(folder);
            
            if (folder.isExpanded) {
                // Render categorized files within the folder
                html += this.renderFolderContents(folder);
            }
        });
        
        tbody.innerHTML = html;
        
        // Update pagination info for tree view
        this.updateTreePagination(filteredFolders.length);
    }

    renderFolderRow(folder) {
        const isSelected = this.selectedFiles.has(folder.id);
        const expandIcon = folder.isExpanded ? 'fa-chevron-down' : 'fa-chevron-right';
        
        return `
            <tr class="folder-row ${isSelected ? 'bg-blue-50' : 'bg-gray-50'} border-l-4 border-l-blue-500">
                <td class="px-6 py-4 whitespace-nowrap">
                    <input type="checkbox" 
                           class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 folder-checkbox" 
                           data-folder-id="${folder.id}"
                           ${isSelected ? 'checked' : ''}
                           onchange="fileManager.toggleFolderSelection('${folder.id}')">
                </td>
                <td class="px-6 py-4">
                    <div class="flex items-center cursor-pointer" onclick="fileManager.toggleFolder('${folder.id}')">
                        <i class="fas ${expandIcon} text-gray-500 mr-2 transition-transform"></i>
                        <i class="fas fa-folder text-yellow-500 mr-3 flex-shrink-0"></i>
                        <div class="min-w-0 flex-1">
                            <div class="text-sm font-semibold text-gray-900 file-name" title="${folder.name}">
                                ${folder.name}
                            </div>
                            <div class="text-xs text-gray-500 mt-1">
                                ${folder.files.length} files • Conversion Folder
                            </div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden-mobile">
                    ${this.getFolderSize(folder)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap hidden-mobile">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Folder
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden-mobile">
                    ${this.getFolderDate(folder)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div class="flex items-center space-x-2">
                        ${this.renderFolderActions(folder)}
                    </div>
                </td>
            </tr>
        `;
    }

    renderFolderContents(folder) {
        let html = '';
        
        // Group files by category for better organization
        const categories = [
            { key: 'originalFile', label: 'Original Document', icon: 'fa-file-upload', files: folder.originalFile ? [folder.originalFile] : [] },
            { key: 'convertedFiles', label: 'Converted Files', icon: 'fa-file-alt', files: folder.convertedFiles },
            { key: 'imageFiles', label: 'Extracted Images', icon: 'fa-image', files: folder.imageFiles }
        ];
        
        categories.forEach(category => {
            if (category.files.length > 0) {
                // Category header
                html += `
                    <tr class="category-header bg-gray-25">
                        <td class="px-6 py-2"></td>
                        <td class="px-6 py-2" colspan="5">
                            <div class="flex items-center pl-8">
                                <i class="fas ${category.icon} text-gray-400 mr-2 text-sm"></i>
                                <span class="text-sm font-medium text-gray-600">${category.label} (${category.files.length})</span>
                            </div>
                        </td>
                    </tr>
                `;
                
                // Files in category
                category.files.forEach(file => {
                    html += this.renderFileRowInFolder(file, folder.id);
                });
            }
        });
        
        return html;
    }

    renderFileRowInFolder(file, folderId) {
        const isSelected = this.selectedFiles.has(file.name);
        const fileIcon = this.getFileIcon(file.type);
        const formattedSize = this.formatFileSize(file.size);
        const formattedDate = this.formatDate(file.lastModified);

        return `
            <tr class="file-in-folder ${isSelected ? 'bg-blue-50' : ''} border-l-4 border-l-gray-200">
                <td class="px-6 py-3 whitespace-nowrap">
                    <input type="checkbox" 
                           class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 file-checkbox" 
                           data-filename="${file.name}"
                           ${isSelected ? 'checked' : ''}
                           onchange="fileManager.toggleFileSelection('${file.name}')">
                </td>
                <td class="px-6 py-3">
                    <div class="flex items-center pl-12">
                        <i class="${fileIcon} text-gray-400 mr-3 flex-shrink-0"></i>
                        <div class="min-w-0 flex-1">
                            <div class="text-sm font-medium text-gray-700 file-name" title="${file.displayName}">
                                ${file.displayName}
                            </div>
                            <div class="block md:hidden text-xs text-gray-500 mt-1">
                                ${formattedSize} • ${file.type} • ${formattedDate}
                            </div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-3 whitespace-nowrap text-sm text-gray-700 hidden-mobile">${formattedSize}</td>
                <td class="px-6 py-3 whitespace-nowrap hidden-mobile">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${this.getTypeColor(file.type)}">
                        ${file.type}
                    </span>
                </td>
                <td class="px-6 py-3 whitespace-nowrap text-sm text-gray-500 hidden-mobile">${formattedDate}</td>
                <td class="px-6 py-3 whitespace-nowrap text-sm font-medium">
                    <div class="flex items-center space-x-2">
                        ${this.renderActionButtons(file)}
                    </div>
                </td>
            </tr>
        `;
    }

    getFolderSize(folder) {
        const totalSize = folder.files.reduce((sum, file) => sum + (file.size || 0), 0);
        return this.formatFileSize(totalSize);
    }

    getFolderDate(folder) {
        const dates = folder.files.map(file => new Date(file.lastModified)).filter(date => !isNaN(date));
        if (dates.length === 0) return '-';
        
        const latestDate = new Date(Math.max(...dates));
        return this.formatDate(latestDate.toISOString());
    }

    renderFolderActions(folder) {
        const buttons = [];
        
        // Expand/Collapse button
        const expandText = folder.isExpanded ? 'Collapse' : 'Expand';
        const expandIcon = folder.isExpanded ? 'fa-compress' : 'fa-expand';
        buttons.push(`
            <button onclick="fileManager.toggleFolder('${folder.id}')" 
                    class="btn-icon text-blue-600 hover:text-blue-800" 
                    title="${expandText}">
                <i class="fas ${expandIcon}"></i>
            </button>
        `);
        
        // Download entire folder button
        buttons.push(`
            <button onclick="fileManager.downloadFolder('${folder.id}')" 
                    class="btn-icon text-green-600 hover:text-green-800" 
                    title="Download Folder">
                <i class="fas fa-download"></i>
            </button>
        `);
        
        // Delete folder button
        buttons.push(`
            <button onclick="fileManager.deleteFolder('${folder.id}')" 
                    class="btn-icon text-red-600 hover:text-red-800" 
                    title="Delete Folder">
                <i class="fas fa-trash"></i>
            </button>
        `);
        
        return buttons.join('');
    }

    toggleFolderSelection(folderId) {
        if (this.selectedFiles.has(folderId)) {
            this.selectedFiles.delete(folderId);
        } else {
            this.selectedFiles.add(folderId);
        }
        
        this.updateBulkActions();
        this.updateSelectAllCheckbox();
    }

    async downloadFolder(folderId) {
        try {
            const folder = this.conversionFolders.find(f => f.id === folderId);
            if (!folder) {
                this.showError('Folder not found');
                return;
            }
            
            // Count total files in all categories
            const totalFiles = (folder.originalFile ? 1 : 0) + 
                             folder.convertedFiles.length + 
                             folder.imageFiles.length;
            
            // Download all files in the folder
            this.showSuccess(`Downloading ${totalFiles} files from ${folder.name}...`);
            
            // Download original file
            if (folder.originalFile) {
                await this.downloadFile(folder.originalFile.name);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // Download converted files
            for (const file of folder.convertedFiles) {
                await this.downloadFile(file.name);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // Download image files
            for (const file of folder.imageFiles) {
                await this.downloadFile(file.name);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            this.showSuccess(`Downloaded all files from ${folder.name}`);
        } catch (error) {
            console.error('Error downloading folder:', error);
            this.showError(`Failed to download folder: ${error.message}`);
        }
    }

    async deleteFolder(folderId) {
        const folder = this.conversionFolders.find(f => f.id === folderId);
        if (!folder) {
            this.showError('Folder not found');
            return;
        }
        
        // Count total files in all categories
        const totalFiles = (folder.originalFile ? 1 : 0) + 
                         folder.convertedFiles.length + 
                         folder.imageFiles.length;
        
        if (confirm(`Are you sure you want to delete the entire conversion folder "${folder.name}" and all ${totalFiles} files?`)) {
            try {
                // Delete original file
                if (folder.originalFile) {
                    await fetch(`/api/delete/${this.currentTab}/${folder.originalFile.name}`, {
                        method: 'DELETE'
                    });
                }
                
                // Delete converted files
                for (const file of folder.convertedFiles) {
                    await fetch(`/api/delete/${this.currentTab}/${file.name}`, {
                        method: 'DELETE'
                    });
                }
                
                // Delete image files  
                for (const file of folder.imageFiles) {
                    await fetch(`/api/delete/${this.currentTab}/${file.name}`, {
                        method: 'DELETE'
                    });
                }
                
                this.showSuccess(`Deleted folder "${folder.name}" and all its files`);
                await this.loadFiles(); // Reload the file list
                
            } catch (error) {
                console.error('Error deleting folder:', error);
                this.showError(`Failed to delete folder: ${error.message}`);
            }
        }
    }

    updateTreePagination(folderCount) {
        // Update info text for tree view - show folder count instead of file count
        document.getElementById('showing-start').textContent = folderCount > 0 ? 1 : 0;
        document.getElementById('showing-end').textContent = folderCount;
        document.getElementById('total-files').textContent = folderCount;

        // For tree view, we show all folders but still keep pagination controls visible
        // in case we implement pagination for folders in the future
        const pagination = document.getElementById('pagination');
        if (pagination) {
            // Show pagination controls but disable them since we show all folders
            pagination.style.display = 'flex';
            document.getElementById('prev-btn').disabled = true;
            document.getElementById('next-btn').disabled = true;
            document.getElementById('prev-mobile').disabled = true;
            document.getElementById('next-mobile').disabled = true;
            
            // Clear page numbers for tree view
            const pageNumbers = document.getElementById('page-numbers');
            if (pageNumbers) {
                pageNumbers.innerHTML = '';
            }
        }
    }

    setViewMode(mode) {
        this.viewMode = mode;
        
        // Update button states if they exist
        const listBtn = document.getElementById('list-view-btn');
        const treeBtn = document.getElementById('tree-view-btn');
        if (listBtn && treeBtn) {
            listBtn.classList.toggle('active', mode === 'list');
            treeBtn.classList.toggle('active', mode === 'tree');
        }
        
        // Re-render with new view mode
        this.filterAndSort();
    }

    getExpandedFileList() {
        const expandedFiles = [];
        
        for (const selectedItem of this.selectedFiles) {
            if (this.viewMode === 'tree' && this.conversionFolders) {
                // Check if selected item is a folder ID
                const folder = this.conversionFolders.find(f => f.id === selectedItem);
                if (folder) {
                    // Add all files from the folder (from all categories)
                    if (folder.originalFile) {
                        expandedFiles.push(folder.originalFile.name);
                    }
                    folder.convertedFiles.forEach(file => {
                        expandedFiles.push(file.name);
                    });
                    folder.imageFiles.forEach(file => {
                        expandedFiles.push(file.name);
                    });
                } else {
                    // It's an individual file
                    expandedFiles.push(selectedItem);
                }
            } else {
                // List view - just add the file
                expandedFiles.push(selectedItem);
            }
        }
        
        return expandedFiles;
    }
}

// Global functions for inline event handlers
let fileManager;

function switchTab(tab) {
    // Update tab styling
    document.querySelectorAll('[id^="tab-"]').forEach(el => {
        el.classList.remove('tab-active');
        el.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    });
    
    document.getElementById(`tab-${tab}`).classList.add('tab-active');
    document.getElementById(`tab-${tab}`).classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    
    // Show/hide view mode toggle based on tab
    const viewModeContainer = document.getElementById('view-mode-container');
    if (viewModeContainer) {
        if (tab === 'outputs') {
            viewModeContainer.classList.remove('hidden');
            // Default to tree view for outputs
            fileManager.setViewMode('tree');
        } else {
            viewModeContainer.classList.add('hidden');
            // Use list view for other tabs
            fileManager.setViewMode('list');
        }
    }
    
    // Switch tab and reload files
    fileManager.currentTab = tab;
    fileManager.selectedFiles.clear();
    fileManager.expandedFolders.clear(); // Reset expanded folders when switching tabs
    fileManager.loadFiles();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all');
    
    if (fileManager.viewMode === 'tree' && fileManager.conversionFolders) {
        // Tree view - select/deselect all folders
        if (selectAllCheckbox.checked) {
            fileManager.conversionFolders.forEach(folder => fileManager.selectedFiles.add(folder.id));
        } else {
            fileManager.conversionFolders.forEach(folder => fileManager.selectedFiles.delete(folder.id));
        }
    } else {
        // List view - select/deselect current page files
        const currentPageFiles = fileManager.getCurrentPageFiles();
        if (selectAllCheckbox.checked) {
            currentPageFiles.forEach(file => fileManager.selectedFiles.add(file.name));
        } else {
            currentPageFiles.forEach(file => fileManager.selectedFiles.delete(file.name));
        }
    }
    
    fileManager.updateBulkActions();
    fileManager.renderFiles(); // Re-render to update checkboxes
}

function refreshFiles() {
    fileManager.loadFiles();
}

async function bulkDelete() {
    const selectedCount = fileManager.selectedFiles.size;
    if (selectedCount === 0) return;
    
    if (confirm(`Are you sure you want to delete ${selectedCount} selected item(s)?`)) {
        try {
            // Expand folder selections to individual files
            const filesToDelete = fileManager.getExpandedFileList();
            
            fileManager.showNotification(`Deleting ${filesToDelete.length} files...`, 'info');
            
            const response = await fetch(`/api/bulk-delete/${fileManager.currentTab}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filenames: filesToDelete }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.deleted_count > 0) {
                fileManager.showSuccess(`Successfully deleted ${result.deleted_count} file(s)`);
            }
            
            if (result.failed_count > 0) {
                fileManager.showError(`Failed to delete ${result.failed_count} file(s)`);
            }
            
            // Clear selections and reload files
            fileManager.selectedFiles.clear();
            await fileManager.loadFiles();
            
        } catch (error) {
            console.error('Error bulk deleting files:', error);
            fileManager.showError('Failed to delete selected files');
        }
    }
}

async function bulkDownload() {
    const selectedCount = fileManager.selectedFiles.size;
    if (selectedCount === 0) return;
    
    try {
        // Expand folder selections to individual files
        const filesToDownload = fileManager.getExpandedFileList();
        
        fileManager.showNotification(`Preparing download for ${filesToDownload.length} file(s)...`, 'info');
        
        // Use the bulk download endpoint to create a zip file
        const response = await fetch(`/api/bulk-download/${fileManager.currentTab}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ filenames: filesToDownload }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        // Get the blob data and create download link
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        
        // Extract filename from response headers or create default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${fileManager.currentTab}_files.zip`;
        if (contentDisposition && contentDisposition.includes('filename=')) {
            filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
        }
        
        // Create and trigger download
        const downloadLink = document.createElement('a');
        downloadLink.href = downloadUrl;
        downloadLink.download = filename;
        downloadLink.style.display = 'none';
        
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        
        // Clean up the blob URL
        window.URL.revokeObjectURL(downloadUrl);
        
        fileManager.showSuccess(`Successfully downloaded ${selectedCount} file(s) as ${filename}`);
        
        // Clear selections after download
        fileManager.selectedFiles.clear();
        fileManager.updateBulkActions();
        fileManager.renderFiles();
        
    } catch (error) {
        console.error('Error bulk downloading files:', error);
        fileManager.showError(`Failed to download selected files: ${error.message}`);
    }
}

function closePreview() {
    document.getElementById('preview-modal').classList.add('hidden');
}

// Initialize the file manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fileManager = new FileManager();
});
