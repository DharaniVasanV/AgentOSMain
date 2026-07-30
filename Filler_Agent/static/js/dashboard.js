document.addEventListener('DOMContentLoaded', () => {
    const formProcess = document.getElementById('startFormProcess');
    const formUrlInput = document.getElementById('formUrlInput');
    const btnStart = document.getElementById('btnStartProcess');
    const startSpinner = document.getElementById('startSpinner');
    const btnText = document.getElementById('btnStartText');

    if (formProcess) {
        formProcess.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = formUrlInput.value.trim();
            if (!url) {
                showToast('Please enter a valid Google Form URL', 'error');
                return;
            }

            // Show loading state
            btnStart.disabled = true;
            startSpinner.classList.remove('d-none');
            btnText.textContent = 'Analyzing Form...';

            try {
                const res = await apiRequest('/api/start-form', 'POST', { form_url: url });
                showToast('Form analyzed successfully! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = res.redirect_url;
                }, 1000);
            } catch (err) {
                btnStart.disabled = false;
                startSpinner.classList.add('d-none');
                btnText.textContent = 'Start Process';
                showToast(err.message || 'Failed to analyze form. Check the URL and try again.', 'error');
            }
        });
    }

    // Profile CRUD Modal logic
    const saveProfileForm = document.getElementById('saveProfileForm');
    const profFileInput = document.getElementById('profFileInput');

    if (profFileInput) {
        profFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);

            showToast(`Uploading ${file.name}...`, 'info');
            try {
                const res = await fetch('/api/upload-file', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.file_path) {
                    document.getElementById('profValInput').value = data.file_path;
                    if (!document.getElementById('profKeyInput').value) {
                        document.getElementById('profKeyInput').value = 'Resume / Document';
                    }
                    if (!document.getElementById('profCatInput').value) {
                        document.getElementById('profCatInput').value = 'Documents';
                    }
                    showToast(`Uploaded ${data.filename} to profile!`, 'success');
                }
            } catch (err) {
                showToast('File upload failed: ' + err.message, 'error');
            }
        });
    }

    if (saveProfileForm) {
        saveProfileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const key = document.getElementById('profKeyInput').value.trim();
            const val = document.getElementById('profValInput').value.trim();
            const cat = document.getElementById('profCatInput').value.trim();

            if (!key || !val) {
                showToast('Please fill key and value fields', 'error');
                return;
            }

            try {
                await apiRequest('/api/profiles', 'POST', {
                    field_key: key,
                    field_value: val,
                    category: cat || 'General'
                });
                showToast('Profile field saved successfully!', 'success');
                setTimeout(() => window.location.reload(), 800);
            } catch (err) {
                // Handled in apiRequest
            }
        });
    }
});


async function deleteProfileField(id) {
    if (!confirm('Are you sure you want to remove this profile item?')) return;
    try {
        await apiRequest(`/api/profiles/${id}`, 'DELETE');
        showToast('Profile item removed', 'success');
        setTimeout(() => window.location.reload(), 600);
    } catch (err) {}
}
