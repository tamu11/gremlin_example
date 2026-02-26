"""
Data loader module for loading test data into the graph database.
"""

import src.gremlin.graph_db as graph_db


def load_test_data():
    """
    Load test data into the graph database.

    Creates:
    - People vertices
    - Documents vertices
    - Knowledge Areas vertices
    - Relationships between them
    """
    print("Loading test data...")

    # Clear existing data
    graph_db.clear_graph()

    # Add test people
    people = [
        {
            "id": "person1",
            "name": "John Doe",
            "email": "john@example.com",
            "department": "Engineering"
        },
        {
            "id": "person2",
            "name": "Jane Smith",
            "email": "jane@example.com",
            "department": "Science"
        },
        {
            "id": "person3",
            "name": "Bob Johnson",
            "email": "bob@example.com",
            "department": "Engineering"
        }
    ]

    for person in people:
        graph_db.add_vertex("Person", person)

    # Add test documents
    documents = [
        {"id": "doc1", "title": "Machine Learning Basics", "year": 2020},
        {"id": "doc2", "title": "Deep Learning Tutorial", "year": 2021},
        {"id": "doc3", "title": "Graph Databases", "year": 2022},
        {"id": "doc4", "title": "Artificial Intelligence Overview", "year": 2019}
    ]

    for doc in documents:
        graph_db.add_vertex("Document", doc)

    # Add knowledge areas
    knowledge_areas = [
        {"id": "ka1", "topic": "Machine Learning"},
        {"id": "ka2", "topic": "Deep Learning"},
        {"id": "ka3", "topic": "Graph Databases"},
        {"id": "ka4", "topic": "Artificial Intelligence"}
    ]

    for ka in knowledge_areas:
        graph_db.add_vertex("KnowledgeArea", ka)

    # Add relationships
    relationships = [
        ("person1", "doc1", "AUTHORED"),
        ("person1", "doc2", "AUTHORED"),
        ("person2", "doc3", "AUTHORED"),
        ("person2", "doc4", "AUTHORED"),
        ("person3", "doc1", "REVIEWED"),
        ("person3", "doc3", "REVIEWED"),
        ("doc1", "ka1", "ABOUT"),
        ("doc2", "ka2", "ABOUT"),
        ("doc3", "ka3", "ABOUT"),
        ("doc4", "ka4", "ABOUT")
    ]

    for from_id, to_id, rel in relationships:
        graph_db.add_edge(from_id, to_id, rel)

    print("Test data loaded successfully!")


def load_sample_data():
    """
    Load sample data with specific test cases.
    """
    print("Loading sample data...")
    # Implementation similar to load_test_data but with specific test scenarios
    graph_db.clear_graph()

    # Add people
    people = [
        {
            "id": "expert1",
            "name": "Alice Researcher",
            "email": "alice@example.com",
            "department": "Computer Science"
        }
    ]

    for person in people:
        graph_db.add_vertex("Person", person)

    # Add documents
    documents = [
        {"id": "paper1", "title": "Expert System Research", "year": 2023}
    ]

    for doc in documents:
        graph_db.add_vertex("Document", doc)

    # Add knowledge areas
    knowledge_areas = [
        {"id": "expertise1", "topic": "Expert Systems"}
    ]

    for ka in knowledge_areas:
        graph_db.add_vertex("KnowledgeArea", ka)

    # Add relationships
    relationships = [
        ("expert1", "paper1", "AUTHORED"),
        ("paper1", "expertise1", "ABOUT")
    ]

    for from_id, to_id, rel in relationships:
        graph_db.add_edge(from_id, to_id, rel)

    print("Sample data loaded successfully!")
