export class DarkModeManager {
    constructor() {
        this.callbacks = [];
    }
    
    init() {
        const darkModeToggle = document.getElementById('darkModeToggle');
        
        // Check for saved preference or default to dark mode
        const isDarkMode = localStorage.getItem('darkMode') !== 'light';
        
        // Set initial state
        this.setDarkMode(isDarkMode);
        darkModeToggle.checked = isDarkMode;
        
        // Add event listener
        darkModeToggle.addEventListener('change', (e) => {
            const isDark = e.target.checked;
            this.setDarkMode(isDark);
            localStorage.setItem('darkMode', isDark ? 'dark' : 'light');
        });
    }
    
    setDarkMode(isDark) {
        document.body.classList.toggle('dark-mode', isDark);
        this.updateChartDefaults(isDark);
        this.notifyCallbacks(isDark);
    }
    
    updateChartDefaults(isDarkMode) {
        if (typeof Chart !== 'undefined') {
            Chart.defaults.color = isDarkMode ? '#f0f0f0' : '#666';
            Chart.defaults.scale.grid.color = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        }
    }
    
    onModeChange(callback) {
        this.callbacks.push(callback);
    }
    
    notifyCallbacks(isDark) {
        this.callbacks.forEach(callback => callback(isDark));
    }
    
    isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }
}
