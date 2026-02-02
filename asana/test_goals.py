#!/usr/bin/env python3
"""
Unit Tests for Asana Goals SDK

Tests the goals module without making real API calls.
Uses mocking to simulate Asana API responses.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from asana_sdk.errors import AsanaClientError


class TestGetGoals(unittest.TestCase):
    """Test get_goals function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_get_goals_basic(self, mock_get_client):
        """Test getting goals from workspace."""
        from asana_sdk.goals import get_goals

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.get_goals.return_value = [
            {"gid": "goal1", "name": "Q1 Revenue Target"},
            {"gid": "goal2", "name": "Improve NPS"},
        ]

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = get_goals(workspace_gid="ws123")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Q1 Revenue Target")
        mock_goals_api.get_goals.assert_called_once()

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_get_goals_with_filters(self, mock_get_client):
        """Test getting goals with team and time_period filters."""
        from asana_sdk.goals import get_goals

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.get_goals.return_value = []

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            get_goals(
                workspace_gid="ws123",
                team_gid="team456",
                time_period_gid="tp789"
            )

        # Verify the opts were passed correctly
        call_args = mock_goals_api.get_goals.call_args
        opts = call_args[0][0] if call_args[0] else call_args[1].get("opts", {})
        self.assertIn("workspace", str(call_args))

    def test_get_goals_validates_workspace(self):
        """Test get_goals requires workspace_gid."""
        from asana_sdk.goals import get_goals

        with self.assertRaises(ValueError) as ctx:
            get_goals(workspace_gid="")
        self.assertIn("workspace_gid", str(ctx.exception).lower())

        with self.assertRaises(ValueError):
            get_goals(workspace_gid=None)


class TestGetGoal(unittest.TestCase):
    """Test get_goal function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_get_goal_basic(self, mock_get_client):
        """Test getting a single goal."""
        from asana_sdk.goals import get_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goal_response = MagicMock()
        mock_goal_response.to_dict.return_value = {
            "gid": "goal123",
            "name": "Increase Revenue",
            "owner": {"gid": "user1", "name": "John"},
            "status": "on_track",
        }

        mock_goals_api = MagicMock()
        mock_goals_api.get_goal.return_value = mock_goal_response

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = get_goal("goal123")

        self.assertEqual(result["gid"], "goal123")
        self.assertEqual(result["status"], "on_track")

    def test_get_goal_validates_gid(self):
        """Test get_goal validates goal_gid."""
        from asana_sdk.goals import get_goal

        with self.assertRaises(ValueError):
            get_goal("")

        with self.assertRaises(ValueError):
            get_goal(None)


class TestCreateGoal(unittest.TestCase):
    """Test create_goal function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_create_goal_basic(self, mock_get_client):
        """Test creating a goal with minimal params."""
        from asana_sdk.goals import create_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.create_goal.return_value = {"gid": "new_goal_123"}

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = create_goal(
                name="Q2 Revenue Target",
                workspace_gid="ws123"
            )

        self.assertEqual(result, "new_goal_123")
        mock_goals_api.create_goal.assert_called_once()

        # Verify body structure
        call_body = mock_goals_api.create_goal.call_args[0][0]
        self.assertEqual(call_body["data"]["name"], "Q2 Revenue Target")
        self.assertEqual(call_body["data"]["workspace"], "ws123")

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_create_goal_with_all_params(self, mock_get_client):
        """Test creating a goal with all parameters."""
        from asana_sdk.goals import create_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.create_goal.return_value = {"gid": "new_goal_456"}

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = create_goal(
                name="Increase MRR",
                workspace_gid="ws123",
                owner_gid="user456",
                due_on="2026-03-31",
                start_on="2026-01-01",
                status="on_track",
                notes="Target $100k MRR by end of Q1",
                time_period_gid="tp789",
            )

        self.assertEqual(result, "new_goal_456")

        # Verify all params were included
        call_body = mock_goals_api.create_goal.call_args[0][0]
        data = call_body["data"]
        self.assertEqual(data["owner"], "user456")
        self.assertEqual(data["due_on"], "2026-03-31")
        self.assertEqual(data["start_on"], "2026-01-01")
        self.assertEqual(data["status"], "on_track")
        self.assertIn("$100k", data["notes"])

    def test_create_goal_validates_name(self):
        """Test create_goal validates name."""
        from asana_sdk.goals import create_goal

        with self.assertRaises(ValueError):
            create_goal(name="", workspace_gid="ws123")

        with self.assertRaises(ValueError):
            create_goal(name=None, workspace_gid="ws123")

    def test_create_goal_validates_workspace(self):
        """Test create_goal validates workspace_gid."""
        from asana_sdk.goals import create_goal

        with self.assertRaises(ValueError):
            create_goal(name="Goal", workspace_gid="")

    def test_create_goal_validates_status(self):
        """Test create_goal validates status enum."""
        from asana_sdk.goals import create_goal

        with self.assertRaises(ValueError) as ctx:
            create_goal(name="Goal", workspace_gid="ws123", status="invalid_status")
        self.assertIn("status", str(ctx.exception).lower())


