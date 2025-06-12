export class WebSocketManager {
    constructor() {
        this.connections = {};
        this.eventBuffers = {};
        this.eventStats = {};
        this.eventProcessors = {};
        this.dataCallbacks = [];

        this.EVENT_BUFFER_LIMIT = 5000;
        this.DISPLAY_CHUNK_SIZE = 20;
    }

    connect(moduleId) {
        if (this.connections[moduleId]) {
            return; // Already connected
        }

        this.initializeModuleData(moduleId);
        this.updateConnectionUI(moduleId, 'connecting');
        this.addSystemEvent(moduleId, 'Connecting to WebSocket...', 'system');

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/${moduleId}`);

        this.setupWebSocketEvents(moduleId, ws);
        this.connections[moduleId] = ws;
    }

    disconnect(moduleId) {
        const ws = this.connections[moduleId];
        if (ws) {
            ws.close();
            this.cleanup(moduleId);
        }
    }

    setupWebSocketEvents(moduleId, ws) {
        ws.onopen = () => this.handleOpen(moduleId);
        ws.onmessage = (event) => this.handleMessage(moduleId, event);
        ws.onclose = (event) => this.handleClose(moduleId, event);
        ws.onerror = (error) => this.handleError(moduleId, error);
    }

    handleOpen(moduleId) {
        this.updateConnectionUI(moduleId, 'connected');
        this.addSystemEvent(moduleId, 'WebSocket connection established', 'system');
        this.setupPingInterval(moduleId);
        this.setupEventProcessor(moduleId);
        this.setupStatsDisplay(moduleId);
        this.setupPerformanceSettings(moduleId);
    }

    handleMessage(moduleId, event) {
        try {
            const data = JSON.parse(event.data);

            if (data.response === 'pong') return;

            // Update event counter
            this.updateEventCounter(moduleId);
            this.updateEventStats(moduleId);
            this.bufferEvent(moduleId, data);
            this.notifyDataCallbacks(moduleId, data);

        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
            this.addSystemEvent(moduleId, `Error parsing message: ${e.message}`, 'system');
        }
    }

    handleClose(moduleId, event) {
        this.cleanup(moduleId);
        this.updateConnectionUI(moduleId, 'disconnected');

        if (event.wasClean) {
            this.addSystemEvent(moduleId, `WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`, 'system');
        } else {
            this.addSystemEvent(moduleId, 'WebSocket connection died', 'system');
        }
    }

    handleError(moduleId, error) {
        this.updateConnectionUI(moduleId, 'error');
        this.addSystemEvent(moduleId, `WebSocket error: ${error.message || 'Unknown error'}`, 'system');
        console.error(`WebSocket error for ${moduleId}:`, error);
    }

    initializeModuleData(moduleId) {
        this.eventBuffers[moduleId] = [];
        this.eventStats[moduleId] = {
            totalReceived: 0,
            displayed: 0,
            dropped: 0,
            lastDisplayUpdate: Date.now(),
            eventsPerSecond: 0,
            lastRateUpdate: Date.now(),
            receivedSinceLastUpdate: 0,
            eventCount: 0
        };
    }

    updateConnectionUI(moduleId, status) {
        const connectBtn = document.getElementById(`${moduleId}-connect-ws-btn`);
        const disconnectBtn = document.getElementById(`${moduleId}-disconnect-ws-btn`);
        const statusIndicator = document.getElementById(`${moduleId}-connection-status`);

        switch (status) {
            case 'connecting':
                if (connectBtn) connectBtn.disabled = true;
                if (disconnectBtn) disconnectBtn.disabled = false;
                if (statusIndicator) statusIndicator.className = 'connection-status connecting';
                break;
            case 'connected':
                if (connectBtn) connectBtn.disabled = true;
                if (disconnectBtn) disconnectBtn.disabled = false;
                if (statusIndicator) statusIndicator.className = 'connection-status connected';
                break;
            case 'disconnected':
                if (connectBtn) connectBtn.disabled = false;
                if (disconnectBtn) disconnectBtn.disabled = true;
                if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
                break;
        }
    }

    setupPingInterval(moduleId) {
        const ws = this.connections[moduleId];
        if (ws) {
            ws.pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ command: 'ping' }));
                }
            }, 30000);
        }
    }

    setupStatsDisplay(moduleId) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);

        // Add stats display elements
        const statsContainer = document.createElement('div');
        statsContainer.id = `${moduleId}-event-stats`;
        statsContainer.className = 'event-stats';
        statsContainer.innerHTML = `
            <div class="event-rate">Events/sec: 0</div>
            <div class="buffer-status">Buffer: 0/0</div>
            <div class="display-latency">Display lag: 0ms</div>
        `;
        eventsContainer.parentNode.insertBefore(statsContainer, eventsContainer);
    }

    setupPerformanceSettings(moduleId) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);

        // Add performance settings
        const perfSettings = document.createElement('div');
        perfSettings.className = 'perf-settings mb-2';
        perfSettings.innerHTML = `
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="${moduleId}-high-performance" checked>
                <label class="form-check-label" for="${moduleId}-high-performance">High performance mode</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" id="${moduleId}-skip-events" checked>
                <label class="form-check-label" for="${moduleId}-skip-events">Skip events when overloaded</label>
            </div>
        `;
        eventsContainer.parentNode.insertBefore(perfSettings, eventsContainer);
    }

    setupEventProcessor(moduleId) {
        // Initialize processor state
        this.eventProcessors[moduleId] = {
            lastProcessTime: performance.now(),
            processingActive: false,
            animFrameId: null
        };

        // Function to process event buffer with animation frame
        const processEvents = () => {
            const processor = this.eventProcessors[moduleId];
            if (!processor) return; // Processor was stopped

            const now = performance.now();
            const elapsed = now - processor.lastProcessTime;

            // Process events if any in buffer
            if (this.eventBuffers[moduleId] && this.eventBuffers[moduleId].length > 0) {
                this.processEventBuffer(moduleId);
            }

            processor.lastProcessTime = now;
            processor.animFrameId = requestAnimationFrame(processEvents);
        };

        // Start the processing loop
        this.eventProcessors[moduleId].animFrameId = requestAnimationFrame(processEvents);
    }

    processEventBuffer(moduleId) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);
        const highPerformanceMode = document.getElementById(`${moduleId}-high-performance`)?.checked || false;
        const autoScroll = document.getElementById(`${moduleId}-auto-scroll`)?.checked || false;

        // Determine how many events to process in this frame
        let processCount = highPerformanceMode ?
            Math.min(this.DISPLAY_CHUNK_SIZE, this.eventBuffers[moduleId].length) :
            Math.min(5, this.eventBuffers[moduleId].length);

        // Extract the events to process
        const eventsToProcess = this.eventBuffers[moduleId].splice(0, processCount);

        // Create a document fragment for batch DOM operations
        const fragment = document.createDocumentFragment();

        // Process each event
        eventsToProcess.forEach(data => {
            // Update stats
            this.eventStats[moduleId].displayed++;

            // Determine event type for styling
            let eventClass = 'event';
            let eventType = data.event_type || data.type || 'unknown';

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
            const formattedData = highPerformanceMode ?
                this.formatEventDataCompact(data) :
                JSON.stringify(data, null, 2);

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
            fragment.appendChild(eventElement);
        });

        // Batch append to DOM
        eventsContainer.appendChild(fragment);

        // Clean up old events if we have too many
        const maxDisplayEvents = highPerformanceMode ? 200 : 500;
        while (eventsContainer.childElementCount > maxDisplayEvents) {
            eventsContainer.removeChild(eventsContainer.firstChild);
        }

        // Auto-scroll if enabled
        if (autoScroll) {
            eventsContainer.scrollTop = eventsContainer.scrollHeight;
        }

        // Update display stats
        this.updateDisplayStats(moduleId);
    }

    formatEventDataCompact(data) {
        // Extract the most useful properties based on event type
        const eventType = data.event_type || data.type || 'unknown';

        let result = eventType;

        // Add info based on event type
        if (data.key) {
            result += `: ${data.key}`;
        } else if (data.button) {
            result += `: ${data.button}`;
        }

        // For PS4 controller events
        if (data.ps4_state) {
            const ps4 = data.ps4_state;
            // Add active buttons
            if (ps4.active_buttons && ps4.active_buttons.length) {
                result += ` [${ps4.active_buttons.join(', ')}]`;
            }

            // Add stick info for significant movements
            if (ps4.sticks) {
                if (ps4.sticks.left && (Math.abs(ps4.sticks.left.x) > 0.1 || Math.abs(ps4.sticks.left.y) > 0.1)) {
                    result += ` Left: ${ps4.sticks.left.direction} (${ps4.sticks.left.percentage_x}, ${ps4.sticks.left.percentage_y})`;
                }
                if (ps4.sticks.right && (Math.abs(ps4.sticks.right.x) > 0.1 || Math.abs(ps4.sticks.right.y) > 0.1)) {
                    result += ` Right: ${ps4.sticks.right.direction} (${ps4.sticks.right.percentage_x}, ${ps4.sticks.right.percentage_y})`;
                }
            }

            // Add trigger info
            if (ps4.triggers) {
                if (ps4.triggers.left && ps4.triggers.left.value > 0.1) {
                    result += ` L2: ${ps4.triggers.left.percentage}`;
                }
                if (ps4.triggers.right && ps4.triggers.right.value > 0.1) {
                    result += ` R2: ${ps4.triggers.right.percentage}`;
                }
            }

            return result;
        }

        // For mouse movements
        if (data.movement) {
            const mv = data.movement;
            if (mv.status) {
                result += `: ${mv.status}`;
            }
        }

        // For key events
        if (data.keys && data.keys.length) {
            result += ` [${data.keys.join(', ')}]`;
        }

        return result;
    }

    updateEventCounter(moduleId) {
        this.eventStats[moduleId].eventCount++;
        const eventCountEl = document.getElementById(`${moduleId}-event-count`);
        if (eventCountEl) {
            eventCountEl.textContent = `Events: ${this.eventStats[moduleId].eventCount}`;
        }
    }

    updateEventStats(moduleId) {
        const stats = this.eventStats[moduleId];
        stats.totalReceived++;
        stats.receivedSinceLastUpdate++;

        const now = Date.now();
        if (now - stats.lastRateUpdate > 500) {
            const elapsed = (now - stats.lastRateUpdate) / 1000;
            stats.eventsPerSecond = Math.round(stats.receivedSinceLastUpdate / elapsed);
            stats.receivedSinceLastUpdate = 0;
            stats.lastRateUpdate = now;

            this.updateStatsDisplay(moduleId);
        }
    }

    updateStatsDisplay(moduleId) {
        const statsEl = document.querySelector(`#${moduleId}-event-stats .event-rate`);
        if (statsEl) {
            statsEl.textContent = `Events/sec: ${this.eventStats[moduleId].eventsPerSecond}`;
        }

        const bufferStatusEl = document.querySelector(`#${moduleId}-event-stats .buffer-status`);
        if (bufferStatusEl) {
            bufferStatusEl.textContent = `Buffer: ${this.eventBuffers[moduleId].length}/${this.EVENT_BUFFER_LIMIT}`;
        }
    }

    updateDisplayStats(moduleId) {
        const latency = Date.now() - this.eventStats[moduleId].lastDisplayUpdate;
        this.eventStats[moduleId].lastDisplayUpdate = Date.now();

        const latencyEl = document.querySelector(`#${moduleId}-event-stats .display-latency`);
        if (latencyEl) {
            latencyEl.textContent = `Display lag: ${latency}ms`;
            // Visual indicator for high latency
            if (latency > 250) {
                latencyEl.style.color = 'red';
            } else if (latency > 100) {
                latencyEl.style.color = 'orange';
            } else {
                latencyEl.style.color = '';
            }
        }
    }

    bufferEvent(moduleId, data) {
        const buffer = this.eventBuffers[moduleId];
        const stats = this.eventStats[moduleId];

        // High-performance mode logic
        const highPerformanceMode = document.getElementById(`${moduleId}-high-performance`)?.checked || false;
        const skipEvents = document.getElementById(`${moduleId}-skip-events`)?.checked || false;

        if (highPerformanceMode && skipEvents && buffer.length > this.EVENT_BUFFER_LIMIT * 0.8) {
            if (!this.isImportantEvent(data)) {
                stats.dropped++;
                return;
            }
        }

        if (buffer.length >= this.EVENT_BUFFER_LIMIT) {
            const toRemove = Math.max(100, Math.floor(this.EVENT_BUFFER_LIMIT * 0.2));
            buffer.splice(0, toRemove);
            stats.dropped += toRemove;
        }

        buffer.push(data);
    }

    isImportantEvent(data) {
        const eventType = data.event_type || data.type || '';

        if (eventType.includes('connected') ||
            eventType.includes('disconnected') ||
            eventType.includes('error') ||
            eventType.includes('state_change')) {
            return true;
        }

        if (eventType.includes('button_press') || eventType.includes('button_release')) {
            return true;
        }

        return Math.random() < 0.2;
    }

    addSystemEvent(moduleId, message, type) {
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);
        if (!eventsContainer) return;

        const eventElement = document.createElement('div');
        eventElement.className = `event event-${type}`;
        eventElement.textContent = message;
        eventsContainer.appendChild(eventElement);

        // Auto-scroll if enabled
        const autoScrollCheckbox = document.getElementById(`${moduleId}-auto-scroll`);
        if (autoScrollCheckbox?.checked) {
            eventsContainer.scrollTop = eventsContainer.scrollHeight;
        }
    }

    cleanup(moduleId) {
        const ws = this.connections[moduleId];
        if (ws?.pingInterval) {
            clearInterval(ws.pingInterval);
        }

        if (this.eventProcessors[moduleId]) {
            cancelAnimationFrame(this.eventProcessors[moduleId].animFrameId);
            delete this.eventProcessors[moduleId];
        }

        // Clean up stats display
        const statsEl = document.getElementById(`${moduleId}-event-stats`);
        if (statsEl) statsEl.remove();

        // Clean up perf settings
        const eventsContainer = document.getElementById(`${moduleId}-events-container`);
        const perfSettings = eventsContainer.parentNode.querySelector('.perf-settings');
        if (perfSettings) perfSettings.remove();

        delete this.connections[moduleId];
        delete this.eventBuffers[moduleId];
        delete this.eventStats[moduleId];
    }

    onDataReceived(callback) {
        this.dataCallbacks.push(callback);
    }

    notifyDataCallbacks(moduleId, data) {
        this.dataCallbacks.forEach(callback => callback(moduleId, data));
    }
}
