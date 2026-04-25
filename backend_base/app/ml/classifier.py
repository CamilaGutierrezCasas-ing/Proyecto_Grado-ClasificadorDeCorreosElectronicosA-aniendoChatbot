from __future__ import annotations

from pathlib import Path
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "logistic_model.joblib"
VECTORIZER_PATH = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
MODEL_VERSION = "fase3-logistic-v1"


def preprocess_text(subject: str, body: str) -> str:
    subject = subject or ""
    body = body or ""
    return f"{subject} {body}".strip().lower()


def _demo_training_data() -> tuple[list[str], list[str]]:
    samples = [
        ("pago pendiente urgente responder hoy", "urgente"),
        ("reunion importante a primera hora con gerencia", "urgente"),
        ("entrega informe laboral proyecto cliente", "trabajo"),
        ("cronograma reunion oficina y tareas del equipo", "trabajo"),
        ("matricula semestre examen docente aula universidad", "educacion"),
        ("actividad academica estudiante curso plataforma", "educacion"),
        ("cita medica eps resultados laboratorio formula", "salud"),
        ("control medico incapacidad tratamiento y salud", "salud"),
        ("gana dinero oferta promocion haz clic premio", "spam"),
        ("descuento gratis compra ahora publicidad", "spam"),
        ("feliz cumpleanos fotos del fin de semana", "otros"),
        ("invitacion almuerzo familia y saludo", "otros"),
    ]
    texts = [t for t, _ in samples]
    labels = [y for _, y in samples]
    return texts, labels


def train_and_save_demo_model() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    texts, labels = _demo_training_data()

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    model = LogisticRegression(max_iter=1000)
    model.fit(X, labels)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)


def ensure_model_artifacts() -> None:
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        train_and_save_demo_model()


def load_model_and_vectorizer():
    ensure_model_artifacts()
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    return model, vectorizer


def classify_email(subject: str, body: str) -> tuple[str, float]:
    model, vectorizer = load_model_and_vectorizer()
    text = preprocess_text(subject, body)

    X = vectorizer.transform([text])
    prediction = model.predict(X)[0]

    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba(X)[0]))
    else:
        confidence = 0.0

    return prediction, round(confidence, 4)