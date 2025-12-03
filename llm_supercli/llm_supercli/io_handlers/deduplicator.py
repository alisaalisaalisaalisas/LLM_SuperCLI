"""
Output deduplicator for llm_supercli.
Removes duplicate content from LLM responses to ensure clean output.
"""
import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class DeduplicationResult:
    """Result of deduplication operation."""
    original_content: str
    deduplicated_content: str
    duplicates_removed: int
    
    @property
    def had_duplicates(self) -> bool:
        """Check if any duplicates were removed."""
        return self.duplicates_removed > 0


class OutputDeduplicator:
    """
    Removes duplicate paragraphs/sections from LLM output.
    
    Uses content hashing to detect duplicates and preserves
    the first occurrence while removing subsequent ones.
    """
    
    # Minimum length for a section to be considered for deduplication
    MIN_SECTION_LENGTH = 20
    
    # Patterns that indicate section boundaries
    SECTION_SEPARATORS = [
        r'\n\n+',           # Multiple newlines
        r'\n---+\n',        # Horizontal rules
        r'\n\*\*\*+\n',     # Asterisk separators
        r'\n#{1,6}\s',      # Markdown headers
    ]
    
    def __init__(self, min_section_length: int = MIN_SECTION_LENGTH) -> None:
        """
        Initialize deduplicator.
        
        Args:
            min_section_length: Minimum length for sections to deduplicate
        """
        self._min_section_length = min_section_length
        self._seen_hashes: Set[str] = set()
    
    def deduplicate(self, content: str) -> str:
        """
        Remove duplicate paragraphs/sections from content.
        
        Args:
            content: The content to deduplicate
            
        Returns:
            Content with duplicates removed
        """
        if not content or not content.strip():
            return content
        
        # Reset seen hashes for each deduplication call
        self._seen_hashes.clear()
        
        # Split content into sections
        sections = self._split_into_sections(content)
        
        # Filter out duplicates, preserving first occurrence
        unique_sections: List[str] = []
        for section in sections:
            if self._is_unique(section):
                unique_sections.append(section)
        
        # Rejoin sections
        return self._join_sections(unique_sections)
    
    def deduplicate_with_result(self, content: str) -> DeduplicationResult:
        """
        Remove duplicates and return detailed result.
        
        Args:
            content: The content to deduplicate
            
        Returns:
            DeduplicationResult with original, deduplicated content and stats
        """
        if not content or not content.strip():
            return DeduplicationResult(
                original_content=content,
                deduplicated_content=content,
                duplicates_removed=0
            )
        
        # Reset seen hashes
        self._seen_hashes.clear()
        
        # Split content into sections
        sections = self._split_into_sections(content)
        original_count = len(sections)
        
        # Filter out duplicates
        unique_sections: List[str] = []
        for section in sections:
            if self._is_unique(section):
                unique_sections.append(section)
        
        deduplicated = self._join_sections(unique_sections)
        duplicates_removed = original_count - len(unique_sections)
        
        return DeduplicationResult(
            original_content=content,
            deduplicated_content=deduplicated,
            duplicates_removed=duplicates_removed
        )
    
    def _split_into_sections(self, content: str) -> List[str]:
        """
        Split content into logical sections.
        
        Uses paragraph breaks (double newlines) as primary separator.
        """
        # Primary split on double newlines
        sections = re.split(r'\n\n+', content)
        
        # Filter out empty sections
        return [s for s in sections if s.strip()]
    
    def _is_unique(self, section: str) -> bool:
        """
        Check if a section is unique (not seen before).
        
        Short sections are always considered unique to avoid
        removing common phrases.
        """
        normalized = self._normalize(section)
        
        # Short sections are always unique
        if len(normalized) < self._min_section_length:
            return True
        
        # Hash the normalized content
        content_hash = self._hash_content(normalized)
        
        if content_hash in self._seen_hashes:
            return False
        
        self._seen_hashes.add(content_hash)
        return True
    
    def _normalize(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Removes extra whitespace and converts to lowercase.
        """
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', text)
        # Strip and lowercase
        return normalized.strip().lower()
    
    def _hash_content(self, content: str) -> str:
        """Generate a hash for content comparison."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _join_sections(self, sections: List[str]) -> str:
        """Rejoin sections with appropriate separators."""
        return '\n\n'.join(sections)
    
    def reset(self) -> None:
        """Reset the deduplicator state."""
        self._seen_hashes.clear()


# Global instance
_deduplicator: Optional[OutputDeduplicator] = None


def get_deduplicator() -> OutputDeduplicator:
    """Get the global deduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = OutputDeduplicator()
    return _deduplicator


def deduplicate_content(content: str) -> str:
    """Convenience function to deduplicate content."""
    return get_deduplicator().deduplicate(content)
