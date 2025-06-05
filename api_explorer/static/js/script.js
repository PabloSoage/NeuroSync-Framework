// JavaScript for API Explorer functionality
const webSockets = {};
const moduleCharts = {}; // Store chart objects by module
const channelData = {}; // Store historical data by module and channel
const activeTypeFilters = {}; // Store active type filters by module

let currentBrowseDefaultExt;

// Dark Mode Toggle Functionality
function initDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');

    // Check for saved preference or default to dark mode if no preference saved
    const isDarkMode = localStorage.getItem('darkMode') !== 'light';

    // Set initial state
    document.body.classList.toggle('dark-mode', isDarkMode);
    darkModeToggle.checked = isDarkMode;

    // Update charts if they exist
    updateChartsForDarkMode(isDarkMode);

    // Add event listener for toggle changes
    darkModeToggle.addEventListener('change', function() {
        const isDark = this.checked;
        document.body.classList.toggle('dark-mode', isDark);
        localStorage.setItem('darkMode', isDark ? 'dark' : 'light');

        // Update charts for the new mode
        updateChartsForDarkMode(isDark);
    });
}

// Update chart themes based on dark mode
function updateChartsForDarkMode(isDarkMode) {
    // Set Chart.js defaults based on mode
    Chart.defaults.color = isDarkMode ? '#f0f0f0' : '#666';
    Chart.defaults.scale.grid.color = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    // Set the background color for charts
    const backgroundColor = isDarkMode ? '#2d2d2d' : '#ffffff';

    // Update existing module charts
    Object.keys(moduleCharts).forEach(moduleId => {
        if (moduleCharts[moduleId]) {
            // Update chart background color
            moduleCharts[moduleId].options.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
            moduleCharts[moduleId].options.plugins.tooltip.titleColor = isDarkMode ? '#fff' : '#000';
            moduleCharts[moduleId].options.plugins.tooltip.bodyColor = isDarkMode ? '#fff' : '#000';

            // Force color refresh on scales
            if (moduleCharts[moduleId].options.scales.y) {
                moduleCharts[moduleId].options.scales.y.ticks = {
                    color: isDarkMode ? '#f0f0f0' : '#666'
                };
                moduleCharts[moduleId].options.scales.y.title.color = isDarkMode ? '#f0f0f0' : '#666';
            }

            if (moduleCharts[moduleId].options.scales.x) {
                moduleCharts[moduleId].options.scales.x.ticks = {
                    color: isDarkMode ? '#f0f0f0' : '#666'
                };
            }

            // Force full update to refresh colors
            moduleCharts[moduleId].update('none');
        }
    });

    // Update individual channel charts
    if (window.channelCharts) {
        Object.keys(window.channelCharts).forEach(moduleId => {
            Object.keys(window.channelCharts[moduleId] || {}).forEach(channelId => {
                if (window.channelCharts[moduleId][channelId]) {
                    // Update chart background color
                    window.channelCharts[moduleId][channelId].options.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
                    window.channelCharts[moduleId][channelId].options.plugins.tooltip.titleColor = isDarkMode ? '#fff' : '#000';
                    window.channelCharts[moduleId][channelId].options.plugins.tooltip.bodyColor = isDarkMode ? '#fff' : '#000';

                    // Force color refresh on scales
                    if (window.channelCharts[moduleId][channelId].options.scales.y) {
                        window.channelCharts[moduleId][channelId].options.scales.y.ticks = {
                            color: isDarkMode ? '#f0f0f0' : '#666'
                        };
                    }

                    if (window.channelCharts[moduleId][channelId].options.scales.x) {
                        window.channelCharts[moduleId][channelId].options.scales.x.ticks = {
                            color: isDarkMode ? '#f0f0f0' : '#666'
                        };
                    }

                    // Force full update to refresh colors
                    window.channelCharts[moduleId][channelId].update('none');
                }
            });
        });
    }

    // For modules that have graph view enabled, force a full refresh
    document.querySelectorAll('[id$="-show-graph"]').forEach(toggle => {
        if (toggle.checked) {
            const moduleId = toggle.id.replace('-show-graph', '');
            // Force a full rebuild of the charts to apply new theme
            clearAllCharts(moduleId);
            initOrUpdateGraph(moduleId);
        }
    });
}

// Toggle method details
function toggleMethod(moduleId, methodId) {
    const methodBody = document.getElementById(`${moduleId}-${methodId}`);
    methodBody.classList.toggle('active');
}

// Execute API method
async function executeMethod(moduleId, methodId) {
    const responseElem = document.getElementById(`${moduleId}-${methodId}_response`);
    responseElem.textContent = "Loading...";

    try {
        // Get parameters from form elements
        const paramElements = document.querySelectorAll(`[id^="${moduleId}-${methodId}_param_"]`);
        let url = `/api/${moduleId}/${methodId}`;
        let options = { method: 'GET' };
        let body = null;
        let queryParams = [];

        // Check if this is a POST method
        const methodType = document.getElementById(`${moduleId}-${methodId}_type`);
        if (methodType && methodType.value === 'POST') {
            options.method = 'POST';
            body = {};
        }

        // Process parameters
        paramElements.forEach(param => {
            const paramName = param.id.replace(`${moduleId}-${methodId}_param_`, '');
            const paramValue = param.value.trim();

            if (paramValue) {
                if (options.method === 'GET') {
                    queryParams.push(`${paramName}=${encodeURIComponent(paramValue)}`);
                } else {
                    // For POST, add to body
                    body[paramName] = paramValue;
                }
            }
        });

        // Add query parameters to URL for GET requests
        if (queryParams.length > 0 && options.method === 'GET') {
            url += `?${queryParams.join('&')}`;
        }

        // Set up headers and body for POST requests
        if (options.method === 'POST' && body) {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(body);
        }

        // Make API request
        const response = await fetch(url, options);
        const data = await response.json();

        // Update response element
        responseElem.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        responseElem.textContent = `Error: ${error.message}`;
    }
}

