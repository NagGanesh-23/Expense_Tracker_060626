import os
import re
import hashlib
import yaml
import numpy as np
import pandas as pd
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz

    _HAS_RAPIDFUZZ = True
except ImportError:
    import difflib

    _HAS_RAPIDFUZZ = False

# Banking/UPI boilerplate that carries no category signal.
_BANK_NAMES = [
    "yes bank",
    "union bank",
    "canara",
    "indusind",
    "federal bank",
    "bank of baroda",
    "icici",
    "hdfc",
    "sbi",
    "axis",
    "kotak",
    "idfc",
    "boi",
]
_NOISE_TOKENS = [
    "upi",
    "neft",
    "imps",
    "rtgs",
    "nach",
    "trxn",
    "ach",
    "paid via c",
    "payment fr",
    "payment on",
    "payment received",
    "credit trxn",
    "fund transfer",
    "bil payment",
    "cms",
    "pvt ltd",
    "private limited",
    "ltd",
    "corp",
    "clearing corp",
    "bank",
    "bengaluru",
    "bangalore",
    "mumbai",
    "newdelhi",
    "new delhi",
    "chennai",
    "noida",
    "gurugram",
    "gurgaon",
    "hyderabad",
    "surat",
    "mysore",
    "mandya",
    "ind",
    " in ",
    " ka ",
]


