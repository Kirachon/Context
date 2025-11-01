"""
Code Similarity Detection

Detects similar code patterns and structures across different programming languages.
"""

import logging
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from pathlib import Path
import hashlib

from src.parsing.models import ParseResult, SymbolInfo, ClassInfo, Language

logger = logging.getLogger(__name__)


@dataclass
class SimilarityMatch:
    """Represents a similarity match between code elements."""
    source_file: str
    source_symbol: str
    source_language: str
    target_file: str
    target_symbol: str
    target_language: str
    similarity_score: float
    similarity_type: str  # structural, semantic, functional
    evidence: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "source_language": self.source_language,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "target_language": self.target_language,
            "similarity_score": self.similarity_score,
            "similarity_type": self.similarity_type,
            "evidence": self.evidence
        }


@dataclass
class CodeSignature:
    """Represents a normalized signature of a code element."""
    name: str
    type: str
    parameter_count: int
    parameter_types: List[str]
    return_type: Optional[str]
    modifiers: Set[str]
    complexity_score: float
    
    def to_hash(self) -> str:
        """Generate hash for similarity comparison."""
        content = f"{self.type}:{self.parameter_count}:{':'.join(sorted(self.parameter_types))}:{self.return_type}:{':'.join(sorted(self.modifiers))}"
        return hashlib.md5(content.encode()).hexdigest()


