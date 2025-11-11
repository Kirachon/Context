"""
Query Expander

Expands queries using Word2Vec, CodeBERT embeddings, and custom mappings
to find synonyms and related terms.
"""

import logging
from typing import List, Dict, Set, Optional
import re

from .models import ExpandedTerm, QueryExpansion

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expands search queries with synonyms, related terms, and acronym expansions.

    Supports:
    - Word2Vec embeddings (optional)
    - CodeBERT embeddings (optional)
    - Manual synonym mappings
    - Acronym expansion
    """

    # Code-specific synonyms and related terms
    CODE_SYNONYMS = {
        "auth": ["authentication", "login", "signin", "authorize", "oauth", "jwt"],
        "authentication": ["auth", "login", "signin", "oauth", "jwt", "token"],
        "login": ["signin", "auth", "authentication", "session"],
        "api": ["endpoint", "route", "service", "interface", "rest"],
        "endpoint": ["api", "route", "handler", "controller"],
        "database": ["db", "storage", "persistence", "data"],
        "db": ["database", "storage", "sql", "nosql"],
        "error": ["exception", "failure", "bug", "issue"],
        "exception": ["error", "failure", "throw", "catch"],
        "test": ["spec", "testing", "unittest", "integration"],
        "config": ["configuration", "settings", "environment", "env"],
        "function": ["method", "procedure", "routine", "func"],
        "method": ["function", "procedure", "routine"],
        "class": ["type", "object", "model", "entity"],
        "variable": ["var", "field", "property", "attribute"],
        "file": ["module", "script", "document"],
        "frontend": ["client", "ui", "interface", "webapp"],
        "backend": ["server", "api", "service", "serverside"],
        "cache": ["memoize", "store", "buffer"],
        "query": ["search", "find", "select", "filter"],
        "validation": ["validate", "check", "verify", "sanitize"],
        "middleware": ["interceptor", "filter", "handler"],
        "model": ["schema", "entity", "type", "class"],
        "controller": ["handler", "endpoint", "route"],
        "service": ["logic", "business", "manager"],
        "util": ["utility", "helper", "tool", "common"],
        "helper": ["utility", "util", "tool", "common"],
    }

    # Common programming acronyms
    ACRONYMS = {
        "API": "Application Programming Interface",
        "REST": "Representational State Transfer",
        "HTTP": "Hypertext Transfer Protocol",
        "HTTPS": "Hypertext Transfer Protocol Secure",
        "URL": "Uniform Resource Locator",
        "URI": "Uniform Resource Identifier",
        "JWT": "JSON Web Token",
        "OAuth": "Open Authorization",
        "SQL": "Structured Query Language",
        "ORM": "Object-Relational Mapping",
        "CRUD": "Create Read Update Delete",
        "MVC": "Model View Controller",
        "MVP": "Model View Presenter",
        "MVVM": "Model View ViewModel",
        "SPA": "Single Page Application",
        "SSR": "Server-Side Rendering",
        "CSR": "Client-Side Rendering",
        "SSG": "Static Site Generation",
        "JSON": "JavaScript Object Notation",
        "XML": "Extensible Markup Language",
        "YAML": "YAML Ain't Markup Language",
        "CLI": "Command Line Interface",
        "GUI": "Graphical User Interface",
        "UI": "User Interface",
        "UX": "User Experience",
        "DB": "Database",
        "CI": "Continuous Integration",
        "CD": "Continuous Deployment",
        "AWS": "Amazon Web Services",
        "GCP": "Google Cloud Platform",
        "SDK": "Software Development Kit",
        "IDE": "Integrated Development Environment",
        "NPM": "Node Package Manager",
        "HTML": "Hypertext Markup Language",
        "CSS": "Cascading Style Sheets",
        "JS": "JavaScript",
        "TS": "TypeScript",
    }

    # Related concepts (hierarchical relationships)
    RELATED_CONCEPTS = {
        "authentication": ["session", "token", "password", "credentials", "security"],
        "authorization": ["permissions", "roles", "access", "rbac"],
        "database": ["table", "column", "row", "index", "query"],
        "api": ["request", "response", "status", "headers"],
        "testing": ["assert", "mock", "spy", "fixture"],
        "error": ["logging", "monitoring", "debugging"],
    }

    def __init__(self, use_word2vec: bool = False, use_codebert: bool = False):
        """
        Initialize query expander.

        Args:
            use_word2vec: Whether to use Word2Vec model (requires gensim)
            use_codebert: Whether to use CodeBERT model (requires transformers)
        """
        self.use_word2vec = use_word2vec
        self.use_codebert = use_codebert
        self.word2vec_model = None
        self.codebert_model = None
        self.codebert_tokenizer = None

        # Try to load Word2Vec
        if use_word2vec:
            try:
                from gensim.models import KeyedVectors
                # Try to load pre-trained model (would need to be downloaded)
                logger.info("Word2Vec enabled (model loading not implemented)")
                # self.word2vec_model = KeyedVectors.load_word2vec_format('path/to/model')
            except ImportError:
                logger.warning("gensim not installed. Word2Vec disabled.")
                self.use_word2vec = False

        # Try to load CodeBERT
        if use_codebert:
            try:
                from transformers import RobertaTokenizer, RobertaModel
                logger.info("CodeBERT enabled (model loading not implemented)")
                # self.codebert_tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base")
                # self.codebert_model = RobertaModel.from_pretrained("microsoft/codebert-base")
            except ImportError:
                logger.warning("transformers not installed. CodeBERT disabled.")
                self.use_codebert = False

    def expand(
        self,
        query: str,
        max_expansions: int = 10,
        min_relevance: float = 0.5
    ) -> QueryExpansion:
        """
        Expand query with synonyms and related terms.

        Args:
            query: Original query string
            max_expansions: Maximum number of expanded terms
            min_relevance: Minimum relevance score (0-1)

        Returns:
            QueryExpansion with expanded terms
        """
        expanded_terms: List[ExpandedTerm] = []
        synonyms: Dict[str, List[str]] = {}
        acronym_expansions: Dict[str, str] = {}
        related_concepts: List[str] = []

        # Tokenize query
        tokens = self._tokenize(query)

        # Process each token
        for token in tokens:
            token_lower = token.lower()

            # Manual synonyms
            if token_lower in self.CODE_SYNONYMS:
                syns = self.CODE_SYNONYMS[token_lower]
                synonyms[token] = syns[:5]  # Limit to top 5
                for syn in syns[:3]:
                    expanded_terms.append(
                        ExpandedTerm(
                            original=token,
                            expanded=syn,
                            relevance_score=0.9,
                            expansion_type="synonym",
                            source="manual"
                        )
                    )

            # Acronym expansion
            token_upper = token.upper()
            if token_upper in self.ACRONYMS:
                expansion = self.ACRONYMS[token_upper]
                acronym_expansions[token] = expansion
                expanded_terms.append(
                    ExpandedTerm(
                        original=token,
                        expanded=expansion,
                        relevance_score=1.0,
                        expansion_type="acronym",
                        source="manual"
                    )
                )

            # Related concepts
            if token_lower in self.RELATED_CONCEPTS:
                concepts = self.RELATED_CONCEPTS[token_lower]
                related_concepts.extend(concepts)
                for concept in concepts[:2]:
                    expanded_terms.append(
                        ExpandedTerm(
                            original=token,
                            expanded=concept,
                            relevance_score=0.8,
                            expansion_type="related",
                            source="manual"
                        )
                    )

            # Word2Vec expansion (if available)
            if self.use_word2vec and self.word2vec_model:
                w2v_terms = self._expand_word2vec(token, max_expansions=3)
                expanded_terms.extend(w2v_terms)

            # CodeBERT expansion (if available)
            if self.use_codebert and self.codebert_model:
                codebert_terms = self._expand_codebert(token, max_expansions=3)
                expanded_terms.extend(codebert_terms)

        # Filter by relevance and limit
        expanded_terms = [
            term for term in expanded_terms
            if term.relevance_score >= min_relevance
        ]
        expanded_terms = expanded_terms[:max_expansions]

        return QueryExpansion(
            original_query=query,
            expanded_terms=expanded_terms,
            synonyms=synonyms,
            acronym_expansions=acronym_expansions,
            related_concepts=related_concepts
        )

    def _tokenize(self, query: str) -> List[str]:
        """Tokenize query into words"""
        # Split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', query)
        return [t for t in tokens if len(t) > 1]

    def _expand_word2vec(self, term: str, max_expansions: int = 3) -> List[ExpandedTerm]:
        """Expand term using Word2Vec model"""
        if not self.word2vec_model:
            return []

        try:
            # Get similar words
            similar = self.word2vec_model.most_similar(term.lower(), topn=max_expansions)
            return [
                ExpandedTerm(
                    original=term,
                    expanded=word,
                    relevance_score=float(score),
                    expansion_type="similar",
                    source="word2vec"
                )
                for word, score in similar
            ]
        except KeyError:
            # Term not in vocabulary
            return []

    def _expand_codebert(self, term: str, max_expansions: int = 3) -> List[ExpandedTerm]:
        """Expand term using CodeBERT model"""
        if not self.codebert_model or not self.codebert_tokenizer:
            return []

        # CodeBERT expansion would involve:
        # 1. Encoding the term
        # 2. Finding similar embeddings
        # 3. Decoding to terms
        # This is a placeholder for actual implementation
        return []

    def expand_concept(self, concept: str) -> Set[str]:
        """
        Expand a single concept to all related terms.

        Args:
            concept: Concept to expand

        Returns:
            Set of related terms
        """
        terms = {concept}
        concept_lower = concept.lower()

        # Add synonyms
        if concept_lower in self.CODE_SYNONYMS:
            terms.update(self.CODE_SYNONYMS[concept_lower])

        # Add related concepts
        if concept_lower in self.RELATED_CONCEPTS:
            terms.update(self.RELATED_CONCEPTS[concept_lower])

        # Add acronym expansion
        concept_upper = concept.upper()
        if concept_upper in self.ACRONYMS:
            terms.add(self.ACRONYMS[concept_upper])

        return terms

    def get_synonyms(self, term: str) -> List[str]:
        """Get synonyms for a term"""
        term_lower = term.lower()
        return self.CODE_SYNONYMS.get(term_lower, [])

    def expand_acronym(self, acronym: str) -> Optional[str]:
        """Expand acronym to full form"""
        return self.ACRONYMS.get(acronym.upper())

    def is_code_concept(self, term: str) -> bool:
        """Check if term is a known code concept"""
        term_lower = term.lower()
        return (
            term_lower in self.CODE_SYNONYMS or
            term_lower in self.RELATED_CONCEPTS or
            term.upper() in self.ACRONYMS
        )

    def add_custom_synonym(self, term: str, synonyms: List[str]):
        """Add custom synonym mapping"""
        term_lower = term.lower()
        if term_lower in self.CODE_SYNONYMS:
            self.CODE_SYNONYMS[term_lower].extend(synonyms)
        else:
            self.CODE_SYNONYMS[term_lower] = synonyms

    def add_custom_acronym(self, acronym: str, expansion: str):
        """Add custom acronym expansion"""
        self.ACRONYMS[acronym.upper()] = expansion
