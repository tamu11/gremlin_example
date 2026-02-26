#!/usr/bin/env python3
"""
Script to load sample data into the Gremlin graph database.

This script creates a graph with people, documents, and knowledge areas,
and establishes relationships between them.
"""

import time
import random
from gremlin_python.driver import client
from gremlin_python.driver.protocol import GremlinServerError
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

# Configuration
GREMLIN_SERVER = "ws://localhost:8182/gremlin"

MAX_RETRIES = 5


def submit_with_retry(traversal, params=None):
    """Submit a Gremlin query with retry logic for deadlocks."""
    for attempt in range(MAX_RETRIES):
        try:
            if params:
                return client.submit(traversal, bindings=params).all().result()
            return client.submit(traversal).all().result()
        except GremlinServerError as e:
            err_str = str(e)
            if "DeadlockException" in err_str and attempt < MAX_RETRIES - 1:
                wait = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                print(f"  Deadlock detected, retrying in {wait:.2f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise


def clear_graph():
    """
    Clear all data from the graph.
    """
    print("Clearing existing graph data...")
    try:
        result = submit_with_retry("g.V().drop().iterate()")
        print("OK Graph cleared successfully!")
        return True
    except GremlinServerError as e:
        print(f"ERROR clearing graph: {e}")
        return False


def load_people():
    """
    Load people (employees) into the graph.

    Returns:
        list: List of person IDs
    """
    print("\nLoading people...")

    people = [
        {"id": "p1", "name": "Alice Johnson", "email": "alice.johnson@company.com", "department": "Engineering"},
        {"id": "p2", "name": "Bob Smith", "email": "bob.smith@company.com", "department": "Engineering"},
        {"id": "p3", "name": "Carol Davis", "email": "carol.davis@company.com", "department": "Data Science"},
        {"id": "p4", "name": "David Lee", "email": "david.lee@company.com", "department": "Data Science"},
        {"id": "p5", "name": "Eve Wilson", "email": "eve.wilson@company.com", "department": "Product Management"},
        {"id": "p6", "name": "Frank Miller", "email": "frank.miller@company.com", "department": "DevOps"},
        {"id": "p7", "name": "Grace Brown", "email": "grace.brown@company.com", "department": "Data Science"},
    ]

    try:
        for person in people:
            submit_with_retry(
                "g.addV('Person')"
                ".property('id', pid)"
                ".property('name', pname)"
                ".property('email', pemail)"
                ".property('department', pdept)",
                {
                    "pid": person["id"],
                    "pname": person["name"],
                    "pemail": person["email"],
                    "pdept": person["department"],
                }
            )

        print(f"OK Loaded {len(people)} people")
        return people

    except GremlinServerError as e:
        print(f"ERROR loading people: {e}")
        return []


def load_documents():
    """
    Load documents (research papers, white papers, etc.) into the graph.

    Returns:
        list: List of document IDs
    """
    print("\nLoading documents...")

    documents = [
        {"id": "d1", "title": "Machine Learning in Production", "date": "2023-01-15", "type": "White Paper"},
        {"id": "d2", "title": "Deep Learning Architectures", "date": "2023-02-20", "type": "Research Paper"},
        {"id": "d3", "title": "Data Pipeline Optimization", "date": "2023-03-10", "type": "Technical Report"},
        {"id": "d4", "title": "Cloud Migration Guide", "date": "2023-04-05", "type": "Guide"},
        {"id": "d5", "title": "Kubernetes Best Practices", "date": "2023-05-12", "type": "Technical Report"},
        {"id": "d6", "title": "Data Governance Framework", "date": "2023-06-18", "type": "White Paper"},
    ]

    try:
        for doc in documents:
            submit_with_retry(
                "g.addV('Document')"
                ".property('id', did)"
                ".property('title', dtitle)"
                ".property('date', ddate)"
                ".property('type', dtype)",
                {
                    "did": doc["id"],
                    "dtitle": doc["title"],
                    "ddate": doc["date"],
                    "dtype": doc["type"],
                }
            )

        print(f"OK Loaded {len(documents)} documents")
        return documents

    except GremlinServerError as e:
        print(f"ERROR loading documents: {e}")
        return []


def load_knowledge_areas():
    """
    Load knowledge areas (topics) into the graph.

    Returns:
        dict: Dictionary mapping short codes to knowledge area names
    """
    print("\nLoading knowledge areas...")

    knowledge_areas = [
        {"id": "ml", "name": "Machine Learning"},
        {"id": "dl", "name": "Deep Learning"},
        {"id": "de", "name": "Data Engineering"},
        {"id": "cloud", "name": "Cloud Computing"},
        {"id": "devops", "name": "DevOps"},
        {"id": "dg", "name": "Data Governance"}
    ]

    try:
        for area in knowledge_areas:
            submit_with_retry(
                "g.addV('KnowledgeArea')"
                ".property('id', aid)"
                ".property('name', aname)",
                {
                    "aid": area["id"],
                    "aname": area["name"],
                }
            )

        print(f"OK Loaded {len(knowledge_areas)} knowledge areas")
        return knowledge_areas

    except GremlinServerError as e:
        print(f"ERROR loading knowledge areas: {e}")
        return []


def create_relationships():
    """
    Create relationships between nodes.
    """
    print("\nCreating relationships...")

    # Alice authored ML paper (covers ML)
    add_edge("p1", "d1", "AUTHORED")
    add_edge("d1", "ml", "COVERS")

    # Bob authored ML paper and DL architectures (covers ML and DL)
    add_edge("p2", "d1", "AUTHORED")
    add_edge("p2", "d2", "AUTHORED")
    add_edge("d2", "dl", "COVERS")

    # Carol authored data pipeline (covers Data Engineering)
    add_edge("p3", "d3", "AUTHORED")
    add_edge("d3", "de", "COVERS")

    # David authored data pipeline and cloud migration (covers Data Engineering and Cloud)
    add_edge("p4", "d3", "AUTHORED")
    add_edge("p4", "d4", "AUTHORED")
    add_edge("d4", "cloud", "COVERS")

    # Eve authored cloud migration (covers Cloud)
    add_edge("p5", "d4", "AUTHORED")

    # Frank authored Kubernetes guide (covers DevOps and Cloud)
    add_edge("p6", "d5", "AUTHORED")
    add_edge("d5", "devops", "COVERS")
    add_edge("d5", "cloud", "COVERS")

    # Grace authored data governance (covers Data Governance and Data Engineering)
    add_edge("p7", "d6", "AUTHORED")
    add_edge("d6", "dg", "COVERS")
    add_edge("d6", "de", "COVERS")

    print("OK Relationships created successfully!")


def add_edge(from_id, to_id, relation_type):
    """
    Add an edge (relationship) between two nodes.

    Args:
        from_id (str): ID of the source node
        to_id (str): ID of the target node
        relation_type (str): Type of relationship
    """
    try:
        submit_with_retry(
            "g.V().has('id', from_id).as('a').V().has('id', to_id).addE(rel).from('a')",
            {"from_id": from_id, "to_id": to_id, "rel": relation_type}
        )
    except GremlinServerError as e:
        print(f"ERROR adding edge {from_id} -> {to_id}: {e}")


def verify_data():
    """
    Verify that data was loaded correctly.
    """
    print("\nVerifying data...")

    # Count nodes by type
    try:
        person_count  = submit_with_retry("g.V().hasLabel('Person').count()")[0]
        doc_count     = submit_with_retry("g.V().hasLabel('Document').count()")[0]
        area_count    = submit_with_retry("g.V().hasLabel('KnowledgeArea').count()")[0]
        edge_count    = submit_with_retry("g.E().count()")[0]

        print(f"  People: {person_count}")
        print(f"  Documents: {doc_count}")
        print(f"  Knowledge Areas: {area_count}")
        print(f"  Relationships: {edge_count}")

        print("OK Data verification complete!")

    except GremlinServerError as e:
        print(f"ERROR verifying data: {e}")


def main():
    """Main function to load sample data"""
    global client

    print("Loading sample data into Gremlin graph database...")
    print("="*70)

    try:
        # Connect to Gremlin Server
        print(f"Connecting to {GREMLIN_SERVER}...")
        client = client.Client(GREMLIN_SERVER, 'g', message_serializer=GraphSONSerializersV3d0())
        print("OK Connected successfully!")

        # Clear existing data
        if not clear_graph():
            print("Warning: Could not clear graph, continuing anyway...")

        # Load data
        people = load_people()
        documents = load_documents()
        knowledge_areas = load_knowledge_areas()

        # Create relationships
        create_relationships()

        # Verify data
        verify_data()

        print("\nOK Sample data loaded successfully!")
        print("\nYou can now query the graph using: python scripts/query_experts.py")

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nPlease make sure:")
        print("1. The database is running: ./scripts/start_database.sh")
        print("2. The port 8182 is available")

    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()