class SimilarityDetector:
    """
    Code Similarity Detector
    
    Detects similar code patterns across different programming languages
    using structural, semantic, and functional analysis.
    """
    
    def __init__(self):
        """Initialize similarity detector."""
        self.language_normalizers = {
            Language.PYTHON: self._normalize_python_symbol,
            Language.JAVASCRIPT: self._normalize_javascript_symbol,
            Language.TYPESCRIPT: self._normalize_typescript_symbol,
            Language.JAVA: self._normalize_java_symbol,
            Language.CPP: self._normalize_cpp_symbol,
            Language.GO: self._normalize_go_symbol,
            Language.RUST: self._normalize_rust_symbol,
        }
        
        self.stats = {
            "comparisons_performed": 0,
            "similarities_found": 0,
            "cross_language_matches": 0
        }
        
        logger.info("SimilarityDetector initialized")
    
    def find_similarities(self, parse_results: List[ParseResult], 
                         min_similarity: float = 0.7) -> List[SimilarityMatch]:
        """
        Find similar code patterns across parse results.
        
        Args:
            parse_results: List of parse results to analyze
            min_similarity: Minimum similarity score to report
            
        Returns:
            List of similarity matches
        """
        logger.info(f"Finding similarities across {len(parse_results)} files")
        
        # Generate signatures for all symbols
        signatures = self._generate_signatures(parse_results)
        
        # Find matches
        matches = self._find_matches(signatures, min_similarity)
        
        # Update statistics
        self.stats["comparisons_performed"] += len(signatures) * (len(signatures) - 1) // 2
        self.stats["similarities_found"] = len(matches)
        self.stats["cross_language_matches"] = len([
            m for m in matches if m.source_language != m.target_language
        ])
        
        logger.info(f"Found {len(matches)} similarity matches")
        return matches
    
    def _generate_signatures(self, parse_results: List[ParseResult]) -> List[Tuple[CodeSignature, ParseResult, SymbolInfo]]:
        """Generate normalized signatures for all symbols."""
        signatures = []
        
        for result in parse_results:
            normalizer = self.language_normalizers.get(result.language)
            if not normalizer:
                logger.warning(f"No normalizer for language: {result.language}")
                continue
            
            for symbol in result.symbols:
                try:
                    signature = normalizer(symbol)
                    signatures.append((signature, result, symbol))
                except Exception as e:
                    logger.warning(f"Failed to normalize symbol {symbol.name}: {e}")
        
        return signatures
    
    def _find_matches(self, signatures: List[Tuple[CodeSignature, ParseResult, SymbolInfo]], 
                     min_similarity: float) -> List[SimilarityMatch]:
        """Find similarity matches between signatures."""
        matches = []
        
        for i, (sig1, result1, symbol1) in enumerate(signatures):
            for j, (sig2, result2, symbol2) in enumerate(signatures[i+1:], i+1):
                # Skip self-comparisons
                if result1.file_path == result2.file_path and symbol1.name == symbol2.name:
                    continue
                
                # Calculate similarity
                similarity_score, similarity_type, evidence = self._calculate_similarity(
                    sig1, sig2, symbol1, symbol2
                )
                
                if similarity_score >= min_similarity:
                    matches.append(SimilarityMatch(
                        source_file=str(result1.file_path),
                        source_symbol=symbol1.name,
                        source_language=result1.language.value,
                        target_file=str(result2.file_path),
                        target_symbol=symbol2.name,
                        target_language=result2.language.value,
                        similarity_score=similarity_score,
                        similarity_type=similarity_type,
                        evidence=evidence
                    ))
        
        return matches
    
    def _calculate_similarity(self, sig1: CodeSignature, sig2: CodeSignature,
                            symbol1: SymbolInfo, symbol2: SymbolInfo) -> Tuple[float, str, Dict[str, Any]]:
        """Calculate similarity between two code signatures."""
        evidence = {}
        similarity_components = []
        
        # Structural similarity
        structural_score = self._calculate_structural_similarity(sig1, sig2, evidence)
        similarity_components.append(("structural", structural_score, 0.4))
        
        # Semantic similarity
        semantic_score = self._calculate_semantic_similarity(symbol1, symbol2, evidence)
        similarity_components.append(("semantic", semantic_score, 0.4))
        
        # Functional similarity
        functional_score = self._calculate_functional_similarity(sig1, sig2, evidence)
        similarity_components.append(("functional", functional_score, 0.2))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in similarity_components)
        
        # Determine primary similarity type
        primary_type = max(similarity_components, key=lambda x: x[1])[0]
        
        return total_score, primary_type, evidence
    
    def _calculate_structural_similarity(self, sig1: CodeSignature, sig2: CodeSignature,
                                       evidence: Dict[str, Any]) -> float:
        """Calculate structural similarity between signatures."""
        score = 0.0
        
        # Type similarity
        if sig1.type == sig2.type:
            score += 0.3
            evidence["same_type"] = True
        
        # Parameter count similarity
        if sig1.parameter_count == sig2.parameter_count:
            score += 0.2
            evidence["same_parameter_count"] = True
        elif abs(sig1.parameter_count - sig2.parameter_count) <= 1:
            score += 0.1
            evidence["similar_parameter_count"] = True
        
        # Parameter type similarity
        if sig1.parameter_types and sig2.parameter_types:
            common_types = set(sig1.parameter_types) & set(sig2.parameter_types)
            type_similarity = len(common_types) / max(len(sig1.parameter_types), len(sig2.parameter_types))
            score += type_similarity * 0.2
            evidence["parameter_type_similarity"] = type_similarity
        
        # Return type similarity
        if sig1.return_type and sig2.return_type:
            if self._normalize_type(sig1.return_type) == self._normalize_type(sig2.return_type):
                score += 0.15
                evidence["same_return_type"] = True
        
        # Modifier similarity
        common_modifiers = sig1.modifiers & sig2.modifiers
        if common_modifiers:
            modifier_similarity = len(common_modifiers) / max(len(sig1.modifiers), len(sig2.modifiers))
            score += modifier_similarity * 0.15
            evidence["modifier_similarity"] = modifier_similarity
        
        return min(score, 1.0)
    
    def _calculate_semantic_similarity(self, symbol1: SymbolInfo, symbol2: SymbolInfo,
                                     evidence: Dict[str, Any]) -> float:
        """Calculate semantic similarity between symbols."""
        score = 0.0
        
        # Name similarity
        name_similarity = self._calculate_name_similarity(symbol1.name, symbol2.name)
        score += name_similarity * 0.4
        evidence["name_similarity"] = name_similarity
        
        # Documentation similarity
        if symbol1.docstring and symbol2.docstring:
            doc_similarity = self._calculate_text_similarity(symbol1.docstring, symbol2.docstring)
            score += doc_similarity * 0.3
            evidence["documentation_similarity"] = doc_similarity
        
        # Context similarity (parent class, etc.)
        if symbol1.parent_class and symbol2.parent_class:
            context_similarity = self._calculate_name_similarity(symbol1.parent_class, symbol2.parent_class)
            score += context_similarity * 0.3
            evidence["context_similarity"] = context_similarity
        
        return min(score, 1.0)

    def _calculate_functional_similarity(self, sig1: CodeSignature, sig2: CodeSignature,
                                       evidence: Dict[str, Any]) -> float:
        """Calculate functional similarity between signatures."""
        score = 0.0

        # Complexity similarity
        if sig1.complexity_score > 0 and sig2.complexity_score > 0:
            complexity_diff = abs(sig1.complexity_score - sig2.complexity_score)
            complexity_similarity = 1.0 - min(complexity_diff, 1.0)
            score += complexity_similarity * 0.5
            evidence["complexity_similarity"] = complexity_similarity

        # Signature hash similarity (exact structural match)
        if sig1.to_hash() == sig2.to_hash():
            score += 0.5
            evidence["exact_signature_match"] = True

        return min(score, 1.0)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        if name1 == name2:
            return 1.0

        # Normalize names (remove underscores, convert to lowercase)
        norm1 = name1.lower().replace('_', '').replace('-', '')
        norm2 = name2.lower().replace('_', '').replace('-', '')

        if norm1 == norm2:
            return 0.9

        # Check for common prefixes/suffixes
        if norm1.startswith(norm2) or norm2.startswith(norm1):
            return 0.7

        # Longest common prefix boost
        lcp_len = 0
        for c1, c2 in zip(norm1, norm2):
            if c1 == c2:
                lcp_len += 1
            else:
                break
        if lcp_len >= 6:
            return 0.7

        if norm1.endswith(norm2) or norm2.endswith(norm1):
            return 0.6

        # Token overlap (snake/camel)
        def split_tokens(s: str) -> List[str]:
            tokens = []
            buf = ''
            for ch in s:
                if ch in ['_', '-']:
                    if buf:
                        tokens.append(buf)
                        buf = ''
                elif ch.isupper():
                    if buf:
                        tokens.append(buf)
                    buf = ch.lower()
                else:
                    buf += ch
            if buf:
                tokens.append(buf)
            return tokens
        toks1 = split_tokens(name1)
        toks2 = split_tokens(name2)
        if toks1 and toks2:
            common = set(toks1) & set(toks2)
            token_overlap = len(common) / max(len(set(toks1)), len(set(toks2)))
            if token_overlap >= 0.5:
                return 0.6

        # Simple character overlap
        common_chars = set(norm1) & set(norm2)
        if common_chars:
            overlap = len(common_chars) / max(len(set(norm1)), len(set(norm2)))
            return overlap * 0.5

        return 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        common_words = words1 & words2
        return len(common_words) / max(len(words1), len(words2))

    def _normalize_type(self, type_str: str) -> str:
        """Normalize type strings for cross-language comparison."""
        if not type_str:
            return ""

        # Common type mappings
        type_mappings = {
            # String types
            "string": "string", "str": "string", "String": "string",
            # Integer types
            "int": "integer", "integer": "integer", "Integer": "integer", "i32": "integer", "i64": "integer",
            # Boolean types
            "bool": "boolean", "boolean": "boolean", "Boolean": "boolean",
            # Float types
            "float": "float", "double": "float", "f32": "float", "f64": "float",
            # Array/List types
            "list": "array", "List": "array", "array": "array", "Array": "array", "Vec": "array",
            # Map/Dict types
            "dict": "map", "Dict": "map", "map": "map", "Map": "map", "HashMap": "map", "hashmap": "map",
        }

        raw = type_str.strip()
        normalized = raw.lower()
        mapped = type_mappings.get(normalized)
        if mapped is not None:
            return mapped
        # If not a known primitive/container, preserve original (likely a domain type)
        return raw

    # Language-specific normalizers
    def _normalize_python_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize Python symbol to signature."""
        modifiers = set()
        if symbol.is_async:
            modifiers.add("async")
        if symbol.is_static:
            modifiers.add("static")
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        # Add decorators as modifiers
        modifiers.update(symbol.decorators)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("any")

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else None,
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_javascript_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize JavaScript symbol to signature."""
        modifiers = set()
        if symbol.is_async:
            modifiers.add("async")
        if symbol.is_static:
            modifiers.add("static")

        # JavaScript doesn't have explicit types, so we use 'any'
        parameter_types = ["any"] * len(symbol.parameters)

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type="any",  # JavaScript is dynamically typed
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_typescript_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize TypeScript symbol to signature."""
        modifiers = set()
        if symbol.is_async:
            modifiers.add("async")
        if symbol.is_static:
            modifiers.add("static")
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("any")

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else "any",
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_java_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize Java symbol to signature."""
        modifiers = set()
        if symbol.is_static:
            modifiers.add("static")
        if symbol.is_abstract:
            modifiers.add("abstract")
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("Object")

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else "void",
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_cpp_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize C++ symbol to signature."""
        modifiers = set()
        if symbol.is_static:
            modifiers.add("static")
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("auto")

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else "void",
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_go_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize Go symbol to signature."""
        modifiers = set()
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("interface{}")

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else "void",
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _normalize_rust_symbol(self, symbol: SymbolInfo) -> CodeSignature:
        """Normalize Rust symbol to signature."""
        modifiers = set()
        if symbol.visibility:
            modifiers.add(symbol.visibility)

        parameter_types = []
        for param in symbol.parameters:
            if param.type_hint:
                parameter_types.append(self._normalize_type(param.type_hint))
            else:
                parameter_types.append("_")  # Rust type inference

        return CodeSignature(
            name=symbol.name,
            type=symbol.type,
            parameter_count=len(symbol.parameters),
            parameter_types=parameter_types,
            return_type=self._normalize_type(symbol.return_type) if symbol.return_type else "()",
            modifiers=modifiers,
            complexity_score=self._estimate_symbol_complexity(symbol)
        )

    def _estimate_symbol_complexity(self, symbol: SymbolInfo) -> float:
        """Estimate complexity score for a symbol."""
        complexity = 0.0

        # Base complexity
        complexity += 1.0

        # Parameter complexity
        complexity += len(symbol.parameters) * 0.2

        # Modifier complexity
        if symbol.is_async:
            complexity += 0.5
        if symbol.is_static:
            complexity += 0.2
        if symbol.is_abstract:
            complexity += 0.3

        # Decorator complexity
        complexity += len(symbol.decorators) * 0.1

        return complexity

    def get_stats(self) -> Dict[str, Any]:
        """Get similarity detector statistics."""
        return self.stats.copy()


# Global similarity detector instance
_global_detector: Optional[SimilarityDetector] = None


def get_similarity_detector() -> SimilarityDetector:
    """Get the global similarity detector instance."""
    global _global_detector
    if _global_detector is None:
        _global_detector = SimilarityDetector()
    return _global_detector
