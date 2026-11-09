import argparse, os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--text-column", default="text")
    p.add_argument("--label-column", default="label")
    args = p.parse_args()
    df = pd.read_csv(args.input).dropna(subset=[args.text_column, args.label_column])
    X = df[args.text_column].astype(str)
    y = df[args.label_column].astype(str).str.lower()
    if y.nunique() < 2 or len(df) < 20:
        raise SystemExit("Need at least 20 labeled rows and two classes.")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=50000, strip_accents="unicode", sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print(classification_report(y_test, pred, zero_division=0))
    print("Confusion matrix:\n", confusion_matrix(y_test, pred, labels=sorted(y.unique())))
    os.makedirs("app/ml/artifacts", exist_ok=True)
    joblib.dump(model, "app/ml/artifacts/message_model.joblib")
    print("Saved app/ml/artifacts/message_model.joblib. Evaluate on a separate external test set before deployment.")

if __name__ == "__main__":
    main()
