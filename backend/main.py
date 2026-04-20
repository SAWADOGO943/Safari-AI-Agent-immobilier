import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from fastapi.middleware.cors import CORSMiddleware

# Import nécessaire pour détecter l'erreur de quota (429)
from google.api_core import exceptions

# 1. Chargement et vérification de la clé
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERREUR : La clé GOOGLE_API_KEY est introuvable.")
else:
    print(f"✅ Clé API détectée : {api_key[:5]}...")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# On définit les deux modèles
llm_principal = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
llm_secours = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)


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
    print(f"📩 Question reçue : {question}")

    if not docs_globaux:
        return {"reponse": "Je n'ai pas de documents pour vous répondre."}

    contexte_total = "\n\n".join([p.page_content for p in docs_globaux])
    prompt = f"""
    Tu es l'expert immobilier de l'agence Safari.
    CONTEXTE : {contexte_total}
    CLIENT : {question}
    RÉPONSE :"""

    try:
        # --- TENTATIVE 1 : Modèle 2.5 Flash ---
        print("尝试 appel modèle 2.5 Flash...")
        reponse = llm_principal.invoke(prompt)
        print("🤖 Réponse générée avec Gemini 2.5 !")
        return {"reponse": reponse.content}

    except exceptions.ResourceExhausted:
        # --- TENTATIVE 2 : Bascule sur 1.5 Flash si quota épuisé ---
        print("⚠️ Quota 2.5 épuisé (429). Tentative de secours avec 1.5 Flash...")
        try:
            reponse = llm_secours.invoke(prompt)
            print("🤖 Réponse générée avec Gemini 1.5 (Secours) !")
            return {"reponse": reponse.content}
        except Exception as backup_error:
            print(f"💥 Échec du secours : {str(backup_error)}")
            return {
                "reponse": "Désolé, tous nos serveurs d'IA sont saturés. Réessaye dans une minute."
            }

    except Exception as e:
        print(f"💥 ERREUR AUTRE : {str(e)}")
        return {"reponse": f"Erreur technique : {str(e)}"}


if __name__ == "__main__":
    # Render utilise souvent la variable d'environnement PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
