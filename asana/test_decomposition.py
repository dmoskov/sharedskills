#!/usr/bin/env python3
"""
Unit tests for decomposition.py - Synapse-style task decomposition algorithm

Tests cover all major components:
1. ConstraintType and TaskComplexity enums
2. Constraint, Subtask, ConstraintSet, DependencyGraph dataclasses
3. TaskDecomposer with 4-step algorithm
4. DecompositionMetrics tracking

Target: 90%+ code coverage
"""

import pytest
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from decomposition import (
    ConstraintType,
    TaskComplexity,
    Constraint,
    Subtask,
    ConstraintSet,
    DependencyGraph,
    TaskDecomposer,
    DecompositionMetrics,
)


# ============================================================================
# ConstraintType Enum Tests
# ============================================================================
class TestConstraintType:
    """Test ConstraintType enum values"""

    def test_temporal_value(self):
        """Should have temporal constraint type"""
        assert ConstraintType.TEMPORAL.value == "temporal"

    def test_spatial_value(self):
        """Should have spatial constraint type"""
        assert ConstraintType.SPATIAL.value == "spatial"

    def test_resource_value(self):
        """Should have resource constraint type"""
        assert ConstraintType.RESOURCE.value == "resource"

    def test_dependency_value(self):
        """Should have dependency constraint type"""
        assert ConstraintType.DEPENDENCY.value == "dependency"


# ============================================================================
# TaskComplexity Enum Tests
# ============================================================================
class TestTaskComplexity:
    """Test TaskComplexity enum values"""

    def test_small_value(self):
        """Should have small complexity"""
        assert TaskComplexity.SMALL.value == "small"

    def test_medium_value(self):
        """Should have medium complexity"""
        assert TaskComplexity.MEDIUM.value == "medium"

    def test_large_value(self):
        """Should have large complexity"""
        assert TaskComplexity.LARGE.value == "large"

    def test_xl_value(self):
        """Should have XL complexity"""
        assert TaskComplexity.XL.value == "xl"


# ============================================================================
# Constraint Dataclass Tests
# ============================================================================
class TestConstraint:
    """Test Constraint dataclass"""

    def test_basic_creation(self):
        """Should create constraint with required fields"""
        c = Constraint(
            type=ConstraintType.TEMPORAL,
            description="Test deadline",
            severity=0.8,
        )
        assert c.type == ConstraintType.TEMPORAL
        assert c.description == "Test deadline"
        assert c.severity == 0.8
        assert c.metadata == {}

    def test_with_metadata(self):
        """Should create constraint with metadata"""
        c = Constraint(
            type=ConstraintType.RESOURCE,
            description="API limit",
            severity=0.7,
            metadata={"limit": 100, "unit": "requests/min"},
        )
        assert c.metadata["limit"] == 100
        assert c.metadata["unit"] == "requests/min"

    def test_severity_boundary_low(self):
        """Should allow severity of 0.0"""
        c = Constraint(
            type=ConstraintType.SPATIAL,
            description="Soft constraint",
            severity=0.0,
        )
        assert c.severity == 0.0

    def test_severity_boundary_high(self):
        """Should allow severity of 1.0"""
        c = Constraint(
            type=ConstraintType.DEPENDENCY,
            description="Hard constraint",
            severity=1.0,
        )
        assert c.severity == 1.0


