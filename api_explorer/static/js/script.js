// Main script - Initialization and coordination
import { DarkModeManager } from './modules/darkModeManager.js';
import { WebSocketManager } from './modules/webSocketManager.js';
import { ChartManager } from './modules/chartManager.js';
import { APIMethodsManager } from './modules/apiMethodsManager.js';
import { FileBrowserManager } from './modules/fileBrowserManager.js';
import { EventDisplayManager } from './modules/eventDisplayManager.js';

class APIExplorer {
    constructor() {
        this.darkModeManager = new DarkModeManager();
        this.webSocketManager = new WebSocketManager();
        this.chartManager = new ChartManager();
        this.apiMethodsManager = new APIMethodsManager();
        this.fileBrowserManager = new FileBrowserManager();
        this.eventDisplayManager = new EventDisplayManager();

        this.init();
    }

    init() {
        // Initialize all managers
        this.darkModeManager.init();
        this.fileBrowserManager.init();

        // Set up inter-manager communication
        this.setupManagerCommunication();

        // Initialize module-specific functionality
        this.initializeModules();
    }

    setupManagerCommunication() {
        // Connect chart manager to dark mode changes
        this.darkModeManager.onModeChange((isDark) => {
            this.chartManager.updateTheme(isDark);
        });

        // Connect WebSocket to chart updates
        this.webSocketManager.onDataReceived((moduleId, data) => {
            this.chartManager.updateData(moduleId, data);
            this.eventDisplayManager.addEvent(moduleId, data);
        });

        // Connect chart manager to event display
        this.eventDisplayManager.onGraphToggle((moduleId, showGraph) => {
            this.chartManager.toggleGraph(moduleId, showGraph);
        });

        this.eventDisplayManager.onSeparateChannelsToggle((moduleId, separate) => {
            this.chartManager.toggleSeparateChannels(moduleId, separate);
        });
    }

    initializeModules() {
        // Find all modules and initialize their functionality
        document.querySelectorAll('[id$="-show-graph"]').forEach(toggle => {
            const moduleId = toggle.id.replace('-show-graph', '');

            // Initialize chart management for this module
            this.chartManager.initializeModule(moduleId);
            this.eventDisplayManager.initializeModule(moduleId);

            console.log(`Initialized module: ${moduleId}`);
        });
    }
}

// Global functions for backwards compatibility
window.toggleMethod = (moduleId, methodId) => {
    if (APIExplorer.instance && APIExplorer.instance.apiMethodsManager) {
        APIExplorer.instance.apiMethodsManager.toggleMethod(moduleId, methodId);
    }
};

window.executeMethod = (moduleId, methodId) => {
    if (APIExplorer.instance && APIExplorer.instance.apiMethodsManager) {
        APIExplorer.instance.apiMethodsManager.executeMethod(moduleId, methodId);
    }
};

// Add test functions for debugging
window.testAPIManager = () => {
    if (APIExplorer.instance && APIExplorer.instance.apiMethodsManager) {
        return APIExplorer.instance.apiMethodsManager.testButtonFunctionality();
    }
    return { error: 'API Manager not available' };
};

window.getAPIManager = () => {
    return APIExplorer.instance ? APIExplorer.instance.apiMethodsManager : null;
};

window.connectWebSocket = (moduleId) => {
    APIExplorer.instance.webSocketManager.connect(moduleId);
};

window.disconnectWebSocket = (moduleId) => {
    APIExplorer.instance.webSocketManager.disconnect(moduleId);
};

window.clearEvents = (moduleId) => {
    APIExplorer.instance.eventDisplayManager.clearEvents(moduleId);
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing API Explorer...');
    APIExplorer.instance = new APIExplorer();
    
    // Ensure API methods manager is accessible globally for debugging
    window.apiMethodsManager = APIExplorer.instance.apiMethodsManager;
    
    console.log('API Explorer initialized');
    console.log('API Methods Manager:', window.apiMethodsManager);
    
    // Wait a bit and test functionality
    setTimeout(() => {
        console.log('Running delayed test...');
        if (window.apiMethodsManager && window.apiMethodsManager.testButtonFunctionality) {
            const result = window.apiMethodsManager.testButtonFunctionality();
            console.log('Test result:', result);
        }
    }, 1000);
});
