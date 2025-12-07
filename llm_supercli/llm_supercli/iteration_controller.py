"""
Iteration controller for conversation loop management.

Controls the conversation iteration loop with proper termination conditions,
tracking iteration count and managing continuation decisions.

Requirements: 1.4 - Display warning and allow manual continuation at max iterations
"""
from dataclasses import dataclass
from typing import Optional

from .completion_detector import CompletionResult


@dataclass
class IterationState:
    """Tracks the current state of the iteration loop.
    
    Attributes:
        current_iteration: The current iteration number (1-indexed).
        max_iterations: The maximum allowed iterations.
        should_continue: Whether the loop should continue.
        warning_message: Optional warning message to display.
    """
    current_iteration: int
    max_iterations: int
    should_continue: bool
    warning_message: Optional[str] = None


class IterationController:
    """Controls conversation iteration loop.
    
    Manages the conversation loop by tracking iterations, determining
    when to continue based on completion results, and providing warnings
    when maximum iterations are reached.
    
    Requirements:
    - 1.4: Display warning and allow manual continuation at max iterations
    """
    
    DEFAULT_MAX_ITERATIONS: int = 15
    
    def __init__(self, max_iterations: int = 15) -> None:
        """Initialize the iteration controller.
        
        Args:
            max_iterations: Maximum number of iterations before warning.
                           Defaults to 15.
        """
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.retry_count = 0
    
    def should_continue(self, completion_result: CompletionResult) -> bool:
        """Determine if loop should continue based on completion result.
        
        Evaluates the completion result and current iteration count to
        decide whether the conversation loop should continue.
        
        Args:
            completion_result: The result from CompletionDetector.is_complete().
            
        Returns:
            True if the loop should continue, False otherwise.
            
        Requirements:
        - 1.4: Stop at max iterations (return False)
        """
        # If we've hit max iterations, don't continue
        if self.current_iteration >= self.max_iterations:
            return False
        
        # Delegate to the completion result's should_continue flag
        return completion_result.should_continue
    
    def on_iteration_start(self) -> None:
        """Called at start of each iteration for tracking.
        
        Increments the iteration counter. Should be called at the
        beginning of each conversation loop iteration.
        """
        self.current_iteration += 1
    
    def on_max_iterations_reached(self) -> str:
        """Return warning message when max iterations hit.
        
        Provides a user-friendly warning message explaining that the
        maximum iteration limit has been reached and offering guidance.
        
        Returns:
            Warning message string for display to user.
            
        Requirements:
        - 1.4: Display warning and allow manual continuation
        """
        return (
            f"⚠️  Maximum iterations ({self.max_iterations}) reached. "
            f"The task may not be complete. You can type 'continue' to "
            f"resume, or provide additional instructions."
        )
    
    def is_at_max_iterations(self) -> bool:
        """Check if the controller has reached max iterations.
        
        Returns:
            True if current_iteration >= max_iterations.
        """
        return self.current_iteration >= self.max_iterations
    
    def reset(self) -> None:
        """Reset the controller state for a new conversation.
        
        Resets iteration count and retry count to initial values.
        """
        self.current_iteration = 0
        self.retry_count = 0
    
    def get_state(self) -> IterationState:
        """Get the current iteration state.
        
        Returns:
            IterationState with current tracking information.
        """
        warning = None
        if self.is_at_max_iterations():
            warning = self.on_max_iterations_reached()
        
        return IterationState(
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            should_continue=not self.is_at_max_iterations(),
            warning_message=warning
        )