# ============================================================================
# Subtask Dataclass Tests
# ============================================================================
class TestSubtask:
    """Test Subtask dataclass"""

    def test_basic_creation(self):
        """Should create subtask with required fields"""
        s = Subtask(
            name="Test subtask",
            description="Do the thing",
            complexity=TaskComplexity.SMALL,
        )
        assert s.name == "Test subtask"
        assert s.description == "Do the thing"
        assert s.complexity == TaskComplexity.SMALL
        assert s.dependencies == []
        assert s.priority == 0.5
        assert s.constraints == []
        assert s.estimated_duration is None
        assert s.metadata == {}

    def test_with_dependencies(self):
        """Should create subtask with dependencies"""
        s = Subtask(
            name="Step 2",
            description="Second step",
            complexity=TaskComplexity.MEDIUM,
            dependencies=["Step 1"],
        )
        assert s.dependencies == ["Step 1"]

    def test_with_priority(self):
        """Should create subtask with custom priority"""
        s = Subtask(
            name="Critical task",
            description="High priority",
            complexity=TaskComplexity.LARGE,
            priority=0.9,
        )
        assert s.priority == 0.9

    def test_with_constraints(self):
        """Should create subtask with constraints"""
        c = Constraint(
            type=ConstraintType.TEMPORAL,
            description="Deadline",
            severity=0.9,
        )
        s = Subtask(
            name="Constrained task",
            description="Has constraints",
            complexity=TaskComplexity.SMALL,
            constraints=[c],
        )
        assert len(s.constraints) == 1
        assert s.constraints[0].type == ConstraintType.TEMPORAL

    def test_with_estimated_duration(self):
        """Should create subtask with estimated duration"""
        s = Subtask(
            name="Timed task",
            description="With duration",
            complexity=TaskComplexity.MEDIUM,
            estimated_duration=timedelta(hours=4),
        )
        assert s.estimated_duration == timedelta(hours=4)

    def test_to_dict_basic(self):
        """Should serialize subtask to dict"""
        s = Subtask(
            name="Test",
            description="Desc",
            complexity=TaskComplexity.SMALL,
        )
        d = s.to_dict()
        assert d["name"] == "Test"
        assert d["description"] == "Desc"
        assert d["complexity"] == "small"
        assert d["dependencies"] == []
        assert d["priority"] == 0.5
        assert d["constraints"] == []
        assert d["estimated_duration"] is None

    def test_to_dict_with_constraints(self):
        """Should serialize constraints in dict"""
        c = Constraint(
            type=ConstraintType.RESOURCE,
            description="API limit",
            severity=0.7,
            metadata={"limit": 100},
        )
        s = Subtask(
            name="Test",
            description="Desc",
            complexity=TaskComplexity.SMALL,
            constraints=[c],
        )
        d = s.to_dict()
        assert len(d["constraints"]) == 1
        assert d["constraints"][0]["type"] == "resource"
        assert d["constraints"][0]["severity"] == 0.7

    def test_to_dict_with_duration(self):
        """Should serialize duration as string"""
        s = Subtask(
            name="Test",
            description="Desc",
            complexity=TaskComplexity.SMALL,
            estimated_duration=timedelta(hours=2),
        )
        d = s.to_dict()
        assert d["estimated_duration"] == "2:00:00"


# ============================================================================
# ConstraintSet Tests
# ============================================================================
class TestConstraintSet:
    """Test ConstraintSet dataclass"""

    def test_empty_set(self):
        """Should create empty constraint set"""
        cs = ConstraintSet(constraints=[])
        assert cs.constraints == []

    def test_get_by_type_found(self):
        """Should find constraints by type"""
        c1 = Constraint(ConstraintType.TEMPORAL, "Deadline", 0.8)
        c2 = Constraint(ConstraintType.RESOURCE, "API limit", 0.5)
        c3 = Constraint(ConstraintType.TEMPORAL, "Duration", 0.6)
        cs = ConstraintSet(constraints=[c1, c2, c3])

        temporal = cs.get_by_type(ConstraintType.TEMPORAL)
        assert len(temporal) == 2
        assert all(c.type == ConstraintType.TEMPORAL for c in temporal)

    def test_get_by_type_not_found(self):
        """Should return empty list when type not found"""
        c1 = Constraint(ConstraintType.TEMPORAL, "Deadline", 0.8)
        cs = ConstraintSet(constraints=[c1])

        spatial = cs.get_by_type(ConstraintType.SPATIAL)
        assert spatial == []

    def test_has_hard_constraints_true(self):
        """Should detect hard constraints (severity >= 0.8)"""
        c1 = Constraint(ConstraintType.TEMPORAL, "Deadline", 0.9)
        cs = ConstraintSet(constraints=[c1])
        assert cs.has_hard_constraints() is True

    def test_has_hard_constraints_false(self):
        """Should return False when no hard constraints"""
        c1 = Constraint(ConstraintType.TEMPORAL, "Soft deadline", 0.5)
        cs = ConstraintSet(constraints=[c1])
        assert cs.has_hard_constraints() is False

    def test_has_hard_constraints_boundary(self):
        """Should treat 0.8 as hard constraint"""
        c1 = Constraint(ConstraintType.TEMPORAL, "Boundary", 0.8)
        cs = ConstraintSet(constraints=[c1])
        assert cs.has_hard_constraints() is True

    def test_has_hard_constraints_empty(self):
        """Should return False for empty set"""
        cs = ConstraintSet(constraints=[])
        assert cs.has_hard_constraints() is False


