export class ChartManager {
    constructor() {
        this.moduleCharts = {};
        this.channelData = {};
        this.activeTypeFilters = {};
        this.separateChannels = {};
        this.channelCharts = {};
        this.chartUpdateThrottlers = {};
        this.pendingChartUpdates = {};
        this.chartUpdateCounters = {};

        this.CHART_UPDATE_INTERVAL = 16;
        this.SCALE_UPDATE_INTERVAL = 10;
        this.colors = {
            eeg: 'rgba(75, 108, 183, 1)',
            emg: 'rgba(92, 184, 92, 1)',
            ecg: 'rgba(217, 83, 79, 1)',
            accel: 'rgba(240, 173, 78, 1)',
            gyro: 'rgba(91, 192, 222, 1)',
            eda: 'rgba(142, 68, 173, 1)',
            ppg: 'rgba(232, 62, 140, 1)',
            temperature: 'rgba(253, 126, 20, 1)'
        };
    }

    initializeModule(moduleId) {
        this.channelData[moduleId] = {};
        this.activeTypeFilters[moduleId] = '';
        this.separateChannels[moduleId] = false;
        this.channelCharts[moduleId] = {};
    }

    updateData(moduleId, data) {
        if (!data.visualization_data?.list_view) return;

        let hasNewData = false;
        const updatedChannels = new Set();

        data.visualization_data.list_view.forEach(item => {
            const channelId = item.channel;
            const type = item.type;

            // CAMBIO PRINCIPAL: Usar todas las muestras del evento, no solo una
            const allValues = item.values || [item.value]; // Usar 'values' si está disponible, sino 'value'
            const samplesCount = item.samples_count || allValues.length;

            hasNewData = true;
            updatedChannels.add(channelId);

            if (!this.channelData[moduleId][channelId]) {
                this.channelData[moduleId][channelId] = {
                    type: type,
                    values: Array(100).fill(allValues[0] || 0)
                };
            }

            // NUEVO: Añadir todas las muestras del evento
            allValues.forEach(value => {
                const numValue = parseFloat(value) || 0;
                this.channelData[moduleId][channelId].values.push(numValue);
            });

            // Mantener el límite del buffer
            const bufferLimit = 100;
            while (this.channelData[moduleId][channelId].values.length > bufferLimit) {
                this.channelData[moduleId][channelId].values.shift();
            }
        });

        if (hasNewData && document.getElementById(`${moduleId}-show-graph`)?.checked) {
            updatedChannels.forEach(channelId => {
                this.queueChartUpdate(moduleId, channelId, this.channelData[moduleId][channelId]);
            });
        }
    }

    toggleGraph(moduleId, showGraph) {
        const graphContainer = document.getElementById(`${moduleId}-graph-container`);
        const tableContainer = document.getElementById(`${moduleId}-table-container`);
        const typeFilters = document.getElementById(`${moduleId}-type-filters`);
        const separateToggleContainer = document.getElementById(`${moduleId}-separate-toggle-container`);

        if (showGraph) {
            graphContainer.style.display = 'block';
            tableContainer.style.display = 'none';
            typeFilters.style.display = 'block';
            separateToggleContainer.style.display = 'block';

            this.initOrUpdateGraph(moduleId);
        } else {
            graphContainer.style.display = 'none';
            tableContainer.style.display = 'block';
            typeFilters.style.display = 'none';
            separateToggleContainer.style.display = 'none';
        }
    }

    toggleSeparateChannels(moduleId, separate) {
        this.separateChannels[moduleId] = separate;
        this.clearAllCharts(moduleId);
        this.initOrUpdateGraph(moduleId);
    }

    initOrUpdateGraph(moduleId) {
        // Get all available types
        const types = new Set();
        Object.values(this.channelData[moduleId]).forEach(channelInfo => {
            types.add(channelInfo.type);
        });

        const typeArray = Array.from(types);

        // Set default active type if none set
        if (!this.activeTypeFilters[moduleId] && typeArray.length > 0) {
            this.activeTypeFilters[moduleId] = typeArray.includes('eeg') ? 'eeg' : typeArray[0];
        }

        const activeType = this.activeTypeFilters[moduleId];
        this.updateTypeFilters(moduleId, typeArray, activeType);

        const graphContainer = document.getElementById(`${moduleId}-graph-container`);
        const channelsOfActiveType = Object.values(this.channelData[moduleId])
            .filter(info => info.type === activeType);

        if (channelsOfActiveType.length === 0) {
            if (graphContainer) {
                graphContainer.innerHTML = `<div class="alert alert-info mt-3">No data available for type: ${activeType || ''}. Select a different type.</div>`;
            }
            return;
        }

        graphContainer.innerHTML = '';

        if (this.separateChannels[moduleId]) {
            this.createSeparateChannelGraphs(moduleId, graphContainer, activeType);
        } else {
            this.createCombinedGraph(moduleId, graphContainer, activeType);
        }
    }

