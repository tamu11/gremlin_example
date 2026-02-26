"""
Integration test for the expert finding workflow.

This test verifies the complete workflow:
1. Connect to the graph database
2. Load test data
3. Query for experts
4. Verify results
5. Clean up
"""

import pytest
from unittest.mock import MagicMock, patch
import src.gremlin.graph_db as graph_db
import src.gremlin.data_loader as data_loader
import src.gremlin.expert_finder as expert_finder


class TestIntegration:
    """Integration tests for the complete expert finding workflow."""

    def test_complete_workflow(self, capsys):
        """Test the complete workflow from data loading to expert finding."""

        # Mock the database connection
        mock_client = MagicMock()

        # Mock results for different queries
        def mock_submit(query, bindings=None):
            result_mock = MagicMock()

            # Mock different query responses
            if "V().count()" in query:
                result_mock.all().result.return_value = [0]
            elif "hasLabel('Person')" in query:
                result_mock.all().result.return_value = [3]  # 3 people
            elif "hasLabel('KnowledgeArea')" in query:
                result_mock.all().result.return_value = [4]  # 4 knowledge areas
            elif "hasLabel('Document')" in query:
                result_mock.all().result.return_value = [4]  # 4 documents
            elif "E().count()" in query:
                result_mock.all().result.return_value = [10]  # 10 relationships
            elif "has('KnowledgeArea', 'name', topic_name)" in query:
                # Mock expert query results - check bindings for topic
                topic = bindings["topic_name"] if bindings and "topic_name" in bindings else "Machine Learning"
                # Return different results based on topic
                if topic == "Machine Learning":
                    result_mock.all().result.return_value = [
                        {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]},
                        {"id": ["person2"], "name": ["Jane Smith"], "email": ["jane@example.com"], "department": ["Science"]}
                    ]
                else:
                    result_mock.all().result.return_value = []
            else:
                result_mock.all().result.return_value = []

            return result_mock

        mock_client.submit.side_effect = mock_submit

        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock_client):
            with patch('src.gremlin.data_loader.print'):
                with patch('src.gremlin.expert_finder.print'):
                    # Connect to database
                    graph_db.connect()

                    # Verify initial state
                    graph_db.verify_data()

                    # Load test data
                    data_loader.load_test_data()

                    # Find experts
                    experts = expert_finder.find_experts("Machine Learning")

                    # Verify results
                    assert len(experts) == 2
                    assert experts[0]["person_id"] == "person1"
                    assert experts[1]["person_id"] == "person2"

                    # Close connection
                    graph_db.close()

    def test_workflow_with_multiple_topics(self):
        """Test the workflow with multiple knowledge areas."""

        mock_client = MagicMock()

        # Mock results
        def mock_submit(query, bindings=None):
            result_mock = MagicMock()

            if "V().count()" in query:
                result_mock.all().result.return_value = [0]
            elif "hasLabel('Person')" in query:
                result_mock.all().result.return_value = [3]  # 3 people
            elif "hasLabel('KnowledgeArea')" in query:
                result_mock.all().result.return_value = [4]  # 4 knowledge areas
            elif "hasLabel('Document')" in query:
                result_mock.all().result.return_value = [4]  # 4 documents
            elif "E().count()" in query:
                result_mock.all().result.return_value = [10]  # 10 relationships
            elif "has('KnowledgeArea', 'name', topic_name)" in query:
                # Mock based on topic
                topic = bindings["topic_name"] if bindings and "topic_name" in bindings else "ML"
                if topic in ["ML", "AI"]:
                    result_mock.all().result.return_value = [
                        {"id": ["person1"], "name": ["John Doe"], "email": ["john@example.com"], "department": ["Engineering"]}
                    ]
                else:
                    result_mock.all().result.return_value = []
            else:
                result_mock.all().result.return_value = []

            return result_mock

        mock_client.submit.side_effect = mock_submit

        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock_client):
            with patch('src.gremlin.data_loader.print'):
                with patch('src.gremlin.expert_finder.print'):
                    # Connect
                    graph_db.connect()

                    # Load test data
                    data_loader.load_test_data()

                    # Find experts for multiple topics
                    experts = expert_finder.find_experts(["ML", "AI", "Deep Learning"])

                    # Should have results for ML and AI
                    assert len(experts) >= 1

                    # Close
                    graph_db.close()

    def test_error_handling_in_workflow(self, capsys):
        """Test that errors are handled gracefully in the workflow."""

        mock_client = MagicMock()

        # Mock submit to raise an error
        from gremlin_python.driver.protocol import GremlinServerError
        mock_client.submit.side_effect = GremlinServerError(
            {'code': 500, 'message': 'Connection error', 'attributes': {}}
        )

        with patch('src.gremlin.graph_db.gremlin_driver.Client', return_value=mock_client):
            with patch('src.gremlin.data_loader.print'):
                with patch('src.gremlin.expert_finder.print'):
                    # Connect
                    graph_db.connect()

                    # Verify that queries return empty results on error
                    experts = expert_finder.find_experts("Machine Learning")
                    assert experts == []

                    # Close
                    graph_db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
