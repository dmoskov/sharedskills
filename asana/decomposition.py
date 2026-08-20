#!/usr/bin/env python3
"""
Task Decomposition Module - Synapse-inspired Algorithm

Implements the Project Synapse framework's 4-step decomposition algorithm
for breaking complex tasks into optimally-sized subtasks:

1. Constraint Analysis (temporal, spatial, resource)
2. Dependency Mapping (prerequisites, ordering)
3. Priority Assignment (impact-based ranking)
4. Granularity Optimization (subtask sizing)

Pure algorithm — stdlib only, no Asana or project dependencies. Pair it with
asana_client.py / asana_config_loader.py to create the resulting subtasks in
your workspace, or use it standalone for any task-planning pipeline.

Reference: arXiv:2601.08156v1 - Project Synapse
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta


class ConstraintType(Enum):
    """Types of constraints that can affect task execution."""

    TEMPORAL = "temporal"  # Time-based constraints (deadlines, duration)
    SPATIAL = "spatial"  # Location/environment constraints (local vs remote)
    RESOURCE = "resource"  # Resource constraints (API limits, compute, cost)
    DEPENDENCY = "dependency"  # External dependencies (blocked by other tasks)


class TaskComplexity(Enum):
    """Task complexity levels based on effort estimate."""

    SMALL = "small"  # < 4h
    MEDIUM = "medium"  # 1-2 days
    LARGE = "large"  # 3-5 days
    XL = "xl"  # 1 week+


@dataclass
class Constraint:
    """Represents a constraint on task execution."""

    type: ConstraintType
    description: str
    severity: float  # 0.0 (soft constraint) to 1.0 (hard constraint)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subtask:
    """Represents a decomposed subtask."""

    name: str
    description: str
    complexity: TaskComplexity
    dependencies: List[str] = field(
        default_factory=list
    )  # Names of prerequisite subtasks
    priority: float = 0.5  # 0.0 (lowest) to 1.0 (highest)
    constraints: List[Constraint] = field(default_factory=list)
    estimated_duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "complexity": self.complexity.value,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "constraints": [
                {
                    "type": c.type.value,
                    "description": c.description,
                    "severity": c.severity,
                    "metadata": c.metadata,
                }
                for c in self.constraints
            ],
            "estimated_duration": str(self.estimated_duration)
            if self.estimated_duration
            else None,
            "metadata": self.metadata,
        }


@dataclass
class ConstraintSet:
    """Set of constraints identified for a task."""

    constraints: List[Constraint]

    def get_by_type(self, constraint_type: ConstraintType) -> List[Constraint]:
        """Get all constraints of a specific type."""
        return [c for c in self.constraints if c.type == constraint_type]

    def has_hard_constraints(self) -> bool:
        """Check if any constraints are hard (severity >= 0.8)."""
        return any(c.severity >= 0.8 for c in self.constraints)


@dataclass
class DependencyGraph:
    """Represents dependencies between subtasks."""

    nodes: List[str]  # Subtask names
    edges: List[Tuple[str, str]]  # (prerequisite, dependent)

    def get_prerequisites(self, node: str) -> List[str]:
        """Get all prerequisites for a given node."""
        return [src for src, dst in self.edges if dst == node]

    def get_dependents(self, node: str) -> List[str]:
        """Get all nodes that depend on a given node."""
        return [dst for src, dst in self.edges if src == node]

    def has_cycle(self) -> bool:
        """Check if the dependency graph has cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dependent in self.get_dependents(node):
                if dependent not in visited:
                    if dfs(dependent):
                        return True
                elif dependent in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def topological_sort(self) -> Optional[List[str]]:
        """Return topologically sorted nodes, or None if cycle exists."""
        if self.has_cycle():
            return None

        in_degree = {node: 0 for node in self.nodes}
        for src, dst in self.edges:
            in_degree[dst] += 1

        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dependent in self.get_dependents(node):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result if len(result) == len(self.nodes) else None


