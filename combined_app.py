import os
import threading
import requests
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel


# Charger les ressources nécessaires pour le serveur FastAPI
#model = joblib.load("server/model.pkl")
#metrics = joblib.load("server/metrics.pkl")
#feature_names = joblib.load("server/feature_names.pkl")

# Définir un chemin absolu basé sur le répertoire racine
file_path = os.path.join("server", "metrics.pkl")
metrics = joblib.load(file_path)

# Définir un chemin absolu basé sur le répertoire racine
file_path1 = os.path.join("server", "model.pkl")
model = joblib.load(file_path1)

# Définir un chemin absolu basé sur le répertoire racine
file_path2 = os.path.join("server", "feature_names.pkl")
feature_names = joblib.load(file_path2)


# ---------------------------------------------
# Configuration FastAPI
# ---------------------------------------------
fastapi_app = FastAPI()

# Autoriser les requêtes CORS pour Streamlit
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permettre les requêtes de toutes origines
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Schéma pour la requête de prédiction
class PredictionRequest(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float


@fastapi_app.post("/predict/")
def predict(request: PredictionRequest):
    input_data = [
        request.sepal_length,
        request.sepal_width,
        request.petal_length,
        request.petal_width,
    ]
    prediction = model.predict([input_data])[0]
    class_name = {0: "Setosa", 1: "Versicolor", 2: "Virginica"}
    return {"prediction": class_name[prediction]}


@fastapi_app.get("/metrics/")
def get_metrics():
    return metrics


# Fonction pour démarrer FastAPI
def start_fastapi():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)


# ---------------------------------------------
# Configuration Streamlit
# ---------------------------------------------
# URL de l'API FastAPI
API_URL = "http://localhost:8000"

# Fonction pour afficher la page de prédiction
def prediction_page():
    st.title("Iris Flower Predictor")
    st.write("Entrez les caractéristiques de la fleur pour prédire sa catégorie.")

    # Champs de saisie pour la prédiction
    sepal_length = st.number_input("Sepal Length", min_value=0.0, step=0.1)
    sepal_width = st.number_input("Sepal Width", min_value=0.0, step=0.1)
    petal_length = st.number_input("Petal Length", min_value=0.0, step=0.1)
    petal_width = st.number_input("Petal Width", min_value=0.0, step=0.1)

    if st.button("Prédire"):
        if all(v == 0.0 for v in [sepal_length, sepal_width, petal_length, petal_width]):
            st.error("Veuillez entrer des valeurs non nulles pour les caractéristiques.")
        else:
            payload = {
                "sepal_length": sepal_length,
                "sepal_width": sepal_width,
                "petal_length": petal_length,
                "petal_width": petal_width,
            }
            try:
                response = requests.post(f"{API_URL}/predict/", json=payload)
                if response.status_code == 200:
                    prediction = response.json()["prediction"]
                    st.success(f"La fleur prédite est : **{prediction}**")
                else:
                    st.error(f"Erreur API ({response.status_code}): {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion à l'API : {e}")


# Fonction pour afficher la page des métriques
def metrics_page():
    st.title("Métriques d'apprentissage du modèle")
    try:
        response = requests.get(f"{API_URL}/metrics/")
        if response.status_code == 200:
            metrics = response.json()
            st.subheader("Accuracy")
            st.write(f"Accuracy: {metrics['accuracy']:.2f}")

            st.subheader("Classification Report")
            st.text(metrics['classification_report'])

            st.subheader("AUC ROC")
            for i, auc in enumerate(metrics["roc_auc"]):
                st.write(f"AUC ROC for class {i}: {auc:.2f}")

            st.subheader("Courbe ROC")
            for i, (fpr, tpr, auc) in enumerate(
                zip(metrics["fpr"], metrics["tpr"], metrics["roc_auc"])
            ):
                fig, ax = plt.subplots()
                ax.plot(fpr, tpr, label=f"Class {i} (AUC = {auc:.2f})")
                ax.plot([0, 1], [0, 1], "k--")
                ax.legend()
                st.pyplot(fig)
        else:
            st.error(f"Erreur API ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {e}")


# ---------------------- Gestion de la navigation ----------------------
# Ajouter les boutons dans la barre latérale pour changer de page
if st.sidebar.button("Page Prédiction"):
    st.session_state.current_page = "Prédiction"

if st.sidebar.button("Page Métriques"):
    st.session_state.current_page = "Métriques"

# ---------------------------------------------
# Démarrage des applications
# ---------------------------------------------
if __name__ == "__main__":
    # Démarrer FastAPI dans un thread séparé
    api_thread = threading.Thread(target=start_fastapi, daemon=True)
    api_thread.start()

    # Démarrer Streamlit
    main()