// WebSocket connection for real-time events
function connectWebSocket(moduleId) {
    if (webSockets[moduleId]) {
        return; // Already connected
    }

    const connectBtn = document.getElementById(`${moduleId}-connect-ws-btn`);
    const disconnectBtn = document.getElementById(`${moduleId}-disconnect-ws-btn`);
    const eventsContainer = document.getElementById(`${moduleId}-events-container`);
    const statusIndicator = document.getElementById(`${moduleId}-connection-status`);

    // Clear previous events
    eventsContainer.innerHTML = '';

    // Create WebSocket connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    webSockets[moduleId] = new WebSocket(`${wsProtocol}//${window.location.host}/ws/${moduleId}`);

    // Event counter
    let eventCount = 0;
    const eventCountEl = document.getElementById(`${moduleId}-event-count`);

    // Update UI to show connecting state
    if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
    addEvent(moduleId, 'Connecting to WebSocket...', 'system');

    webSockets[moduleId].onopen = function(e) {
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        if (statusIndicator) statusIndicator.className = 'connection-status connected';
        addEvent(moduleId, 'WebSocket connection established', 'system');

        // Ping the server every 30 seconds to keep the connection alive
        webSockets[moduleId].pingInterval = setInterval(() => {
            if (webSockets[moduleId] && webSockets[moduleId].readyState === WebSocket.OPEN) {
                webSockets[moduleId].send(JSON.stringify({ command: 'ping' }));
            }
        }, 30000);
    };

    webSockets[moduleId].onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            // Skip system messages like pong responses
            if (data.response === 'pong') return;

            // Update event counter
            eventCount++;
            if (eventCountEl) eventCountEl.textContent = `Events: ${eventCount}`;

            // Update the channel data and graph if visualization data exists
            if (data.visualization_data && data.visualization_data.list_view) {
                // Update channel data for the graph
                updateChannelData(moduleId, data);

                // Update the table if it exists
                const tableBody = document.querySelector(`#${moduleId}-data-table tbody`);
                if (tableBody) {
                    // Clear existing rows
                    tableBody.innerHTML = '';

                    // Add new rows from list_view data
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

            // Determine event type for styling
            let eventClass = 'event';
            let eventType = data.event_type || 'unknown';

            if (eventType.includes('key')) {
                eventClass += ' event-key';
            } else if (eventType.includes('mouse')) {
                eventClass += ' event-mouse';
            } else if (eventType.includes('button') || eventType.includes('click')) {
                eventClass += ' event-button';
            } else if (eventType.includes('controller') || eventType.includes('axis')) {
                eventClass += ' event-controller';
            } else {
                eventClass += ' event-system';
            }

            // Format event data for display
            const formattedData = JSON.stringify(data, null, 2);

            // Format timestamp
            let timeStr = '';
            if (data.timestamp) {
                const date = new Date(data.timestamp * 1000);
                timeStr = `<span class="event-time">${date.toLocaleTimeString()}.${date.getMilliseconds().toString().padStart(3, '0')}</span>`;
            }

            // Create and append event element
            const eventElement = document.createElement('div');
            eventElement.className = eventClass;
            eventElement.innerHTML = `${timeStr}<pre>${formattedData}</pre>`;
            eventsContainer.appendChild(eventElement);

            // Auto-scroll if enabled
            if (document.getElementById(`${moduleId}-auto-scroll`).checked) {
                eventsContainer.scrollTop = eventsContainer.scrollHeight;
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e, event.data);
            addEvent(moduleId, `Error parsing message: ${e.message}`, 'system');
        }
    };

    webSockets[moduleId].onclose = function(event) {
        if (webSockets[moduleId].pingInterval) {
            clearInterval(webSockets[moduleId].pingInterval);
        }

        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';

        if (event.wasClean) {
            addEvent(moduleId, `WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`, 'system');
        } else {
            addEvent(moduleId, 'WebSocket connection died', 'system');
        }

        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        webSockets[moduleId] = null;
    };

    webSockets[moduleId].onerror = function(error) {
        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
        addEvent(moduleId, `WebSocket error: ${error.message || 'Unknown error'}`, 'system');
    };
}

function disconnectWebSocket(moduleId) {
    if (webSockets[moduleId]) {
        webSockets[moduleId].close();
        if (webSockets[moduleId].pingInterval) {
            clearInterval(webSockets[moduleId].pingInterval);
        }
        webSockets[moduleId] = null;

        document.getElementById(`${moduleId}-connect-ws-btn`).disabled = false;
        document.getElementById(`${moduleId}-disconnect-ws-btn`).disabled = true;

        const statusIndicator = document.getElementById(`${moduleId}-connection-status`);
        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
    }
}

function clearEvents(moduleId) {
    document.getElementById(`${moduleId}-events-container`).innerHTML = '';
}

