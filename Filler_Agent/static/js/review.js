document.addEventListener('DOMContentLoaded', () => {
    const btnExecute = document.getElementById('btnStartExecution');
    if (btnExecute) {
        btnExecute.addEventListener('click', async () => {
            const sessionId = btnExecute.dataset.sessionId;
            
            // Get selected fill mode radio
            const autoRadio = document.getElementById('modeAuto');
            const fillMode = autoRadio && autoRadio.checked ? 'auto' : 'manual';

            // Gather all question input values
            const questionUpdates = {};
            document.querySelectorAll('.editable-q-input').forEach(input => {
                const qId = input.dataset.questionId;
                questionUpdates[qId] = input.value.trim();
            });

            btnExecute.disabled = true;
            btnExecute.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Initializing Execution...`;

            try {
                const res = await apiRequest(`/api/review/${sessionId}`, 'POST', {
                    fill_mode: fillMode,
                    question_updates: questionUpdates
                });
                const msg = fillMode === 'manual' ? 'Redirecting to Google Form...' : 'Review confirmed! Redirecting to live execution...';
                showToast(msg, 'success');
                setTimeout(() => {
                    window.location.href = res.redirect_url;
                }, 800);
            } catch (err) {
                btnExecute.disabled = false;
                btnExecute.innerHTML = `<i class="fa-solid fa-bolt"></i> Launch Automation Agent`;
            }
        });
    }

    // Computer File Picker in Review Page
    document.querySelectorAll('.computer-file-picker').forEach(picker => {
        picker.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const targetId = picker.dataset.targetId;
            const linkId = picker.dataset.linkId;
            const targetInput = document.getElementById(targetId);
            const linkElem = document.getElementById(linkId);

            const formData = new FormData();
            formData.append('file', file);

            showToast(`Uploading ${file.name}...`, 'info');
            try {
                const res = await fetch('/api/upload-file', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.file_path && targetInput) {
                    targetInput.value = data.file_path;
                    if (linkElem) {
                        linkElem.href = '/' + data.file_path;
                        linkElem.classList.remove('d-none');
                    }
                    showToast(`File ${data.filename} uploaded & ready!`, 'success');
                }
            } catch (err) {
                showToast('File upload failed: ' + err.message, 'error');
            }
        });
    });

    // Modal Configuration for Options Edit
    let activeQuestionId = null;
    let activeFieldType = null;
    const modalOptionsContainer = document.getElementById('modalOptionsContainer');
    const modalQuestionText = document.getElementById('modalQuestionText');
    const btnSaveModalOptions = document.getElementById('btnSaveModalOptions');

    document.querySelectorAll('.edit-options-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            activeQuestionId = btn.dataset.questionId;
            activeFieldType = btn.dataset.fieldType;
            const questionText = btn.dataset.questionText;

            // Read options from hidden elements in HTML to prevent parsing issues
            const options = [];
            const wrapper = btn.closest('.input-group');
            if (wrapper) {
                const source = wrapper.querySelector('.question-options-source');
                if (source) {
                    source.querySelectorAll('.option-item').forEach(item => {
                        options.push(item.innerText.trim());
                    });
                }
            }

            modalQuestionText.innerText = questionText;
            modalOptionsContainer.innerHTML = '';

            // Get current selected answer
            const currentVal = document.getElementById(`q_input_${activeQuestionId}`).value.trim();
            const selectedSet = new Set(currentVal.split(',').map(s => s.trim().toLowerCase()));

            if (options.length === 0) {
                modalOptionsContainer.innerHTML = '<div class="text-muted small">No choices detected for this field.</div>';
                return;
            }

            options.forEach((opt, idx) => {
                const optClean = opt.trim();
                const optLower = optClean.toLowerCase();
                const containerDiv = document.createElement('div');
                containerDiv.className = 'form-check d-flex align-items-center gap-2 py-1';

                const input = document.createElement('input');
                input.className = 'form-check-input';
                input.value = optClean;
                input.id = `modal_opt_${idx}`;

                if (activeFieldType === 'checkbox') {
                    input.type = 'checkbox';
                    if (selectedSet.has(optLower)) {
                        input.checked = true;
                    }
                } else {
                    input.type = 'radio';
                    input.name = 'modal_radio_group';
                    if (currentVal.toLowerCase() === optLower) {
                        input.checked = true;
                    }
                }

                const label = document.createElement('label');
                label.className = 'form-check-label text-light fs-7 cursor-pointer flex-grow-1';
                label.htmlFor = `modal_opt_${idx}`;
                label.innerText = optClean;

                containerDiv.appendChild(input);
                containerDiv.appendChild(label);
                modalOptionsContainer.appendChild(containerDiv);
            });
        });
    });

    if (btnSaveModalOptions) {
        btnSaveModalOptions.addEventListener('click', () => {
            if (!activeQuestionId) return;

            const targetInput = document.getElementById(`q_input_${activeQuestionId}`);
            let finalValue = '';

            if (activeFieldType === 'checkbox') {
                const selected = [];
                modalOptionsContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
                    selected.push(cb.value);
                });
                finalValue = selected.join(', ');
            } else {
                const selectedRadio = modalOptionsContainer.querySelector('input[type="radio"]:checked');
                if (selectedRadio) {
                    finalValue = selectedRadio.value;
                }
            }

            if (targetInput) {
                targetInput.value = finalValue;
            }

            // Hide modal
            const modalEl = document.getElementById('optionsEditModal');
            const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }

});

