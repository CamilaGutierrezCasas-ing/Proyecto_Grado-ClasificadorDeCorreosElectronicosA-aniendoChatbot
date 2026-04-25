from collections import Counter
from pathlib import Path
import csv

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.models.email import Email
from app.ml.classifier import MODEL_PATH, VECTORIZER_PATH

DATASET_PATH = Path("app/ml/data/dataset_entrenamiento_correos.csv")


def load_csv_dataset():
    texts = []
    labels = []

    if not DATASET_PATH.exists():
        return texts, labels

    with open(DATASET_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subject = row.get("subject", "")
            body = row.get("body", "")
            category = row.get("category", "").strip().lower()

            text = f"{subject} {body}".strip()
            if text and category:
                texts.append(text)
                labels.append(category)

    return texts, labels


def load_db_dataset(db: Session):
    emails = db.query(Email).all()

    texts = []
    labels = []

    for e in emails:
        subject = e.subject or ""
        body = e.body or ""
        category = e.predicted_category or "otros"

        # ❌ excluir datos basura
        if not subject and not body:
            continue

        if e.source_account == "local-demo":
            continue

        text = f"{subject} {body}".strip()

        texts.append(text)
        labels.append(category.lower())

    return texts, labels


def retrain_model_from_all_sources(db: Session) -> dict:

    # 🔹 cargar CSV
    csv_texts, csv_labels = load_csv_dataset()

    # 🔹 cargar BD
    db_texts, db_labels = load_db_dataset(db)

    # 🔹 unir datasets
    texts = csv_texts + db_texts
    labels = csv_labels + db_labels

    if len(texts) < 20:
        raise ValueError("No hay suficientes datos para entrenar")

    class_counts = Counter(labels)

    if len(class_counts) < 2:
        raise ValueError("Se necesitan al menos 2 categorías")

    # 🔹 split
    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    # 🔹 vectorizador
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        max_features=5000,
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # 🔹 modelo
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_vec, y_train)

    # 🔹 evaluación simple
    y_pred = model.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)

    # 🔹 guardar modelo
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    return {
        "message": "Modelo entrenado con CSV + BD",
        "total_samples": len(texts),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(float(accuracy), 4),
        "categories": dict(class_counts),
    }