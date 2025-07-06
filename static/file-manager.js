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
        if (this.filteredFiles.length === 0) {
            this.showEmpty();
            return;
        }

        this.showTable();
        
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
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <i class="${fileIcon} text-gray-400 mr-3"></i>
                        <div>
                            <div class="text-sm font-medium text-gray-900">${file.name}</div>
                            ${file.originalName ? `<div class="text-sm text-gray-500">Original: ${file.originalName}</div>` : ''}
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formattedSize}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${this.getTypeColor(file.type)}">
                        ${file.type}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formattedDate}</td>
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
        
        // Download button
        buttons.push(`
            <button onclick="fileManager.downloadFile('${file.name}')" 
                    class="btn-icon text-blue-600 hover:text-blue-800" 
                    title="Download">
                <i class="fas fa-download"></i>
            </button>
        `);

        // Preview button (for text/markdown files)
        if (this.isPreviewable(file.type)) {
            buttons.push(`
                <button onclick="fileManager.previewFile('${file.name}')" 
                        class="btn-icon text-green-600 hover:text-green-800" 
                        title="Preview">
                    <i class="fas fa-eye"></i>
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
        return ['txt', 'md', 'json', 'csv'].includes(type.toLowerCase());
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
        if (this.selectedFiles.size > 0) {
            bulkDeleteBtn.classList.remove('hidden');
        } else {
            bulkDeleteBtn.classList.add('hidden');
        }
    }

    updateSelectAllCheckbox() {
        const selectAllCheckbox = document.getElementById('select-all');
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

    getCurrentPageFiles() {
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredFiles.length);
        return this.filteredFiles.slice(startIndex, endIndex);
    }

    async downloadFile(filename) {
        try {
            const response = await fetch(`/api/download/${this.currentTab}/${filename}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showSuccess(`Downloaded ${filename}`);
        } catch (error) {
            console.error('Error downloading file:', error);
            this.showError(`Failed to download ${filename}`);
        }
    }

    async previewFile(filename) {
        try {
            const response = await fetch(`/api/preview/${this.currentTab}/${filename}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const content = await response.text();
            this.showPreview(filename, content);
        } catch (error) {
            console.error('Error previewing file:', error);
            this.showError(`Failed to preview ${filename}`);
        }
    }

    showPreview(filename, content) {
        document.getElementById('preview-title').textContent = filename;
        const previewContent = document.getElementById('preview-content');
        
        // Format content based on file type
        const extension = filename.split('.').pop().toLowerCase();
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
    
    // Switch tab and reload files
    fileManager.currentTab = tab;
    fileManager.selectedFiles.clear();
    fileManager.loadFiles();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all');
    const currentPageFiles = fileManager.getCurrentPageFiles();
    
    if (selectAllCheckbox.checked) {
        currentPageFiles.forEach(file => fileManager.selectedFiles.add(file.name));
    } else {
        currentPageFiles.forEach(file => fileManager.selectedFiles.delete(file.name));
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
    
    if (confirm(`Are you sure you want to delete ${selectedCount} selected file(s)?`)) {
        try {
            const filenames = Array.from(fileManager.selectedFiles);
            
            fileManager.showNotification(`Deleting ${selectedCount} files...`, 'info');
            
            const response = await fetch(`/api/bulk-delete/${fileManager.currentTab}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filenames: filenames }),
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

function closePreview() {
    document.getElementById('preview-modal').classList.add('hidden');
}

// Initialize the file manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    fileManager = new FileManager();
});
