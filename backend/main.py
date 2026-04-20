import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from fastapi.middleware.cors import CORSMiddleware

# 1. Chargement et vérification de la clé
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(
        "❌ ERREUR : La clé GOOGLE_API_KEY est introuvable. Vérifie ton fichier .env !"
    )
else:
    print(f"✅ Clé API détectée : {api_key[:5]}...")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du modèle
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)


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
    print(f"📩 Question reçue : {question}")  # Pour voir si le frontend appelle bien
    if not docs_globaux:
        return {"reponse": "Je n'ai pas de documents pour vous répondre."}

    try:
        contexte_total = "\n\n".join([p.page_content for p in docs_globaux])

        prompt = f"""
        Tu es l'expert immobilier de l'agence Safari.
        CONTEXTE : {contexte_total}
        CLIENT : {question}
        RÉPONSE :"""

        # Appel au modèle
        reponse = llm.invoke(prompt)
        print("🤖 Réponse générée avec succès !")
        return {"reponse": reponse.content}

    except Exception as e:
        print(f"💥 ERREUR CRITIQUE : {str(e)}")
        return {"reponse": f"Erreur interne : {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