class TestUpdateGoal(unittest.TestCase):
    """Test update_goal function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_update_goal_basic(self, mock_get_client):
        """Test updating a goal."""
        from asana_sdk.goals import update_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = update_goal(
                goal_gid="goal123",
                name="Updated Goal Name",
                status="at_risk"
            )

        self.assertTrue(result)
        mock_goals_api.update_goal.assert_called_once()

        # Verify body
        call_body = mock_goals_api.update_goal.call_args[0][0]
        self.assertEqual(call_body["data"]["name"], "Updated Goal Name")
        self.assertEqual(call_body["data"]["status"], "at_risk")

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_update_goal_no_updates(self, mock_get_client):
        """Test update_goal with no updates returns True."""
        from asana_sdk.goals import update_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = update_goal(goal_gid="goal123")

        self.assertTrue(result)

    def test_update_goal_validates_gid(self):
        """Test update_goal validates goal_gid."""
        from asana_sdk.goals import update_goal

        with self.assertRaises(ValueError):
            update_goal(goal_gid="")


class TestDeleteGoal(unittest.TestCase):
    """Test delete_goal function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_delete_goal(self, mock_get_client):
        """Test deleting a goal."""
        from asana_sdk.goals import delete_goal

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = delete_goal("goal123")

        self.assertTrue(result)
        mock_goals_api.delete_goal.assert_called_once_with("goal123")

    def test_delete_goal_validates_gid(self):
        """Test delete_goal validates goal_gid."""
        from asana_sdk.goals import delete_goal

        with self.assertRaises(ValueError):
            delete_goal("")


class TestUpdateGoalMetric(unittest.TestCase):
    """Test update_goal_metric function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_update_goal_metric(self, mock_get_client):
        """Test updating a goal metric value."""
        from asana_sdk.goals import update_goal_metric

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.update_goal_metric.return_value = {
            "gid": "metric1",
            "current_number_value": 75000
        }

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = update_goal_metric("goal123", current_number_value=75000)

        self.assertEqual(result["current_number_value"], 75000)
        mock_goals_api.update_goal_metric.assert_called_once()

        # Verify body structure
        call_body = mock_goals_api.update_goal_metric.call_args[0][0]
        self.assertEqual(call_body["data"]["current_number_value"], 75000)

    def test_update_goal_metric_validates_gid(self):
        """Test update_goal_metric validates goal_gid."""
        from asana_sdk.goals import update_goal_metric

        with self.assertRaises(ValueError):
            update_goal_metric("", current_number_value=100)


class TestCreateGoalMetric(unittest.TestCase):
    """Test create_goal_metric function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_create_goal_metric(self, mock_get_client):
        """Test setting up a metric for a goal."""
        from asana_sdk.goals import create_goal_metric

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.create_goal_metric.return_value = {
            "gid": "metric1",
            "resource_subtype": "number",
            "current_number_value": 0,
            "target_number_value": 100000,
        }

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = create_goal_metric(
                goal_gid="goal123",
                metric_type="number",
                target_number_value=100000,
                unit="USD"
            )

        self.assertEqual(result["target_number_value"], 100000)

        # Verify body
        call_body = mock_goals_api.create_goal_metric.call_args[0][0]
        self.assertEqual(call_body["data"]["resource_subtype"], "number")
        self.assertEqual(call_body["data"]["target_number_value"], 100000)

    def test_create_goal_metric_validates_type(self):
        """Test create_goal_metric validates metric_type."""
        from asana_sdk.goals import create_goal_metric

        with self.assertRaises(ValueError) as ctx:
            create_goal_metric(
                goal_gid="goal123",
                metric_type="invalid_type",
                target_number_value=100
            )
        self.assertIn("metric_type", str(ctx.exception).lower())


class TestGoalFollowers(unittest.TestCase):
    """Test goal follower operations."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_add_goal_followers(self, mock_get_client):
        """Test adding followers to a goal."""
        from asana_sdk.goals import add_goal_followers

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = add_goal_followers("goal123", ["user1", "user2"])

        self.assertTrue(result)
        mock_goals_api.add_followers.assert_called_once()

        # Verify body
        call_body = mock_goals_api.add_followers.call_args[0][0]
        self.assertEqual(call_body["data"]["followers"], ["user1", "user2"])

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_remove_goal_followers(self, mock_get_client):
        """Test removing followers from a goal."""
        from asana_sdk.goals import remove_goal_followers

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = remove_goal_followers("goal123", ["user1"])

        self.assertTrue(result)
        mock_goals_api.remove_followers.assert_called_once()

    def test_add_followers_validates_inputs(self):
        """Test add_goal_followers validates inputs."""
        from asana_sdk.goals import add_goal_followers

        with self.assertRaises(ValueError):
            add_goal_followers("", ["user1"])

        with self.assertRaises(ValueError):
            add_goal_followers("goal123", [])


class TestGetParentGoals(unittest.TestCase):
    """Test get_parent_goals function."""

    @patch("asana_sdk.goals.get_client")
    @patch("asana_sdk.goals.ASANA_SDK_AVAILABLE", True)
    def test_get_parent_goals(self, mock_get_client):
        """Test getting parent goals."""
        from asana_sdk.goals import get_parent_goals

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_goals_api = MagicMock()
        mock_goals_api.get_parent_goals_for_goal.return_value = [
            {"gid": "parent1", "name": "Company OKR"},
        ]

        with patch("asana_sdk.goals.asana") as mock_asana:
            mock_asana.GoalsApi.return_value = mock_goals_api

            result = get_parent_goals("goal123")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Company OKR")


if __name__ == "__main__":
    unittest.main(verbosity=2)
