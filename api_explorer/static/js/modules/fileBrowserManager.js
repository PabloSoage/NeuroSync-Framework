export class FileBrowserManager {
    constructor() {
        this.modal = null;
        this.currentPath = '';
        this.currentTargetId = '';
        this.currentDefaultExt = '';
    }
    
    init() {
        if (document.getElementById('fileBrowserModal')) {
            this.modal = new bootstrap.Modal(document.getElementById('fileBrowserModal'));
            this.setupEventListeners();
        }
    }
    
    setupEventListeners() {
        document.getElementById('fileBrowserGo')?.addEventListener('click', () => {
            const path = document.getElementById('fileBrowserPath').value;
            this.openDialog(path);
        });
        
        document.getElementById('fileBrowserSelect')?.addEventListener('click', () => {
            this.selectFile();
        });
        
        document.querySelectorAll('.file-dialog-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dataset = e.currentTarget.dataset;
                this.currentTargetId = dataset.target;
                this.currentDefaultExt = dataset.defaultExtension || '';
                this.openDialog();
            });
        });
    }
    
    async openDialog(overridePath) {
        const listEl = document.getElementById('file-list');
        const pathInput = document.getElementById('fileBrowserPath');
        const labelEl = document.getElementById('fileBrowserLabel');
        
        const basePath = overridePath !== undefined
            ? overridePath.replace(/\\/g, '/')
            : (document.getElementById(this.currentTargetId).value.replace(/\\/g, '/')
               || window.baseBrowsePath);
        
        this.currentPath = basePath.endsWith('/') ? basePath : basePath + '/';
        pathInput.value = basePath;
        labelEl.textContent = `Select Directory: ${basePath}`;
        
        listEl.innerHTML = '<li class="list-group-item">Loading...</li>';
        this.modal.show();
        
        try {
            const response = await fetch(`/api/files?path=${encodeURIComponent(basePath)}`);
            const data = await response.json();
            
            if (!response.ok || !Array.isArray(data.items)) {
                listEl.innerHTML = `<li class="list-group-item">Error: ${data.error || 'Invalid response'}</li>`;
                return;
            }
            
            this.populateFileList(data.items);
            
        } catch (error) {
            listEl.innerHTML = `<li class="list-group-item">Error: ${error.message}</li>`;
        }
    }
    
    populateFileList(items) {
        const listEl = document.getElementById('file-list');
        listEl.innerHTML = '';
        
        if (items.length === 0) {
            listEl.innerHTML = '<li class="list-group-item">No items found</li>';
            return;
        }
        
        items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action';
            li.textContent = item.name;
            li.onclick = () => this.openDialog(item.path);
            listEl.appendChild(li);
        });
    }
    
    selectFile() {
        if (this.currentTargetId) {
            let dir = this.currentPath;
            const prefix = document.getElementById('fileBrowserPrefix').value.trim();
            
            let fullPath = dir.endsWith('/') ? dir : dir + '/';
            if (prefix) fullPath += prefix;
            
            if (this.currentDefaultExt && !fullPath.toLowerCase().endsWith(this.currentDefaultExt.toLowerCase())) {
                fullPath += this.currentDefaultExt;
            }
            
            document.getElementById(this.currentTargetId).value = fullPath;
        }
        this.modal.hide();
    }
}
