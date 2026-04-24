const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

const API_URL = "https://safari-ai-agent-immobilier.onrender.com/query";

// Gestion de l'ID utilisateur pour la mémoire ChromaDB
let userId = localStorage.getItem('safari_user_id');
if (!userId) {
    userId = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('safari_user_id', userId);
}

// Fonction pour afficher les messages (nom unique utilisé partout)
function appendMessage(side, text) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', side);
    msgDiv.innerText = text;
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function askAI() {
    const question = userInput.value.trim();
    if (!question) return;

    // 1. Afficher le message utilisateur
    appendMessage('user', question);
    userInput.value = '';
    
    // Désactiver le bouton pendant la requête
    sendBtn.disabled = true;

    try {
        // 2. Requête vers ton backend Python avec user_id
        const response = await fetch(`${API_URL}?question=${encodeURIComponent(question)}&user_id=${userId}`);
        
        if (!response.ok) throw new Error('Erreur réseau');

        const data = await response.json();
        
        // 3. Afficher la réponse de l'IA
        if (data.reponse) {
            appendMessage('assistant', data.reponse);
        } else {
            appendMessage('assistant', "Désolé, je rencontre une petite difficulté technique.");
        }
    } catch (error) {
        console.error("Erreur:", error);
        appendMessage('assistant', "Impossible de contacter le serveur Safari. Vérifie ta connexion.");
    } finally {
        // Réactiver le bouton
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// Écouteurs d'événements
sendBtn.addEventListener('click', askAI);

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        askAI();
    }
});