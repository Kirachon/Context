"""
Embedding Quality Evaluator

Compares different embedding models for code semantic similarity tasks.
Evaluates UniXcoder vs sentence-transformers on real parsed code samples.
"""

import logging
import time
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import precision_recall_fscore_support

from src.parsing.parser import get_parser
from src.parsing.models import ParseResult

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingModel:
    """Represents an embedding model for evaluation."""

    name: str
    model_type: str  # 'sentence_transformers', 'unixcoder', 'custom'
    model_instance: Any
    embedding_dim: int

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        raise NotImplementedError


@dataclass
class CodeSample:
    """Represents a code sample for evaluation."""

    id: str
    language: str
    code: str
    description: str
    category: str  # 'function', 'class', 'async', 'factory', 'repository', etc.
    parse_result: Optional[ParseResult] = None


@dataclass
class SimilarityPair:
    """Represents a pair of code samples with expected similarity."""

    sample1: CodeSample
    sample2: CodeSample
    expected_similarity: float  # 0.0 to 1.0
    similarity_type: str  # 'semantic', 'structural', 'functional'


@dataclass
class EvaluationResult:
    """Results of embedding model evaluation."""

    model_name: str
    precision: float
    recall: float
    f1_score: float
    avg_similarity_accuracy: float
    encoding_time_ms: float
    memory_usage_mb: float
    cross_language_accuracy: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "avg_similarity_accuracy": self.avg_similarity_accuracy,
            "encoding_time_ms": self.encoding_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cross_language_accuracy": self.cross_language_accuracy,
        }


class SentenceTransformersModel(EmbeddingModel):
    """Sentence-transformers embedding model wrapper."""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        try:
            from sentence_transformers import SentenceTransformer

            model_instance = SentenceTransformer(model_name)
            super().__init__(
                name=f"sentence-transformers/{model_name}",
                model_type="sentence_transformers",
                model_instance=model_instance,
                embedding_dim=768,  # all-mpnet-base-v2 dimension
            )
        except ImportError:
            logger.error("sentence-transformers not available")
            raise

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts using sentence-transformers."""
        return self.model_instance.encode(texts)


class UniXcoderModel(EmbeddingModel):
    """UniXcoder embedding model wrapper."""

    def __init__(self, model_name: str = "microsoft/unixcoder-base"):
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            model_instance = AutoModel.from_pretrained(model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_instance.to(self.device)

            super().__init__(
                name=f"unixcoder/{model_name}",
                model_type="unixcoder",
                model_instance=model_instance,
                embedding_dim=768,  # UniXcoder base dimension
            )
        except ImportError:
            logger.error("transformers not available for UniXcoder")
            raise

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts using UniXcoder."""
        import torch

        embeddings = []

        for text in texts:
            # Tokenize and encode
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model_instance(**inputs)
                # Use CLS token embedding
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                embeddings.append(embedding[0])

        return np.array(embeddings)


