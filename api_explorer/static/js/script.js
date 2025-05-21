// JavaScript for API Explorer functionality
const webSockets = {};
const moduleCharts = {}; // Store chart objects by module
const channelData = {}; // Store historical data by module and channel
const activeTypeFilters = {}; // Store active type filters by module

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
            const formattedData = formatEventData(data);
            
            // Format timestamp
            let timeStr = '';
            if (data.timestamp) {
                const date = new Date(data.timestamp * 1000);
                timeStr = `<span class="event-time">${date.toLocaleTimeString()}.${date.getMilliseconds().toString().padStart(3, '0')}</span>`;
            }
            
            // Create and append event element
            const eventElement = document.createElement('div');
            eventElement.className = eventClass;
            eventElement.innerHTML = `${timeStr}${formattedData}`;
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

// Function to format event data for better display
function formatEventData(data) {
    // Create a simplified representation for display
    let output = '';
    
    // Add event type
    if (data.event_type) {
        output += `<strong>Event:</strong> ${data.event_type}\n`;
    }
    
    // Add key info if present
    if (data.key) {
        output += `<strong>Key:</strong> ${data.key}\n`;
    }
    
    // Add active keys if present
    if (data.active_keys && data.active_keys.length > 0) {
        output += `<strong>Active Keys:</strong> ${data.active_keys.join(', ')}\n`;
    }
    
    // Add mouse position if present
    if (data.mouse_x !== undefined && data.mouse_y !== undefined) {
        output += `<strong>Mouse Position:</strong> (${data.mouse_x}, ${data.mouse_y})\n`;
    }
    
    // Add mouse button if present
    if (data.button_pressed) {
        output += `<strong>Button:</strong> ${data.button_pressed}\n`;
    }
    
    // Add direction if present
    if (data.direction) {
        output += `<strong>Direction:</strong> ${data.direction}\n`;
    }
    
    // Add joystick position if present
    if (data.rel_x !== undefined && data.rel_y !== undefined) {
        output += `<strong>Joystick:</strong> (${data.rel_x.toFixed(2)}, ${data.rel_y.toFixed(2)})\n`;
    }
    
    // If there's no specific data to display, show the full object
    if (!output) {
        output = JSON.stringify(data, null, 2);
    }
    
    return output;
}

