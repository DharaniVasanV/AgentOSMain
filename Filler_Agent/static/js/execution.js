document.addEventListener('DOMContentLoaded', () => {
    const executionContainer = document.getElementById('executionTimeline');
    if (!executionContainer) return;

    const sessionId = executionContainer.dataset.sessionId;
    const progressBar = document.getElementById('executionProgressBar');
    const statusHeader = document.getElementById('executionStatusHeader');

    let isCompleted = false;
    let errorCount = 0;
    const MAX_ERRORS = 3;

    const eventSource = new EventSource(`/api/execution/${sessionId}/stream`);

    window.addEventListener('beforeunload', () => eventSource.close());
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden' && isCompleted) eventSource.close();
    });

    eventSource.onmessage = (event) => {
        errorCount = 0;
        try {
            const data = JSON.parse(event.data);
            if (data.ping) return;

            if (data.completed) {
                isCompleted = true;
                eventSource.close();
                showToast('Form execution completed successfully!', 'success');
                setTimeout(() => { window.location.href = data.redirect_url; }, 1000);
                return;
            }

            if (Array.isArray(data)) renderExecutionSteps(data);
        } catch (e) {
            console.error('SSE parse error:', e);
        }
    };

    eventSource.onerror = () => {
        if (isCompleted) { eventSource.close(); return; }
        errorCount++;
        if (errorCount >= MAX_ERRORS) {
            eventSource.close();
            if (statusHeader) statusHeader.textContent = 'Connection lost. Server may be offline.';
            showToast('Lost connection to server. Please refresh the page.', 'error');
        }
    };

    function renderExecutionSteps(steps) {
        let completedCount = 0;
        executionContainer.innerHTML = '';

        steps.forEach((step) => {
            if (step.status === 'success') completedCount++;

            const stepCard = document.createElement('div');
            stepCard.className = `step-card status-${step.status}`;

            let iconHtml = '<i class="fa-solid fa-clock"></i>';
            if (step.status === 'running') iconHtml = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
            if (step.status === 'success') iconHtml = '<i class="fa-solid fa-check"></i>';
            if (step.status === 'error') iconHtml = '<i class="fa-solid fa-xmark"></i>';

            stepCard.innerHTML = `
                <div class="step-icon">${iconHtml}</div>
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <h6 class="mb-0 font-weight-bold text-light">${step.step_name}</h6>
                    <small class="text-muted fs-7">${step.timestamp || ''}</small>
                </div>
                <p class="mb-0 text-secondary-custom small">${step.message}</p>
            `;
            executionContainer.appendChild(stepCard);
        });

        const percentage = steps.length ? Math.round((completedCount / steps.length) * 100) : 0;
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
        if (statusHeader) {
            statusHeader.textContent = percentage === 100 ? 'Execution Complete!' : `Live Agent Execution (${percentage}%)`;
        }
    }
});