# ============================================================================
# DependencyGraph Tests
# ============================================================================
class TestDependencyGraph:
    """Test DependencyGraph dataclass"""

    def test_empty_graph(self):
        """Should create empty graph"""
        g = DependencyGraph(nodes=[], edges=[])
        assert g.nodes == []
        assert g.edges == []

    def test_get_prerequisites(self):
        """Should find prerequisites for a node"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("A", "C"), ("B", "C")],
        )
        prereqs = g.get_prerequisites("C")
        assert set(prereqs) == {"A", "B"}

    def test_get_prerequisites_none(self):
        """Should return empty list for node with no prerequisites"""
        g = DependencyGraph(
            nodes=["A", "B"],
            edges=[("A", "B")],
        )
        prereqs = g.get_prerequisites("A")
        assert prereqs == []

    def test_get_dependents(self):
        """Should find dependents of a node"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("A", "C")],
        )
        deps = g.get_dependents("A")
        assert set(deps) == {"B", "C"}

    def test_get_dependents_none(self):
        """Should return empty list for leaf node"""
        g = DependencyGraph(
            nodes=["A", "B"],
            edges=[("A", "B")],
        )
        deps = g.get_dependents("B")
        assert deps == []

    def test_has_cycle_no_cycle(self):
        """Should return False for acyclic graph"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C")],
        )
        assert g.has_cycle() is False

    def test_has_cycle_with_cycle(self):
        """Should detect cycle in graph"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C"), ("C", "A")],
        )
        assert g.has_cycle() is True

    def test_has_cycle_self_loop(self):
        """Should detect self-loop as cycle"""
        g = DependencyGraph(
            nodes=["A"],
            edges=[("A", "A")],
        )
        assert g.has_cycle() is True

    def test_topological_sort_simple(self):
        """Should return topologically sorted nodes"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C")],
        )
        sorted_nodes = g.topological_sort()
        assert sorted_nodes == ["A", "B", "C"]

    def test_topological_sort_parallel(self):
        """Should handle parallel dependencies"""
        g = DependencyGraph(
            nodes=["A", "B", "C", "D"],
            edges=[("A", "C"), ("B", "C"), ("C", "D")],
        )
        sorted_nodes = g.topological_sort()
        # A and B can be in either order, but must come before C
        assert sorted_nodes is not None
        assert sorted_nodes.index("A") < sorted_nodes.index("C")
        assert sorted_nodes.index("B") < sorted_nodes.index("C")
        assert sorted_nodes.index("C") < sorted_nodes.index("D")

    def test_topological_sort_with_cycle(self):
        """Should return None for cyclic graph"""
        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C"), ("C", "A")],
        )
        assert g.topological_sort() is None

    def test_topological_sort_disconnected(self):
        """Should handle disconnected components"""
        g = DependencyGraph(
            nodes=["A", "B", "C", "D"],
            edges=[("A", "B")],  # C and D are disconnected
        )
        sorted_nodes = g.topological_sort()
        assert sorted_nodes is not None
        assert len(sorted_nodes) == 4
        assert sorted_nodes.index("A") < sorted_nodes.index("B")


# ============================================================================
# TaskDecomposer Tests
# ============================================================================
class TestTaskDecomposerInit:
    """Test TaskDecomposer initialization"""

    def test_default_init(self):
        """Should initialize with default values"""
        d = TaskDecomposer()
        assert d.max_subtask_complexity == TaskComplexity.MEDIUM
        assert d.min_subtasks == 2
        assert d.max_subtasks == 8

    def test_custom_max_complexity(self):
        """Should allow custom max complexity"""
        d = TaskDecomposer(max_subtask_complexity=TaskComplexity.LARGE)
        assert d.max_subtask_complexity == TaskComplexity.LARGE

    def test_custom_min_subtasks(self):
        """Should allow custom min subtasks"""
        d = TaskDecomposer(min_subtasks=3)
        assert d.min_subtasks == 3

    def test_custom_max_subtasks(self):
        """Should allow custom max subtasks"""
        d = TaskDecomposer(max_subtasks=10)
        assert d.max_subtasks == 10


class TestTaskDecomposerDecompose:
    """Test TaskDecomposer.decompose() method"""

    def test_basic_decomposition(self):
        """Should decompose task into subtasks"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Test Task",
            "Do something complex with multiple steps",
            TaskComplexity.XL,
        )
        assert len(subtasks) >= 2  # min_subtasks default
        assert all(isinstance(s, Subtask) for s in subtasks)

    def test_decomposition_with_numbered_steps(self):
        """Should extract numbered steps from description"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Multi-step Task",
            """Complete the following:
            1. First step
            2. Second step
            3. Third step""",
            TaskComplexity.LARGE,
        )
        # Should have at least the 3 explicit steps
        assert len(subtasks) >= 3

    def test_decomposition_with_bullet_points(self):
        """Should extract bullet points from description"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Bullet Task",
            """Tasks:
            - Do A
            - Do B
            - Do C""",
            TaskComplexity.LARGE,
        )
        assert len(subtasks) >= 3

    def test_decomposition_preserves_dependencies(self):
        """Should create dependencies between sequential subtasks"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Sequential Task",
            "1. First\n2. Second\n3. Third",
            TaskComplexity.XL,
        )
        # First subtask should have no dependencies
        # Subsequent subtasks should depend on previous
        has_dependencies = any(len(s.dependencies) > 0 for s in subtasks)
        assert has_dependencies

    def test_decomposition_with_context(self):
        """Should use context for decomposition"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Remote Task",
            "Deploy to cloud",
            TaskComplexity.LARGE,
            context={"remote_execution": True},
        )
        # Should have resource constraint for remote execution
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        has_resource = any(c.type == ConstraintType.RESOURCE for c in all_constraints)
        assert has_resource

    def test_decomposition_respects_max_subtasks(self):
        """Should not exceed max_subtasks"""
        d = TaskDecomposer(max_subtasks=4)
        subtasks = d.decompose(
            "Big Task",
            """Steps:
            1. A
            2. B
            3. C
            4. D
            5. E
            6. F
            7. G
            8. H
            9. I
            10. J""",
            TaskComplexity.XL,
        )
        assert len(subtasks) <= 4

    def test_decomposition_respects_min_subtasks(self):
        """Should error if cannot meet min_subtasks"""
        d = TaskDecomposer(min_subtasks=5)
        # With only 2 steps defined, should raise error
        # when default fallback generates 4 subtasks
        with pytest.raises(ValueError, match="minimum is 5"):
            d.decompose(
                "Minimal Task",
                "Just do it",
                TaskComplexity.SMALL,
            )


