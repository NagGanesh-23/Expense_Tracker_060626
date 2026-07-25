import pandas as pd
from google import genai
from google.genai import types
from openai import OpenAI
import yaml
import json
import os
import time


class LLMClassifier:
    """Stage C: Gemini Flash LLM Primary with Nvidia NIM Fallback."""

    def __init__(self, config_path: str = "config.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file) or {}
        else:
            self.config = {}

        # Load training data for Exact Match Bypass
        self.exact_matches = {}
        try:
            if os.path.exists("models/training_data.csv"):
                train_df = pd.read_csv("models/training_data.csv")
                for _, row in train_df.iterrows():
                    if len(row) >= 6:
                        if (
                            "description" in row
                            and "category" in row
                            and pd.notna(row["description"])
                            and pd.notna(row["category"])
                        ):
                            desc = str(row["description"]).strip().lower()
                            cat = str(row["category"]).strip()
                            self.exact_matches[desc] = cat
                print(
                    f"✅ Loaded {len(self.exact_matches)} exact match rules from Col B & Col F."
                )
        except Exception as e:
            print(f"❌ Could not load training data for bypass: {e}")

        gemini_key = self.config.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.gemini_client = genai.Client(api_key=gemini_key)
            self.gemini_model = "gemini-2.0-flash"
            self.has_gemini = True
        else:
            self.has_gemini = False

        nvidia_key = self.config.get("nvidia_api_key") or os.getenv("NVIDIA_API_KEY")
        if nvidia_key:
            self.nvidia_client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key
            )
            self.nvidia_model = "openai/gpt-oss-120b"
            self.has_nvidia = True
        else:
            self.has_nvidia = False

        self.active = self.has_gemini or self.has_nvidia

        self.categories = [
            "Bank Charges & Fees",
            "Cashback & Rewards",
            "Credit Card Payment",
            "Dividend",
            "Food & Dining",
            "Fuel & Transport",
            "Domestic Help & Services",
            "Groceries & Supermarket",
            "Investments & Finance",
            "Jewellery & Gifts",
            "Un Wanted",
            "Travel & Accommodation",
            "Shopping",
            "Self Transfer",
            "Subscriptions & Software",
            "Medical & Health",
            "Mutton",
            "Chicken",
            "Others",
            "Uncategorized",
        ]

        self.system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        cats_json = json.dumps(self.categories, ensure_ascii=False)
        return f"""You are an expert financial transaction classifier for Indian personal finance.
You have deep knowledge of Indian payment rails (UPI, NEFT, IMPS, RTGS) and merchants.

## ALLOWED CATEGORIES
{cats_json}

## RULES
1. Classify the given transaction into EXACTLY one of the allowed categories.
2. If you are unsure, you must return "Others".
3. For single predictions, return ONLY valid JSON in this exact format: {{"category": "Category Name", "confidence": 0.95}}
4. For batch predictions, return ONLY a valid JSON array of objects in the exact same order as the input: [{{"category": "Category Name", "confidence": 0.95}}, ...]
"""

    def _build_prompt(self, txn: dict) -> str:
        return f"""
Transaction Details:
- Date: {txn.get('transaction_date', '')}
- Amount: {txn.get('amount', 0)}
- Type: {txn.get('transaction_type', '')}
- Description: {txn.get('raw_description', '')}

Classify this transaction.
"""

    def predict_single(self, txn: dict) -> tuple:
        """
        Evaluates a single transaction dictionary against the Gemini LLM with retries,
        and falls back to Nvidia NIM if Gemini fails.
        """
        if not self.active or not txn:
            return None, 0.0, "none"

        clean_desc = str(txn.get("raw_description", "")).strip().lower()

        # Local Bypass
        if clean_desc in self.exact_matches:
            return self.exact_matches[clean_desc], 1.0, "exact_match"

        prompt = self._build_prompt(txn)
        max_retries = 3
        backoff = 3

        if self.has_gemini:
            for attempt in range(max_retries):
                try:
                    response = self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction,
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                    parsed = json.loads(response.text)
                    result = parsed[0] if isinstance(parsed, list) else parsed
                    return (
                        result.get("category", "Others"),
                        float(result.get("confidence", 0.0)),
                        "llm_gemini",
                    )
                except Exception as e:
                    err_str = str(e).lower()
                    print(f"Gemini LLM Error on attempt {attempt + 1}: {e}")
                    if "429" in err_str or "exhausted" in err_str or "quota" in err_str:
                        print("Gemini quota exhausted. Falling back to Nvidia...")
                        break
                    if attempt < max_retries - 1:
                        time.sleep(backoff ** (attempt + 1))

        if self.has_nvidia:
            for attempt in range(max_retries):
                try:
                    response = self.nvidia_client.chat.completions.create(
                        model=self.nvidia_model,
                        messages=[
                            {"role": "system", "content": self.system_instruction},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        top_p=1,
                        max_tokens=4096,
                        stream=False,
                    )
                    content = response.choices[0].message.content or ""
                    content = content.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(content)
                    result = parsed[0] if isinstance(parsed, list) else parsed
                    return (
                        result.get("category", "Others"),
                        float(result.get("confidence", 0.0)),
                        "llm_nvidia",
                    )
                except Exception as e:
                    print(f"Nvidia LLM Error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(backoff ** (attempt + 1))

        return None, 0.0, "none"

    def predict_batch(self, txns: list) -> list:
        """
        Evaluates a batch of transactions using a single prompt to the LLM.
        """
        if not self.active or not txns:
            return [(None, 0.0, "none")] * len(txns)

        results = [(None, 0.0, "none")] * len(txns)
        to_infer = []
        infer_indices = []

        for i, txn in enumerate(txns):
            clean_desc = str(txn.get("raw_description", "")).strip().lower()
            if clean_desc in self.exact_matches:
                results[i] = (self.exact_matches[clean_desc], 1.0, "exact_match")
            else:
                infer_indices.append(i)
                to_infer.append(txn)

        if not to_infer:
            return results

        prompt = "Classify these transactions and return a JSON list of objects:\n"
        for idx, txn in enumerate(to_infer):
            prompt += f"[{idx}] Date: {txn.get('transaction_date', '')}, Amount: {txn.get('amount', 0)}, Type: {txn.get('transaction_type', '')}, Desc: {txn.get('raw_description', '')}\n"

        max_retries = 3
        backoff = 3

        if self.has_gemini:
            for attempt in range(max_retries):
                try:
                    response = self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_instruction,
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                    parsed = json.loads(response.text)
                    if not isinstance(parsed, list):
                        parsed = [parsed]

                    for list_idx, original_idx in enumerate(infer_indices):
                        if list_idx < len(parsed):
                            res = parsed[list_idx]
                            results[original_idx] = (
                                res.get("category", "Others"),
                                float(res.get("confidence", 0.0)),
                                "llm_gemini",
                            )
                    return results
                except Exception as e:
                    err_str = str(e).lower()
                    print(f"Gemini Bulk Error on attempt {attempt + 1}: {e}")
                    if "429" in err_str or "exhausted" in err_str or "quota" in err_str:
                        print("Gemini quota exhausted. Falling back to Nvidia...")
                        break
                    if attempt < max_retries - 1:
                        time.sleep(backoff ** (attempt + 1))

        if self.has_nvidia:
            for attempt in range(max_retries):
                try:
                    response = self.nvidia_client.chat.completions.create(
                        model=self.nvidia_model,
                        messages=[
                            {"role": "system", "content": self.system_instruction},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        top_p=1,
                        max_tokens=4096,
                        stream=False,
                    )
                    content = response.choices[0].message.content or ""
                    content = content.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(content)
                    if not isinstance(parsed, list):
                        parsed = [parsed]

                    for list_idx, original_idx in enumerate(infer_indices):
                        if list_idx < len(parsed):
                            res = parsed[list_idx]
                            results[original_idx] = (
                                res.get("category", "Others"),
                                float(res.get("confidence", 0.0)),
                                "llm_nvidia",
                            )
                    return results
                except Exception as e:
                    print(f"Nvidia Bulk Error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(backoff ** (attempt + 1))

        return results