    createSeparateChannelGraphs(moduleId, container, activeType) {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'channel-graphs-grid';
        container.appendChild(gridContainer);

        const channelsOfType = Object.entries(this.channelData[moduleId])
            .filter(([_, info]) => info.type === activeType)
            .map(([channel, _]) => channel);

        let columns = channelsOfType.length > 6 ? 3 : 2;
        gridContainer.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;

        const rows = Math.ceil(channelsOfType.length / columns);
        const calculatedHeight = (rows * 210) + 20;
        container.style.height = `${calculatedHeight}px`;

        channelsOfType.forEach(channel => {
            this.createChannelChart(moduleId, channel, gridContainer, activeType);
        });
    }

    createChannelChart(moduleId, channel, container, activeType) {
        const channelContainer = document.createElement('div');
        channelContainer.className = 'channel-graph-container';
        channelContainer.id = `${moduleId}-${channel}-container`;
        container.appendChild(channelContainer);

        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-${channel}-canvas`;
        channelContainer.appendChild(canvas);

        const channelInfo = this.channelData[moduleId][channel];
        const values = channelInfo.values.slice(-100);

        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.2;

        const chartConfig = {
            type: 'line',
            data: {
                labels: Array(100).fill(''),
                datasets: [{
                    label: channel,
                    data: values,
                    borderColor: this.colors[activeType] || 'rgba(0, 0, 0, 1)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        min: minValue - padding,
                        max: maxValue + padding,
                        title: { display: false },
                        grid: { color: 'rgba(200, 200, 200, 0.2)' }
                    },
                    x: {
                        display: false,
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { boxWidth: 10, font: { size: 10 } }
                    }
                }
            }
        };

        this.channelCharts[moduleId][channel] = new Chart(canvas, chartConfig);
    }

    createCombinedGraph(moduleId, container, activeType) {
        const canvas = document.createElement('canvas');
        canvas.id = `${moduleId}-graph-canvas`;
        container.appendChild(canvas);

        let minValue = Number.POSITIVE_INFINITY;
        let maxValue = Number.NEGATIVE_INFINITY;
        let datasets = [];

        Object.entries(this.channelData[moduleId]).forEach(([channel, channelInfo]) => {
            if (channelInfo.type === activeType) {
                const values = channelInfo.values.slice(-100);
                const channelMin = Math.min(...values);
                const channelMax = Math.max(...values);

                if (channelMin < minValue) minValue = channelMin;
                if (channelMax > maxValue) maxValue = channelMax;

                datasets.push({
                    label: channel,
                    data: values,
                    borderColor: this.colors[channelInfo.type] || 'rgba(0, 0, 0, 1)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3
                });
            }
        });

        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.2;

        const chartConfig = {
            type: 'line',
            data: { labels: Array(100).fill(''), datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        min: minValue - padding,
                        max: maxValue + padding,
                        title: { display: true, text: 'Value' },
                        grid: { color: 'rgba(200, 200, 200, 0.2)' }
                    },
                    x: {
                        display: true,
                        grid: { display: false },
                        ticks: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, usePointStyle: true }
                    }
                }
            }
        };

        this.moduleCharts[moduleId] = new Chart(canvas, chartConfig);
    }

    updateTypeFilters(moduleId, types, activeType) {
        const filterContainer = document.querySelector(`#${moduleId}-type-filters .filter-buttons`);
        filterContainer.innerHTML = '';

        types.forEach(type => {
            const btn = document.createElement('button');
            btn.className = `type-filter-btn type-${type} ${type === activeType ? 'active' : ''}`;
            btn.textContent = type.toUpperCase();
            btn.addEventListener('click', () => {
                this.activeTypeFilters[moduleId] = type;

                filterContainer.querySelectorAll('.type-filter-btn').forEach(button => {
                    button.classList.toggle('active', button.textContent === type.toUpperCase());
                });

                this.initOrUpdateGraph(moduleId);
            });

            filterContainer.appendChild(btn);
        });

        if (types.length === 0) {
            const msg = document.createElement('div');
            msg.className = 'alert alert-info mt-2';
            msg.textContent = 'No data types available yet. Connect WebSocket and wait for data.';
            filterContainer.appendChild(msg);
        }
    }