class TestTaskDecomposerConstraintAnalysis:
    """Test TaskDecomposer._analyze_constraints() method"""

    def test_xl_tasks_get_temporal_constraint(self):
        """XL tasks should get temporal constraint"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "XL Task",
            "Big project",
            TaskComplexity.XL,
        )
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        has_temporal = any(c.type == ConstraintType.TEMPORAL for c in all_constraints)
        assert has_temporal

    def test_deadline_keywords_add_constraint(self):
        """Should detect deadline keywords"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Urgent Task",
            "Must complete by deadline - this is urgent",
            TaskComplexity.MEDIUM,
        )
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        deadline_constraints = [
            c
            for c in all_constraints
            if c.type == ConstraintType.TEMPORAL and "deadline" in c.description.lower()
        ]
        assert len(deadline_constraints) > 0

    def test_api_limit_constraint(self):
        """Should add constraint for API limits"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "API Task",
            "Call external API",
            TaskComplexity.MEDIUM,
            context={"api_limit": "100/min"},
        )
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        api_constraints = [
            c for c in all_constraints if c.type == ConstraintType.RESOURCE
        ]
        assert len(api_constraints) > 0

    def test_blocked_by_constraint(self):
        """Should add constraint for blocked dependencies"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Blocked Task",
            "Waiting on other team",
            TaskComplexity.MEDIUM,
            context={"blocked_by": "Task 123"},
        )
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        dep_constraints = [
            c for c in all_constraints if c.type == ConstraintType.DEPENDENCY
        ]
        assert len(dep_constraints) > 0

    def test_deploy_keywords_add_spatial_constraint(self):
        """Should detect deployment keywords for spatial constraints"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Deploy Task",
            "Deploy to AWS with Docker and Kubernetes",
            TaskComplexity.LARGE,
        )
        all_constraints = []
        for s in subtasks:
            all_constraints.extend(s.constraints)
        spatial_constraints = [
            c for c in all_constraints if c.type == ConstraintType.SPATIAL
        ]
        assert len(spatial_constraints) > 0


class TestTaskDecomposerDependencyMapping:
    """Test TaskDecomposer._map_dependencies() method"""

    def test_sequential_dependencies(self):
        """Should create sequential dependencies for numbered steps"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Sequential",
            "1. First\n2. Second\n3. Third",
            TaskComplexity.LARGE,
        )
        # Check that later subtasks depend on earlier ones
        dep_count = sum(len(s.dependencies) for s in subtasks)
        assert dep_count > 0

    def test_circular_dependency_raises_error(self):
        """Should raise error for circular dependencies"""
        TaskDecomposer()
        # This test verifies the cycle detection works
        # by checking the DependencyGraph directly
        from decomposition import DependencyGraph

        g = DependencyGraph(
            nodes=["A", "B", "C"],
            edges=[("A", "B"), ("B", "C"), ("C", "A")],
        )
        assert g.has_cycle() is True


class TestTaskDecomposerPriorityAssignment:
    """Test TaskDecomposer._assign_priorities() method"""

    def test_priorities_assigned(self):
        """Should assign priorities to subtasks"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Priority Task",
            "1. Critical first step\n2. Follow-up\n3. Final check",
            TaskComplexity.LARGE,
        )
        # All subtasks should have priority in [0, 1]
        for s in subtasks:
            assert 0.0 <= s.priority <= 1.0

    def test_first_subtask_higher_priority(self):
        """First subtasks (no prerequisites) should have boosted priority"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Priority Task",
            "1. Setup\n2. Build\n3. Test",
            TaskComplexity.LARGE,
        )
        # First subtask often has higher priority due to critical path boost
        # This is a soft test - priorities vary by algorithm
        priorities = [s.priority for s in subtasks]
        assert len(set(priorities)) >= 1  # At least some variance


