"""
Tree-sitter Language Loader

Provides runtime loading of Tree-sitter language parsers with fallback support.
Tries prebuilt language pack first, then falls back to compiled libraries.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict
from tree_sitter import Language

logger = logging.getLogger(__name__)


class TreeSitterLoader:
    """
    Tree-sitter language loader with fallback support.
    
    Attempts to load languages in the following order:
    1. Prebuilt languages from tree_sitter_languages package
    2. Compiled language library (my-languages.dll/so/dylib)
    3. Raises exception if neither is available
    """
    
    def __init__(self):
        """Initialize the loader."""
        self._languages: Dict[str, Language] = {}
        self._build_path = Path(__file__).parent / "_build"
        
        # Language name mappings
        self._language_mappings = {
            "python": "python",
            "javascript": "javascript", 
            "typescript": "typescript",
            "java": "java",
            "cpp": "cpp",
            "go": "go",
            "rust": "rust"
        }
        
        logger.info("TreeSitterLoader initialized")
    
    def load_language(self, name: str) -> Language:
        """
        Load a Tree-sitter language by name.
        
        Args:
            name: Language name (python, javascript, typescript, java, cpp, go, rust)
            
        Returns:
            Language: Tree-sitter Language object
            
        Raises:
            ValueError: If language name is not supported
            RuntimeError: If language cannot be loaded
        """
        if name in self._languages:
            return self._languages[name]
        
        if name not in self._language_mappings:
            raise ValueError(f"Unsupported language: {name}. Supported: {list(self._language_mappings.keys())}")
        
        mapped_name = self._language_mappings[name]
        
        # Try prebuilt languages first
        try:
            language = self._load_prebuilt_language(mapped_name)
            self._languages[name] = language
            logger.debug(f"Loaded prebuilt language: {name}")
            return language
        except Exception as e:
            logger.debug(f"Failed to load prebuilt language {name}: {e}")
        
        # Try compiled library fallback
        try:
            language = self._load_compiled_language(mapped_name)
            self._languages[name] = language
            logger.debug(f"Loaded compiled language: {name}")
            return language
        except Exception as e:
            logger.debug(f"Failed to load compiled language {name}: {e}")
        
        raise RuntimeError(f"Could not load Tree-sitter language: {name}")
    
    def _load_prebuilt_language(self, name: str):
        """Load language from per-language tree_sitter_* packages (0.25+)."""
        # Map language name to module and function providing the PyCapsule
        module_map = {
            "python": ("tree_sitter_python", "language"),
            "javascript": ("tree_sitter_javascript", "language"),
            "typescript": ("tree_sitter_typescript", "language_typescript"),
            "java": ("tree_sitter_java", "language"),
            "cpp": ("tree_sitter_cpp", "language"),
            "go": ("tree_sitter_go", "language"),
            "rust": ("tree_sitter_rust", "language"),
        }
        if name not in module_map:
            raise RuntimeError(f"Unsupported language: {name}")
        mod_name, func_name = module_map[name]
        try:
            from tree_sitter import Language as TS_Language
            mod = __import__(mod_name, fromlist=[func_name])
            lang_fn = getattr(mod, func_name)
            capsule = lang_fn()
            return TS_Language(capsule)
        except Exception as e:
            raise RuntimeError(f"Failed to load prebuilt language {name} from {mod_name}.{func_name}: {e}")

    def _load_compiled_language(self, name: str) -> Language:
        """Load language from compiled library."""
        # Determine library extension based on platform
        if os.name == "nt":  # Windows
            lib_ext = ".dll"
        elif sys.platform == "darwin":  # macOS
            lib_ext = ".dylib"
        else:  # Linux and others
            lib_ext = ".so"
        
        lib_path = self._build_path / f"my-languages{lib_ext}"
        
        if not lib_path.exists():
            raise RuntimeError(f"Compiled language library not found: {lib_path}")
        
        try:
            return Language(str(lib_path), name)
        except Exception as e:
            raise RuntimeError(f"Failed to load compiled language {name} from {lib_path}: {e}")
    
    def get_available_languages(self) -> list[str]:
        """Get list of available language names."""
        return list(self._language_mappings.keys())
    
    def is_language_available(self, name: str) -> bool:
        """Check if a language is available for loading."""
        if name not in self._language_mappings:
            return False
        
        try:
            self.load_language(name)
            return True
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the language cache."""
        self._languages.clear()
        logger.debug("Language cache cleared")


# Global loader instance
_global_loader: Optional[TreeSitterLoader] = None


def get_loader() -> TreeSitterLoader:
    """Get the global Tree-sitter loader instance."""
    global _global_loader
    if _global_loader is None:
        _global_loader = TreeSitterLoader()
    return _global_loader


def load_language(name: str) -> Language:
    """
    Load a Tree-sitter language by name.
    
    Convenience function that uses the global loader instance.
    
    Args:
        name: Language name (python, javascript, typescript, java, cpp, go, rust)
        
    Returns:
        Language: Tree-sitter Language object
    """
    return get_loader().load_language(name)


def get_available_languages() -> list[str]:
    """Get list of available language names."""
    return get_loader().get_available_languages()


def is_language_available(name: str) -> bool:
    """Check if a language is available for loading."""
    return get_loader().is_language_available(name)
