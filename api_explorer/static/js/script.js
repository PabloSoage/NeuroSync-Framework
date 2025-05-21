// JavaScript for API Explorer functionality
const webSockets = {};

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
            
            // Update the EEG data table if visualization_data exists AND the table exists
            if (data.visualization_data && data.visualization_data.list_view) {
                const tableBody = document.querySelector(`#${moduleId}-data-table tbody`);
                if (tableBody) {  // Solo procesar si la tabla existe
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