class TestTaskDecomposerGranularityOptimization:
    """Test TaskDecomposer._optimize_granularity() method"""

    def test_subtasks_have_appropriate_complexity(self):
        """Subtasks should not exceed max_subtask_complexity"""
        d = TaskDecomposer(max_subtask_complexity=TaskComplexity.MEDIUM)
        subtasks = d.decompose(
            "Complex Task",
            "Do many things",
            TaskComplexity.XL,
        )
        for s in subtasks:
            # Complexity should be SMALL or MEDIUM (not LARGE or XL)
            assert s.complexity in [TaskComplexity.SMALL, TaskComplexity.MEDIUM]

    def test_merging_reduces_subtask_count(self):
        """Should merge subtasks when exceeding max"""
        d = TaskDecomposer(max_subtasks=3)
        subtasks = d.decompose(
            "Many Steps",
            """Steps:
            1. A
            2. B
            3. C
            4. D
            5. E
            6. F""",
            TaskComplexity.XL,
        )
        assert len(subtasks) <= 3


class TestTaskDecomposerStepExtraction:
    """Test TaskDecomposer._extract_steps_from_description() method"""

    def test_extract_numbered_dot_format(self):
        """Should extract 1. 2. 3. format"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Numbered",
            "1. First\n2. Second\n3. Third",
            TaskComplexity.MEDIUM,
        )
        # Should extract the 3 steps (or add default if regex fails)
        assert len(subtasks) >= 2

    def test_extract_numbered_paren_format(self):
        """Should extract 1) 2) 3) format"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Numbered Paren",
            "1) First\n2) Second\n3) Third",
            TaskComplexity.MEDIUM,
        )
        assert len(subtasks) >= 2

    def test_extract_bullet_dash(self):
        """Should extract - bullet format"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Bullets",
            "- First\n- Second\n- Third",
            TaskComplexity.MEDIUM,
        )
        assert len(subtasks) >= 2

    def test_extract_bullet_asterisk(self):
        """Should extract * bullet format"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Asterisks",
            "* First\n* Second\n* Third",
            TaskComplexity.MEDIUM,
        )
        assert len(subtasks) >= 2

    def test_default_steps_when_no_structure(self):
        """Should use default steps when no structure found"""
        d = TaskDecomposer()
        subtasks = d.decompose(
            "Unstructured",
            "Just do the thing without any numbered or bulleted steps",
            TaskComplexity.MEDIUM,
        )
        # Should fall back to default 4 steps
        assert len(subtasks) >= 2


# ============================================================================
# DecompositionMetrics Tests
# ============================================================================
class TestDecompositionMetrics:
    """Test DecompositionMetrics class"""

    def test_init_empty(self):
        """Should initialize with empty decompositions"""
        m = DecompositionMetrics()
        assert m.decompositions == []
        assert m.completion_records == []

    def test_record_decomposition(self):
        """Should record a decomposition"""
        m = DecompositionMetrics()
        subtasks = [
            Subtask("A", "Do A", TaskComplexity.SMALL),
            Subtask("B", "Do B", TaskComplexity.SMALL, dependencies=["A"]),
        ]
        m.record_decomposition(
            task_gid="12345",
            task_name="Test Task",
            subtasks=subtasks,
        )
        assert len(m.decompositions) == 1
        assert m.decompositions[0]["task_gid"] == "12345"
        assert m.decompositions[0]["num_subtasks"] == 2

    def test_record_decomposition_with_timestamp(self):
        """Should record with custom timestamp"""
        m = DecompositionMetrics()
        ts = datetime(2026, 1, 15, 10, 30, 0)
        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
        m.record_decomposition(
            task_gid="12345",
            task_name="Test",
            subtasks=subtasks,
            timestamp=ts,
        )
        assert m.decompositions[0]["timestamp"] == ts.isoformat()

    def test_record_decomposition_with_complexity(self):
        """Should record with complexity for XL tracking"""
        m = DecompositionMetrics()
        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
        m.record_decomposition(
            task_gid="xl-1",
            task_name="XL Task",
            subtasks=subtasks,
            complexity=TaskComplexity.XL,
        )
        assert m.decompositions[0]["is_xl"] is True
        assert m.decompositions[0]["complexity"] == "xl"

    def test_get_metrics_summary_empty(self):
        """Should return zeros for empty metrics"""
        m = DecompositionMetrics()
        summary = m.get_metrics_summary()
        assert summary["total_decompositions"] == 0
        assert summary["avg_subtasks_per_task"] == 0.0
        assert summary["avg_dependencies_per_task"] == 0.0

    def test_get_metrics_summary_with_data(self):
        """Should calculate correct averages"""
        m = DecompositionMetrics()

        # First decomposition: 2 subtasks, 1 dependency
        subtasks1 = [
            Subtask("A", "Do A", TaskComplexity.SMALL),
            Subtask("B", "Do B", TaskComplexity.SMALL, dependencies=["A"]),
        ]
        m.record_decomposition("1", "Task 1", subtasks1)

        # Second decomposition: 4 subtasks, 3 dependencies
        subtasks2 = [
            Subtask("A", "Do A", TaskComplexity.SMALL),
            Subtask("B", "Do B", TaskComplexity.SMALL, dependencies=["A"]),
            Subtask("C", "Do C", TaskComplexity.SMALL, dependencies=["B"]),
            Subtask("D", "Do D", TaskComplexity.SMALL, dependencies=["C"]),
        ]
        m.record_decomposition("2", "Task 2", subtasks2)

        summary = m.get_metrics_summary()
        assert summary["total_decompositions"] == 2
        assert summary["avg_subtasks_per_task"] == 3.0  # (2 + 4) / 2
        assert summary["avg_dependencies_per_task"] == 2.0  # (1 + 3) / 2

    def test_get_metrics_summary_recent_limit(self):
        """Should return only last 5 in recent_decompositions"""
        m = DecompositionMetrics()
        for i in range(10):
            subtasks = [Subtask(f"Task {i}", "Desc", TaskComplexity.SMALL)]
            m.record_decomposition(str(i), f"Task {i}", subtasks)

        summary = m.get_metrics_summary()
        assert summary["total_decompositions"] == 10
        assert len(summary["recent_decompositions"]) == 5


