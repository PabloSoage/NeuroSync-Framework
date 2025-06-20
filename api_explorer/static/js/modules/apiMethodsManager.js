export class APIMethodsManager {
    constructor() {
        // Manager for API method execution
        console.log('APIMethodsManager constructor called');
        this.setupEventListeners();
    }

    setupEventListeners() {
        console.log('Setting up event listeners');

        // Setup template loading with more specific event delegation
        document.addEventListener('click', (e) => {
            console.log('Click event detected:', e.target);

            if (e.target.classList.contains('load-template-btn')) {
                console.log('Load template button clicked');
                e.preventDefault();
                e.stopPropagation();
                this.loadTemplate(e.target);
            } else if (e.target.classList.contains('format-json-btn')) {
                console.log('Format JSON button clicked');
                e.preventDefault();
                e.stopPropagation();
                this.formatJson(e.target);
            } else if (e.target.classList.contains('validate-json-btn')) {
                console.log('Validate JSON button clicked');
                e.preventDefault();
                e.stopPropagation();
                this.validateJson(e.target);
            }
        });

        // Setup change listeners for template sources
        document.addEventListener('change', (e) => {
            if (e.target.tagName === 'SELECT') {
                console.log('Select change detected:', e.target.id, 'value:', e.target.value);
                this.handleSelectChange(e.target);
            }
        });

        console.log('Event listeners setup complete');
    }

    handleSelectChange(selectElement) {
        // Check if this select is a template source for any json_template fields
        const moduleMethodId = selectElement.id.split('_param_')[0];
        const paramName = selectElement.id.split('_param_')[1];

        console.log(`Select changed: ${selectElement.id}, value: ${selectElement.value}`);

        // Find any json_template fields that use this as template source
        const templateFields = document.querySelectorAll(`[data-template-source="${paramName}"]`);
        templateFields.forEach(field => {
            if (field.dataset.moduleId && field.dataset.methodId) {
                const fieldModuleMethodId = `${field.dataset.moduleId}-${field.dataset.methodId}`;
                if (fieldModuleMethodId === moduleMethodId) {
                    console.log(`Auto-loading template for field: ${field.id}`);
                    // Auto-load template when source changes
                    this.loadTemplateForField(field, selectElement.value);
                }
            }
        });
    }

    async loadTemplate(button) {
        console.log('loadTemplate called with button:', button);

        const targetId = button.dataset.target;
        const templateSource = button.dataset.templateSource;
        const moduleId = button.dataset.moduleId;
        const methodId = button.dataset.methodId;

        console.log('Template loading params:', {
            targetId,
            templateSource,
            moduleId,
            methodId
        });

        try {
            // Get the source value
            const sourceElement = document.getElementById(`${moduleId}-${methodId}_param_${templateSource}`);
            if (!sourceElement) {
                console.error('Template source element not found:', `${moduleId}-${methodId}_param_${templateSource}`);
                return;
            }

            const sourceValue = sourceElement.value;
            console.log('Source value:', sourceValue);

            await this.loadTemplateForField(document.getElementById(targetId), sourceValue);

        } catch (error) {
            console.error('Error loading template:', error);
        }
    }

    async loadTemplateForField(targetField, sourceValue) {
        try {
            const templateSource = targetField.dataset.templateSource;
            const moduleId = targetField.dataset.moduleId;
            const methodId = targetField.dataset.methodId;

            console.log(`Loading template for ${templateSource} with value: ${sourceValue}`);

            let template = {};

            // Handle different template sources
            if (templateSource === 'board_id') {
                template = await this.getBoardTemplate(sourceValue, moduleId);
            } else if (templateSource === 'streamer_type') {
                template = await this.getStreamerTemplate(sourceValue, moduleId);
            } else {
                console.warn(`Unknown template source: ${templateSource}`);
                return;
            }

            if (Object.keys(template).length > 0) {
                let formattedTemplate = this.formatTemplateWithComments(template);
                targetField.value = JSON.stringify(formattedTemplate, null, 2);
                console.log('Template loaded successfully');
            } else {
                console.warn('No template data received');
                targetField.value = JSON.stringify({}, null, 2);
            }
        } catch (error) {
            console.error('Error loading template for field:', error);
            targetField.value = JSON.stringify({}, null, 2);
        }
    }

    formatTemplateWithComments(template) {
        const result = {};
        const comments = [];

        for (const [key, value] of Object.entries(template)) {
            if (key.endsWith('_REQUIRED') || key.endsWith('_DESCRIPTION')) {
                // Skip metadata fields
                continue;
            }

            const requiredKey = `${key}_REQUIRED`;
            const descriptionKey = `${key}_DESCRIPTION`;

            if (template[requiredKey]) {
                comments.push(`${key}: REQUIRED - ${template[descriptionKey] || 'Required field'}`);
            }

            result[key] = value;
        }

        // Add comments at the top
        if (comments.length > 0) {
            result['_COMMENTS'] = [
                'Required fields for this board:',
                ...comments,
                'Remove this _COMMENTS field before executing'
            ];
        }

        return result;
    }

    async getBoardTemplate(boardId, moduleId = null) {
        try {
            // Auto-detect module if not provided
            if (!moduleId) {
                moduleId = 'eeg_processor_control';
                const templateFields = document.querySelectorAll('[data-template-source="board_id"]');
                if (templateFields.length > 0) {
                    const field = templateFields[0];
                    const moduleFromField = field.dataset.moduleId;
                    if (moduleFromField) {
                        moduleId = moduleFromField;
                    }
                }
            }

            const url = `/api/${moduleId}/get_board_template?board_id=${boardId}`;
            console.log('Fetching board template from:', url);

            const response = await fetch(url);
            if (!response.ok) {
                console.error('API response not OK:', response.status, response.statusText);
                return {};
            }

            const data = await response.json();
            console.log('Board template response:', data);

            if (data && data.template) {
                return this.convertTemplateFormat(data.template);
            }

            console.warn('No template data in response');
            return {};
        } catch (error) {
            console.error('Error fetching board template:', error);
            return {};
        }
    }

    async getStreamerTemplate(streamerType, moduleId = null) {
        try {
            // Auto-detect module if not provided
            if (!moduleId) {
                moduleId = 'eeg_processor_control';
                const templateFields = document.querySelectorAll('[data-template-source="streamer_type"]');
                if (templateFields.length > 0) {
                    const field = templateFields[0];
                    const moduleFromField = field.dataset.moduleId;
                    if (moduleFromField) {
                        moduleId = moduleFromField;
                    }
                }
            }

            const url = `/api/${moduleId}/get_streamer_template?streamer_type=${streamerType}`;
            console.log('Fetching streamer template from:', url);

            const response = await fetch(url);
            if (!response.ok) {
                console.error('API response not OK:', response.status, response.statusText);
                return {};
            }

            const data = await response.json();
            console.log('Streamer template response:', data);

            if (data && data.template) {
                return this.convertTemplateFormat(data.template);
            }

            console.warn('No template data in response');
            return {};
        } catch (error) {
            console.error('Error fetching streamer template:', error);
            return {};
        }
    }

    convertTemplateFormat(templateData) {
        // Convert the enhanced template to a simple object for JSON display
        const template = {};

        for (const [key, fieldInfo] of Object.entries(templateData)) {
            if (typeof fieldInfo === 'object' && fieldInfo.hasOwnProperty('value')) {
                // Enhanced template format with metadata
                template[key] = fieldInfo.value;

                // Add comment for required fields
                if (fieldInfo.required) {
                    template[`${key}_REQUIRED`] = true;
                    template[`${key}_DESCRIPTION`] = fieldInfo.description || '';
                }
            } else {
                // Simple template format (fallback) or _COMMENTS array
                template[key] = fieldInfo;
            }
        }

        return template;
    }

    formatJson(button) {
        console.log('formatJson called with button:', button);

        const targetId = button.dataset.target;
        const textarea = document.getElementById(targetId);

        if (!textarea) {
            console.error('Target textarea not found:', targetId);
            return;
        }

        try {
            const jsonObj = JSON.parse(textarea.value);
            textarea.value = JSON.stringify(jsonObj, null, 2);
            console.log('JSON formatted successfully');
        } catch (error) {
            console.error('Invalid JSON:', error);
            alert('Invalid JSON: ' + error.message);
        }
    }

    toggleMethod(moduleId, methodId) {
        const methodBody = document.getElementById(`${moduleId}-${methodId}`);
        methodBody.classList.toggle('active');
    }

    async executeMethod(moduleId, methodId) {
        const responseElem = document.getElementById(`${moduleId}-${methodId}_response`);
        responseElem.textContent = "Loading...";

        try {
            const { url, options } = this.prepareRequest(moduleId, methodId);
            const response = await fetch(url, options);
            const data = await response.json();

            responseElem.textContent = JSON.stringify(data, null, 2);

        } catch (error) {
            responseElem.textContent = `Error: ${error.message}`;
        }
    }

    prepareRequest(moduleId, methodId) {
        const paramElements = document.querySelectorAll(`[id^="${moduleId}-${methodId}_param_"]`);
        let url = `/api/${moduleId}/${methodId}`;
        let options = { method: 'GET' };
        let body = null;
        let queryParams = [];

        const methodType = document.getElementById(`${moduleId}-${methodId}_type`);
        if (methodType && methodType.value === 'POST') {
            options.method = 'POST';
            body = {};
        }

        paramElements.forEach(param => {
            const paramName = param.id.replace(`${moduleId}-${methodId}_param_`, '');
            let paramValue;

            // Handle different input types
            if (param.tagName === 'SELECT') {
                paramValue = param.value;
            } else if (param.classList.contains('json-template-textarea')) {
                // Parse JSON for template fields
                try {
                    const rawValue = param.value || '{}';
                    let jsonObj = JSON.parse(rawValue.trim());

                    // Clean up metadata fields (anything starting with _)
                    const cleanedObj = {};
                    for (const [key, value] of Object.entries(jsonObj)) {
                        if (!key.startsWith('_')) {
                            cleanedObj[key] = value;
                        }
                    }

                    paramValue = cleanedObj;
                    console.log('Cleaned JSON params:', paramValue);
                } catch (error) {
                    console.error(`Invalid JSON in ${paramName}:`, error);
                    paramValue = {};
                }
            } else if (param.type === 'range') {
                // Handle range inputs (sliders) - ensure they're sent as numbers
                paramValue = parseFloat(param.value);
                console.log(`Range input ${paramName}: ${paramValue} (type: ${typeof paramValue})`);
            } else if (param.type === 'number') {
                // Handle number inputs - ensure they're sent as numbers
                paramValue = parseFloat(param.value);
                console.log(`Number input ${paramName}: ${paramValue} (type: ${typeof paramValue})`);
            } else {
                // Handle regular text inputs - ensure value exists before trim
                const rawValue = param.value || '';
                paramValue = rawValue.trim();
            }

            // Special validation for bandpass filter ranges
            if (methodId === 'apply_filters') {
                if (paramName === 'bandpass_low' || paramName === 'bandpass_high') {
                    // Ensure it's a number
                    paramValue = parseFloat(paramValue);

                    // Validate bandpass range
                    if (paramName === 'bandpass_low') {
                        const highElement = document.getElementById(`${moduleId}-${methodId}_param_bandpass_high`);
                        if (highElement && paramValue >= parseFloat(highElement.value)) {
                            alert('Bandpass low frequency must be less than high frequency');
                            return { url, options: { ...options, error: 'Invalid frequency range' } };
                        }
                    }
                }
            }

            // Only add non-empty values
            if (paramValue !== null && paramValue !== undefined && paramValue !== '') {
                // For objects, check if they have any actual content
                if (typeof paramValue === 'object') {
                    if (Object.keys(paramValue).length > 0) {
                        if (options.method === 'GET') {
                            queryParams.push(`${paramName}=${encodeURIComponent(JSON.stringify(paramValue))}`);
                        } else {
                            body[paramName] = paramValue;
                        }
                    }
                } else {
                    // For primitive values (including numbers)
                    if (options.method === 'GET') {
                        // For GET requests, convert numbers to strings in URL
                        queryParams.push(`${paramName}=${encodeURIComponent(paramValue)}`);
                    } else {
                        // For POST requests, keep the correct type
                        body[paramName] = paramValue;
                    }
                }
            }
        });

        if (queryParams.length > 0 && options.method === 'GET') {
            url += `?${queryParams.join('&')}`;
        }

        if (options.method === 'POST' && body) {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(body);
            console.log('POST request body:', options.body);
        }

        return { url, options };
    }

    validateJson(button) {
        console.log('validateJson called with button:', button);

        const targetId = button.dataset.target;
        const textarea = document.getElementById(targetId);

        if (!textarea) {
            console.error('Target textarea not found:', targetId);
            return;
        }

        const helpContainer = document.getElementById(targetId + '_help');
        const paramHelp = textarea.closest('.json-template-container').querySelector('.param-help');

        try {
            const jsonObj = JSON.parse(textarea.value);
            console.log('JSON is valid:', jsonObj);

            // Check for required fields if this is a board template
            const templateSource = textarea.dataset.templateSource;
            if (templateSource === 'board_id') {
                this.validateBoardTemplate(jsonObj, helpContainer, paramHelp);
            }

            // Show success message
            this.showValidationMessage(button, 'Valid JSON', 'success');

        } catch (error) {
            console.error('JSON validation failed:', error);
            this.showValidationMessage(button, 'Invalid JSON: ' + error.message, 'error');

            // Show help for JSON format
            if (helpContainer) {
                helpContainer.innerHTML = '<li>Fix JSON syntax errors first</li>';
                if (paramHelp) paramHelp.style.display = 'block';
            }
        }
    }

    async validateBoardTemplate(jsonObj, helpContainer, paramHelp) {
        try {
            // Get board ID from the form
            const templateFields = document.querySelectorAll('[data-template-source="board_id"]');
            if (templateFields.length === 0) return;

            const field = templateFields[0];
            const moduleId = field.dataset.moduleId;
            const methodId = field.dataset.methodId;

            if (!moduleId || !methodId) return;

            const boardIdElement = document.getElementById(`${moduleId}-${methodId}_param_board_id`);
            if (!boardIdElement) return;

            const boardId = boardIdElement.value;

            // Use the correct module ID for the API call
            const url = `/api/${moduleId}/get_board_requirements?board_id=${boardId}`;
            const response = await fetch(url);

            if (!response.ok) {
                console.error('Board requirements API response not OK:', response.status);
                return;
            }

            const data = await response.json();

            if (data && data.requirements) {
                const requirements = data.requirements;
                const issues = [];
                const suggestions = [];

                // Check required fields
                for (const [field, required] of Object.entries(requirements)) {
                    if (required && (!jsonObj.hasOwnProperty(field) || jsonObj[field] === "")) {
                        issues.push(`Missing required field: ${field}`);
                    }
                }

                // Check for unnecessary fields for this board
                for (const field of Object.keys(jsonObj)) {
                    if (field.startsWith('_')) continue; // Skip metadata fields
                    if (!requirements.hasOwnProperty(field)) {
                        suggestions.push(`Field '${field}' is not used by this board type`);
                    }
                }

                // Update help display
                if (helpContainer) {
                    helpContainer.innerHTML = '';

                    if (issues.length > 0) {
                        issues.forEach(issue => {
                            helpContainer.innerHTML += `<li style="color: #dc3545;">${issue}</li>`;
                        });
                    }

                    if (suggestions.length > 0) {
                        suggestions.forEach(suggestion => {
                            helpContainer.innerHTML += `<li style="color: #ffc107;">${suggestion}</li>`;
                        });
                    }

                    if (issues.length === 0 && suggestions.length === 0) {
                        helpContainer.innerHTML = '<li style="color: #28a745;">All required fields present</li>';
                    }

                    paramHelp.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('Error validating board template:', error);
        }
    }

    showValidationMessage(button, message, type) {
        const originalText = button.textContent;
        const originalClass = button.className;

        // Update button appearance
        button.textContent = message;
        button.className = button.className.replace(/btn-\w+/, type === 'success' ? 'btn-success' : 'btn-danger');

        // Reset after 2 seconds
        setTimeout(() => {
            button.textContent = originalText;
            button.className = originalClass;
        }, 2000);
    }

    // Add a test method to verify the instance is working
    testButtonFunctionality() {
        console.log('Testing button functionality...');

        // Find buttons
        const loadBtns = document.querySelectorAll('.load-template-btn');
        const formatBtns = document.querySelectorAll('.format-json-btn');
        const validateBtns = document.querySelectorAll('.validate-json-btn');

        console.log('Found buttons:', {
            loadBtns: loadBtns.length,
            formatBtns: formatBtns.length,
            validateBtns: validateBtns.length
        });

        // Test first load button if available
        if (loadBtns.length > 0) {
            console.log('Testing first load button...');
            this.loadTemplate(loadBtns[0]);
        }

        // Test first format button if available
        if (formatBtns.length > 0) {
            console.log('Testing first format button...');
            this.formatJson(formatBtns[0]);
        }

        return {
            loadBtns: loadBtns.length,
            formatBtns: formatBtns.length,
            validateBtns: validateBtns.length
        };
    }
}
