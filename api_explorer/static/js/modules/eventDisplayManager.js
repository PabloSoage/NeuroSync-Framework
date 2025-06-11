export class EventDisplayManager {
    constructor() {
        this.graphToggleCallbacks = [];
        this.separateChannelsCallbacks = [];
    }
    
    initializeModule(moduleId) {
        // Initialize event listeners for this module
        const showGraphToggle = document.getElementById(`${moduleId}-show-graph`);
        const separateChannelsToggle = document.getElementById(`${moduleId}-separate-channels`);
        
        if (showGraphToggle) {
            showGraphToggle.addEventListener('change', (e) => {
                this.notifyGraphToggle(moduleId, e.target.checked);
            });
        }
        
        if (separateChannelsToggle) {
            separateChannelsToggle.addEventListener('change', (e) => {
                this.notifySeparateChannelsToggle(moduleId, e.target.checked);
            });
        }
    }
    
    addEvent(moduleId, data, type = 'info') {
        // Handle both string messages and data objects
        if (typeof data === 'string') {
            this.addSystemEvent(moduleId, data, type);
        } else {
            this.addDataEvent(moduleId, data);
        }
    }
    
    addSystemEvent(moduleId, message, type) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);
        if (!eventsContainer) return;
        
        const eventElement = document.createElement('div');
        eventElement.className = `event event-${type}`;
        eventElement.textContent = message;
        eventsContainer.appendChild(eventElement);
        
        this.autoScroll(moduleId);
    }
    
    addDataEvent(moduleId, data) {
        // This would integrate with the event buffer system
        // For now, update the table if it exists
        this.updateDataTable(moduleId, data);
    }
    
    updateDataTable(moduleId, data) {
        if (!data.visualization_data?.list_view) return;
        
        // Throttle table updates
        if (!this.updateDataTable.lastUpdate) this.updateDataTable.lastUpdate = {};
        const now = Date.now();
        
        if (now - (this.updateDataTable.lastUpdate[moduleId] || 0) < 100) {
            return;
        }
        this.updateDataTable.lastUpdate[moduleId] = now;
        
        const tableBody = document.querySelector(`#${moduleId}-data-table tbody`);
        if (tableBody) {
            tableBody.innerHTML = '';
            
            data.visualization_data.list_view.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.channel}</td>
                    <td>${item.type}</td>
                    <td>${item.value.toFixed(2)}</td>
                `;
                tableBody.appendChild(tr);
            });
        }
    }
    
    clearEvents(moduleId) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);
        if (eventsContainer) {
            eventsContainer.innerHTML = '';
        }
    }
    
    autoScroll(moduleId) {
        const autoScrollCheckbox = document.getElementById(`${moduleId}-auto-scroll`);
        if (autoScrollCheckbox?.checked) {
            const eventsContainer = document.getElementById(`${moduleId}-events-container`);
            if (eventsContainer) {
                eventsContainer.scrollTop = eventsContainer.scrollHeight;
            }
        }
    }
    
    onGraphToggle(callback) {
        this.graphToggleCallbacks.push(callback);
    }
    
    onSeparateChannelsToggle(callback) {
        this.separateChannelsCallbacks.push(callback);
    }
    
    notifyGraphToggle(moduleId, showGraph) {
        this.graphToggleCallbacks.forEach(callback => callback(moduleId, showGraph));
    }
    
    notifySeparateChannelsToggle(moduleId, separate) {
        this.separateChannelsCallbacks.forEach(callback => callback(moduleId, separate));
    }
}
