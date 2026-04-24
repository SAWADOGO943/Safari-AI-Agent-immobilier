import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Les imports spécifiques pour chaque IA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_community.document_loaders import PyPDFLoader
from google.api_core import exceptions as google_exceptions

# 1. Chargement des clés API
load_dotenv()
google_key = os.getenv("GOOGLE_API_KEY")
mistral_key = os.getenv("MISTRAL_API_KEY")

app = FastAPI()

# Configuration du CORS pour autoriser Vercel


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autorise toutes les sources (Vercel, Local, Mobile)
    allow_credentials=False,  # Important : mettre à False si origins est "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Initialisation des modèles (on les prépare une seule fois)
llm_25 = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_key)
llm_15 = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key)
# On n'initialise Mistral que si la clé est présente pour éviter de faire planter le démarrage
llm_mistral = None
if mistral_key:
    llm_mistral = ChatMistralAI(
        model="mistral-small-latest", mistral_api_key=mistral_key
    )


# 3. Chargement des documents
def charger_tous_les_documents():
    tous_les_docs = []
    dossier = "DOCUMENTS"
    if not os.path.exists(dossier):
        print(f"❌ Dossier {dossier} absent.")
        return []
    for fichier in os.listdir(dossier):
        if fichier.endswith(".pdf"):
            try:
                loader = PyPDFLoader(os.path.join(dossier, fichier))
                tous_les_docs.extend(loader.load())
                print(f"✅ Document chargé : {fichier}")
            except Exception as e:
                print(f"⚠️ Erreur chargement {fichier} : {e}")
    return tous_les_docs


docs_globaux = charger_tous_les_documents()

# 2. Initialisation des modèles
llm_25 = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", google_api_key=google_key
)  # Note: Gemini 2.0 est le nom actuel
llm_15 = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key)


# 3. Fonction unique de chargement
def charger_tous_les_documents():
    tous_les_docs = []
    dossier = "DOCUMENTS"
    if not os.path.exists(dossier):
        print(f"❌ Dossier {dossier} absent.")
        return []
    for fichier in os.listdir(dossier):
        if fichier.endswith(".pdf"):
            try:
                loader = PyPDFLoader(os.path.join(dossier, fichier))
                tous_les_docs.extend(loader.load())
                print(f"✅ Document chargé : {fichier}")
            except Exception as e:
                print(f"⚠️ Erreur chargement {fichier} : {e}")
    return tous_les_docs


# 4. Configuration ChromaDB
embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-001")
persist_directory = "./db_safari"

# INITIALISATION DE LA BASE (Le coeur du système)
if not os.path.exists(persist_directory):
    print("📦 Première utilisation : Indexation des documents dans ChromaDB...")
    docs = charger_tous_les_documents()  # On utilise la fonction qui marche !

    if not docs:
        print("❌ Erreur : Aucun document PDF trouvé.")
        # On crée une base vide pour éviter les erreurs au lancement
        vector_db = Chroma(
            persist_directory=persist_directory, embedding_function=embeddings
        )
    else:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100
        )
        splits = text_splitter.split_documents(docs)
        vector_db = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=persist_directory,
        )
        print("✅ Indexation terminée !")
else:
    print("   Base de données détectée, chargement en cours...")
    vector_db = Chroma(
        persist_directory=persist_directory, embedding_function=embeddings
    )

# Initialisation de la collection historique
history_db = Chroma(
    persist_directory=persist_directory,
    embedding_function=embeddings,
    collection_name="chat_history",
)


@app.get("/query")
async def query_agent(question: str, user_id: str = "default_user"):
    try:
        # --- ETAPE 1 : Récupérer l'historique récent ---
        # On cherche les messages passés de cet utilisateur
        vieux_messages = history_db.get(
            where={"user_id": user_id},
            limit=6,  # On prend les 6 derniers messages pour garder du contexte
        )

        historique_formate = ""
        if vieux_messages["documents"]:
            for i, msg in enumerate(vieux_messages["documents"]):
                role = vieux_messages["metadatas"][i]["role"]
                historique_formate += f"{role}: {msg}\n"

        # --- ETAPE 2 : Recherche dans les documents PDF (RAG) ---
        recherche_docs = vector_db.similarity_search(question, k=3)
        contexte_pdf = "\n\n".join([doc.page_content for doc in recherche_docs])

        # --- ETAPE 3 : Construction du Prompt "Mémoire + Documents" ---
        prompt = f"""Tu es l'expert immobilier Safari. 
        Réponds en utilisant l'historique et les documents fournis.

        HISTORIQUE DE LA CONVERSATION :
        {historique_formate}

        DOCUMENTS PERTINENTS :
        {contexte_pdf}

        QUESTION ACTUELLE : {question}
        """

        # --- ETAPE 4 : Appel à l'IA (Triple Secours) ---
        # Utilise ton bloc try/except Gemini/Mistral ici
        res = llm_25.invoke(prompt)
        reponse_finale = res.content

        # --- ETAPE 5 : Sauvegarder l'échange actuel dans ChromaDB ---
        # On enregistre la question et la réponse pour la prochaine fois
        history_db.add_texts(
            texts=[question, reponse_finale],
            metadatas=[
                {"user_id": user_id, "role": "Utilisateur"},
                {"user_id": user_id, "role": "Assistant"},
            ],
        )

        return {"reponse": reponse_finale, "engine": "Gemini 2.5"}

    except Exception as e:
        return {"reponse": "Désolé, j'ai un souci technique.", "error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Récupère le port de Render
    uvicorn.run(app, host="0.0.0.0", port=port)
