"""
Property-based tests for rules loading.

Tests correctness properties defined in the design document using hypothesis.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
from pathlib import Path
import tempfile
import os

from llm_supercli.prompts.rules import RuleFile, RulesLoader


# Strategies for generating test data

def valid_filename_strategy():
    """Generate valid filenames for rule files."""
    return st.from_regex(r"^[a-zA-Z][a-zA-Z0-9_-]{0,20}\.txt$", fullmatch=True)


def rule_content_strategy():
    """Generate valid rule content."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
            blacklist_characters='\x00'
        ),
        min_size=1,
        max_size=200
    )


@st.composite
def rule_files_strategy(draw, source: str, min_size: int = 0, max_size: int = 5):
    """Generate a list of RuleFile objects with unique filenames and unique content."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    files = []
    used_names = set()
    
    for i in range(count):
        # Generate unique filename
        base_name = draw(valid_filename_strategy())
        # Ensure uniqueness by appending index if needed
        name = f"{i}_{base_name}"
        while name in used_names:
            name = f"{i}_{draw(valid_filename_strategy())}"
        used_names.add(name)
        
        base_content = draw(rule_content_strategy())
        # Ensure unique content by including source, index, and filename
        # This guarantees each rule has unique content for position-based testing
        content = f"[{source}_{i}_{name}] {base_content}"
        # Use a fake path for testing
        path = Path(f"/fake/{source}/{name}")
        files.append(RuleFile(path=path, content=content, source=source))
    
    return files


@st.composite
def global_and_local_rules_strategy(draw):
    """Generate both global and local rule files."""
    global_rules = draw(rule_files_strategy("global", min_size=0, max_size=5))
    local_rules = draw(rule_files_strategy("local", min_size=0, max_size=5))
    return global_rules, local_rules


# **Feature: prompt-system-refactor, Property 5: Rules precedence and ordering**
@settings(max_examples=100)
@given(data=global_and_local_rules_strategy())
def test_rules_precedence_global_before_local(data):
    """
    Property 5: Rules precedence and ordering (global before local)
    
    For any set of global rule files and local rule files, merging SHALL
    produce output where all global rules appear before all local rules.
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    global_rules, local_rules = data
    
    # Skip if both are empty
    assume(len(global_rules) > 0 or len(local_rules) > 0)
    
    # Combine rules in the expected order (global first, then local)
    all_rules = global_rules + local_rules
    
    loader = RulesLoader()
    merged = loader.merge(all_rules)
    
    if not merged:
        # Empty merge is valid if no rules
        assert len(all_rules) == 0 or all(not r.content.strip() for r in all_rules)
        return
    
    # Find positions of global and local content in merged output
    global_positions = []
    local_positions = []
    
    for rule in global_rules:
        if rule.content.strip():
            pos = merged.find(rule.content.strip())
            if pos != -1:
                global_positions.append(pos)
    
    for rule in local_rules:
        if rule.content.strip():
            pos = merged.find(rule.content.strip())
            if pos != -1:
                local_positions.append(pos)
    
    # All global positions should be before all local positions
    if global_positions and local_positions:
        max_global_pos = max(global_positions)
        min_local_pos = min(local_positions)
        assert max_global_pos < min_local_pos, (
            f"Global rules should appear before local rules. "
            f"Max global position: {max_global_pos}, Min local position: {min_local_pos}"
        )


