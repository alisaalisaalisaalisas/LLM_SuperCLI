"""
Property-based tests for prompt sections.

Tests correctness properties defined in the design document using hypothesis.
"""

import allure
import pytest
from hypothesis import given, settings, strategies as st
from dataclasses import dataclass

from llm_supercli.prompts.sections import (
    PromptSection,
    SectionContext,
    SectionManager,
    ModeConfig,
)


# Test helpers - concrete section implementations for testing

class ConcreteSection(PromptSection):
    """A concrete section implementation for testing."""
    
    def __init__(self, name: str, order: int, content: str):
        self._name = name
        self._order = order
        self._content = content
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def order(self) -> int:
        return self._order
    
    def render(self, context: SectionContext) -> str:
        return self._content


# Strategies for generating test data

@st.composite
def unique_sections_strategy(draw, min_size=1, max_size=10):
    """Generate a list of sections with unique names and unique content."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    sections = []
    
    for i in range(count):
        # Generate unique name by appending index
        base_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=15
        ))
        name = f"{base_name}_{i}"
        
        order = draw(st.integers(min_value=0, max_value=1000))
        # Use unique content by including the index to avoid duplicate content issues
        base_content = draw(st.text(min_size=1, max_size=50))
        content = f"[SECTION_{i}]{base_content}"
        sections.append(ConcreteSection(name=name, order=order, content=content))
    
    return sections


def create_test_context() -> SectionContext:
    """Create a minimal SectionContext for testing."""
    mode = ModeConfig(
        slug="test",
        name="Test Mode",
        role_definition="A test mode for property testing",
    )
    return SectionContext(
        mode=mode,
        cwd="/test",
        os_type="posix",
        shell="/bin/bash",
    )


# **Feature: prompt-system-refactor, Property 1: Section ordering determinism**
@allure.feature("Prompt Sections")
@allure.story("Section ordering determinism")
@allure.severity(allure.severity_level.CRITICAL)
@settings(max_examples=100)
@given(sections=unique_sections_strategy(min_size=1, max_size=10))
def test_section_ordering_deterministic(sections: list[ConcreteSection]):
    """
    Property 1: Section ordering determinism
    
    For any set of registered sections with assigned order values,
    rendering them multiple times with the same context SHALL produce
    identical output with sections appearing in ascending order by
    their order value.
    
    **Validates: Requirements 1.2**
    """
    # Create manager and register all sections
    manager = SectionManager()
    for section in sections:
        manager.register(section)
    
    context = create_test_context()
    
    # Render multiple times
    output1 = manager.render_all(context)
    output2 = manager.render_all(context)
    output3 = manager.render_all(context)
    
    # All outputs should be identical
    assert output1 == output2, "First and second render should be identical"
    assert output2 == output3, "Second and third render should be identical"
    
    # Verify sections appear in order
    # Sort sections by (order, name) as the manager does
    sorted_sections = sorted(sections, key=lambda s: (s.order, s.name))
    
    # Check that content appears in the correct order using unique markers
    last_pos = -1
    for section in sorted_sections:
        # Find the unique marker for this section
        marker = f"[SECTION_{sections.index(section)}]"
        pos = output1.find(marker)
        if pos != -1:  # Content found
            assert pos > last_pos, (
                f"Section '{section.name}' (order={section.order}) "
                f"should appear after previous sections"
            )
            last_pos = pos


class MutableSection(PromptSection):
    """A section with mutable content for testing isolation."""
    
    def __init__(self, name: str, order: int, content: str):
        self._name = name
        self._order = order
        self.content = content  # Mutable - can be changed
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def order(self) -> int:
        return self._order
    
    def render(self, context: SectionContext) -> str:
        return self.content


@st.composite
def mutable_sections_strategy(draw, min_size=2, max_size=10):
    """Generate a list of mutable sections with unique names and content."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    sections = []
    
    for i in range(count):
        base_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=15
        ))
        name = f"{base_name}_{i}"
        
        order = draw(st.integers(min_value=0, max_value=1000))
        base_content = draw(st.text(min_size=1, max_size=50))
        content = f"[SECTION_{i}]{base_content}"
        sections.append(MutableSection(name=name, order=order, content=content))
    
    return sections


# **Feature: prompt-system-refactor, Property 2: Section isolation**
@allure.feature("Prompt Sections")
@allure.story("Section isolation")
@allure.severity(allure.severity_level.CRITICAL)
@settings(max_examples=100)
@given(
    sections=mutable_sections_strategy(min_size=2, max_size=10),
    new_content=st.text(min_size=1, max_size=50)
)
def test_section_isolation(sections: list[MutableSection], new_content: str):
    """
    Property 2: Section isolation
    
    For any set of sections where one section's template is modified,
    re-rendering SHALL produce output where only the modified section's
    content changes while all other sections remain byte-for-byte identical.
    
    **Validates: Requirements 1.3**
    """
    # Create manager and register all sections
    manager = SectionManager()
    for section in sections:
        manager.register(section)
    
    context = create_test_context()
    
    # Render before modification
    output_before = manager.render_all(context)
    
    # Pick a section to modify (first one)
    modified_section = sections[0]
    original_content = modified_section.content
    modified_section.content = f"[MODIFIED]{new_content}"
    
    # Render after modification
    output_after = manager.render_all(context)
    
    # Verify the modified section's content changed
    assert original_content in output_before, "Original content should be in first render"
    assert original_content not in output_after, "Original content should not be in second render"
    assert f"[MODIFIED]{new_content}" in output_after, "New content should be in second render"
    
    # Verify all other sections remain unchanged
    for section in sections[1:]:
        assert section.content in output_before, f"Section {section.name} should be in first render"
        assert section.content in output_after, f"Section {section.name} should be in second render"