    clearAllCharts(moduleId) {
        if (this.chartUpdateThrottlers[moduleId]) {
            clearTimeout(this.chartUpdateThrottlers[moduleId]);
            delete this.chartUpdateThrottlers[moduleId];
        }

        if (this.pendingChartUpdates[moduleId]) {
            delete this.pendingChartUpdates[moduleId];
        }

        if (this.chartUpdateCounters[moduleId]) {
            delete this.chartUpdateCounters[moduleId];
        }

        if (this.moduleCharts[moduleId]) {
            this.moduleCharts[moduleId].destroy();
            this.moduleCharts[moduleId] = null;
        }

        if (this.channelCharts[moduleId]) {
            Object.values(this.channelCharts[moduleId]).forEach(chart => {
                if (chart) chart.destroy();
            });
            this.channelCharts[moduleId] = {};
        }

        const graphContainer = document.getElementById(`${moduleId}-graph-container`);
        if (graphContainer) {
            graphContainer.innerHTML = '';
            graphContainer.style.height = 'auto';
        }
    }

    queueChartUpdate(moduleId, channelId, newData) {
        if (!this.pendingChartUpdates[moduleId]) {
            this.pendingChartUpdates[moduleId] = {};
        }

        // Store the update with a timestamp to track timing
        this.pendingChartUpdates[moduleId][channelId] = {
            ...newData,
            updateTime: performance.now()
        };

        // Use a slightly more aggressive throttling for smoother updates
        const adaptiveDelay = this.getAdaptiveDelay(moduleId);

        this.throttleChartUpdate(moduleId, () => {
            this.applyBatchedChartUpdates(moduleId);
        }, adaptiveDelay);
    }

    throttleChartUpdate(moduleId, updateFn, delay = this.CHART_UPDATE_INTERVAL) {
        // Cancel any existing throttled update
        if (this.chartUpdateThrottlers[moduleId]) {
            clearTimeout(this.chartUpdateThrottlers[moduleId]);
        }

        // Use requestAnimationFrame for smoother updates
        this.chartUpdateThrottlers[moduleId] = setTimeout(() => {
            requestAnimationFrame(() => {
                updateFn();
                // Clear the throttler reference
                if (this.chartUpdateThrottlers[moduleId]) {
                    delete this.chartUpdateThrottlers[moduleId];
                }
            });
        }, delay);
    }

    applyBatchedChartUpdates(moduleId) {
        if (!this.pendingChartUpdates[moduleId]) return;

        const updates = this.pendingChartUpdates[moduleId];
        const separateChannels = this.separateChannels[moduleId];
        const activeType = this.activeTypeFilters[moduleId];

        // Initialize counter if needed
        if (!this.chartUpdateCounters[moduleId]) {
            this.chartUpdateCounters[moduleId] = 0;
        }
        this.chartUpdateCounters[moduleId]++;

        const shouldUpdateScale = this.chartUpdateCounters[moduleId] % this.SCALE_UPDATE_INTERVAL === 0;

        if (separateChannels) {
            // Use the original approach for separate channels (it worked fine)
            Object.keys(updates).forEach(channelId => {
                if (this.channelData[moduleId][channelId]?.type === activeType &&
                    this.channelCharts[moduleId][channelId]) {

                    const chart = this.channelCharts[moduleId][channelId];
                    const values = this.channelData[moduleId][channelId].values;

                    // Update data - simple assignment works fine for individual charts
                    chart.data.datasets[0].data = values;

                    // Only update scale periodically or if significant change
                    if (shouldUpdateScale) {
                        const minValue = Math.min(...values);
                        const maxValue = Math.max(...values);
                        const valueRange = maxValue - minValue;
                        const padding = valueRange * 0.2;

                        const currentMin = chart.options.scales.y.min;
                        const currentMax = chart.options.scales.y.max;

                        // Only update if significant change
                        if (this.shouldUpdateChartScale(currentMin, currentMax, minValue - padding, maxValue + padding)) {
                            chart.options.scales.y.min = minValue - padding;
                            chart.options.scales.y.max = maxValue + padding;
                            chart.update('resize'); // Use resize for scale changes
                        } else {
                            chart.update('none'); // Fast update without scale change
                        }
                    } else {
                        chart.update('none'); // Fast update
                    }
                }
            });
        } else if (this.moduleCharts[moduleId]) {
            // Use the NEW approach for combined chart (prevents stuttering)
            const chart = this.moduleCharts[moduleId];
            let needsScaleUpdate = false;
            let globalMin = Number.POSITIVE_INFINITY;
            let globalMax = Number.NEGATIVE_INFINITY;

            // Critical fix: Update ALL datasets at once, not individually
            const updatedDatasets = [];
            let hasValidData = false;

            // First pass: collect all data and create new datasets
            chart.data.datasets.forEach((dataset, index) => {
                const channel = dataset.label;
                if (this.channelData[moduleId][channel]?.type === activeType) {
                    const values = [...this.channelData[moduleId][channel].values]; // Create copy
                    updatedDatasets.push({
                        ...dataset,
                        data: values
                    });
                    hasValidData = true;

                    if (shouldUpdateScale) {
                        const min = Math.min(...values);
                        const max = Math.max(...values);
                        if (min < globalMin) globalMin = min;
                        if (max > globalMax) globalMax = max;
                    }
                } else {
                    // Keep existing dataset unchanged
                    updatedDatasets.push(dataset);
                }
            });

            if (hasValidData) {
                // Update all datasets at once - this prevents the "stuttering" effect
                chart.data.datasets = updatedDatasets;

                // Update scale if needed
                if (shouldUpdateScale && globalMin !== Number.POSITIVE_INFINITY) {
                    const valueRange = globalMax - globalMin;
                    const padding = valueRange * 0.2;
                    const newMin = globalMin - padding;
                    const newMax = globalMax + padding;

                    const currentMin = chart.options.scales.y.min;
                    const currentMax = chart.options.scales.y.max;

                    if (this.shouldUpdateChartScale(currentMin, currentMax, newMin, newMax)) {
                        chart.options.scales.y.min = newMin;
                        chart.options.scales.y.max = newMax;
                        needsScaleUpdate = true;
                    }
                }

                // Single update call instead of multiple - this fixes the visual glitch for combined mode
                if (needsScaleUpdate) {
                    chart.update('resize'); // Use 'resize' mode for scale changes
                } else {
                    chart.update('none'); // Fast update for data only
                }
            }
        }

        // Clear pending updates
        this.pendingChartUpdates[moduleId] = {};
    }