// Initialize or update the graph for a module
function initOrUpdateGraph(moduleId) {
    const canvas = document.getElementById(`${moduleId}-graph-canvas`);
    
    // Initialize data structures if needed
    initModuleDataStructures(moduleId);
    
    // If we already have a chart, destroy it first
    if (moduleCharts[moduleId]) {
        moduleCharts[moduleId].destroy();
    }
    
    // Prepare datasets from channelData
    const datasets = [];
    const types = new Set();
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
    
    // Get all available types from data
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
    
    // Track min and max values for auto-scaling
    let minValue = Number.POSITIVE_INFINITY;
    let maxValue = Number.NEGATIVE_INFINITY;
    let datasetsByChannel = {};
    
    // First pass: determine data ranges and prepare dataset data
    Object.keys(channelData[moduleId]).forEach(channel => {
        const channelInfo = channelData[moduleId][channel];
        const type = channelInfo.type;
        
        // Only include channels with active type
        if (type === activeType) {
            const values = channelInfo.values.slice(-100);
            datasetsByChannel[channel] = values;
            
            // Find min/max for axis scaling
            const channelMin = Math.min(...values);
            const channelMax = Math.max(...values);
            
            if (channelMin < minValue) minValue = channelMin;
            if (channelMax > maxValue) maxValue = channelMax;
        }
    });
    
    // Add padding to the min/max values (20% padding)
    const valueRange = maxValue - minValue;
    const padding = valueRange * 0.2;
    minValue = minValue - padding;
    maxValue = maxValue + padding;
    
    // Now create datasets with the full value range context
    Object.keys(datasetsByChannel).forEach(channel => {
        const channelInfo = channelData[moduleId][channel];
        const type = channelInfo.type;
        const values = datasetsByChannel[channel];
        
        // Compute vertical offset to prevent overlap between signals
        // Each channel gets its own "lane" within the full range
        const channelColor = colors[type] || 'rgba(0, 0, 0, 1)';
        
        datasets.push({
            label: channel,
            data: values,
            borderColor: channelColor,
            backgroundColor: 'rgba(0, 0, 0, 0)',
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3, // Add slight smoothing for better visualization
            hidden: false
        });
    });
    
    // Check if we have data to display for the current type
    const hasDataForCurrentType = datasets.length > 0;
    
    // Update type filters UI
    updateTypeFilters(moduleId, typeArray, activeType);
    
    // If no data for current type but we have data for other types,
    // display a message
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    
    if (!hasDataForCurrentType) {
        if (graphContainer) {
            graphContainer.innerHTML = `<div class="alert alert-info mt-3">No data available for type: ${activeType || ''}. Select a different type.</div>`;
            
            // Create a new canvas for when data arrives
            const newCanvas = document.createElement('canvas');
            newCanvas.id = `${moduleId}-graph-canvas`;
            graphContainer.appendChild(newCanvas);
        }
        return;
    }
    
    // Clear any previous "no data" message
    if (graphContainer) {
        graphContainer.innerHTML = '';
        const newCanvas = document.createElement('canvas');
        newCanvas.id = `${moduleId}-graph-canvas`;
        graphContainer.appendChild(newCanvas);
    }
    
    // Now get the canvas (might be newly created)
    const canvasToUse = document.getElementById(`${moduleId}-graph-canvas`);
    
    // Create chart with improved configuration
    moduleCharts[moduleId] = new Chart(canvasToUse, {
        type: 'line',
        data: {
            labels: Array(100).fill(''), // Empty labels for the X-axis
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear', // Use linear scale instead of logarithmic
                    min: minValue,
                    max: maxValue,
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'  // Lighter grid lines
                    }
                },
                x: {
                    display: true,
                    grid: {
                        display: false  // Hide vertical grid lines for cleaner look
                    },
                    ticks: {
                        display: false  // Hide tick labels
                    }
                }
            },
            animation: {
                duration: 0 // Disable animations for performance
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
        // If it's our first data, we need to initialize the graph
        if (!moduleCharts[moduleId]) {
            initOrUpdateGraph(moduleId);
        } else {
            // Get current active type
            const activeType = activeTypeFilters[moduleId];
            
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
            const chart = moduleCharts[moduleId];
            const currentMin = chart.options.scales.y.min;
            const currentMax = chart.options.scales.y.max;
            
            // If range changed significantly (more than 20%), update scale
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
            
            // Update chart with optimized options
            chart.update(needsFullRefresh ? undefined : 'none');
        }
    }
}

// Function for handling show graph toggle
function toggleGraphView(moduleId) {
    const showGraph = document.getElementById(`${moduleId}-show-graph`).checked;
    const graphContainer = document.getElementById(`${moduleId}-graph-container`);
    const tableContainer = document.getElementById(`${moduleId}-table-container`);
    const typeFilters = document.getElementById(`${moduleId}-type-filters`);
    
    if (showGraph) {
        // Show graph, hide table
        graphContainer.style.display = 'block';
        tableContainer.style.display = 'none';
        typeFilters.style.display = 'block';
        
        // Initialize or update the graph
        initOrUpdateGraph(moduleId);
    } else {
        // Show table, hide graph
        graphContainer.style.display = 'none';
        tableContainer.style.display = 'block';
        typeFilters.style.display = 'none';
    }
    
    console.log(`Graph view toggled for ${moduleId}: ${showGraph ? 'on' : 'off'}`);
}

// Add event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Find all show-graph toggles and add event listeners
    document.querySelectorAll('[id$="-show-graph"]').forEach(toggle => {
        const moduleId = toggle.id.replace('-show-graph', '');
        toggle.addEventListener('change', () => toggleGraphView(moduleId));
        console.log(`Added event listener for ${moduleId} graph toggle`);
    });
});
