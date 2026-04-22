import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/query")
async def query_agent(question: str):
    if not docs_globaux:
        return {"reponse": "Je n'ai pas de documents pour vous répondre."}

    contexte = "\n\n".join([p.page_content for p in docs_globaux])
    prompt = f"Tu es l'expert de l'agence Safari. Réponds à cette question en te basant sur le contexte suivant.\n\nCONTEXTE: {contexte}\n\nQUESTION: {question}"

    # --- NIVEAU 1 : Gemini 2.5 ---
    try:
        print("Tentative avec Gemini 2.5...")
        res = llm_25.invoke(prompt)
        return {"reponse": res.content, "engine": "Gemini 2.5"}

    except google_exceptions.ResourceExhausted:
        # --- NIVEAU 2 : Gemini 1.5 ---
        try:
            print("⚠️ Quota 2.5 épuisé. Bascule vers Gemini 1.5...")
            res = llm_15.invoke(prompt)
            return {"reponse": res.content, "engine": "Gemini 1.5"}

        except Exception as e:
            # --- NIVEAU 3 : Mistral AI ---
            if llm_mistral:
                try:
                    print(
                        "⚠️ Gemini totalement saturé. Bascule vers Mistral (Plan C)..."
                    )
                    res = llm_mistral.invoke(prompt)
                    return {"reponse": res.content, "engine": "Mistral"}
                except Exception as mistral_err:
                    return {
                        "reponse": "Désolé, tous les services (Google & Mistral) sont saturés.",
                        "error": str(mistral_err),
                    }
            else:
                return {
                    "reponse": "Quota Google épuisé et Mistral n'est pas configuré.",
                    "error": str(e),
                }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Récupère le port de Render
    uvicorn.run(app, host="0.0.0.0", port=port)
