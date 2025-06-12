export class APIMethodsManager {
    constructor() {
        // Manager for API method execution
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
            const paramValue = param.value.trim();

            if (paramValue) {
                if (options.method === 'GET') {
                    queryParams.push(`${paramName}=${encodeURIComponent(paramValue)}`);
                } else {
                    body[paramName] = paramValue;
                }
            }
        });

        if (queryParams.length > 0 && options.method === 'GET') {
            url += `?${queryParams.join('&')}`;
        }

        if (options.method === 'POST' && body) {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(body);
        }

        return { url, options };
    }
}