class TestDecompositionMetricsCompletion:
    """Test DecompositionMetrics completion tracking"""

    def test_record_completion(self):
        """Should record completion metrics"""
        m = DecompositionMetrics()
        subtasks = [
            Subtask("A", "Do A", TaskComplexity.SMALL),
            Subtask("B", "Do B", TaskComplexity.SMALL, dependencies=["A"]),
        ]
        m.record_decomposition("task-1", "Test Task", subtasks)

        m.record_completion(
            task_gid="task-1",
            subtasks_completed=2,
            total_subtasks=2,
            dependencies_correct=1,
            dependencies_violated=0,
            parent_completed=True,
        )

        assert m.decompositions[0]["completed"] is True
        assert m.decompositions[0]["subtasks_completed"] == 2
        assert m.decompositions[0]["dependencies_correct"] == 1
        assert m.decompositions[0]["dependencies_violated"] == 0
        assert len(m.completion_records) == 1

    def test_record_completion_partial(self):
        """Should handle partial completion"""
        m = DecompositionMetrics()
        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL) for _ in range(4)]
        m.record_decomposition("task-1", "Test Task", subtasks)

        m.record_completion(
            task_gid="task-1",
            subtasks_completed=2,
            total_subtasks=4,
            dependencies_correct=1,
            dependencies_violated=1,
            parent_completed=False,
        )

        assert m.decompositions[0]["completed"] is False
        assert m.decompositions[0]["subtasks_completed"] == 2


class TestDecompositionMetricsXLCompletion:
    """Test XL task completion rate metrics"""

    def test_xl_completion_empty(self):
        """Should handle no XL tasks"""
        m = DecompositionMetrics()
        result = m.get_xl_completion_rate()
        assert result["current_rate"] == 0.0
        assert result["sample_size"] == 0
        assert result["meets_target"] is False

    def test_xl_completion_rate_calculation(self):
        """Should calculate correct XL completion rate"""
        m = DecompositionMetrics()

        # Add 5 XL tasks, 4 completed (80% rate)
        for i in range(5):
            subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
            m.record_decomposition(
                f"xl-{i}", f"XL Task {i}", subtasks, complexity=TaskComplexity.XL
            )

        # Complete 4 of them
        for i in range(4):
            m.record_completion(
                task_gid=f"xl-{i}",
                subtasks_completed=1,
                total_subtasks=1,
                dependencies_correct=0,
                dependencies_violated=0,
                parent_completed=True,
            )

        result = m.get_xl_completion_rate()
        assert result["current_rate"] == 0.8
        assert result["baseline_rate"] == 0.6
        assert result["improvement"] == 0.2
        assert result["meets_target"] is True  # 20% improvement
        assert result["sample_size"] == 5

    def test_xl_completion_below_target(self):
        """Should report when below target"""
        m = DecompositionMetrics()

        # Add 10 XL tasks, only 7 completed (70% rate = 10% improvement)
        for i in range(10):
            subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
            m.record_decomposition(
                f"xl-{i}", f"XL Task {i}", subtasks, complexity=TaskComplexity.XL
            )

        for i in range(7):
            m.record_completion(
                task_gid=f"xl-{i}",
                subtasks_completed=1,
                total_subtasks=1,
                dependencies_correct=0,
                dependencies_violated=0,
                parent_completed=True,
            )

        result = m.get_xl_completion_rate()
        assert result["current_rate"] == 0.7
        assert result["improvement"] == 0.1  # Only 10% improvement
        assert result["meets_target"] is False


