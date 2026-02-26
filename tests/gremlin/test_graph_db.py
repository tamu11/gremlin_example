"""
Unit tests for graph_db.py module.

Tests cover:
- Connection management (connect, close)
- Query execution (submit, submit_with_retry)
- Graph operations (clear_graph, add_vertex, add_edge)
- Expert finding queries
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch, call
from gremlin_python.driver.protocol import GremlinServerError

# Import the module under test
import src.gremlin.graph_db as graph_db


class TestConnectionManagement:
    """Tests for connection management functions."""

    def test_connect_creates_client(self):
        """Test that connect() creates a gremlin client."""
        with patch('src.gremlin.graph_db.gremlin_driver.Client') as mock_client:
            client = graph_db.connect()
            mock_client.assert_called_once()
            args, kwargs = mock_client.call_args
            assert kwargs['message_serializer'] is not None
            assert graph_db._client is not None

    def test_connect_with_custom_url(self):
        """Test that connect() accepts custom URL."""
        custom_url = "ws://test:8182/gremlin"
        with patch('src.gremlin.graph_db.gremlin_driver.Client') as mock_client:
            graph_db.connect(url=custom_url)
            # Check that Client was called with the right URL
            args, kwargs = mock_client.call_args
            assert args[0] == custom_url
            assert args[1] == 'g'
            assert kwargs['message_serializer'] is not None

    def test_close_with_active_connection(self):
        """Test that close() closes the active client."""
        mock_client = MagicMock()
        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock_client):
            graph_db.connect()
            assert graph_db._client is not None

            graph_db.close()
            mock_client.close.assert_called_once()
            assert graph_db._client is None

    def test_close_without_active_connection(self):
        """Test that close() does nothing when no connection exists."""
        graph_db.close()  # Should not raise an error


class TestQueryExecution:
    """Tests for query execution functions."""

    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mock gremlin client."""
        mock = MagicMock()
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["result1", "result2"]
        mock.submit.return_value = mock_result
        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock):
            graph_db.connect()
            yield mock
        graph_db.close()

    def test_submit_returns_results(self, mock_client):
        """Test that submit() returns query results."""
        # Need to mock the entire submit chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["result1", "result2"]
        mock_client.submit.return_value = mock_result

        result = graph_db.submit("g.V().limit(10)")
        assert result == ["result1", "result2"]
        mock_client.submit.assert_called_with("g.V().limit(10)", bindings=None)

    def test_submit_with_bindings(self, mock_client):
        """Test that submit() uses bindings correctly."""
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["result1", "result2"]
        mock_client.submit.return_value = mock_result

        bindings = {"name": "test"}
        result = graph_db.submit("g.V().has('name', name)", bindings)
        mock_client.submit.assert_called_with(
            "g.V().has('name', name)",
            bindings=bindings
        )

    def test_submit_without_connection_raises_error(self):
        """Test that submit() raises RuntimeError when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            graph_db.submit("g.V()")

    def test_submit_with_retry_success_on_first_attempt(self, mock_client):
        """Test that submit_with_retry() succeeds on first attempt."""
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["result1", "result2"]
        mock_client.submit.return_value = mock_result

        result = graph_db.submit_with_retry("g.V().limit(10)")
        assert result == ["result1", "result2"]
        mock_client.submit.assert_called_once()

    def test_submit_with_retry_on_deadlock(self, mock_client):
        """Test that submit_with_retry() retries on DeadlockException."""
        # Mock the result chain for successful call
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["result1", "result2"]

        # First two attempts raise DeadlockException, third succeeds
        error = GremlinServerError({'code': 500, 'message': 'DeadlockException: Database lock contention', 'attributes': {}})
        mock_client.submit.side_effect = [error, error, mock_result]

        with patch('src.gremlin.graph_db.time.sleep'):
            with patch('src.gremlin.graph_db.random.uniform', return_value=0.05):
                result = graph_db.submit_with_retry("g.V().limit(10)")
                assert result == ["result1", "result2"]
                assert mock_client.submit.call_count == 3

    def test_submit_with_retry_max_retries_exceeded(self, mock_client):
        """Test that submit_with_retry() raises after MAX_RETRIES."""
        # Create mock result for error
        error = GremlinServerError({'code': 500, 'message': 'DeadlockException: Database lock contention', 'attributes': {}})
        mock_client.submit.side_effect = [error] * 10

        with patch('src.gremlin.graph_db.time.sleep'):
            with patch('src.gremlin.graph_db.random.uniform', return_value=0.05):
                with pytest.raises(GremlinServerError):
                    graph_db.submit_with_retry("g.V().limit(10)")

    def test_submit_with_retry_non_deadlock_error(self, mock_client):
        """Test that submit_with_retry() raises non-deadlock errors immediately."""
        # Create mock result for error
        error = GremlinServerError({'code': 404, 'message': 'Connection refused', 'attributes': {}})
        mock_client.submit.side_effect = error

        with pytest.raises(GremlinServerError):
            graph_db.submit_with_retry("g.V().limit(10)")
        mock_client.submit.assert_called_once()


class TestGraphOperations:
    """Tests for low-level graph operations."""

    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mock gremlin client."""
        mock = MagicMock()
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = []
        mock.submit.return_value = mock_result
        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock):
            graph_db.connect()
            yield mock
        graph_db.close()

    def test_clear_graph_success(self, mock_client):
        """Test that clear_graph() executes the drop query."""
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = ["success"]
        mock_client.submit.return_value = mock_result

        result = graph_db.clear_graph()
        assert result is True
        mock_client.submit.assert_called_once()

    def test_clear_graph_failure(self, mock_client):
        """Test that clear_graph() returns False on GremlinServerError."""
        # Mock the result chain
        mock_result = MagicMock()
        error = GremlinServerError({'code': 500, 'message': 'Connection error', 'attributes': {}})
        mock_client.submit.side_effect = error
        result = graph_db.clear_graph()
        assert result is False

    def test_add_vertex(self, mock_client):
        """Test that add_vertex() builds correct query with bindings."""
        properties = {"id": "123", "name": "John Doe", "email": "john@example.com"}
        graph_db.add_vertex("Person", properties)

        # Verify the query was called with proper parameters
        args, kwargs = mock_client.submit.call_args
        query = args[0]
        bindings = kwargs['bindings']

        assert "vlabel" in bindings
        assert "pval0" in bindings
        assert "pval1" in bindings
        assert "pval2" in bindings
        assert bindings["pval0"] == "123"
        assert bindings["pval1"] == "John Doe"
        assert bindings["pval2"] == "john@example.com"

    def test_add_edge(self, mock_client):
        """Test that add_edge() builds correct query."""
        graph_db.add_edge("person1", "doc1", "AUTHORED")

        args, kwargs = mock_client.submit.call_args
        query = args[0]
        bindings = kwargs['bindings']

        assert "from_id" in bindings
        assert "to_id" in bindings
        assert "rel" in bindings
        assert bindings["from_id"] == "person1"
        assert bindings["to_id"] == "doc1"
        assert bindings["rel"] == "AUTHORED"


