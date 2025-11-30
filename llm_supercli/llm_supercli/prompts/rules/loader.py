"""
Rules loading module.

Provides functionality for loading and merging custom rules from file system.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RuleFile:
    """A loaded rule file."""
    path: Path
    content: str
    source: str  # "global" or "local"


class RulesLoader:
    """Loads custom rules from file system.
    
    Rules are loaded from two locations:
    1. Global rules: ~/.supercli/rules/
    2. Local rules: .supercli/rules/ (relative to cwd)
    
    Rules are merged with global rules first, then local rules.
    Within each category, files are sorted alphabetically by filename.
    Local rules take precedence over global rules.
    
    Legacy support: Also checks for .superclirules and .clirules files.
    """
    
    GLOBAL_RULES_DIR = Path.home() / ".supercli" / "rules"
    LOCAL_RULES_DIR = ".supercli/rules"
    LEGACY_FILES = [".superclirules", ".clirules"]
    
    def load(self, cwd: Path) -> list[RuleFile]:
        """Load all applicable rules for the given directory.
        
        Args:
            cwd: The current working directory to load local rules from.
            
        Returns:
            List of RuleFile objects, ordered by precedence:
            - Global rules first (alphabetically sorted)
            - Local rules second (alphabetically sorted)
            - Legacy files last
        """
        rules: list[RuleFile] = []
        
        # Load global rules
        rules.extend(self._load_from_directory(self.GLOBAL_RULES_DIR, "global"))
        
        # Load local rules
        local_rules_dir = cwd / self.LOCAL_RULES_DIR
        rules.extend(self._load_from_directory(local_rules_dir, "local"))
        
        # Load legacy files (from cwd)
        rules.extend(self._load_legacy_files(cwd))
        
        return rules
    
    def _load_from_directory(self, directory: Path, source: str) -> list[RuleFile]:
        """Load rule files from a directory.
        
        Args:
            directory: The directory to load rules from.
            source: The source identifier ("global" or "local").
            
        Returns:
            List of RuleFile objects, sorted alphabetically by filename.
        """
        rules: list[RuleFile] = []
        
        if not directory.exists() or not directory.is_dir():
            return rules
        
        # Get all files in the directory, sorted alphabetically
        try:
            files = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError:
            logger.warning(f"Permission denied accessing rules directory: {directory}")
            return rules
        
        for file_path in files:
            if file_path.is_file():
                rule_file = self._load_file(file_path, source)
                if rule_file:
                    rules.append(rule_file)
        
        return rules
    
    def _load_legacy_files(self, cwd: Path) -> list[RuleFile]:
        """Load legacy rule files from the current working directory.
        
        Args:
            cwd: The current working directory.
            
        Returns:
            List of RuleFile objects for any found legacy files.
        """
        rules: list[RuleFile] = []
        
        for legacy_name in self.LEGACY_FILES:
            legacy_path = cwd / legacy_name
            if legacy_path.exists() and legacy_path.is_file():
                rule_file = self._load_file(legacy_path, "local")
                if rule_file:
                    rules.append(rule_file)
        
        return rules
    
    def _load_file(self, file_path: Path, source: str) -> Optional[RuleFile]:
        """Load a single rule file.
        
        Args:
            file_path: Path to the rule file.
            source: The source identifier ("global" or "local").
            
        Returns:
            RuleFile object if successful, None if file couldn't be read.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return RuleFile(path=file_path, content=content, source=source)
        except (PermissionError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to load rule file {file_path}: {e}")
            return None
    
    def merge(self, rules: list[RuleFile]) -> str:
        """Merge rules into a single string, respecting precedence.
        
        Rules are merged in the order they appear in the list.
        Each rule file's content is separated by a header indicating its source.
        
        Args:
            rules: List of RuleFile objects to merge.
            
        Returns:
            Merged rules as a single string.
        """
        if not rules:
            return ""
        
        parts: list[str] = []
        
        for rule in rules:
            # Add header with source and filename
            header = f"# Rules from {rule.source}: {rule.path.name}"
            parts.append(header)
            parts.append(rule.content.strip())
            parts.append("")  # Empty line between rule files
        
        return "\n".join(parts).strip()