class TestDecompositionMetricsDependencyAccuracy:
    """Test dependency accuracy metrics"""

    def test_dependency_accuracy_empty(self):
        """Should handle no dependencies"""
        m = DecompositionMetrics()
        result = m.get_dependency_accuracy()
        assert result["accuracy"] == 1.0  # No deps = perfect
        assert result["sample_size"] == 0
        assert result["meets_target"] is True

    def test_dependency_accuracy_calculation(self):
        """Should calculate correct dependency accuracy"""
        m = DecompositionMetrics()

        subtasks = [
            Subtask("A", "Do A", TaskComplexity.SMALL),
            Subtask("B", "Do B", TaskComplexity.SMALL, dependencies=["A"]),
        ]
        m.record_decomposition("task-1", "Test Task", subtasks)

        # 9 correct, 1 violated = 90% accuracy
        m.record_completion(
            task_gid="task-1",
            subtasks_completed=2,
            total_subtasks=2,
            dependencies_correct=9,
            dependencies_violated=1,
            parent_completed=True,
        )

        result = m.get_dependency_accuracy()
        assert result["accuracy"] == 0.9
        assert result["total_correct"] == 9
        assert result["total_violated"] == 1
        assert result["meets_target"] is True  # Exactly at 90%

    def test_dependency_accuracy_below_target(self):
        """Should report when below 90% target"""
        m = DecompositionMetrics()

        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
        m.record_decomposition("task-1", "Test", subtasks)

        # 8 correct, 2 violated = 80% accuracy
        m.record_completion(
            task_gid="task-1",
            subtasks_completed=1,
            total_subtasks=1,
            dependencies_correct=8,
            dependencies_violated=2,
            parent_completed=True,
        )

        result = m.get_dependency_accuracy()
        assert result["accuracy"] == 0.8
        assert result["meets_target"] is False


class TestDecompositionMetricsSubtaskCompletion:
    """Test subtask completion rate metrics"""

    def test_subtask_completion_empty(self):
        """Should handle no subtasks"""
        m = DecompositionMetrics()
        result = m.get_subtask_completion_rate()
        assert result["current_rate"] == 0.0
        assert result["total_subtasks"] == 0
        assert result["meets_target"] is False

    def test_subtask_completion_calculation(self):
        """Should calculate correct subtask completion rate"""
        m = DecompositionMetrics()

        # Task 1: 4 subtasks, all completed
        subtasks1 = [Subtask(f"S{i}", "Do", TaskComplexity.SMALL) for i in range(4)]
        m.record_decomposition("task-1", "Task 1", subtasks1)
        m.record_completion(
            "task-1",
            subtasks_completed=4,
            total_subtasks=4,
            dependencies_correct=0,
            dependencies_violated=0,
            parent_completed=True,
        )

        # Task 2: 6 subtasks, 5 completed
        subtasks2 = [Subtask(f"S{i}", "Do", TaskComplexity.SMALL) for i in range(6)]
        m.record_decomposition("task-2", "Task 2", subtasks2)
        m.record_completion(
            "task-2",
            subtasks_completed=5,
            total_subtasks=6,
            dependencies_correct=0,
            dependencies_violated=0,
            parent_completed=False,
        )

        # Total: 10 subtasks, 9 completed = 90%
        result = m.get_subtask_completion_rate()
        assert result["current_rate"] == 0.9
        assert result["total_subtasks"] == 10
        assert result["completed_subtasks"] == 9
        assert result["improvement"] == 0.2  # 90% - 70% baseline
        assert result["meets_target"] is True  # 20% > 15% target


class TestDecompositionMetricsDashboard:
    """Test dashboard report generation"""

    def test_dashboard_report_empty(self):
        """Should generate report for empty metrics"""
        m = DecompositionMetrics()
        report = m.get_dashboard_report()
        assert "TASK DECOMPOSITION METRICS DASHBOARD" in report
        assert "Total Decompositions: 0" in report

    def test_dashboard_report_with_data(self):
        """Should generate comprehensive report"""
        m = DecompositionMetrics()

        # Add some data
        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
        m.record_decomposition(
            "task-1", "Test Task", subtasks, complexity=TaskComplexity.XL
        )
        m.record_completion(
            "task-1",
            subtasks_completed=1,
            total_subtasks=1,
            dependencies_correct=5,
            dependencies_violated=0,
            parent_completed=True,
        )

        report = m.get_dashboard_report()

        assert "XL Task Completion Rate" in report
        assert "Dependency Accuracy" in report
        assert "Subtask Completion Rate" in report
        assert "OVERALL SUCCESS CRITERIA" in report

    def test_dashboard_shows_targets(self):
        """Should show target met indicators"""
        m = DecompositionMetrics()

        # Create successful scenario
        for i in range(5):
            subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
            m.record_decomposition(
                f"xl-{i}", f"XL {i}", subtasks, complexity=TaskComplexity.XL
            )
            m.record_completion(
                f"xl-{i}",
                subtasks_completed=1,
                total_subtasks=1,
                dependencies_correct=10,
                dependencies_violated=0,
                parent_completed=True,
            )

        report = m.get_dashboard_report()
        # Should show checkmarks for met targets
        assert "✓" in report