# **Feature: prompt-system-refactor, Property 5: Rules precedence and ordering**
@settings(max_examples=100)
@given(rules=rule_files_strategy("global", min_size=2, max_size=5))
def test_rules_alphabetical_ordering_within_category(rules: list[RuleFile]):
    """
    Property 5: Rules precedence and ordering (alphabetical within category)
    
    For any set of rule files within a category, merging SHALL produce
    output where files appear in alphabetical order by filename.
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    # Sort rules alphabetically by filename (as the loader does)
    sorted_rules = sorted(rules, key=lambda r: r.path.name)
    
    loader = RulesLoader()
    merged = loader.merge(sorted_rules)
    
    if not merged:
        return
    
    # Verify content appears in alphabetical order
    last_pos = -1
    for rule in sorted_rules:
        if rule.content.strip():
            pos = merged.find(rule.content.strip())
            if pos != -1:
                assert pos > last_pos, (
                    f"Rule '{rule.path.name}' should appear after previous rules. "
                    f"Found at position {pos}, expected after {last_pos}"
                )
                last_pos = pos


# **Feature: prompt-system-refactor, Property 5: Rules precedence and ordering**
@settings(max_examples=100)
@given(
    global_rules=rule_files_strategy("global", min_size=1, max_size=3),
    local_rules=rule_files_strategy("local", min_size=1, max_size=3)
)
def test_rules_merge_contains_all_content(global_rules: list[RuleFile], local_rules: list[RuleFile]):
    """
    Property 5: Rules precedence and ordering (all content preserved)
    
    For any set of rule files, merging SHALL include all rule content
    in the output.
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    all_rules = global_rules + local_rules
    
    loader = RulesLoader()
    merged = loader.merge(all_rules)
    
    # All rule content should be present in merged output
    for rule in all_rules:
        content = rule.content.strip()
        if content:
            assert content in merged, (
                f"Rule content from '{rule.path.name}' should be in merged output"
            )


# **Feature: prompt-system-refactor, Property 5: Rules precedence and ordering**
@settings(max_examples=100)
@given(
    global_rules=rule_files_strategy("global", min_size=1, max_size=3),
    local_rules=rule_files_strategy("local", min_size=1, max_size=3)
)
def test_rules_merge_includes_source_headers(global_rules: list[RuleFile], local_rules: list[RuleFile]):
    """
    Property 5: Rules precedence and ordering (source headers included)
    
    For any set of rule files, merging SHALL include headers indicating
    the source of each rule file.
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    all_rules = global_rules + local_rules
    
    loader = RulesLoader()
    merged = loader.merge(all_rules)
    
    # Each rule should have a header with its source and filename
    for rule in all_rules:
        expected_header = f"# Rules from {rule.source}: {rule.path.name}"
        assert expected_header in merged, (
            f"Expected header '{expected_header}' not found in merged output"
        )


# Integration test with actual file system
class TestRulesLoaderIntegration:
    """Integration tests for RulesLoader with actual file system."""
    
    def test_load_from_empty_directory(self):
        """Test loading from a directory with no rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            loader = RulesLoader()
            rules = loader.load(cwd)
            assert rules == []
    
    def test_load_local_rules(self):
        """Test loading local rules from .supercli/rules/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            rules_dir = cwd / ".supercli" / "rules"
            rules_dir.mkdir(parents=True)
            
            # Create rule files
            (rules_dir / "a_rule.txt").write_text("Rule A content")
            (rules_dir / "b_rule.txt").write_text("Rule B content")
            
            loader = RulesLoader()
            rules = loader.load(cwd)
            
            # Should have 2 local rules
            local_rules = [r for r in rules if r.source == "local"]
            assert len(local_rules) == 2
            
            # Should be in alphabetical order
            assert local_rules[0].path.name == "a_rule.txt"
            assert local_rules[1].path.name == "b_rule.txt"
    
    def test_load_legacy_superclirules(self):
        """Test loading legacy .superclirules file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            legacy_file = cwd / ".superclirules"
            legacy_file.write_text("Legacy rule content")
            
            loader = RulesLoader()
            rules = loader.load(cwd)
            
            assert len(rules) == 1
            assert rules[0].path.name == ".superclirules"
            assert rules[0].content == "Legacy rule content"
            assert rules[0].source == "local"
    
    def test_merge_empty_rules(self):
        """Test merging empty rules list."""
        loader = RulesLoader()
        merged = loader.merge([])
        assert merged == ""