class TestExpertQueries:
    """Tests for expert-finding query functions."""

    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mock gremlin client for expert queries."""
        mock = MagicMock()
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = [
            {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]},
            {"id": ["person2"], "name": ["Jane Smith"], "email": ["jane@example.com"], "department": ["Science"]}
        ]
        mock.submit.return_value = mock_result

        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock):
            graph_db.connect()
            yield mock
        graph_db.close()

    def test_find_experts_by_topic(self, mock_client):
        """Test that find_experts_by_topic() returns formatted expert records."""
        experts = graph_db.find_experts_by_topic("Machine Learning", limit=10)

        assert len(experts) == 2
        assert experts[0]["person_id"] == "person1"
        assert experts[0]["name"] == "John Doe"
        assert experts[0]["topic"] == "Machine Learning"
        assert experts[1]["person_id"] == "person2"
        assert experts[1]["name"] == "Jane Smith"

    def test_find_experts_by_topic_with_error(self, mock_client):
        """Test that find_experts_by_topic() returns empty list on error."""
        error = GremlinServerError({'code': 500, 'message': 'Connection error', 'attributes': {}})
        mock_client.submit.side_effect = error
        experts = graph_db.find_experts_by_topic("Machine Learning")
        assert experts == []

    def test_find_experts_by_topics(self, mock_client):
        """Test that find_experts_by_topics() combines results across multiple topics."""
        # Mock to return same results for both topics
        mock_client.submit.return_value.all.return_value.result.return_value = [
            {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
        ]

        experts = graph_db.find_experts_by_topics(["ML", "AI"], limit=10)

        assert len(experts) == 1
        assert "ML" in experts[0]["topics"]
        assert "AI" in experts[0]["topics"]
        assert experts[0]["name"] == "John Doe"

    def test_find_experts_by_knowledge(self, mock_client):
        """Test that find_experts_by_knowledge() returns scored experts."""
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = [
            {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
        ]
        mock_client.submit.return_value = mock_result

        # Mock the groupCount call to return a score
        def submit_side_effect(query, bindings=None):
            result_mock = MagicMock()
            if "groupCount" in query:
                # Mock groupCount result - person1 has score 3
                mock_vertex = MagicMock()
                mock_vertex.id = "vertex1"
                result_mock.all().result.return_value = [
                    {mock_vertex: 3}
                ]
            else:
                # Mock valueMap result
                result_mock.all().result.return_value = [
                    {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
                ]
            return result_mock

        mock_client.submit.side_effect = submit_side_effect

        experts = graph_db.find_experts_by_knowledge("Machine Learning", limit=10)

        assert len(experts) == 1
        assert experts[0]["association_score"] == 3
        assert experts[0]["name"] == "John Doe"

    def test_find_experts_by_knowledge_list(self, mock_client):
        """Test that find_experts_by_knowledge_list() accumulates scores."""
        # Mock the result chain
        mock_result = MagicMock()
        mock_result.all().result.return_value = [
            {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
        ]
        mock_client.submit.return_value = mock_result

        # Mock the groupCount call - first call returns 2, second call also returns 2
        call_count = [0]
        def submit_side_effect(query, bindings=None):
            result_mock = MagicMock()
            call_count[0] += 1
            if "groupCount" in query:
                # Mock groupCount result - person1 has score 2
                mock_vertex = MagicMock()
                mock_vertex.id = "vertex1"
                result_mock.all().result.return_value = [
                    {mock_vertex: 2}
                ]
            else:
                # Mock valueMap result
                result_mock.all().result.return_value = [
                    {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
                ]
            return result_mock

        mock_client.submit.side_effect = submit_side_effect

        experts = graph_db.find_experts_by_knowledge_list(["ML", "AI"], limit=10)

        assert len(experts) == 1
        # The score should be 4 because we query both ML and AI, each with score 2
        # But the function accumulates scores across topics, so it should be 2 + 2 = 4
        assert experts[0]["association_score"] == 4
        assert "ML" in experts[0]["knowledge_topics"]
        assert "AI" in experts[0]["knowledge_topics"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_verify_data(self, capfd):
        """Test that verify_data() prints summary."""
        mock_client = MagicMock()
        mock_client.submit.return_value.all.return_value.result.return_value = [5]

        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock_client):
            graph_db.connect()
            graph_db.verify_data()
            captured = capfd.readouterr()
            assert "People:" in captured.out
            assert "Documents:" in captured.out
            assert "Knowledge Areas:" in captured.out
            assert "Relationships:" in captured.out
        graph_db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