    // Add adaptive delay based on update frequency
    getAdaptiveDelay(moduleId) {
        const now = performance.now();
        if (!this.lastUpdateTime) this.lastUpdateTime = {};

        const timeSinceLastUpdate = now - (this.lastUpdateTime[moduleId] || 0);
        this.lastUpdateTime[moduleId] = now;

        // If updates are coming very frequently (< 16ms), slow down slightly
        if (timeSinceLastUpdate < 16) {
            return Math.max(16, this.CHART_UPDATE_INTERVAL); // Ensure at least 60fps
        }

        // For normal frequency, use standard interval
        return this.CHART_UPDATE_INTERVAL;
    }

    // Improve the scale update logic to be more stable
    shouldUpdateChartScale(currentMin, currentMax, newMin, newMax) {
        const threshold = 0.15; // Reduced threshold for more responsive scaling

        // Always update if new data is significantly outside current range
        const currentRange = currentMax - currentMin;
        const minDiff = Math.abs(newMin - currentMin) / currentRange;
        const maxDiff = Math.abs(newMax - currentMax) / currentRange;

        if (newMin < currentMin && minDiff > threshold) return true;
        if (newMax > currentMax && maxDiff > threshold) return true;

        // Update if current range is much larger than needed (zoom in)
        const newRange = newMax - newMin;
        if (newRange < currentRange * 0.6) return true; // If new range is less than 60% of current

        return false;
    }

    updateTheme(isDarkMode) {
        // Update all existing charts for the new theme
        Object.keys(this.moduleCharts).forEach(moduleId => {
            this.updateChartTheme(this.moduleCharts[moduleId], isDarkMode);
        });

        Object.keys(this.channelCharts).forEach(moduleId => {
            Object.values(this.channelCharts[moduleId]).forEach(chart => {
                this.updateChartTheme(chart, isDarkMode);
            });
        });
    }

    updateChartTheme(chart, isDarkMode) {
        if (!chart) return;

        chart.options.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(0, 0, 0, 0.7)' : 'rgba(255, 255, 255, 0.7)';
        chart.options.plugins.tooltip.titleColor = isDarkMode ? '#fff' : '#000';
        chart.options.plugins.tooltip.bodyColor = isDarkMode ? '#fff' : '#000';

        if (chart.options.scales.y) {
            chart.options.scales.y.ticks = {
                color: isDarkMode ? '#f0f0f0' : '#666'
            };
        }

        if (chart.options.scales.x) {
            chart.options.scales.x.ticks = {
                color: isDarkMode ? '#f0f0f0' : '#666'
            };
        }

        chart.update('none');
    }
}
