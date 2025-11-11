"""
Search Templates

Pre-built query templates for common search patterns like finding API endpoints,
authentication logic, database models, error handling, etc.
"""

import logging
from typing import Dict, List, Optional
import re

from .models import SearchTemplate, Intent

logger = logging.getLogger(__name__)


class SearchTemplateManager:
    """
    Manages pre-built search templates.

    Provides:
    - Built-in templates for common patterns
    - Custom user-defined templates
    - Template parameter substitution
    """

    # Built-in templates
    BUILTIN_TEMPLATES = [
        SearchTemplate(
            name="api_endpoints",
            description="Find all API endpoints and route handlers",
            query_pattern="route handler endpoint api controller",
            intent=Intent.LIST,
            default_filters={
                "file_types": [".py", ".js", ".ts", ".go", ".rb"],
            },
            search_type="ast",
            examples=[
                "Find all API endpoints",
                "Show me all route handlers",
                "List REST endpoints"
            ]
        ),
        SearchTemplate(
            name="authentication",
            description="Find authentication and authorization logic",
            query_pattern="authentication login signin oauth jwt token session authorize",
            intent=Intent.FIND,
            default_filters={},
            search_type="semantic",
            examples=[
                "Show authentication logic",
                "Find login implementation",
                "Where is JWT handled"
            ]
        ),
        SearchTemplate(
            name="database_models",
            description="Find database models and schemas",
            query_pattern="model schema table entity orm database",
            intent=Intent.LIST,
            default_filters={
                "file_types": [".py", ".js", ".ts", ".go", ".rb"],
            },
            search_type="ast",
            examples=[
                "List all database models",
                "Show ORM schemas",
                "Find table definitions"
            ]
        ),
        SearchTemplate(
            name="error_handling",
            description="Find error handling and exception code",
            query_pattern="error exception try catch throw handle failure",
            intent=Intent.FIND,
            default_filters={},
            search_type="keyword",
            examples=[
                "Find error handling",
                "Show exception handlers",
                "Where are errors caught"
            ]
        ),
        SearchTemplate(
            name="configuration",
            description="Find configuration files and settings",
            query_pattern="config configuration settings environment env",
            intent=Intent.FIND,
            default_filters={
                "file_types": [".json", ".yaml", ".yml", ".toml", ".ini", ".env"],
            },
            search_type="keyword",
            examples=[
                "Show configuration files",
                "Find environment settings",
                "Where is config defined"
            ]
        ),
        SearchTemplate(
            name="tests",
            description="Find test files and test cases",
            query_pattern="test spec unittest integration assert",
            intent=Intent.LIST,
            default_filters={
                "directories": ["test", "tests", "__tests__", "spec"],
            },
            search_type="keyword",
            examples=[
                "List all tests",
                "Show test files",
                "Find unit tests"
            ]
        ),
        SearchTemplate(
            name="components",
            description="Find React/Vue components",
            query_pattern="component {component_name}",
            intent=Intent.FIND,
            default_filters={
                "file_types": [".jsx", ".tsx", ".vue"],
            },
            parameters=["component_name"],
            search_type="semantic",
            examples=[
                "Find Button component",
                "Show Header component",
                "Where is Modal component"
            ]
        ),
        SearchTemplate(
            name="api_client",
            description="Find API client and HTTP request code",
            query_pattern="fetch axios http request api call client",
            intent=Intent.FIND,
            default_filters={},
            search_type="keyword",
            examples=[
                "Find API calls",
                "Show HTTP requests",
                "Where are fetch calls"
            ]
        ),
        SearchTemplate(
            name="database_queries",
            description="Find SQL queries and database operations",
            query_pattern="select insert update delete query sql",
            intent=Intent.FIND,
            default_filters={},
            search_type="keyword",
            examples=[
                "Find SQL queries",
                "Show database operations",
                "Where are SELECT statements"
            ]
        ),
        SearchTemplate(
            name="validation",
            description="Find validation and input sanitization code",
            query_pattern="validate validation sanitize check verify",
            intent=Intent.FIND,
            default_filters={},
            search_type="semantic",
            examples=[
                "Find validation logic",
                "Show input validation",
                "Where is data validated"
            ]
        ),
        SearchTemplate(
            name="middleware",
            description="Find middleware and request interceptors",
            query_pattern="middleware interceptor filter handler",
            intent=Intent.LIST,
            default_filters={},
            search_type="keyword",
            examples=[
                "List all middleware",
                "Show request interceptors",
                "Find middleware functions"
            ]
        ),
        SearchTemplate(
            name="utils",
            description="Find utility and helper functions",
            query_pattern="utility helper util common tool",
            intent=Intent.FIND,
            default_filters={
                "directories": ["utils", "helpers", "lib", "common"],
            },
            search_type="semantic",
            examples=[
                "Find utility functions",
                "Show helper methods",
                "Where are common utilities"
            ]
        ),
        SearchTemplate(
            name="hooks",
            description="Find React hooks",
            query_pattern="use{hook_name} hook custom hook",
            intent=Intent.FIND,
            default_filters={
                "file_types": [".js", ".jsx", ".ts", ".tsx"],
            },
            parameters=["hook_name"],
            search_type="keyword",
            examples=[
                "Find useState hook",
                "Show custom hooks",
                "Where is useEffect"
            ]
        ),
        SearchTemplate(
            name="styles",
            description="Find stylesheets and styling code",
            query_pattern="style css stylesheet theme",
            intent=Intent.FIND,
            default_filters={
                "file_types": [".css", ".scss", ".sass", ".less", ".styled.ts", ".styled.js"],
            },
            search_type="keyword",
            examples=[
                "Find stylesheets",
                "Show CSS files",
                "Where are styles defined"
            ]
        ),
        SearchTemplate(
            name="types",
            description="Find type definitions and interfaces",
            query_pattern="type interface typedef {type_name}",
            intent=Intent.FIND,
            default_filters={
                "file_types": [".ts", ".tsx", ".d.ts"],
            },
            parameters=["type_name"],
            search_type="ast",
            examples=[
                "Find User type",
                "Show interface definitions",
                "Where is type defined"
            ]
        ),
        SearchTemplate(
            name="constants",
            description="Find constants and enums",
            query_pattern="const constant enum {constant_name}",
            intent=Intent.FIND,
            default_filters={},
            parameters=["constant_name"],
            search_type="keyword",
            examples=[
                "Find API_URL constant",
                "Show all constants",
                "Where are enums defined"
            ]
        ),
        SearchTemplate(
            name="logging",
            description="Find logging and debugging code",
            query_pattern="log logger logging debug console print",
            intent=Intent.FIND,
            default_filters={},
            search_type="keyword",
            examples=[
                "Find logging code",
                "Show console.log statements",
                "Where is debugging"
            ]
        ),
        SearchTemplate(
            name="security",
            description="Find security-related code",
            query_pattern="security authentication authorization encryption hash crypto",
            intent=Intent.FIND,
            default_filters={},
            search_type="semantic",
            examples=[
                "Find security code",
                "Show encryption logic",
                "Where is authentication"
            ]
        ),
    ]

    def __init__(self):
        """Initialize template manager"""
        self.templates: Dict[str, SearchTemplate] = {}
        self.custom_templates: Dict[str, SearchTemplate] = {}

        # Load built-in templates
        for template in self.BUILTIN_TEMPLATES:
            self.templates[template.name] = template

        logger.info(f"Loaded {len(self.templates)} built-in search templates")

    def get_template(self, name: str) -> Optional[SearchTemplate]:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            SearchTemplate or None if not found
        """
        # Check custom templates first
        if name in self.custom_templates:
            return self.custom_templates[name]

        # Check built-in templates
        return self.templates.get(name)

    def list_templates(self, category: Optional[str] = None) -> List[SearchTemplate]:
        """
        List all available templates.

        Args:
            category: Optional category filter

        Returns:
            List of templates
        """
        all_templates = list(self.templates.values()) + list(self.custom_templates.values())

        if category:
            # Filter by search_type as category
            all_templates = [t for t in all_templates if t.search_type == category]

        return all_templates

    def apply_template(self, name: str, **params) -> Optional[str]:
        """
        Apply template with parameters.

        Args:
            name: Template name
            **params: Template parameters

        Returns:
            Filled query string or None if template not found
        """
        template = self.get_template(name)
        if not template:
            logger.warning(f"Template not found: {name}")
            return None

        # Apply parameters
        query = template.apply(**params)

        logger.debug(f"Applied template '{name}': {query}")
        return query

    def add_custom_template(self, template: SearchTemplate):
        """
        Add a custom user-defined template.

        Args:
            template: SearchTemplate to add
        """
        self.custom_templates[template.name] = template
        logger.info(f"Added custom template: {template.name}")

    def remove_custom_template(self, name: str) -> bool:
        """
        Remove a custom template.

        Args:
            name: Template name

        Returns:
            True if removed, False if not found
        """
        if name in self.custom_templates:
            del self.custom_templates[name]
            logger.info(f"Removed custom template: {name}")
            return True
        return False

    def match_template(self, query: str) -> Optional[SearchTemplate]:
        """
        Try to match a query to a template.

        Args:
            query: Natural language query

        Returns:
            Matching template or None
        """
        query_lower = query.lower()

        # Check for template keywords
        for template in self.list_templates():
            # Check examples
            for example in template.examples:
                if self._similarity(query_lower, example.lower()) > 0.7:
                    logger.debug(f"Matched query to template '{template.name}'")
                    return template

            # Check description keywords
            desc_words = set(template.description.lower().split())
            query_words = set(query_lower.split())
            overlap = len(desc_words & query_words)
            if overlap >= 2:
                logger.debug(f"Matched query to template '{template.name}' (keyword overlap)")
                return template

        return None

    def suggest_templates(self, query: str, limit: int = 3) -> List[SearchTemplate]:
        """
        Suggest templates based on query.

        Args:
            query: Natural language query
            limit: Maximum number of suggestions

        Returns:
            List of suggested templates
        """
        query_lower = query.lower()
        scored_templates = []

        for template in self.list_templates():
            score = 0.0

            # Score based on description
            desc_words = set(template.description.lower().split())
            query_words = set(query_lower.split())
            overlap = len(desc_words & query_words)
            score += overlap * 0.3

            # Score based on examples
            for example in template.examples:
                similarity = self._similarity(query_lower, example.lower())
                score += similarity * 0.5

            # Score based on intent keywords
            intent_keywords = {
                Intent.FIND: ["find", "where", "show", "get"],
                Intent.LIST: ["list", "all", "enumerate"],
                Intent.EXPLAIN: ["explain", "what", "how"],
            }

            if template.intent in intent_keywords:
                for keyword in intent_keywords[template.intent]:
                    if keyword in query_lower:
                        score += 0.2

            if score > 0:
                scored_templates.append((template, score))

        # Sort by score and return top N
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored_templates[:limit]]

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple word-overlap similarity between two strings"""
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def create_template_from_query(
        self,
        name: str,
        query: str,
        description: str,
        intent: Intent = Intent.SEARCH
    ) -> SearchTemplate:
        """
        Create a new template from a query.

        Args:
            name: Template name
            query: Query pattern
            description: Template description
            intent: Query intent

        Returns:
            New SearchTemplate
        """
        # Extract parameters (words in {braces})
        parameters = re.findall(r'\{(\w+)\}', query)

        template = SearchTemplate(
            name=name,
            description=description,
            query_pattern=query,
            intent=intent,
            parameters=parameters,
            examples=[query]
        )

        logger.info(f"Created template: {name}")
        return template

    def export_templates(self) -> List[Dict]:
        """Export all custom templates to JSON-serializable format"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "query_pattern": t.query_pattern,
                "intent": t.intent.value,
                "default_filters": t.default_filters,
                "parameters": t.parameters,
                "examples": t.examples,
                "search_type": t.search_type
            }
            for t in self.custom_templates.values()
        ]

    def import_templates(self, templates_data: List[Dict]):
        """Import templates from JSON data"""
        for data in templates_data:
            template = SearchTemplate(
                name=data["name"],
                description=data["description"],
                query_pattern=data["query_pattern"],
                intent=Intent(data["intent"]),
                default_filters=data.get("default_filters", {}),
                parameters=data.get("parameters", []),
                examples=data.get("examples", []),
                search_type=data.get("search_type", "semantic")
            )
            self.add_custom_template(template)

        logger.info(f"Imported {len(templates_data)} templates")