class MLClassifier:
    """
    Stage B: Historical-transaction classifier exposing a predict_single stream interface.
    """

    def __init__(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file) or {}
        else:
            self.config = {}

        self.threshold = self.config.get("ml_confidence_threshold", 0.85)
        self.fuzzy_threshold = self.config.get("ml_fuzzy_threshold", 90)
        self.top_k = self.config.get("ml_top_k_neighbors", 3)

        # [Certain] Loading this into memory takes time; it must stay in __init__
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.training_file = "models/training_data.csv"
        self.embedding_cache_file = "models/training_embeddings_cache.npz"

        self.exact_match_map = {}
        self.cleaned_train_descs = []
        self.cleaned_train_categories = []
        self.training_embeddings = None
        self.unique_train_descs = []

        self._load_training_data()

    @staticmethod
    def clean_text(text: str) -> str:
        """Strips banking boilerplate and transaction reference numbers."""
        if not text or not isinstance(text, str):
            return ""

        t = text.lower()
        t = re.sub(r"\b[a-z0-9]{10,}\b", " ", t)
        t = re.sub(r"\b\d{4,}\b", " ", t)

        for token in _BANK_NAMES + _NOISE_TOKENS:
            t = t.replace(token, " ")

        t = re.sub(r"[^a-z\s]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()

        words = t.split()
        deduped = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
        return " ".join(deduped)

    def _load_training_data(self):
        """Builds in-memory data structures required for the cascade."""
        if not os.path.exists(self.training_file):
            return

        df = pd.read_csv(self.training_file)
        if df.empty or "description" not in df.columns or "category" not in df.columns:
            return

        df = df.dropna(subset=["description", "category"]).copy()
        df["cleaned_description"] = df["description"].apply(self.clean_text)
        df = df[df["cleaned_description"] != ""]

        self.cleaned_train_descs = df["cleaned_description"].tolist()
        self.cleaned_train_categories = df["category"].tolist()
        self.unique_train_descs = list(dict.fromkeys(self.cleaned_train_descs))

        grouped = {}
        for desc, cat in zip(self.cleaned_train_descs, self.cleaned_train_categories):
            grouped.setdefault(desc, Counter())[cat] += 1

        for desc, counter in grouped.items():
            best_cat, best_count = counter.most_common(1)[0]
            total = sum(counter.values())
            self.exact_match_map[desc] = (best_cat, best_count / total)

        self.training_embeddings = self._get_or_build_embeddings(
            self.cleaned_train_descs
        )

    def _get_or_build_embeddings(self, cleaned_descs: list) -> np.ndarray:
        """Retrieves or calculates the historical embedding matrix."""
        content_hash = hashlib.sha256(
            "\n".join(cleaned_descs).encode("utf-8")
        ).hexdigest()

        if os.path.exists(self.embedding_cache_file):
            try:
                cached = np.load(self.embedding_cache_file, allow_pickle=True)
                if str(cached["hash"]) == content_hash:
                    return cached["embeddings"]
            except Exception:
                pass

        embeddings = self.model.encode(cleaned_descs, show_progress_bar=False)
        try:
            os.makedirs(os.path.dirname(self.embedding_cache_file), exist_ok=True)
            np.savez(
                self.embedding_cache_file, embeddings=embeddings, hash=content_hash
            )
        except Exception:
            pass

        return embeddings

    def predict_single(self, raw_desc: str) -> tuple:
        """
        Stream-compatible entrypoint. Executes B1 (Exact), B2 (Fuzzy), and B3 (Semantic)
        sequentially on a single transaction string.
        """
        if not self.training_embeddings is not None or not self.cleaned_train_descs:
            return None, 0.0, "none"

        cleaned = self.clean_text(raw_desc)
        if not cleaned:
            return None, 0.0, "none"

        # Pass B1: Exact Match
        if cleaned in self.exact_match_map:
            cat, conf = self.exact_match_map[cleaned]
            if conf >= self.threshold:
                return cat, conf, "ml_exact"

        # Pass B2: Fuzzy Match
        if _HAS_RAPIDFUZZ:
            match = rf_process.extractOne(
                cleaned, self.unique_train_descs, scorer=rf_fuzz.token_sort_ratio
            )
            if match:
                matched_desc, score, _ = match
                confidence = score / 100.0
                if score >= self.fuzzy_threshold and confidence >= self.threshold:
                    cat, _ = self.exact_match_map[matched_desc]
                    return cat, confidence, "ml_fuzzy"
        else:
            close = difflib.get_close_matches(
                cleaned, self.unique_train_descs, n=1, cutoff=0.0
            )
            if close:
                matched_desc = close[0]
                score = (
                    difflib.SequenceMatcher(None, cleaned, matched_desc).ratio() * 100
                )
                confidence = score / 100.0
                if score >= self.fuzzy_threshold and confidence >= self.threshold:
                    cat, _ = self.exact_match_map[matched_desc]
                    return cat, confidence, "ml_fuzzy"

        # Pass B3: Semantic Embedding Match (Costly single-item inference)
        incoming_embedding = self.model.encode([cleaned], show_progress_bar=False)
        sims = cosine_similarity(incoming_embedding, self.training_embeddings)[0]

        k = min(self.top_k, len(sims))
        top_k_idx = np.argsort(sims)[-k:][::-1]
        top_k_scores = sims[top_k_idx]
        top_k_cats = [self.cleaned_train_categories[j] for j in top_k_idx]

        vote_counts = Counter(top_k_cats)
        best_cat, _ = vote_counts.most_common(1)[0]

        supporting_scores = [
            s for s, c in zip(top_k_scores, top_k_cats) if c == best_cat
        ]
        confidence = float(np.mean(supporting_scores))

        if confidence >= self.threshold:
            return best_cat, confidence, "ml_semantic"

        return None, 0.0, "none"

    def predict_batch(self, raw_descs: list) -> list:
        """
        Batch evaluation entrypoint. Executes B1, B2, and B3
        on a list of transaction strings efficiently.
        """
        if self.training_embeddings is None or not self.cleaned_train_descs:
            return [(None, 0.0, "none")] * len(raw_descs)

        results = [(None, 0.0, "none")] * len(raw_descs)
        cleaned_descs = [self.clean_text(d) for d in raw_descs]

        # Track items needing semantic search
        semantic_indices = []
        semantic_queries = []

        for i, cleaned in enumerate(cleaned_descs):
            if not cleaned:
                continue

            # Pass B1: Exact Match
            if cleaned in self.exact_match_map:
                cat, conf = self.exact_match_map[cleaned]
                if conf >= self.threshold:
                    results[i] = (cat, conf, "ml_exact")
                    continue

            # Pass B2: Fuzzy Match
            matched = False
            if _HAS_RAPIDFUZZ:
                match = rf_process.extractOne(
                    cleaned, self.unique_train_descs, scorer=rf_fuzz.token_sort_ratio
                )
                if match:
                    matched_desc, score, _ = match
                    confidence = score / 100.0
                    if score >= self.fuzzy_threshold and confidence >= self.threshold:
                        cat, _ = self.exact_match_map[matched_desc]
                        results[i] = (cat, confidence, "ml_fuzzy")
                        matched = True
            else:
                close = difflib.get_close_matches(
                    cleaned, self.unique_train_descs, n=1, cutoff=0.0
                )
                if close:
                    matched_desc = close[0]
                    score = (
                        difflib.SequenceMatcher(None, cleaned, matched_desc).ratio()
                        * 100
                    )
                    confidence = score / 100.0
                    if score >= self.fuzzy_threshold and confidence >= self.threshold:
                        cat, _ = self.exact_match_map[matched_desc]
                        results[i] = (cat, confidence, "ml_fuzzy")
                        matched = True

            if not matched:
                semantic_indices.append(i)
                semantic_queries.append(cleaned)

        # Pass B3: Semantic Embedding Match (Batch inference)
        if semantic_queries:
            incoming_embeddings = self.model.encode(
                semantic_queries, show_progress_bar=False
            )
            sim_matrix = cosine_similarity(
                incoming_embeddings, self.training_embeddings
            )

            for idx_in_batch, original_idx in enumerate(semantic_indices):
                sims = sim_matrix[idx_in_batch]
                k = min(self.top_k, len(sims))
                top_k_idx = np.argsort(sims)[-k:][::-1]
                top_k_scores = sims[top_k_idx]
                top_k_cats = [self.cleaned_train_categories[j] for j in top_k_idx]

                vote_counts = Counter(top_k_cats)
                best_cat, _ = vote_counts.most_common(1)[0]

                supporting_scores = [
                    s for s, c in zip(top_k_scores, top_k_cats) if c == best_cat
                ]
                confidence = float(np.mean(supporting_scores))

                if confidence >= self.threshold:
                    results[original_idx] = (best_cat, confidence, "ml_semantic")

        return results
