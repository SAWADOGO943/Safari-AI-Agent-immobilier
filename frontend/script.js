const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// URL de ton backend Render
const API_URL = "https://safari-ai-agent-immobilier.onrender.com/query";

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
            const errorMsg = data.erreur || data.erreur_interne || "Erreur inconnue";
            addMessage(`Désolé : ${errorMsg}`, 'bot');
        }
    } catch (error) {
        console.error("Erreur détaillée:", error);
        addMessage("Impossible de contacter le serveur.", 'bot');
    } finally {
        sendBtn.disabled = false;
    }
} // <--- C'est cette accolade qui fermait mal la fonction !

// Écouteurs d'événements
sendBtn.addEventListener('click', () => {
    askAI();
});

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        askAI();
    }
});