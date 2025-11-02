// static/script.js (Final Fixed Logic)

document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imageInput = document.getElementById('image-input');
    const imagePreviewArea = document.getElementById('image-preview-area');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image-btn');
    
    // NEW Elements for Clear Chat
    const newChatBtn = document.getElementById('new-chat-btn');
    const customModal = document.getElementById('custom-modal');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');


    let base64Image = null; // Variable to hold the base64 image data

    // Function to scroll to the bottom
    const scrollToBottom = () => {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    };
    
    setTimeout(scrollToBottom, 100); 


    // --- Image Upload/Remove Logic (No Changes) ---
    imageUploadBtn.addEventListener('click', () => { imageInput.click(); });

    imageInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                base64Image = e.target.result;
                imagePreview.src = base64Image;
                imagePreviewArea.style.display = 'flex';
                imageInput.value = '';
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn.addEventListener('click', () => {
        base64Image = null;
        imagePreview.src = '';
        imagePreviewArea.style.display = 'none';
        imageInput.value = '';
    });


    // --- Send Message Handler (No Changes) ---
    const sendMessage = async () => {
        const message = userInput.value.trim();
        
        if (!message && !base64Image) return;

        const userMsgDiv = document.createElement('div');
        userMsgDiv.className = 'message user-message';
        
        if (base64Image) {
            userMsgDiv.innerHTML = `<i class="fas fa-image" style="margin-right: 5px;"></i> ${message || 'Image Analysis Request'}`;
        } else {
            userMsgDiv.textContent = message;
        }

        chatWindow.appendChild(userMsgDiv); 
        
        userInput.value = '';
        imagePreviewArea.style.display = 'none';
        
        const aiMsgDiv = document.createElement('div');
        aiMsgDiv.className = 'message ai-message';
        aiMsgDiv.textContent = 'Radiant is thinking...'; 
        
        chatWindow.appendChild(aiMsgDiv); 
        
        scrollToBottom(); 
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ message: message, image: base64Image }),
            });

            const data = await response.json();
            aiMsgDiv.textContent = data.response;

        } catch (error) {
            console.error('Chat API Error:', error);
            aiMsgDiv.textContent = 'Sorry, Ya Sidra! Connection lost, please inform Mohammad.';
        } finally {
            base64Image = null;
            scrollToBottom(); 
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); 
            sendMessage();
        }
    });
    
    // --- NEW: Custom Modal Logic ---
    const showModal = () => {
        customModal.style.display = 'block';
    }

    const hideModal = () => {
        customModal.style.display = 'none';
    }

    // Modal background click to close
    window.onclick = function(event) {
        if (event.target == customModal) {
            hideModal();
        }
    }
    
    // Cancel button handler
    modalCancelBtn.addEventListener('click', hideModal);

    // New Chat Button click shows the modal
    newChatBtn.addEventListener('click', showModal);

    // Modal Confirm Handler
    modalConfirmBtn.addEventListener('click', async () => {
        hideModal(); // Modal hide karein
        
        try {
            // API call to clear history
            const response = await fetch('/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
            });

            if (response.ok) {
                // History clear hone ke baad page reload karo
                window.location.reload(); 
            } else {
                console.error('Failed to clear chat history.');
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
        }
    });
    // --- END NEW LOGIC ---
});