class EmbeddingEvaluator:
    """
    Evaluates embedding models on code similarity tasks.

    Compares different models using real parsed code samples and
    measures retrieval accuracy, semantic similarity, and performance.
    """

    def __init__(self):
        """Initialize the evaluator."""
        self.parser = get_parser()
        self.code_samples: List[CodeSample] = []
        self.similarity_pairs: List[SimilarityPair] = []

        logger.info("EmbeddingEvaluator initialized")

    def add_code_sample(self, sample: CodeSample):
        """Add a code sample to the evaluation dataset."""
        # Parse the code sample
        try:
            result = self.parser.parse(
                Path(f"sample_{sample.id}.{self._get_extension(sample.language)}"),
                sample.code,
            )
            sample.parse_result = result
            self.code_samples.append(sample)
            logger.debug(f"Added code sample: {sample.id} ({sample.language})")
        except Exception as e:
            logger.warning(f"Failed to parse sample {sample.id}: {e}")

    def add_similarity_pair(self, pair: SimilarityPair):
        """Add a similarity pair for evaluation."""
        self.similarity_pairs.append(pair)

    def evaluate_model(self, model: EmbeddingModel) -> EvaluationResult:
        """Evaluate an embedding model on the code samples."""
        logger.info(f"Evaluating model: {model.name}")

        # Prepare texts for encoding
        texts = [
            self._prepare_text_for_embedding(sample) for sample in self.code_samples
        ]

        # Measure encoding time
        start_time = time.time()
        embeddings = model.encode(texts)
        encoding_time = (time.time() - start_time) * 1000  # ms

        # Calculate similarity accuracy
        similarity_accuracy = self._calculate_similarity_accuracy(model, embeddings)

        # Calculate retrieval metrics
        precision, recall, f1 = self._calculate_retrieval_metrics(model, embeddings)

        # Calculate cross-language accuracy
        cross_lang_accuracy = self._calculate_cross_language_accuracy(model, embeddings)

        # Estimate memory usage (rough approximation)
        memory_usage = embeddings.nbytes / (1024 * 1024)  # MB

        return EvaluationResult(
            model_name=model.name,
            precision=precision,
            recall=recall,
            f1_score=f1,
            avg_similarity_accuracy=similarity_accuracy,
            encoding_time_ms=encoding_time,
            memory_usage_mb=memory_usage,
            cross_language_accuracy=cross_lang_accuracy,
        )

    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        ext_map = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "go": "go",
            "rust": "rs",
        }
        return ext_map.get(language, "txt")

    def _prepare_text_for_embedding(self, sample: CodeSample) -> str:
        """Prepare code sample text for embedding."""
        # Combine code with description for better semantic understanding
        if sample.description:
            return f"{sample.description}\n\n{sample.code}"
        return sample.code

    def _calculate_similarity_accuracy(
        self, model: EmbeddingModel, embeddings: np.ndarray
    ) -> float:
        """Calculate similarity prediction accuracy."""
        if not self.similarity_pairs:
            return 0.0

        accuracies = []

        for pair in self.similarity_pairs:
            # Find embeddings for the pair
            idx1 = next(
                (i for i, s in enumerate(self.code_samples) if s.id == pair.sample1.id),
                None,
            )
            idx2 = next(
                (i for i, s in enumerate(self.code_samples) if s.id == pair.sample2.id),
                None,
            )

            if idx1 is None or idx2 is None:
                continue

            # Calculate cosine similarity
            emb1 = embeddings[idx1].reshape(1, -1)
            emb2 = embeddings[idx2].reshape(1, -1)
            predicted_similarity = cosine_similarity(emb1, emb2)[0][0]

            # Calculate accuracy (how close predicted is to expected)
            accuracy = 1.0 - abs(predicted_similarity - pair.expected_similarity)
            accuracies.append(accuracy)

        return np.mean(accuracies) if accuracies else 0.0

    def _calculate_retrieval_metrics(
        self, model: EmbeddingModel, embeddings: np.ndarray
    ) -> Tuple[float, float, float]:
        """Calculate precision, recall, and F1 for retrieval tasks."""
        if len(self.code_samples) < 2:
            return 0.0, 0.0, 0.0

        # Create ground truth based on categories
        y_true = []
        y_pred = []

        # For each sample, find most similar samples
        for i, sample in enumerate(self.code_samples):
            emb_i = embeddings[i].reshape(1, -1)

            # Calculate similarities to all other samples
            similarities = []
            for j, other_sample in enumerate(self.code_samples):
                if i != j:
                    emb_j = embeddings[j].reshape(1, -1)
                    sim = cosine_similarity(emb_i, emb_j)[0][0]
                    similarities.append((j, sim, other_sample))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Take top 3 most similar
            top_similar = similarities[:3]

            for j, sim, other_sample in top_similar:
                # Ground truth: same category = relevant
                is_relevant = sample.category == other_sample.category
                # Prediction: high similarity = relevant (threshold 0.7)
                is_predicted_relevant = sim > 0.7

                y_true.append(1 if is_relevant else 0)
                y_pred.append(1 if is_predicted_relevant else 0)

        if not y_true:
            return 0.0, 0.0, 0.0

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )

        return precision, recall, f1

    def _calculate_cross_language_accuracy(
        self, model: EmbeddingModel, embeddings: np.ndarray
    ) -> float:
        """Calculate accuracy for cross-language similarity detection."""
        cross_lang_pairs = [
            pair
            for pair in self.similarity_pairs
            if pair.sample1.language != pair.sample2.language
        ]

        if not cross_lang_pairs:
            return 0.0

        accuracies = []

        for pair in cross_lang_pairs:
            idx1 = next(
                (i for i, s in enumerate(self.code_samples) if s.id == pair.sample1.id),
                None,
            )
            idx2 = next(
                (i for i, s in enumerate(self.code_samples) if s.id == pair.sample2.id),
                None,
            )

            if idx1 is None or idx2 is None:
                continue

            emb1 = embeddings[idx1].reshape(1, -1)
            emb2 = embeddings[idx2].reshape(1, -1)
            predicted_similarity = cosine_similarity(emb1, emb2)[0][0]

            # For cross-language, we expect lower but still meaningful similarity
            # Adjust expected similarity for cross-language comparison
            adjusted_expected = pair.expected_similarity * 0.8  # Cross-language penalty
            accuracy = 1.0 - abs(predicted_similarity - adjusted_expected)
            accuracies.append(accuracy)

        return np.mean(accuracies) if accuracies else 0.0

    def get_evaluation_dataset_stats(self) -> Dict[str, Any]:
        """Get statistics about the evaluation dataset."""
        if not self.code_samples:
            return {"error": "No code samples loaded"}

        languages = {}
        categories = {}

        for sample in self.code_samples:
            languages[sample.language] = languages.get(sample.language, 0) + 1
            categories[sample.category] = categories.get(sample.category, 0) + 1

        return {
            "total_samples": len(self.code_samples),
            "total_similarity_pairs": len(self.similarity_pairs),
            "languages": languages,
            "categories": categories,
            "cross_language_pairs": len(
                [
                    p
                    for p in self.similarity_pairs
                    if p.sample1.language != p.sample2.language
                ]
            ),
        }
