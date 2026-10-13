(() => {
  'use strict';
  const form = document.getElementById('convert-form');
  if (!form) return;
  const customer = document.getElementById('customer_name');
  const code = document.getElementById('customer_code');
  const input = document.getElementById('source-file');
  const zone = document.getElementById('drop-zone');
  const status = document.getElementById('file-status');
  const error = document.getElementById('file-error');
  const button = document.getElementById('convert-button');
  const buttonLabel = document.getElementById('button-label');
  const progress = document.getElementById('processing-status');
  const spinner = button.querySelector('.spinner');
  let submitting = false;

  function updateCustomer() {
    code.value = customer.selectedOptions[0]?.dataset.code || '';
  }
  function setFileError(message) {
    input.setCustomValidity(message);
    error.textContent = message;
    error.hidden = !message;
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
  }
  function validateFile() {
    const file = input.files[0];
    setFileError('');
    status.textContent = file ? `${file.name} · ${Math.max(1, Math.ceil(file.size / 1024)).toLocaleString()} KB` : 'No file selected';
    if (file && !/\.(csv|pdf)$/i.test(file.name)) {
      setFileError('Choose a CSV or PDF file. Other file types cannot be converted.');
    } else if (file && file.size === 0) {
      setFileError('This file is empty. Choose a CSV or PDF file that contains data.');
    }
    return input.validity.valid;
  }
  customer.addEventListener('change', updateCustomer);
  input.addEventListener('change', validateFile);
  ['dragenter', 'dragover'].forEach(event => zone.addEventListener(event, e => {
    e.preventDefault();
    if (!submitting) zone.classList.add('drag-over');
  }));
  ['dragleave', 'drop'].forEach(event => zone.addEventListener(event, () => zone.classList.remove('drag-over')));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    if (submitting) return;
    if (e.dataTransfer.files.length !== 1) {
      setFileError('Choose one file at a time. Drop a single CSV or PDF file, or use the file chooser.');
      return;
    }
    try {
      input.files = e.dataTransfer.files;
      validateFile();
    } catch (_) {
      setFileError('Please use the file chooser to select your CSV or PDF file.');
    }
  });
  form.addEventListener('submit', e => {
    if (submitting) { e.preventDefault(); return; }
    updateCustomer();
    if (!validateFile() || !form.checkValidity()) {
      e.preventDefault();
      form.reportValidity();
      return;
    }
    submitting = true;
    button.disabled = true;
    spinner.hidden = false;
    buttonLabel.textContent = 'Converting…';
    progress.textContent = 'Processing your file. Please keep this page open.';
    form.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    button.disabled = false;
    spinner.hidden = true;
    buttonLabel.textContent = 'Convert file';
    progress.textContent = 'Ready when you are.';
    form.removeAttribute('aria-busy');
    updateCustomer();
    validateFile();
  });
  updateCustomer();
})();
