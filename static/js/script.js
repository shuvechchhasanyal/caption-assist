// --- State Management ---
let selectedCaptionIndex = null;
let generatedOptions = [];
let currentThreadId = null; 

// --- UI Elements ---
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const imagePreview = document.getElementById('image-preview');
const uploadText = document.getElementById('upload-text');

// --- File Upload Logic (Click + Drag & Drop) ---
// 1. Handle clicking to upload
dropzone.addEventListener('click', () => fileInput.click());

// 2. Prevent default browser drag-and-drop behaviors
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// 3. Highlight drop area when dragging a file over it
['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropzone.style.borderColor = 'var(--accent)';
    dropzone.style.background = 'rgba(139, 92, 246, 0.1)';
}

function unhighlight(e) {
    dropzone.style.borderColor = 'rgba(255,255,255,0.15)';
    dropzone.style.background = 'rgba(15, 23, 42, 0.4)';
}

// 4. Handle the actual drop
dropzone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;

    if (files.length > 0) {
        fileInput.files = files; // Sync the dropped file to the hidden input
        processFile(files[0]);
    }
}

// 5. Handle standard file selection via click
fileInput.addEventListener('change', function(e) {
    if (this.files.length > 0) {
        processFile(this.files[0]);
    }
});

// 6. The shared logic to preview the image
function processFile(file) {
    if (file && (file.type === "image/jpeg" || file.type === "image/jpg" || file.type === "image/png")) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            uploadText.style.display = 'none';
            dropzone.style.padding = '1rem';
        };
        reader.readAsDataURL(file);
    } else {
        alert("Please upload a valid image file (.jpg, .jpeg, .png).");
        fileInput.value = "";
    }
}

// --- Navigation Functions ---
function showStep(stepId) {
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    document.getElementById(stepId).classList.add('active');
}

function showLoading(elementId, text) {
    const el = document.getElementById(elementId);
    el.innerHTML = `<div class="spinner"></div>${text}`;
    el.style.display = 'block';
}

function hideLoading(elementId) {
    document.getElementById(elementId).style.display = 'none';
}

// --- Action: Draft Captions (API CALL) ---
async function startDrafting() {
    const file = fileInput.files[0];
    const description = document.getElementById('description').value;

    if (!file) { alert("Please upload an image first."); return; }
    
    showLoading('loading-draft', 'Analyzing image and drafting captions...');
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("description", description);

    try {
        const response = await fetch('/api/draft', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.status === "success") {
            currentThreadId = data.thread_id;
            generatedOptions = data.captions;
            renderCaptions();
            showStep('step-review');
        } else {
            alert("Error drafting captions: " + data.error);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to connect to the server.");
    } finally {
        hideLoading('loading-draft');
    }
}

// --- TEXT CLEANER (Fallback in case the LLM hallucinates labels) ---
function cleanCaptionText(rawText) {
    return rawText.replace(/^Caption \d+.*?(\n|$)/im, '').trim();
}

// --- Action: Render Captions with Inline Copy Buttons ---
function renderCaptions() {
    const container = document.getElementById('caption-list');
    container.innerHTML = '';
    selectedCaptionIndex = null;

    // Map platforms to their FontAwesome icons
    const iconMap = {
        "LinkedIn": '<i class="fa-brands fa-linkedin"></i>',
        "Instagram": '<i class="fa-brands fa-instagram"></i>',
        "WhatsApp": '<i class="fa-brands fa-whatsapp"></i>'
    };

    generatedOptions.forEach((item, index) => {
        // 1. Create a wrapper for the whole section
        const wrapper = document.createElement('div');
        wrapper.className = 'caption-wrapper';

        // 2. Create the label that sits ABOVE the card
        const label = document.createElement('div');
        label.className = 'platform-label';
        const iconHtml = iconMap[item.platform] || '<i class="fa-solid fa-pen"></i>';
        label.innerHTML = `${iconHtml} ${item.platform}`;

        // 3. Create the actual card box
        const div = document.createElement('div');
        div.className = 'caption-card';
        
        // 4. Create the Text Content
        const textSpan = document.createElement('div');
        textSpan.className = 'caption-text-content';
        textSpan.innerText = cleanCaptionText(item.text); 
        
        // 5. Create the inline copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'icon-copy-btn';
        copyBtn.innerText = 'Copy';
        
        copyBtn.onclick = (e) => {
            e.stopPropagation(); 
            copySpecificText(textSpan.innerText, copyBtn);
        };
        
        // Assemble everything
        div.appendChild(textSpan);
        div.appendChild(copyBtn);
        
        div.onclick = () => selectCaption(index, div);
        
        wrapper.appendChild(label);
        wrapper.appendChild(div);
        
        container.appendChild(wrapper);
    });
}

function selectCaption(index, element) {
    selectedCaptionIndex = index;
    document.querySelectorAll('.caption-card').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
}

// --- Action: Copy specific text from a card ---
function copySpecificText(textToCopy, btnElement) {
    navigator.clipboard.writeText(textToCopy).then(() => {
        const originalText = btnElement.innerText;
        btnElement.innerText = "Copied!";
        btnElement.classList.add('copied');
        
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
        alert("Failed to copy to clipboard.");
    });
}

async function sendReview(feedbackAction, customFeedback = "") {
    if (!currentThreadId) return;

    // Extract ONLY the text to send back to the AI for refinement
    let baseCaption = "";
    if (selectedCaptionIndex !== null) {
        baseCaption = generatedOptions[selectedCaptionIndex].text; 
    }
    
    try {
        const response = await fetch('/api/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: currentThreadId,
                feedback: feedbackAction === "refine" ? customFeedback : feedbackAction,
                selected_caption: baseCaption
            })
        });

        const data = await response.json();

        if (data.status === "completed") {
            document.getElementById('final-caption-text').innerText = cleanCaptionText(data.final_caption);
            showStep('step-result');
        } else if (data.status === "drafted") {
            generatedOptions = data.captions;
            renderCaptions();
            showStep('step-review');
        } else {
            alert("Error: " + data.error);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to send review to the server.");
    }
}

function submitFeedback() {
    let feedbackText = document.getElementById('feedback').value;
    
    if (selectedCaptionIndex === null && feedbackText.trim() === "") {
        alert("Please select a caption or provide instructions.");
        return;
    }

    showLoading('loading-refine', 'Polishing your caption...');
    
    sendReview("refine", feedbackText).finally(() => {
        hideLoading('loading-refine');
    });
}

function retryDrafting() {
    document.getElementById('feedback').value = '';
    showLoading('loading-refine', 'Starting over...');
    
    sendReview("retry").finally(() => {
        hideLoading('loading-refine');
    });
}

function stopProcess() {
    if(confirm("Are you sure you want to exit?")) {
        sendReview("exit").then(() => {
            resetApp();
        });
    }
}

function resetApp() {
    fileInput.value = "";
    imagePreview.style.display = "none";
    imagePreview.src = "";
    uploadText.style.display = "block";
    dropzone.style.padding = '2.5rem 2rem';
    document.getElementById('description').value = "";
    document.getElementById('feedback').value = "";
    currentThreadId = null;
    showStep('step-upload');
}