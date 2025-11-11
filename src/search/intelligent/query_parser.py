"""
Query Parser

NLP-based query parser using spaCy for entity extraction, intent detection,
and query understanding.
"""

import re
from typing import List, Optional, Dict, Any
import logging

from .models import ParsedQuery, Entity, EntityType, Intent

logger = logging.getLogger(__name__)


class QueryParser:
    """
    Parses natural language queries using NLP techniques.

    Uses spaCy for:
    - Tokenization
    - Entity extraction
    - Part-of-speech tagging
    - Intent detection
    """

    # Intent keywords mapping
    INTENT_KEYWORDS = {
        Intent.FIND: ["find", "search", "locate", "where", "get"],
        Intent.LIST: ["list", "show all", "enumerate", "display"],
        Intent.SHOW: ["show", "display", "view", "open", "reveal"],
        Intent.EXPLAIN: ["explain", "describe", "what", "how", "why"],
        Intent.COMPARE: ["compare", "difference", "vs", "versus", "between"],
    }

    # Code-specific entity patterns
    CODE_PATTERNS = {
        EntityType.FILE_NAME: [
            r"\b[\w\-]+\.(py|js|ts|tsx|jsx|java|cpp|c|h|go|rs|rb|php)\b",
            r"\b[\w\-]+\.[\w]+\b",
        ],
        EntityType.FUNCTION_NAME: [
            r"\b[a-z_][a-z0-9_]*\(\)",
            r"\bdef\s+([a-z_][a-z0-9_]*)",
            r"\bfunction\s+([a-z_][a-z0-9_]*)",
        ],
        EntityType.CLASS_NAME: [
            r"\bclass\s+([A-Z][a-zA-Z0-9]*)",
            r"\b[A-Z][a-zA-Z0-9]*(?:Class|Service|Controller|Manager)\b",
        ],
    }

    # Common code concepts
    CODE_CONCEPTS = {
        "auth": ["authentication", "login", "signin", "jwt", "oauth", "token", "session"],
        "api": ["endpoint", "route", "handler", "controller", "rest", "graphql"],
        "database": ["db", "sql", "query", "model", "schema", "orm", "migration"],
        "error": ["exception", "error handling", "try", "catch", "throw"],
        "test": ["testing", "spec", "unit test", "integration test"],
        "config": ["configuration", "settings", "environment", "env"],
    }

    def __init__(self, use_spacy: bool = True):
        """
        Initialize query parser.

        Args:
            use_spacy: Whether to use spaCy (requires installation)
        """
        self.use_spacy = use_spacy
        self.nlp = None

        if use_spacy:
            try:
                import spacy
                # Try to load model
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("Loaded spaCy model: en_core_web_sm")
                except OSError:
                    logger.warning(
                        "spaCy model 'en_core_web_sm' not found. "
                        "Install with: python -m spacy download en_core_web_sm"
                    )
                    self.use_spacy = False
            except ImportError:
                logger.warning("spaCy not installed. Using fallback parser.")
                self.use_spacy = False

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse natural language query.

        Args:
            query: Natural language query string

        Returns:
            ParsedQuery with entities, intent, and expanded terms
        """
        # Clean query
        query = query.strip()

        if self.use_spacy and self.nlp:
            return self._parse_with_spacy(query)
        else:
            return self._parse_fallback(query)

    def _parse_with_spacy(self, query: str) -> ParsedQuery:
        """Parse using spaCy NLP"""
        doc = self.nlp(query)

        # Extract entities
        entities = []

        # spaCy named entities
        for ent in doc.ents:
            entity_type = self._map_spacy_entity_type(ent.label_)
            entities.append(
                Entity(
                    text=ent.text,
                    type=entity_type,
                    confidence=0.8,
                    start_pos=ent.start_char,
                    end_pos=ent.end_char
                )
            )

        # Code-specific patterns
        entities.extend(self._extract_code_entities(query))

        # Extract keywords (content words)
        keywords = [
            token.text.lower()
            for token in doc
            if not token.is_stop and not token.is_punct and len(token.text) > 2
        ]

        # Lemmatize
        lemmatized = [
            token.lemma_.lower()
            for token in doc
            if not token.is_stop and not token.is_punct
        ]

        # Detect intent
        intent = self._detect_intent(query, doc)

        # Expand terms
        expanded_terms = self._expand_query_terms(keywords)

        # Calculate confidence based on entity quality
        confidence = self._calculate_confidence(entities, intent, keywords)

        return ParsedQuery(
            original=query,
            entities=entities,
            intent=intent,
            expanded_terms=expanded_terms,
            confidence=confidence,
            keywords=keywords,
            lemmatized_terms=lemmatized
        )

    def _parse_fallback(self, query: str) -> ParsedQuery:
        """Fallback parser without spaCy"""
        # Simple tokenization
        tokens = re.findall(r'\b\w+\b', query.lower())

        # Extract entities using patterns
        entities = self._extract_code_entities(query)

        # Simple stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "is", "are", "was"
        }

        keywords = [t for t in tokens if t not in stop_words and len(t) > 2]

        # Detect intent
        intent = self._detect_intent_simple(query.lower())

        # Expand terms
        expanded_terms = self._expand_query_terms(keywords)

        # Calculate confidence
        confidence = 0.7 if entities else 0.6  # Lower confidence without spaCy

        return ParsedQuery(
            original=query,
            entities=entities,
            intent=intent,
            expanded_terms=expanded_terms,
            confidence=confidence,
            keywords=keywords,
            lemmatized_terms=keywords  # No lemmatization in fallback
        )

    def _extract_code_entities(self, query: str) -> List[Entity]:
        """Extract code-specific entities using regex patterns"""
        entities = []

        for entity_type, patterns in self.CODE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query, re.IGNORECASE)
                for match in matches:
                    entities.append(
                        Entity(
                            text=match.group(0),
                            type=entity_type,
                            confidence=0.9,
                            start_pos=match.start(),
                            end_pos=match.end()
                        )
                    )

        return entities

    def _detect_intent(self, query: str, doc: Any) -> Intent:
        """Detect query intent using spaCy doc"""
        query_lower = query.lower()

        # Check for intent keywords
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent

        # Use verb analysis
        verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
        if verbs:
            verb = verbs[0]
            if verb in ["find", "search", "locate", "get"]:
                return Intent.FIND
            elif verb in ["show", "display", "view"]:
                return Intent.SHOW
            elif verb in ["list", "enumerate"]:
                return Intent.LIST
            elif verb in ["explain", "describe"]:
                return Intent.EXPLAIN

        # Default to SEARCH
        return Intent.SEARCH

    def _detect_intent_simple(self, query: str) -> Intent:
        """Simple intent detection without spaCy"""
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in query for keyword in keywords):
                return intent
        return Intent.SEARCH

    def _map_spacy_entity_type(self, spacy_label: str) -> EntityType:
        """Map spaCy entity labels to our EntityType"""
        mapping = {
            "PERSON": EntityType.CONCEPT,
            "ORG": EntityType.MODULE_NAME,
            "PRODUCT": EntityType.CONCEPT,
            "GPE": EntityType.CONCEPT,
        }
        return mapping.get(spacy_label, EntityType.KEYWORD)

    def _expand_query_terms(self, keywords: List[str]) -> List[str]:
        """Expand query terms with synonyms and related concepts"""
        expanded = set()

        for keyword in keywords:
            # Add original
            expanded.add(keyword)

            # Check code concepts
            keyword_lower = keyword.lower()
            if keyword_lower in self.CODE_CONCEPTS:
                expanded.update(self.CODE_CONCEPTS[keyword_lower])

            # Check if it's a concept that expands to keywords
            for concept, related in self.CODE_CONCEPTS.items():
                if keyword_lower in related:
                    expanded.add(concept)
                    expanded.update(related)

        return list(expanded)

    def _calculate_confidence(
        self, entities: List[Entity], intent: Intent, keywords: List[str]
    ) -> float:
        """Calculate confidence score for parsed query"""
        confidence = 0.5  # Base confidence

        # Boost for entities found
        if entities:
            confidence += 0.2 * min(len(entities), 3) / 3

        # Boost for clear intent
        if intent != Intent.UNKNOWN:
            confidence += 0.15

        # Boost for good keywords
        if len(keywords) >= 2:
            confidence += 0.15

        return min(confidence, 1.0)

    def extract_file_patterns(self, query: str) -> List[str]:
        """Extract file patterns from query (e.g., *.py, auth.js)"""
        patterns = []

        # Match file extensions
        ext_matches = re.findall(r'\*\.(\w+)', query)
        patterns.extend([f"*.{ext}" for ext in ext_matches])

        # Match specific file names
        file_matches = re.findall(r'\b([\w\-]+\.\w+)\b', query)
        patterns.extend(file_matches)

        return patterns

    def extract_directory_hints(self, query: str) -> List[str]:
        """Extract directory hints from query (e.g., 'in backend', 'frontend')"""
        hints = []

        # Common directory keywords
        dir_keywords = [
            "backend", "frontend", "client", "server", "api", "src", "lib",
            "components", "models", "views", "controllers", "services",
            "utils", "helpers", "tests"
        ]

        query_lower = query.lower()
        for keyword in dir_keywords:
            if keyword in query_lower:
                hints.append(keyword)

        # Extract paths
        path_matches = re.findall(r'[\w/]+/[\w/]+', query)
        hints.extend(path_matches)

        return hints
