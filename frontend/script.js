const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// URL de ton backend (à changer une fois déployé)
const API_URL = "http://localhost:8000/query";;

function addMessage(text, side) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', side);
    msgDiv.innerText = text;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function askAI() {
    const question = userInput.value.trim();
    if (!question) return;

    addMessage(question, 'user');
    userInput.value = "";
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}?question=${encodeURIComponent(question)}`);
        const data = await response.json();
        
        if (data.reponse) {
            addMessage(data.reponse, 'bot');
        } else {
            addMessage("Désolé, j'ai rencontré une erreur.", 'bot');
        }
    } catch (error) {
        addMessage("Impossible de contacter le serveur.", 'bot');
    } finally {
        sendBtn.disabled = false;
    }
}

sendBtn.addEventListener('click', askAI);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') askAI();
});