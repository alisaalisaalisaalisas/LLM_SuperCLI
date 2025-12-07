"""
Streaming chunk deduplicator for llm_supercli.
Prevents duplicate consecutive content blocks during streaming display.

Requirements addressed:
- 5.2: Display content incrementally without duplication
- Property 10: Chunk deduplication - no consecutive duplicate content blocks
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class ChunkDeduplicationResult:
    """Result of chunk deduplication operation."""
    original_chunk: str
    deduplicated_chunk: str
    was_duplicate: bool
    duplicate_type: Optional[str] = None  # "exact", "consecutive", "partial"


class ChunkDeduplicator:
    """
    Deduplicates streaming chunks to prevent consecutive identical content blocks.
    
    This class tracks displayed content during streaming and filters out
    duplicate chunks that would result in repeated display. It handles:
    
    1. Exact duplicates: Identical chunks received consecutively
    2. Consecutive block duplicates: Same paragraph/block appearing multiple times
    3. Partial overlaps: Chunks that partially repeat previous content
    
    Requirements addressed:
    - 5.2: Display content incrementally without duplication
    - Property 10: Chunk deduplication
    
    Usage:
        deduplicator = ChunkDeduplicator()
        for chunk in stream:
            result = deduplicator.process_chunk(chunk)
            if not result.was_duplicate:
                display(result.deduplicated_chunk)
    """
    
    # Minimum length for content to be tracked for deduplication
    MIN_TRACKABLE_LENGTH = 10
    
    # Maximum number of recent chunks to track for overlap detection
    MAX_RECENT_CHUNKS = 20
    
    # Maximum length of content hash history to prevent memory bloat
    MAX_HASH_HISTORY = 100
    
    def __init__(
        self,
        min_trackable_length: int = MIN_TRACKABLE_LENGTH,
        max_recent_chunks: int = MAX_RECENT_CHUNKS,
    ) -> None:
        """
        Initialize the chunk deduplicator.
        
        Args:
            min_trackable_length: Minimum length for content to be tracked
            max_recent_chunks: Maximum number of recent chunks to track
        """
        self._min_trackable_length = min_trackable_length
        self._max_recent_chunks = max_recent_chunks
        
        # Track displayed content hashes for exact duplicate detection
        self._displayed_hashes: Set[str] = set()
        
        # Track recent chunks for overlap detection
        self._recent_chunks: List[str] = []
        
        # Track accumulated content for paragraph-level deduplication
        self._accumulated_content: str = ""
        
        # Track displayed paragraphs for block-level deduplication
        self._displayed_paragraphs: Set[str] = set()
        
        # Track displayed lines for line-level deduplication
        self._displayed_lines: Set[str] = set()
    
    def process_chunk(self, chunk: str) -> ChunkDeduplicationResult:
        """
        Process a streaming chunk and return deduplicated content.
        
        Checks for various types of duplicates and returns only new content.
        
        Args:
            chunk: The incoming streaming chunk
            
        Returns:
            ChunkDeduplicationResult with deduplicated content and metadata
        """
        if not chunk:
            return ChunkDeduplicationResult(
                original_chunk="",
                deduplicated_chunk="",
                was_duplicate=False,
            )
        
        # Check for exact duplicate
        chunk_hash = self._hash_content(chunk)
        if chunk_hash in self._displayed_hashes:
            return ChunkDeduplicationResult(
                original_chunk=chunk,
                deduplicated_chunk="",
                was_duplicate=True,
                duplicate_type="exact",
            )
        
        # Check for consecutive duplicate (same as last chunk)
        if self._recent_chunks and chunk == self._recent_chunks[-1]:
            return ChunkDeduplicationResult(
                original_chunk=chunk,
                deduplicated_chunk="",
                was_duplicate=True,
                duplicate_type="consecutive",
            )
        
        # Check for partial overlap with recent content
        deduplicated = self._remove_overlap(chunk)
        if not deduplicated:
            return ChunkDeduplicationResult(
                original_chunk=chunk,
                deduplicated_chunk="",
                was_duplicate=True,
                duplicate_type="partial",
            )
        
        # Track this chunk
        self._track_chunk(deduplicated)
        
        return ChunkDeduplicationResult(
            original_chunk=chunk,
            deduplicated_chunk=deduplicated,
            was_duplicate=False,
        )
    
    def deduplicate_content(self, content: str) -> str:
        """
        Deduplicate complete content (paragraphs and lines).
        
        This method handles deduplication of accumulated content,
        removing duplicate paragraphs and consecutive identical lines.
        
        Args:
            content: The content to deduplicate
            
        Returns:
            Deduplicated content string
        """
        if not content or not content.strip():
            return content
        
        # First, deduplicate paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        unique_paragraphs = []
        
        for para in paragraphs:
            para_key = self._normalize_for_comparison(para)
            if para_key and len(para_key) >= self._min_trackable_length:
                if para_key not in self._displayed_paragraphs:
                    self._displayed_paragraphs.add(para_key)
                    unique_paragraphs.append(para)
            else:
                # Short paragraphs are always kept
                unique_paragraphs.append(para)
        
        content = '\n\n'.join(unique_paragraphs)
        
        # Then, deduplicate consecutive identical lines
        lines = content.split('\n')
        unique_lines = []
        prev_line_key = None
        
        for line in lines:
            line_key = self._normalize_for_comparison(line)
            
            # Keep empty lines for formatting
            if not line_key:
                unique_lines.append(line)
                prev_line_key = None
                continue
            
            # Skip consecutive identical lines
            if line_key == prev_line_key:
                continue
            
            # Check if this line was already displayed (non-consecutive)
            if line_key in self._displayed_lines and len(line_key) >= self._min_trackable_length:
                continue
            
            self._displayed_lines.add(line_key)
            unique_lines.append(line)
            prev_line_key = line_key
        
        return '\n'.join(unique_lines)
    
    def reset(self) -> None:
        """Reset the deduplicator state for a new streaming session."""
        self._displayed_hashes.clear()
        self._recent_chunks.clear()
        self._accumulated_content = ""
        self._displayed_paragraphs.clear()
        self._displayed_lines.clear()
    
    def _track_chunk(self, chunk: str) -> None:
        """Track a chunk for future duplicate detection."""
        if len(chunk) < self._min_trackable_length:
            return
        
        # Add to hash set
        chunk_hash = self._hash_content(chunk)
        self._displayed_hashes.add(chunk_hash)
        
        # Limit hash history size
        if len(self._displayed_hashes) > self.MAX_HASH_HISTORY:
            # Remove oldest hashes (convert to list, remove first items)
            hashes_list = list(self._displayed_hashes)
            self._displayed_hashes = set(hashes_list[-self.MAX_HASH_HISTORY:])
        
        # Add to recent chunks
        self._recent_chunks.append(chunk)
        if len(self._recent_chunks) > self._max_recent_chunks:
            self._recent_chunks.pop(0)
        
        # Accumulate content
        self._accumulated_content += chunk
    
    def _remove_overlap(self, chunk: str) -> str:
        """
        Remove overlapping content from a chunk.
        
        Checks if the beginning of the chunk overlaps with the end of
        accumulated content and removes the overlapping portion.
        
        Args:
            chunk: The incoming chunk
            
        Returns:
            Chunk with overlap removed, or empty string if fully duplicate
        """
        if not self._accumulated_content or not chunk:
            return chunk
        
        # Check for overlap at the boundary
        max_overlap = min(len(self._accumulated_content), len(chunk))
        
        for overlap_len in range(max_overlap, 0, -1):
            if self._accumulated_content[-overlap_len:] == chunk[:overlap_len]:
                # Found overlap, return only the new part
                new_content = chunk[overlap_len:]
                return new_content
        
        return chunk
    
    def _hash_content(self, content: str) -> str:
        """Generate a hash for content comparison."""
        normalized = self._normalize_for_comparison(content)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _normalize_for_comparison(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Collapses whitespace and converts to lowercase for
        more robust duplicate detection.
        """
        if not text:
            return ""
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', text)
        # Strip and lowercase
        return normalized.strip().lower()


# Global instance for convenience
_chunk_deduplicator: Optional[ChunkDeduplicator] = None


def get_chunk_deduplicator() -> ChunkDeduplicator:
    """Get the global chunk deduplicator instance."""
    global _chunk_deduplicator
    if _chunk_deduplicator is None:
        _chunk_deduplicator = ChunkDeduplicator()
    return _chunk_deduplicator


def deduplicate_streaming_chunk(chunk: str) -> ChunkDeduplicationResult:
    """Convenience function to deduplicate a streaming chunk."""
    return get_chunk_deduplicator().process_chunk(chunk)


def reset_chunk_deduplicator() -> None:
    """Reset the global chunk deduplicator for a new session."""
    global _chunk_deduplicator
    if _chunk_deduplicator is not None:
        _chunk_deduplicator.reset()