class TaskDecomposer:
    """
    Synapse-inspired task decomposition algorithm.
    Breaks complex tasks into optimally-sized subtasks.

    This implements the 4-step decomposition process from Project Synapse:
    1. Constraint Analysis - Identify temporal, spatial, resource constraints
    2. Dependency Mapping - Build prerequisite graph
    3. Priority Assignment - Rank by impact
    4. Granularity Optimization - Balance subtask sizing
    """

    def __init__(
        self,
        max_subtask_complexity: TaskComplexity = TaskComplexity.MEDIUM,
        min_subtasks: int = 2,
        max_subtasks: int = 8,
    ):
        """
        Initialize the task decomposer.

        Args:
            max_subtask_complexity: Maximum complexity for individual subtasks
            min_subtasks: Minimum number of subtasks to generate
            max_subtasks: Maximum number of subtasks to generate
        """
        self.max_subtask_complexity = max_subtask_complexity
        self.min_subtasks = min_subtasks
        self.max_subtasks = max_subtasks

    def decompose(
        self,
        task_name: str,
        task_description: str,
        complexity: TaskComplexity = TaskComplexity.XL,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Subtask]:
        """
        Apply 4-step Synapse decomposition algorithm.

        Args:
            task_name: Name of the task to decompose
            task_description: Description of the task
            complexity: Complexity level of the task
            context: Additional context (project info, dependencies, etc.)

        Returns:
            List of subtasks with dependencies and priorities
        """
        # Step 1: Analyze constraints
        constraints = self._analyze_constraints(
            task_name, task_description, complexity, context
        )

        # Step 2: Map dependencies
        dependencies = self._map_dependencies(
            task_name, task_description, constraints, context
        )

        # Step 3: Assign priorities
        priorities = self._assign_priorities(dependencies, constraints, context)

        # Step 4: Optimize granularity
        subtasks = self._optimize_granularity(priorities, constraints, dependencies)

        return subtasks

    def _analyze_constraints(
        self,
        task_name: str,
        task_description: str,
        complexity: TaskComplexity,
        context: Optional[Dict[str, Any]],
    ) -> ConstraintSet:
        """
        Step 1: Identify temporal, spatial, and resource constraints.

        This analyzes the task to identify:
        - Temporal: Deadlines, estimated duration
        - Spatial: Local vs remote execution requirements
        - Resource: API limits, compute resources, budget
        - Dependency: Blocked by other tasks or external factors
        """
        constraints = []

        # Temporal constraints based on complexity
        if complexity == TaskComplexity.XL:
            constraints.append(
                Constraint(
                    type=ConstraintType.TEMPORAL,
                    description="XL task requires decomposition (1w+ effort)",
                    severity=0.9,
                    metadata={"complexity": complexity.value},
                )
            )

        # Check for deadline indicators in description
        deadline_keywords = ["deadline", "due date", "must complete by", "urgent"]
        if any(kw in task_description.lower() for kw in deadline_keywords):
            constraints.append(
                Constraint(
                    type=ConstraintType.TEMPORAL,
                    description="Task has explicit deadline requirement",
                    severity=0.8,
                    metadata={"keywords": deadline_keywords},
                )
            )

        # Resource constraints from context
        if context:
            if context.get("remote_execution"):
                constraints.append(
                    Constraint(
                        type=ConstraintType.RESOURCE,
                        description="Remote execution required (AWS ECS)",
                        severity=0.6,
                        metadata={"execution_location": "remote"},
                    )
                )

            if context.get("api_limit"):
                constraints.append(
                    Constraint(
                        type=ConstraintType.RESOURCE,
                        description=f"API rate limit: {context.get('api_limit')}",
                        severity=0.7,
                        metadata={"limit": context.get("api_limit")},
                    )
                )

            # Check for blocking dependencies
            if context.get("blocked_by"):
                constraints.append(
                    Constraint(
                        type=ConstraintType.DEPENDENCY,
                        description=f"Blocked by: {context.get('blocked_by')}",
                        severity=0.9,
                        metadata={"blocked_by": context.get("blocked_by")},
                    )
                )

        # Spatial constraints based on task keywords
        spatial_keywords = ["deploy", "infrastructure", "aws", "docker", "kubernetes"]
        if any(kw in task_description.lower() for kw in spatial_keywords):
            constraints.append(
                Constraint(
                    type=ConstraintType.SPATIAL,
                    description="Infrastructure/deployment task requires specific environment",
                    severity=0.5,
                    metadata={"keywords": spatial_keywords},
                )
            )

        return ConstraintSet(constraints=constraints)

    def _map_dependencies(
        self,
        task_name: str,
        task_description: str,
        constraints: ConstraintSet,
        context: Optional[Dict[str, Any]],
    ) -> DependencyGraph:
        """
        Step 2: Build prerequisite graph for subtasks.

        This creates a directed acyclic graph (DAG) representing
        the prerequisite relationships between subtasks.
        """
        # Parse task description for sequential steps
        steps = self._extract_steps_from_description(task_description)

        # Create dependency graph
        nodes = [step["name"] for step in steps]
        edges = []

        # Add sequential dependencies
        for i in range(len(steps) - 1):
            # Check if step explicitly mentions dependencies
            if steps[i + 1].get("depends_on"):
                for dep in steps[i + 1]["depends_on"]:
                    if dep in nodes:
                        edges.append((dep, steps[i + 1]["name"]))
            else:
                # Default to sequential dependency
                edges.append((steps[i]["name"], steps[i + 1]["name"]))

        # Add explicit dependencies from context
        if context and context.get("dependencies"):
            for dep_pair in context["dependencies"]:
                if len(dep_pair) == 2:
                    src, dst = dep_pair
                    if src in nodes and dst in nodes:
                        edges.append((src, dst))

        graph = DependencyGraph(nodes=nodes, edges=edges)

        # Validate no cycles
        if graph.has_cycle():
            raise ValueError(
                "Circular dependency detected in task decomposition. "
                "Please review task structure."
            )

        return graph

    def _assign_priorities(
        self,
        dependencies: DependencyGraph,
        constraints: ConstraintSet,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Step 3: Rank subtasks by impact on overall solution quality.

        Priority scoring (0.0 to 1.0) considers:
        - Critical path analysis (tasks blocking others get higher priority)
        - Constraint severity (tasks with hard constraints get higher priority)
        - Explicit priority hints from context
        """
        priorities = {}

        # Calculate critical path impact
        for node in dependencies.nodes:
            # Base priority: number of dependents / total nodes
            num_dependents = len(dependencies.get_dependents(node))
            base_priority = num_dependents / max(len(dependencies.nodes), 1)

            # Boost priority if on critical path (no prerequisites = can start immediately)
            num_prerequisites = len(dependencies.get_prerequisites(node))
            if num_prerequisites == 0:
                base_priority += 0.2

            # Adjust for constraint severity
            # (Higher severity constraints increase priority)
            if constraints.has_hard_constraints():
                base_priority += 0.1

            # Normalize to [0.0, 1.0]
            priorities[node] = min(1.0, max(0.0, base_priority))

        # Apply explicit priorities from context
        if context and context.get("priorities"):
            for node, priority in context["priorities"].items():
                if node in priorities:
                    priorities[node] = priority

        return priorities

    def _optimize_granularity(
        self,
        priorities: Dict[str, float],
        constraints: ConstraintSet,
        dependencies: DependencyGraph,
    ) -> List[Subtask]:
        """
        Step 4: Balance subtask complexity for efficient delegation.

        This ensures subtasks are:
        - Not too large (max complexity threshold)
        - Not too small (min subtask count)
        - Well-balanced in complexity
        """
        subtasks = []

        # Get topologically sorted nodes for proper ordering
        sorted_nodes = dependencies.topological_sort()
        if not sorted_nodes:
            raise ValueError("Cannot optimize granularity: dependency graph has cycles")

        # Create subtasks from nodes
        for node in sorted_nodes:
            # Determine complexity (default to one level below max)
            complexity = TaskComplexity.SMALL
            if self.max_subtask_complexity == TaskComplexity.XL:
                complexity = TaskComplexity.LARGE
            elif self.max_subtask_complexity == TaskComplexity.LARGE:
                complexity = TaskComplexity.MEDIUM

            # Get dependencies for this subtask
            deps = dependencies.get_prerequisites(node)

            # Get priority
            priority = priorities.get(node, 0.5)

            # Create subtask
            subtask = Subtask(
                name=node,
                description=f"Complete {node}",
                complexity=complexity,
                dependencies=deps,
                priority=priority,
                constraints=constraints.constraints.copy(),
            )
            subtasks.append(subtask)

        # Validate subtask count
        if len(subtasks) < self.min_subtasks:
            raise ValueError(
                f"Generated {len(subtasks)} subtasks, but minimum is {self.min_subtasks}. "
                "Task may be too simple to decompose."
            )

        if len(subtasks) > self.max_subtasks:
            # Merge low-priority adjacent subtasks
            subtasks = self._merge_subtasks(subtasks, self.max_subtasks)

        return subtasks

    def _extract_steps_from_description(self, description: str) -> List[Dict[str, Any]]:
        """
        Extract numbered steps or bullet points from task description.

        Returns:
            List of step dictionaries with 'name' and optionally 'depends_on'
        """
        steps = []

        # Try to find numbered steps (1. 2. 3. or 1) 2) 3))
        numbered_pattern = r"(?:^|\n)\s*(\d+)[.)]\s+([^\n]+)"
        numbered_matches = re.findall(numbered_pattern, description)

        if numbered_matches:
            for num, text in numbered_matches:
                step_name = text.strip()[:80]  # Limit length
                steps.append({"name": step_name, "depends_on": []})
        else:
            # Try bullet points (- or *)
            bullet_pattern = r"(?:^|\n)\s*[-*]\s+([^\n]+)"
            bullet_matches = re.findall(bullet_pattern, description)

            if bullet_matches:
                for text in bullet_matches:
                    step_name = text.strip()[:80]
                    steps.append({"name": step_name, "depends_on": []})

        # If no steps found, create default steps based on task structure
        if not steps:
            steps = [
                {"name": "Analyze requirements and design approach", "depends_on": []},
                {
                    "name": "Implement core functionality",
                    "depends_on": ["Analyze requirements and design approach"],
                },
                {
                    "name": "Add error handling and edge cases",
                    "depends_on": ["Implement core functionality"],
                },
                {
                    "name": "Test and validate implementation",
                    "depends_on": ["Add error handling and edge cases"],
                },
            ]

        return steps

    def _merge_subtasks(self, subtasks: List[Subtask], max_count: int) -> List[Subtask]:
        """
        Merge low-priority adjacent subtasks to reduce total count.

        This is used when the initial decomposition creates too many subtasks.
        """
        if len(subtasks) <= max_count:
            return subtasks

        # Sort by priority (lowest first)
        sorted_subtasks = sorted(subtasks, key=lambda s: s.priority)

        # Merge lowest priority pairs until we're at max_count
        merged = subtasks.copy()
        while len(merged) > max_count:
            # Find lowest priority subtask
            lowest = sorted_subtasks[0]

            # Find adjacent subtask to merge with
            idx = merged.index(lowest)
            if idx < len(merged) - 1:
                # Merge with next subtask
                next_task = merged[idx + 1]
                merged_task = Subtask(
                    name=f"{lowest.name} + {next_task.name}",
                    description=f"{lowest.description}\n{next_task.description}",
                    complexity=TaskComplexity.MEDIUM,  # Merged tasks are medium
                    dependencies=list(
                        set(lowest.dependencies + next_task.dependencies)
                    ),
                    priority=(lowest.priority + next_task.priority) / 2,
                    constraints=lowest.constraints,
                )
                merged[idx] = merged_task
                merged.pop(idx + 1)
            else:
                # Last subtask, merge with previous
                prev_task = merged[idx - 1]
                merged_task = Subtask(
                    name=f"{prev_task.name} + {lowest.name}",
                    description=f"{prev_task.description}\n{lowest.description}",
                    complexity=TaskComplexity.MEDIUM,
                    dependencies=list(
                        set(prev_task.dependencies + lowest.dependencies)
                    ),
                    priority=(prev_task.priority + lowest.priority) / 2,
                    constraints=prev_task.constraints,
                )
                merged[idx - 1] = merged_task
                merged.pop(idx)

            # Re-sort for next iteration
            sorted_subtasks = sorted(merged, key=lambda s: s.priority)

        return merged


class DecompositionMetrics:
    """
    Track quality metrics for task decomposition.

    Metrics align with parent task success criteria:
    - XL task completion rate improvement (target: 20%+)
    - Dependency accuracy (target: >90%)
    - Subtask completion rate improvement (target: 15%+)

    Metric Calculation Methodology:
    --------------------------------
    1. XL Task Completion Rate:
       - Formula: (completed_xl_tasks / total_xl_tasks) * 100
       - Improvement measured against baseline of 60% (pre-decomposition)
       - Target: 80%+ (20% improvement)

    2. Dependency Accuracy:
       - Formula: (correct_dependencies / total_dependencies) * 100
       - Correct = subtask completed after all its prerequisites
       - Target: >90% accuracy

    3. Subtask Completion Rate:
       - Formula: (completed_subtasks / total_subtasks) * 100
       - Improvement measured against baseline of 70%
       - Target: 85%+ (15% improvement)
    """

    # Baseline metrics (pre-decomposition system performance)
    BASELINE_XL_COMPLETION_RATE = 0.60  # 60% historical completion
    BASELINE_SUBTASK_COMPLETION_RATE = 0.70  # 70% historical completion
    TARGET_DEPENDENCY_ACCURACY = 0.90  # 90% target

    def __init__(self):
        self.decompositions: List[Dict[str, Any]] = []
        self.completion_records: List[Dict[str, Any]] = []

    def record_decomposition(
        self,
        task_gid: str,
        task_name: str,
        subtasks: List[Subtask],
        timestamp: Optional[datetime] = None,
        complexity: Optional[TaskComplexity] = None,
    ):
        """
        Record a task decomposition for metrics tracking.

        Args:
            task_gid: Unique identifier for the task
            task_name: Human-readable task name
            subtasks: List of generated subtasks
            timestamp: When decomposition occurred (defaults to now)
            complexity: Original task complexity (for XL tracking)
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.decompositions.append(
            {
                "task_gid": task_gid,
                "task_name": task_name,
                "num_subtasks": len(subtasks),
                "subtask_names": [s.name for s in subtasks],
                "subtask_gids": [],  # Populated when subtasks created in Asana
                "timestamp": timestamp.isoformat(),
                "dependency_count": sum(len(s.dependencies) for s in subtasks),
                "complexity": complexity.value if complexity else "unknown",
                "is_xl": complexity == TaskComplexity.XL if complexity else False,
                "completed": False,
                "subtasks_completed": 0,
                "dependencies_correct": 0,
                "dependencies_violated": 0,
            }
        )

    def record_completion(
        self,
        task_gid: str,
        subtasks_completed: int,
        total_subtasks: int,
        dependencies_correct: int,
        dependencies_violated: int,
        parent_completed: bool = False,
    ):
        """
        Record completion metrics for a decomposed task.

        Args:
            task_gid: The task GID to update
            subtasks_completed: Number of subtasks completed
            total_subtasks: Total subtasks in the decomposition
            dependencies_correct: Dependencies honored (prerequisite done first)
            dependencies_violated: Dependencies violated (out of order)
            parent_completed: Whether the parent XL task is now complete
        """
        # Find and update the decomposition record
        for d in self.decompositions:
            if d["task_gid"] == task_gid:
                d["completed"] = parent_completed
                d["subtasks_completed"] = subtasks_completed
                d["dependencies_correct"] = dependencies_correct
                d["dependencies_violated"] = dependencies_violated
                break

        # Also store in completion records for historical analysis
        self.completion_records.append(
            {
                "task_gid": task_gid,
                "timestamp": datetime.now().isoformat(),
                "subtasks_completed": subtasks_completed,
                "total_subtasks": total_subtasks,
                "dependencies_correct": dependencies_correct,
                "dependencies_violated": dependencies_violated,
                "parent_completed": parent_completed,
            }
        )

    def get_xl_completion_rate(self) -> Dict[str, Any]:
        """
        Calculate XL task completion rate and improvement.

        Returns:
            Dict with current_rate, baseline_rate, improvement, meets_target
        """
        xl_tasks = [d for d in self.decompositions if d.get("is_xl", False)]

        if not xl_tasks:
            return {
                "current_rate": 0.0,
                "baseline_rate": self.BASELINE_XL_COMPLETION_RATE,
                "improvement": 0.0,
                "meets_target": False,
                "sample_size": 0,
            }

        completed = sum(1 for d in xl_tasks if d.get("completed", False))
        current_rate = completed / len(xl_tasks)
        improvement = current_rate - self.BASELINE_XL_COMPLETION_RATE

        return {
            "current_rate": round(current_rate, 3),
            "baseline_rate": self.BASELINE_XL_COMPLETION_RATE,
            "improvement": round(improvement, 3),
            "meets_target": improvement >= 0.20,  # 20%+ improvement target
            "sample_size": len(xl_tasks),
        }

    def get_dependency_accuracy(self) -> Dict[str, Any]:
        """
        Calculate dependency accuracy across all decompositions.

        Dependency accuracy = correct / (correct + violated)
        A correct dependency means the prerequisite subtask completed before
        the dependent subtask.

        Returns:
            Dict with accuracy, total_correct, total_violated, meets_target
        """
        total_correct = sum(
            d.get("dependencies_correct", 0) for d in self.decompositions
        )
        total_violated = sum(
            d.get("dependencies_violated", 0) for d in self.decompositions
        )
        total = total_correct + total_violated

        if total == 0:
            return {
                "accuracy": 1.0,  # No dependencies = perfect accuracy
                "total_correct": 0,
                "total_violated": 0,
                "meets_target": True,
                "sample_size": 0,
            }

        accuracy = total_correct / total

        return {
            "accuracy": round(accuracy, 3),
            "total_correct": total_correct,
            "total_violated": total_violated,
            "meets_target": accuracy >= self.TARGET_DEPENDENCY_ACCURACY,
            "sample_size": total,
        }

    def get_subtask_completion_rate(self) -> Dict[str, Any]:
        """
        Calculate subtask completion rate and improvement.

        Returns:
            Dict with current_rate, baseline_rate, improvement, meets_target
        """
        total_subtasks = sum(d.get("num_subtasks", 0) for d in self.decompositions)
        completed_subtasks = sum(
            d.get("subtasks_completed", 0) for d in self.decompositions
        )

        if total_subtasks == 0:
            return {
                "current_rate": 0.0,
                "baseline_rate": self.BASELINE_SUBTASK_COMPLETION_RATE,
                "improvement": 0.0,
                "meets_target": False,
                "total_subtasks": 0,
                "completed_subtasks": 0,
            }

        current_rate = completed_subtasks / total_subtasks
        improvement = current_rate - self.BASELINE_SUBTASK_COMPLETION_RATE

        return {
            "current_rate": round(current_rate, 3),
            "baseline_rate": self.BASELINE_SUBTASK_COMPLETION_RATE,
            "improvement": round(improvement, 3),
            "meets_target": improvement >= 0.15,  # 15%+ improvement target
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of decomposition metrics."""
        if not self.decompositions:
            return {
                "total_decompositions": 0,
                "avg_subtasks_per_task": 0.0,
                "avg_dependencies_per_task": 0.0,
                "xl_completion": self.get_xl_completion_rate(),
                "dependency_accuracy": self.get_dependency_accuracy(),
                "subtask_completion": self.get_subtask_completion_rate(),
                "success_criteria_met": False,
            }

        total = len(self.decompositions)
        avg_subtasks = sum(d["num_subtasks"] for d in self.decompositions) / total
        avg_deps = sum(d["dependency_count"] for d in self.decompositions) / total

        xl_metrics = self.get_xl_completion_rate()
        dep_metrics = self.get_dependency_accuracy()
        subtask_metrics = self.get_subtask_completion_rate()

        # All three criteria must be met for overall success
        success_criteria_met = (
            xl_metrics["meets_target"]
            and dep_metrics["meets_target"]
            and subtask_metrics["meets_target"]
        )

        return {
            "total_decompositions": total,
            "avg_subtasks_per_task": round(avg_subtasks, 2),
            "avg_dependencies_per_task": round(avg_deps, 2),
            "xl_completion": xl_metrics,
            "dependency_accuracy": dep_metrics,
            "subtask_completion": subtask_metrics,
            "success_criteria_met": success_criteria_met,
            "recent_decompositions": self.decompositions[-5:],
        }

    def get_dashboard_report(self) -> str:
        """
        Generate a human-readable dashboard report.

        Returns:
            Formatted string with metrics dashboard
        """
        summary = self.get_metrics_summary()

        report_lines = [
            "=" * 60,
            "TASK DECOMPOSITION METRICS DASHBOARD",
            "=" * 60,
            "",
            f"Total Decompositions: {summary['total_decompositions']}",
            f"Avg Subtasks/Task: {summary['avg_subtasks_per_task']}",
            f"Avg Dependencies/Task: {summary['avg_dependencies_per_task']}",
            "",
            "--- XL Task Completion Rate ---",
            f"  Current Rate: {summary['xl_completion']['current_rate'] * 100:.1f}%",
            f"  Baseline: {summary['xl_completion']['baseline_rate'] * 100:.1f}%",
            f"  Improvement: {summary['xl_completion']['improvement'] * 100:+.1f}%",
            f"  Target Met (20%+): {'✓' if summary['xl_completion']['meets_target'] else '✗'}",
            f"  Sample Size: {summary['xl_completion']['sample_size']}",
            "",
            "--- Dependency Accuracy ---",
            f"  Accuracy: {summary['dependency_accuracy']['accuracy'] * 100:.1f}%",
            f"  Correct: {summary['dependency_accuracy']['total_correct']}",
            f"  Violated: {summary['dependency_accuracy']['total_violated']}",
            f"  Target Met (>90%): {'✓' if summary['dependency_accuracy']['meets_target'] else '✗'}",
            "",
            "--- Subtask Completion Rate ---",
            f"  Current Rate: {summary['subtask_completion']['current_rate'] * 100:.1f}%",
            f"  Baseline: {summary['subtask_completion']['baseline_rate'] * 100:.1f}%",
            f"  Improvement: {summary['subtask_completion']['improvement'] * 100:+.1f}%",
            f"  Target Met (15%+): {'✓' if summary['subtask_completion']['meets_target'] else '✗'}",
            f"  Total Subtasks: {summary['subtask_completion']['total_subtasks']}",
            f"  Completed: {summary['subtask_completion']['completed_subtasks']}",
            "",
            "=" * 60,
            f"OVERALL SUCCESS CRITERIA: {'✓ MET' if summary['success_criteria_met'] else '✗ NOT MET'}",
            "=" * 60,
        ]

        return "\n".join(report_lines)
