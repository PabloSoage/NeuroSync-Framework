export class EventDisplayManager {
    constructor() {
        this.graphToggleCallbacks = [];
        this.separateChannelsCallbacks = [];
        this.lastTableData = {}; // NUEVO: Cache de los últimos datos de la tabla
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
        if (!tableBody) return;

        // NUEVO: Usar actualización incremental en lugar de recrear toda la tabla
        this.updateTableIncremental(moduleId, tableBody, data.visualization_data.list_view);
    }

    updateTableIncremental(moduleId, tableBody, listViewData) {
        // Crear un mapa de los nuevos datos por canal
        const newDataMap = new Map();
        listViewData.forEach(item => {
            let valueDisplay = item.value.toFixed(2);
            if (item.samples_count && item.samples_count > 1) {
                valueDisplay += ` (${item.samples_count} samples)`;
            }

            newDataMap.set(item.channel, {
                channel: item.channel,
                type: item.type,
                value: valueDisplay
            });
        });

        // Obtener filas existentes
        const existingRows = Array.from(tableBody.querySelectorAll('tr'));
        const existingChannels = new Set();

        // Actualizar filas existentes
        existingRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 3) {
                const channelName = cells[0].textContent;
                existingChannels.add(channelName);

                if (newDataMap.has(channelName)) {
                    const newData = newDataMap.get(channelName);

                    // Solo actualizar si el contenido ha cambiado
                    if (cells[1].textContent !== newData.type) {
                        cells[1].textContent = newData.type;
                    }
                    if (cells[2].textContent !== newData.value) {
                        cells[2].textContent = newData.value;
                        // OPCIONAL: Añadir efecto visual de actualización
                        cells[2].classList.add('cell-updated');
                        setTimeout(() => cells[2].classList.remove('cell-updated'), 150);
                    }
                } else {
                    // Remover fila si el canal ya no existe
                    row.remove();
                }
            }
        });

        // Añadir nuevas filas para canales que no existían
        newDataMap.forEach((data, channelName) => {
            if (!existingChannels.has(channelName)) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${data.channel}</td>
                    <td>${data.type}</td>
                    <td>${data.value}</td>
                `;
                tableBody.appendChild(tr);
            }
        });

        // Actualizar cache
        this.lastTableData[moduleId] = newDataMap;
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