function addEvent(moduleId, message, type = 'info') {
    const eventsContainer = document.getElementById(`${moduleId}-events-container`);
    const eventElement = document.createElement('div');
    eventElement.className = `event event-${type}`;
    eventElement.textContent = message;
    eventsContainer.appendChild(eventElement);

    // Auto-scroll if enabled
    if (document.getElementById(`${moduleId}-auto-scroll`).checked) {
        eventsContainer.scrollTop = eventsContainer.scrollHeight;
    }
}

// Initialize or update the graph for a module
function initOrUpdateGraph(moduleId) {
    // Initialize data structures if needed
    initModuleDataStructures(moduleId);

    // Check if we're in separate channels mode
    const separateChannels = window.separateChannels[moduleId];

    // Get all available types from data
    const types = new Set();
    Object.values(channelData[moduleId]).forEach(channelInfo => {
        types.add(channelInfo.type);
    });

    // Convert to array for easier handling
    const typeArray = Array.from(types);

    // If no active type filter is set, default to eeg or first available type
    if (!activeTypeFilters[moduleId] && typeArray.length > 0) {
        // Default to 'eeg' if available, otherwise take the first type
        activeTypeFilters[moduleId] = typeArray.includes('eeg') ? 'eeg' : typeArray[0];
        console.log(`Setting default active type to: ${activeTypeFilters[moduleId]}`);
    }

    // Current active type
    const activeType = activeTypeFilters[moduleId];
    console.log(`Current active type: ${activeType}`);

    // Update type filters UI
    updateTypeFilters(moduleId, typeArray, activeType);

    // Get the graph container and check if we have data
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const channelsOfActiveType = Object.values(channelData[moduleId])
        .filter(info => info.type === activeType);

    if (channelsOfActiveType.length === 0) {
        if (graphContainer) {
            graphContainer.innerHTML = `<div class="alert alert-info mt-3">No data available for type: ${activeType || ''}. Select a different type.</div>`;
        }
        return;
    }

    // Clear any previous "no data" message
    if (graphContainer) {
        graphContainer.innerHTML = '';
    }

    if (separateChannels) {
        // Create a grid for separate channel graphs
        const gridContainer = document.createElement('div');
        gridContainer.className = 'channel-graphs-grid';
        graphContainer.appendChild(gridContainer);

        // Create a separate graph for each channel
        createSeparateChannelGraphs(moduleId, gridContainer, activeType);
    } else {
        // Create a single canvas for combined graph
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-graph-canvas`;
        graphContainer.appendChild(canvas);

        // Create the combined graph
        createCombinedGraph(moduleId, canvas, activeType);
    }
}

// Create separate graphs for each channel
function createSeparateChannelGraphs(moduleId, container, activeType) {
    const colors = {
        eeg: 'rgba(75, 108, 183, 1)',
        emg: 'rgba(92, 184, 92, 1)',
        ecg: 'rgba(217, 83, 79, 1)',
        accel: 'rgba(240, 173, 78, 1)',
        gyro: 'rgba(91, 192, 222, 1)',
        eda: 'rgba(142, 68, 173, 1)',
        ppg: 'rgba(232, 62, 140, 1)',
        temperature: 'rgba(253, 126, 20, 1)'
    };

    // Find all channels of the active type
    const channelsOfType = Object.entries(channelData[moduleId])
        .filter(([_, info]) => info.type === activeType)
        .map(([channel, _]) => channel);

    console.log(`Found ${channelsOfType.length} channels of type ${activeType}`);

    // Dynamically adjust number of columns based on number of channels
    // Cap at 3 columns maximum to prevent horizontal overflow
    let columns = 2; // Default to 2 columns

    if (channelsOfType.length > 6) {
        // Use 3 columns for many channels (7+)
        columns = 3;
    } else if (channelsOfType.length > 3) {
        // Use 3 columns for medium channel count (4-6)
        columns = 3;
    }

    container.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;

    // Calculate rows needed
    const rows = Math.ceil(channelsOfType.length / columns);

    // Calculate and set dynamic container height based on number of rows
    // Each row is 200px (chart) + 10px (gap) = 210px per row
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const calculatedHeight = (rows * 210) + 20; // Add 20px for container padding
    graphContainer.style.height = `${calculatedHeight}px`;

    console.log(`Adjusting grid to ${columns} columns and ${rows} rows with height ${calculatedHeight}px`);

    // Create a separate graph for each channel
    channelsOfType.forEach(channel => {
        // Create container for this channel
        const channelContainer = document.createElement('div');
        channelContainer.className = 'channel-graph-container';
        channelContainer.id = `${moduleId}-${channel}-container`;
        container.appendChild(channelContainer);

        // Create canvas for this channel
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-${channel}-canvas`;
        channelContainer.appendChild(canvas);

        // Get channel data
        const channelInfo = channelData[moduleId][channel];
        const values = channelInfo.values.slice(-100);

        // Find min/max for y-axis
        let minValue = Math.min(...values);
        let maxValue = Math.max(...values);

        // Add padding to the min/max values (20% padding)
        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.2;
        minValue = minValue - padding;
        maxValue = maxValue + padding;

        // Create the chart for this channel
        window.channelCharts[moduleId][channel] = new Chart(canvas, {
            type: 'line',
            data: {
                labels: Array(100).fill(''),
                datasets: [{
                    label: channel,
                    data: values,
                    borderColor: colors[activeType] || 'rgba(0, 0, 0, 1)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    hidden: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        min: minValue,
                        max: maxValue,
                        title: {
                            display: false
                        },
                        grid: {
                            color: 'rgba(200, 200, 200, 0.2)'
                        }
                    },
                    x: {
                        display: false,
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            boxWidth: 10,
                            font: {
                                size: 10
                            }
                        }
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    });
}

// Clear all charts for a module
function clearAllCharts(moduleId) {
    // Destroy main chart if it exists
    if (moduleCharts[moduleId]) {
        moduleCharts[moduleId].destroy();
        moduleCharts[moduleId] = null;
    }

    // Destroy all individual channel charts
    if (window.channelCharts[moduleId]) {
        Object.values(window.channelCharts[moduleId]).forEach(chart => {
            if (chart) chart.destroy();
        });
        window.channelCharts[moduleId] = {};
    }

    // Clear the graph container
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    if (graphContainer) {
        graphContainer.innerHTML = '';
        graphContainer.style.height = 'auto'; // Reset height when clearing
    }
}

// Initialize or update the graph for a module
function initOrUpdateGraph(moduleId) {
    // Initialize data structures if needed
    initModuleDataStructures(moduleId);

    // Check if we're in separate channels mode
    const separateChannels = window.separateChannels[moduleId];

    // Get all available types from data
    const types = new Set();
    Object.values(channelData[moduleId]).forEach(channelInfo => {
        types.add(channelInfo.type);
    });

    // Convert to array for easier handling
    const typeArray = Array.from(types);

    // If no active type filter is set, default to eeg or first available type
    if (!activeTypeFilters[moduleId] && typeArray.length > 0) {
        // Default to 'eeg' if available, otherwise take the first type
        activeTypeFilters[moduleId] = typeArray.includes('eeg') ? 'eeg' : typeArray[0];
        console.log(`Setting default active type to: ${activeTypeFilters[moduleId]}`);
    }

    // Current active type
    const activeType = activeTypeFilters[moduleId];
    console.log(`Current active type: ${activeType}`);

    // Update type filters UI
    updateTypeFilters(moduleId, typeArray, activeType);

    // Get the graph container and check if we have data
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const channelsOfActiveType = Object.values(channelData[moduleId])
        .filter(info => info.type === activeType);

    if (channelsOfActiveType.length === 0) {
        if (graphContainer) {
            graphContainer.innerHTML = `<div class="alert alert-info mt-3">No data available for type: ${activeType || ''}. Select a different type.</div>`;
        }
        return;
    }

    // Clear any previous "no data" message
    if (graphContainer) {
        graphContainer.innerHTML = '';
    }

    if (separateChannels) {
        // Create a grid for separate channel graphs
        const gridContainer = document.createElement('div');
        gridContainer.className = 'channel-graphs-grid';
        graphContainer.appendChild(gridContainer);

        // Create a separate graph for each channel
        createSeparateChannelGraphs(moduleId, gridContainer, activeType);
    } else {
        // Create a single canvas for combined graph
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-graph-canvas`;
        graphContainer.appendChild(canvas);

        // Create the combined graph
        createCombinedGraph(moduleId, canvas, activeType);
    }
}

// Create separate graphs for each channel
function createSeparateChannelGraphs(moduleId, container, activeType) {
    const colors = {
        eeg: 'rgba(75, 108, 183, 1)',
        emg: 'rgba(92, 184, 92, 1)',
        ecg: 'rgba(217, 83, 79, 1)',
        accel: 'rgba(240, 173, 78, 1)',
        gyro: 'rgba(91, 192, 222, 1)',
        eda: 'rgba(142, 68, 173, 1)',
        ppg: 'rgba(232, 62, 140, 1)',
        temperature: 'rgba(253, 126, 20, 1)'
    };

    // Find all channels of the active type
    const channelsOfType = Object.entries(channelData[moduleId])
        .filter(([_, info]) => info.type === activeType)
        .map(([channel, _]) => channel);

    console.log(`Found ${channelsOfType.length} channels of type ${activeType}`);

    // Dynamically adjust number of columns based on number of channels
    // Cap at 3 columns maximum to prevent horizontal overflow
    let columns = 2; // Default to 2 columns

    if (channelsOfType.length > 6) {
        // Use 3 columns for many channels (7+)
        columns = 3;
    } else if (channelsOfType.length > 3) {
        // Use 3 columns for medium channel count (4-6)
        columns = 3;
    }

    container.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;

    // Calculate rows needed
    const rows = Math.ceil(channelsOfType.length / columns);

    // Calculate and set dynamic container height based on number of rows
    // Each row is 200px (chart) + 10px (gap) = 210px per row
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const calculatedHeight = (rows * 210) + 20; // Add 20px for container padding
    graphContainer.style.height = `${calculatedHeight}px`;

    console.log(`Adjusting grid to ${columns} columns and ${rows} rows with height ${calculatedHeight}px`);

    // Create a separate graph for each channel
    channelsOfType.forEach(channel => {
        // Create container for this channel
        const channelContainer = document.createElement('div');
        channelContainer.className = 'channel-graph-container';
        channelContainer.id = `${moduleId}-${channel}-container`;
        container.appendChild(channelContainer);

        // Create canvas for this channel
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-${channel}-canvas`;
        channelContainer.appendChild(canvas);

        // Get channel data
        const channelInfo = channelData[moduleId][channel];
        const values = channelInfo.values.slice(-100);

        // Find min/max for y-axis
        let minValue = Math.min(...values);
        let maxValue = Math.max(...values);

        // Add padding to the min/max values (20% padding)
        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.2;
        minValue = minValue - padding;
        maxValue = maxValue + padding;

        // Create the chart for this channel
        window.channelCharts[moduleId][channel] = new Chart(canvas, {
            type: 'line',
            data: {
                labels: Array(100).fill(''),
                datasets: [{
                    label: channel,
                    data: values,
                    borderColor: colors[activeType] || 'rgba(0, 0, 0, 1)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    hidden: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        min: minValue,
                        max: maxValue,
                        title: {
                            display: false
                        },
                        grid: {
                            color: 'rgba(200, 200, 200, 0.2)'
                        }
                    },
                    x: {
                        display: false,
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            boxWidth: 10,
                            font: {
                                size: 10
                            }
                        }
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    });
}

// Create a combined graph with all channels
function createCombinedGraph(moduleId, canvas, activeType) {
    // Track min and max values for auto-scaling
    let minValue = Number.POSITIVE_INFINITY;
    let maxValue = Number.NEGATIVE_INFINITY;
    let datasets = [];
    const colors = {
        eeg: 'rgba(75, 108, 183, 1)',
        emg: 'rgba(92, 184, 92, 1)',
        ecg: 'rgba(217, 83, 79, 1)',
        accel: 'rgba(240, 173, 78, 1)',
        gyro: 'rgba(91, 192, 222, 1)',
        eda: 'rgba(142, 68, 173, 1)',
        ppg: 'rgba(232, 62, 140, 1)',
        temperature: 'rgba(253, 126, 20, 1)'
    };

    // First pass: determine data ranges
    Object.entries(channelData[moduleId]).forEach(([channel, channelInfo]) => {
        const type = channelInfo.type;

        if (type === activeType) {
            const values = channelInfo.values.slice(-100);
            const channelMin = Math.min(...values);
            const channelMax = Math.max(...values);

            if (channelMin < minValue) minValue = channelMin;
            if (channelMax > maxValue) maxValue = channelMax;

            datasets.push({
                label: channel,
                data: values,
                borderColor: colors[type] || 'rgba(0, 0, 0, 1)',
                backgroundColor: 'rgba(0, 0, 0, 0)',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.3,
                hidden: false
            });
        }
    });

    // Add padding to the min/max values (20% padding)
    const valueRange = maxValue - minValue;
    const padding = valueRange * 0.2;
    minValue = minValue - padding;
    maxValue = maxValue + padding;

    // Create the combined chart
    moduleCharts[moduleId] = new Chart(canvas, {
        type: 'line',
        data: {
            labels: Array(100).fill(''),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    min: minValue,
                    max: maxValue,
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 0
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

// Update type filters UI - modified to work as radio buttons
function updateTypeFilters(moduleId, types, activeType) {
    const filterContainer = document.querySelector(`#${moduleId}-type-filters .filter-buttons`);

    // Clear existing filters
    filterContainer.innerHTML = '';

    // Create a button for each type
    types.forEach(type => {
        const btn = document.createElement('button');
        btn.className = `type-filter-btn type-${type} ${type === activeType ? 'active' : ''}`;
        btn.textContent = type.toUpperCase();
        btn.addEventListener('click', () => {
            console.log(`Clicked filter button for type: ${type}`);

            // Set this as the only active type
            activeTypeFilters[moduleId] = type;

            // Update all buttons to reflect the new active state
            const buttons = filterContainer.querySelectorAll('.type-filter-btn');
            buttons.forEach(button => {
                if (button.textContent === type.toUpperCase()) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            });

            // Update graph with the new selected type
            console.log(`Updating graph with new active type: ${type}`);
            initOrUpdateGraph(moduleId);
        });

        filterContainer.appendChild(btn);
    });

    // If no types, show a message
    if (types.length === 0) {
        const msg = document.createElement('div');
        msg.className = 'alert alert-info mt-2';
        msg.textContent = 'No data types available yet. Connect WebSocket and wait for data.';
        filterContainer.appendChild(msg);
    }
}

// Initialize data structures for a module
function initModuleDataStructures(moduleId) {
    if (!channelData[moduleId]) {
        channelData[moduleId] = {};
    }

    if (activeTypeFilters[moduleId] === undefined) {
        activeTypeFilters[moduleId] = ''; // Now a string instead of a Set
    }

    // Initialize separate channels state
    if (typeof window.separateChannels === 'undefined') {
        window.separateChannels = {};
    }

    if (window.separateChannels[moduleId] === undefined) {
        window.separateChannels[moduleId] = false;
    }

    // Initialize storage for multiple charts when in separate mode
    if (typeof window.channelCharts === 'undefined') {
        window.channelCharts = {};
    }

    if (!window.channelCharts[moduleId]) {
        window.channelCharts[moduleId] = {};
    }
}

// Function for handling show graph toggle
function toggleGraphView(moduleId) {
    const showGraph = document.getElementById(`${moduleId}-show-graph`).checked;
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const tableContainer = document.getElementById(`${moduleId}-table-container`);
    const typeFilters = document.getElementById(`${moduleId}-type-filters`);
    const separateToggleContainer = document.getElementById(`${moduleId}-separate-toggle-container`);

    if (showGraph) {
        // Show graph, hide table
        graphContainer.style.display = 'block';
        tableContainer.style.display = 'none';
        typeFilters.style.display = 'block';
        separateToggleContainer.style.display = 'block';

        // Initialize or update the graph
        initOrUpdateGraph(moduleId);
    } else {
        // Show table, hide graph
        graphContainer.style.display = 'none';
        tableContainer.style.display = 'block';
        typeFilters.style.display = 'none';
        separateToggleContainer.style.display = 'none';
    }

    console.log(`Graph view toggled for ${moduleId}: ${showGraph ? 'on' : 'off'}`);
}

// Function for handling separate channels toggle
function toggleSeparateChannels(moduleId) {
    const separateChannels = document.getElementById(`${moduleId}-separate-channels`).checked;
    window.separateChannels[moduleId] = separateChannels;

    console.log(`Separate channels toggled for ${moduleId}: ${separateChannels ? 'on' : 'off'}`);

    // Clear existing charts
    clearAllCharts(moduleId);

    // Reinitialize the graphs with new layout
    initOrUpdateGraph(moduleId);
}

// Clear all charts for a module
function clearAllCharts(moduleId) {
    // Destroy main chart if it exists
    if (moduleCharts[moduleId]) {
        moduleCharts[moduleId].destroy();
        moduleCharts[moduleId] = null;
    }

    // Destroy all individual channel charts
    if (window.channelCharts[moduleId]) {
        Object.values(window.channelCharts[moduleId]).forEach(chart => {
            if (chart) chart.destroy();
        });
        window.channelCharts[moduleId] = {};
    }

    // Clear the graph container
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    if (graphContainer) {
        graphContainer.innerHTML = '';
        graphContainer.style.height = 'auto'; // Reset height when clearing
    }
}

// Initialize or update the graph for a module
function initOrUpdateGraph(moduleId) {
    // Initialize data structures if needed
    initModuleDataStructures(moduleId);

    // Check if we're in separate channels mode
    const separateChannels = window.separateChannels[moduleId];

    // Get all available types from data
    const types = new Set();
    Object.values(channelData[moduleId]).forEach(channelInfo => {
        types.add(channelInfo.type);
    });

    // Convert to array for easier handling
    const typeArray = Array.from(types);

    // If no active type filter is set, default to eeg or first available type
    if (!activeTypeFilters[moduleId] && typeArray.length > 0) {
        // Default to 'eeg' if available, otherwise take the first type
        activeTypeFilters[moduleId] = typeArray.includes('eeg') ? 'eeg' : typeArray[0];
        console.log(`Setting default active type to: ${activeTypeFilters[moduleId]}`);
    }

    // Current active type
    const activeType = activeTypeFilters[moduleId];
    console.log(`Current active type: ${activeType}`);

    // Update type filters UI
    updateTypeFilters(moduleId, typeArray, activeType);

    // Get the graph container and check if we have data
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const channelsOfActiveType = Object.values(channelData[moduleId])
        .filter(info => info.type === activeType);

    if (channelsOfActiveType.length === 0) {
        if (graphContainer) {
            graphContainer.innerHTML = `<div class="alert alert-info mt-3">No data available for type: ${activeType || ''}. Select a different type.</div>`;
        }
        return;
    }

    // Clear any previous "no data" message
    if (graphContainer) {
        graphContainer.innerHTML = '';
    }

    if (separateChannels) {
        // Create a grid for separate channel graphs
        const gridContainer = document.createElement('div');
        gridContainer.className = 'channel-graphs-grid';
        graphContainer.appendChild(gridContainer);

        // Create a separate graph for each channel
        createSeparateChannelGraphs(moduleId, gridContainer, activeType);
    } else {
        // Create a single canvas for combined graph
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-graph-canvas`;
        graphContainer.appendChild(canvas);

        // Create the combined graph
        createCombinedGraph(moduleId, canvas, activeType);
    }
}

// Create separate graphs for each channel
function createSeparateChannelGraphs(moduleId, container, activeType) {
    const colors = {
        eeg: 'rgba(75, 108, 183, 1)',
        emg: 'rgba(92, 184, 92, 1)',
        ecg: 'rgba(217, 83, 79, 1)',
        accel: 'rgba(240, 173, 78, 1)',
        gyro: 'rgba(91, 192, 222, 1)',
        eda: 'rgba(142, 68, 173, 1)',
        ppg: 'rgba(232, 62, 140, 1)',
        temperature: 'rgba(253, 126, 20, 1)'
    };

    // Find all channels of the active type
    const channelsOfType = Object.entries(channelData[moduleId])
        .filter(([_, info]) => info.type === activeType)
        .map(([channel, _]) => channel);

    console.log(`Found ${channelsOfType.length} channels of type ${activeType}`);

    // Dynamically adjust number of columns based on number of channels
    // Cap at 3 columns maximum to prevent horizontal overflow
    let columns = 2; // Default to 2 columns

    if (channelsOfType.length > 6) {
        // Use 3 columns for many channels (7+)
        columns = 3;
    } else if (channelsOfType.length > 3) {
        // Use 3 columns for medium channel count (4-6)
        columns = 3;
    }

    container.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;

    // Calculate rows needed
    const rows = Math.ceil(channelsOfType.length / columns);

    // Calculate and set dynamic container height based on number of rows
    // Each row is 200px (chart) + 10px (gap) = 210px per row
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const calculatedHeight = (rows * 210) + 20; // Add 20px for container padding
    graphContainer.style.height = `${calculatedHeight}px`;

    console.log(`Adjusting grid to ${columns} columns and ${rows} rows with height ${calculatedHeight}px`);

    // Create a separate graph for each channel
    channelsOfType.forEach(channel => {
        // Create container for this channel
        const channelContainer = document.createElement('div');
        channelContainer.className = 'channel-graph-container';
        channelContainer.id = `${moduleId}-${channel}-container`;
        container.appendChild(channelContainer);

        // Create canvas for this channel
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-${channel}-canvas`;
        channelContainer.appendChild(canvas);

        // Get channel data
        const channelInfo = channelData[moduleId][channel];
        const values = channelInfo.values.slice(-100);

        // Find min/max for y-axis
        let minValue = Math.min(...values);
        let maxValue = Math.max(...values);

        // Add padding to the min/max values (20% padding)
        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.2;
        minValue = minValue - padding;
        maxValue = maxValue + padding;

        // Create the chart for this channel
        window.channelCharts[moduleId][channel] = new Chart(canvas, {
            type: 'line',
            data: {
                labels: Array(100).fill(''),
                datasets: [{
                    label: channel,
                    data: values,
                    borderColor: colors[activeType] || 'rgba(0, 0, 0, 1)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    hidden: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        min: minValue,
                        max: maxValue,
                        title: {
                            display: false
                        },
                        grid: {
                            color: 'rgba(200, 200, 200, 0.2)'
                        }
                    },
                    x: {
                        display: false,
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            boxWidth: 10,
                            font: {
                                size: 10
                            }
                        }
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    });
}

// Create a combined graph with all channels
function createCombinedGraph(moduleId, canvas, activeType) {
    // Track min and max values for auto-scaling
    let minValue = Number.POSITIVE_INFINITY;
    let maxValue = Number.NEGATIVE_INFINITY;
    let datasets = [];
    const colors = {
        eeg: 'rgba(75, 108, 183, 1)',
        emg: 'rgba(92, 184, 92, 1)',
        ecg: 'rgba(217, 83, 79, 1)',
        accel: 'rgba(240, 173, 78, 1)',
        gyro: 'rgba(91, 192, 222, 1)',
        eda: 'rgba(142, 68, 173, 1)',
        ppg: 'rgba(232, 62, 140, 1)',
        temperature: 'rgba(253, 126, 20, 1)'
    };

    // First pass: determine data ranges
    Object.entries(channelData[moduleId]).forEach(([channel, channelInfo]) => {
        const type = channelInfo.type;

        if (type === activeType) {
            const values = channelInfo.values.slice(-100);
            const channelMin = Math.min(...values);
            const channelMax = Math.max(...values);

            if (channelMin < minValue) minValue = channelMin;
            if (channelMax > maxValue) maxValue = channelMax;

            datasets.push({
                label: channel,
                data: values,
                borderColor: colors[type] || 'rgba(0, 0, 0, 1)',
                backgroundColor: 'rgba(0, 0, 0, 0)',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.3,
                hidden: false
            });
        }
    });

    // Add padding to the min/max values (20% padding)
    const valueRange = maxValue - minValue;
    const padding = valueRange * 0.2;
    minValue = minValue - padding;
    maxValue = maxValue + padding;

    // Create the combined chart
    moduleCharts[moduleId] = new Chart(canvas, {
        type: 'line',
        data: {
            labels: Array(100).fill(''),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    min: minValue,
                    max: maxValue,
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 0
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

// Update channel data from WebSocket message
function updateChannelData(moduleId, data) {
    if (!data.visualization_data || !data.visualization_data.list_view) return;

    // Initialize data structures if needed
    initModuleDataStructures(moduleId);

    // Flag to check if we received new data
    let hasNewData = false;

    // Update channel data
    data.visualization_data.list_view.forEach(item => {
        const channelId = item.channel;
        const type = item.type;
        let value = item.value;

        hasNewData = true;

        // Initialize channel if new
        if (!channelData[moduleId][channelId]) {
            channelData[moduleId][channelId] = {
                type: type,
                values: Array(100).fill(value) // Pre-fill with current value
            };
        }

        // Update channel data
        channelData[moduleId][channelId].values.push(value);

        // Limit to last 100 values
        if (channelData[moduleId][channelId].values.length > 100) {
            channelData[moduleId][channelId].values.shift();
        }
    });

    // Update graph if visible and we have new data
    if (hasNewData && document.getElementById(`${moduleId}-show-graph`).checked) {
        const separateChannels = window.separateChannels[moduleId];
        const activeType = activeTypeFilters[moduleId];

        if (separateChannels) {
            // Update each individual channel graph
            data.visualization_data.list_view.forEach(item => {
                const channelId = item.channel;
                const type = item.type;

                // Only update if it's the selected type and has a chart
                if (type === activeType && window.channelCharts[moduleId][channelId]) {
                    const chart = window.channelCharts[moduleId][channelId];
                    const values = channelData[moduleId][channelId].values;

                    // Update data
                    chart.data.datasets[0].data = values;

                    // Check if we need to adjust y-axis scale
                    const minValue = Math.min(...values);
                    const maxValue = Math.max(...values);
                    const valueRange = maxValue - minValue;
                    const padding = valueRange * 0.2;

                    chart.options.scales.y.min = minValue - padding;
                    chart.options.scales.y.max = maxValue + padding;

                    // Update without animation
                    chart.update('none');
                }
            });
        } else if (moduleCharts[moduleId]) {
            // Update the combined chart
            const chart = moduleCharts[moduleId];

            // Check if we need to recalculate chart scale
            let needsFullRefresh = false;
            let minValue = Number.POSITIVE_INFINITY;
            let maxValue = Number.NEGATIVE_INFINITY;

            // Find min/max across all channels of active type
            Object.keys(channelData[moduleId]).forEach(channel => {
                if (channelData[moduleId][channel].type === activeType) {
                    const values = channelData[moduleId][channel].values;
                    const min = Math.min(...values);
                    const max = Math.max(...values);

                    if (min < minValue) minValue = min;
                    if (max > maxValue) maxValue = max;
                }
            });

            // Add padding (20%)
            const valueRange = maxValue - minValue;
            const padding = valueRange * 0.2;
            minValue = minValue - padding;
            maxValue = maxValue + padding;

            // Check if we need to update the scale
            const currentMin = chart.options.scales.y.min;
            const currentMax = chart.options.scales.y.max;

            // If range changed significantly, update scale
            if (minValue < currentMin || maxValue > currentMax ||
                minValue > currentMin * 1.2 || maxValue < currentMax * 0.8) {
                chart.options.scales.y.min = minValue;
                chart.options.scales.y.max = maxValue;
                needsFullRefresh = true;
            }

            // Update each dataset with new data
            chart.data.datasets.forEach(dataset => {
                const channel = dataset.label;
                if (channelData[moduleId][channel] && channelData[moduleId][channel].type === activeType) {
                    dataset.data = channelData[moduleId][channel].values;
                }
            });

            // Update without animation
            chart.update(needsFullRefresh ? undefined : 'none');
        }
    }
}

// Add event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dark mode
    initDarkMode();

    // Find all show-graph toggles and add event listeners
    document.querySelectorAll('[id$="-show-graph"]').forEach(toggle => {
        const moduleId = toggle.id.replace('-show-graph', '');
        toggle.addEventListener('change', () => toggleGraphView(moduleId));
        console.log(`Added event listener for ${moduleId} graph toggle`);
    });

    // Find all separate-channels toggles and add event listeners
    document.querySelectorAll('[id$="-separate-channels"]').forEach(toggle => {
        const moduleId = toggle.id.replace('-separate-channels', '');
        toggle.addEventListener('change', () => toggleSeparateChannels(moduleId));
        console.log(`Added event listener for ${moduleId} separate channels toggle`);
    });

    // Init Bootstrap modal
    fileBrowserModal = new bootstrap.Modal(document.getElementById('fileBrowserModal'));

    // "Go" button inside modal
    document.getElementById('fileBrowserGo')
        .addEventListener('click', () => {
            const p = document.getElementById('fileBrowserPath').value;
            openBrowserDialog(p);
        });

    // "Select" button inside modal
    document.getElementById('fileBrowserSelect')
        .addEventListener('click', () => {
            if (currentBrowseTargetId) {
                let dir    = currentBrowsePath;
                const prefix = document.getElementById('fileBrowserPrefix').value.trim();

                // Build the filepath prefix only; the backend service will append its own timestamp
                let full = dir.endsWith('/') ? dir : dir + '/';
                if (prefix) full += prefix;

                // Ensure default extension
                if (currentBrowseDefaultExt && !full.toLowerCase().endsWith(currentBrowseDefaultExt.toLowerCase())) {
                    full += currentBrowseDefaultExt;
                }
                document.getElementById(currentBrowseTargetId).value = full;
            }
            fileBrowserModal.hide();
        });

    // Override file-dialog buttons to open our modal
    document.querySelectorAll('.file-dialog-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tgt = e.currentTarget.dataset;
            currentBrowseTargetId     = tgt.target;
            currentBrowseDefaultExt   = tgt.defaultExtension || '';
            openBrowserDialog();
        });
    });
});

// Fetch and display server directory listing
async function openBrowserDialog(overridePath) {
    const listEl    = document.getElementById('file-list');
    const pathInput = document.getElementById('fileBrowserPath');
    const labelEl   = document.getElementById('fileBrowserLabel');

    // Determine base path
    const base = overridePath !== undefined
        ? overridePath.replace(/\\/g,'/')
        : ( document.getElementById(currentBrowseTargetId).value.replace(/\\/g,'/')
            || window.baseBrowsePath );
    currentBrowsePath = base.endsWith('/') ? base : base + '/';  // ensure trailing slash
    pathInput.value   = base;
    labelEl.textContent = `Select Directory: ${base}`;

    // Show loading state and open modal
    listEl.innerHTML = '<li class="list-group-item">Loading...</li>';
    fileBrowserModal.show();

    try {
        const res  = await fetch(`/api/files?path=${encodeURIComponent(base)}`);
        const data = await res.json();

        if (!res.ok || !Array.isArray(data.items)) {
            listEl.innerHTML = `<li class="list-group-item">Error: ${data.error||'Invalid response'}</li>`;
            return;
        }

        // Populate list
        listEl.innerHTML = '';
        if (data.items.length === 0) {
            listEl.innerHTML = '<li class="list-group-item">No items found</li>';
        }
        data.items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action';
            li.textContent = item.name;
            li.onclick = () => openBrowserDialog(item.path);
            listEl.appendChild(li);
        });

    } catch (err) {
        listEl.innerHTML = `<li class="list-group-item">Error: ${err.message}</li>`;
    }
}