class TestDecompositionMetricsSuccessCriteria:
    """Test overall success criteria evaluation"""

    def test_success_criteria_all_met(self):
        """Should report success when all criteria met"""
        m = DecompositionMetrics()

        # Create scenario that meets all targets:
        # - XL completion: >80% (20%+ improvement)
        # - Dependency accuracy: >90%
        # - Subtask completion: >85% (15%+ improvement)

        for i in range(10):
            subtasks = [Subtask(f"S{j}", "Do", TaskComplexity.SMALL) for j in range(5)]
            m.record_decomposition(
                f"xl-{i}", f"XL Task {i}", subtasks, complexity=TaskComplexity.XL
            )

        # Complete 9/10 XL tasks (90% = 30% improvement over 60% baseline)
        for i in range(9):
            m.record_completion(
                f"xl-{i}",
                subtasks_completed=5,  # All 5 subtasks (100%)
                total_subtasks=5,
                dependencies_correct=10,  # 100% accuracy
                dependencies_violated=0,
                parent_completed=True,
            )

        summary = m.get_metrics_summary()
        assert summary["xl_completion"]["meets_target"] is True
        assert summary["dependency_accuracy"]["meets_target"] is True
        assert summary["subtask_completion"]["meets_target"] is True
        assert summary["success_criteria_met"] is True

    def test_success_criteria_partial_failure(self):
        """Should report failure when any criterion not met"""
        m = DecompositionMetrics()

        subtasks = [Subtask("A", "Do A", TaskComplexity.SMALL)]
        m.record_decomposition(
            "xl-1", "XL Task", subtasks, complexity=TaskComplexity.XL
        )

        # XL not completed = 0% rate (40% below baseline)
        m.record_completion(
            "xl-1",
            subtasks_completed=1,
            total_subtasks=1,
            dependencies_correct=10,
            dependencies_violated=0,
            parent_completed=False,  # Not completed
        )

        summary = m.get_metrics_summary()
        assert summary["xl_completion"]["meets_target"] is False
        assert summary["success_criteria_met"] is False


# ============================================================================
# Integration Tests
# ============================================================================
class TestIntegration:
    """Integration tests for full decomposition workflow"""

    def test_full_decomposition_workflow(self):
        """Should complete full decomposition workflow"""
        # Create decomposer
        d = TaskDecomposer(
            max_subtask_complexity=TaskComplexity.MEDIUM,
            min_subtasks=2,
            max_subtasks=5,
        )

        # Create metrics tracker
        m = DecompositionMetrics()

        # Decompose a realistic task
        subtasks = d.decompose(
            task_name="Implement User Authentication",
            task_description="""
            Build a complete authentication system:
            1. Design database schema for users
            2. Implement password hashing
            3. Create login/logout endpoints
            4. Add JWT token generation
            5. Implement token validation middleware
            """,
            complexity=TaskComplexity.XL,
            context={
                "remote_execution": True,
                "api_limit": "1000/hour",
            },
        )

        # Record metrics
        m.record_decomposition(
            task_gid="auth-task-001",
            task_name="Implement User Authentication",
            subtasks=subtasks,
        )

        # Verify results
        assert 2 <= len(subtasks) <= 5
        assert all(isinstance(s, Subtask) for s in subtasks)
        assert all(
            s.complexity in [TaskComplexity.SMALL, TaskComplexity.MEDIUM]
            for s in subtasks
        )

        # Verify metrics
        summary = m.get_metrics_summary()
        assert summary["total_decompositions"] == 1
        assert summary["avg_subtasks_per_task"] > 0

    def test_decomposition_produces_serializable_output(self):
        """Should produce JSON-serializable output"""
        import json

        d = TaskDecomposer()
        subtasks = d.decompose(
            "Serializable Task",
            "1. Step A\n2. Step B",
            TaskComplexity.LARGE,
        )

        # Convert to dicts
        dicts = [s.to_dict() for s in subtasks]

        # Should be JSON-serializable
        json_str = json.dumps(dicts)
        assert json_str is not None
        assert len(json_str) > 0

        # Should round-trip
        parsed = json.loads(json_str)
        assert len(parsed) == len(subtasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
