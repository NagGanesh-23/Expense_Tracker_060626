import gc
from typing import Dict, Any, Iterator, Optional

from pipeline.rule_classifier import RuleClassifier
from pipeline.ml_classifier import MLClassifier
from pipeline.llm_classifier import LLMClassifier


class ClassificationOrchestrator:
    """
    Central orchestrator that drives the zero-disk in-memory classification cascade.
    Consumes single transaction dictionaries from a stream and filters them through
    Rules, ML, and LLM layers sequentially.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.rule_classifier = RuleClassifier(config_path)
        self.ml_classifier = MLClassifier(config_path)
        self.llm_classifier = LLMClassifier(config_path)

        # [Certain] In-memory deduplication cache is required to save ML/LLM latency
        self.memo_cache: Dict[str, tuple] = {}

    def process_batch(self, txns: list) -> list:
        """
        Processes a batch of transactions at once.
        Applies batching to rule, ML, and LLM layers to maximize throughput.
        """
        # Pre-assign from cache
        for txn in txns:
            if not txn or "description" not in txn:
                continue

            cache_key = txn["description"].strip().upper()
            if cache_key in self.memo_cache:
                cat, conf, method = self.memo_cache[cache_key]
                txn["category"] = cat
                txn["confidence"] = conf
                txn["classification_method"] = method

        # Find uncategorized
        uncategorized = [
            t
            for t in txns
            if "description" in t
            and ("category" not in t or t.get("classification_method") == "none")
        ]

        if not uncategorized:
            return txns

        # Extract unique keys
        unique_keys = list(
            dict.fromkeys(t["description"].strip().upper() for t in uncategorized)
        )

        # 1. Rule Batch
        rule_results = self.rule_classifier.predict_batch(unique_keys)

        failed_rule_keys = []
        for key, (cat, conf, method) in zip(unique_keys, rule_results):
            if cat:
                self.memo_cache[key] = (cat, conf, method)
            else:
                failed_rule_keys.append(key)

        # 2. ML Batch
        if failed_rule_keys:
            ml_results = self.ml_classifier.predict_batch(failed_rule_keys)
            failed_ml_keys = []

            for key, (cat, conf, method) in zip(failed_rule_keys, ml_results):
                if cat:
                    self.memo_cache[key] = (cat, conf, method)
                else:
                    failed_ml_keys.append(key)

            # 3. LLM Batch
            if failed_ml_keys:
                rep_txns = []
                for key in failed_ml_keys:
                    rep = next(
                        t
                        for t in uncategorized
                        if t["description"].strip().upper() == key
                    )
                    rep_txns.append(rep)

                # Chunk LLM requests to avoid payload limits (50 at a time)
                chunk_size = 50
                for i in range(0, len(rep_txns), chunk_size):
                    chunk = rep_txns[i : i + chunk_size]
                    llm_results = self.llm_classifier.predict_batch(chunk)

                    for rep_txn, (cat, conf, method) in zip(chunk, llm_results):
                        key = rep_txn["description"].strip().upper()
                        if cat and cat != "Others":
                            self.memo_cache[key] = (cat, conf, method)
                        else:
                            self.memo_cache[key] = ("Uncategorized", 0.0, "none")

        # Final assignment from memo cache
        for txn in uncategorized:
            cache_key = txn["description"].strip().upper()
            if cache_key in self.memo_cache:
                cat, conf, method = self.memo_cache[cache_key]
                txn["category"] = cat
                txn["confidence"] = conf
                txn["classification_method"] = method
            else:
                txn["category"] = "Uncategorized"
                txn["confidence"] = 0.0
                txn["classification_method"] = "none"

        return txns
