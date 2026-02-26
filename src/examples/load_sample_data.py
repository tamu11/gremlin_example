#!/usr/bin/env python3
"""
load_sample_data.py

Loads sample people, documents, and knowledge areas into the Gremlin graph
database, then wires them together with AUTHORED and COVERS edges.

Database operations are delegated to the gremlin_example package.
"""

import sys
sys.path.insert(0, '../')

from gremlin import graph_db
from gremlin_python.driver.protocol import GremlinServerError


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

PEOPLE = [
    {"id": "p1", "name": "Alice Johnson", "email": "alice.johnson@company.com", "department": "Engineering"},
    {"id": "p2", "name": "Bob Smith",     "email": "bob.smith@company.com",     "department": "Engineering"},
    {"id": "p3", "name": "Carol Davis",   "email": "carol.davis@company.com",   "department": "Data Science"},
    {"id": "p4", "name": "David Lee",     "email": "david.lee@company.com",     "department": "Data Science"},
    {"id": "p5", "name": "Eve Wilson",    "email": "eve.wilson@company.com",    "department": "Product Management"},
    {"id": "p6", "name": "Frank Miller",  "email": "frank.miller@company.com",  "department": "DevOps"},
    {"id": "p7", "name": "Grace Brown",   "email": "grace.brown@company.com",   "department": "Data Science"},
]

DOCUMENTS = [
    {"id": "d1", "title": "Machine Learning in Production", "date": "2023-01-15", "type": "White Paper"},
    {"id": "d2", "title": "Deep Learning Architectures",    "date": "2023-02-20", "type": "Research Paper"},
    {"id": "d3", "title": "Data Pipeline Optimization",     "date": "2023-03-10", "type": "Technical Report"},
    {"id": "d4", "title": "Cloud Migration Guide",          "date": "2023-04-05", "type": "Guide"},
    {"id": "d5", "title": "Kubernetes Best Practices",      "date": "2023-05-12", "type": "Technical Report"},
    {"id": "d6", "title": "Data Governance Framework",      "date": "2023-06-18", "type": "White Paper"},
]

KNOWLEDGE_AREAS = [
    {"id": "ml",     "name": "Machine Learning"},
    {"id": "dl",     "name": "Deep Learning"},
    {"id": "de",     "name": "Data Engineering"},
    {"id": "cloud",  "name": "Cloud Computing"},
    {"id": "devops", "name": "DevOps"},
    {"id": "dg",     "name": "Data Governance"},
]

# (author_id, document_id) pairs
AUTHORED_EDGES = [
    ("p1", "d1"),
    ("p2", "d1"), ("p2", "d2"),
    ("p3", "d3"),
    ("p4", "d3"), ("p4", "d4"),
    ("p5", "d4"),
    ("p6", "d5"),
    ("p7", "d6"),
]

# (document_id, knowledge_area_id) pairs
COVERS_EDGES = [
    ("d1", "ml"),
    ("d2", "dl"),
    ("d3", "de"),
    ("d4", "cloud"),
    ("d5", "devops"), ("d5", "cloud"),
    ("d6", "dg"),     ("d6", "de"),
]


# ---------------------------------------------------------------------------
# Loading functions
# ---------------------------------------------------------------------------

def load_people():
    """Insert all Person vertices."""
    print("\nLoading people...")
    try:
        for person in PEOPLE:
            graph_db.add_vertex("Person", person)
        print(f"OK Loaded {len(PEOPLE)} people")
        return PEOPLE
    except GremlinServerError as e:
        print(f"ERROR loading people: {e}")
        return []


def load_documents():
    """Insert all Document vertices."""
    print("\nLoading documents...")
    try:
        for doc in DOCUMENTS:
            graph_db.add_vertex("Document", doc)
        print(f"OK Loaded {len(DOCUMENTS)} documents")
        return DOCUMENTS
    except GremlinServerError as e:
        print(f"ERROR loading documents: {e}")
        return []


def load_knowledge_areas():
    """Insert all KnowledgeArea vertices."""
    print("\nLoading knowledge areas...")
    try:
        for area in KNOWLEDGE_AREAS:
            graph_db.add_vertex("KnowledgeArea", area)
        print(f"OK Loaded {len(KNOWLEDGE_AREAS)} knowledge areas")
        return KNOWLEDGE_AREAS
    except GremlinServerError as e:
        print(f"ERROR loading knowledge areas: {e}")
        return []


def create_relationships():
    """Create AUTHORED and COVERS edges between vertices."""
    print("\nCreating relationships...")
    try:
        for author_id, doc_id in AUTHORED_EDGES:
            graph_db.add_edge(author_id, doc_id, "AUTHORED")
        for doc_id, area_id in COVERS_EDGES:
            graph_db.add_edge(doc_id, area_id, "COVERS")
        print("OK Relationships created successfully!")
    except GremlinServerError as e:
        print(f"ERROR creating relationships: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Loading sample data into Gremlin graph database...")
    print("=" * 70)

    try:
        print(f"Connecting to {graph_db.GREMLIN_SERVER}...")
        graph_db.connect()
        print("OK Connected successfully!")

        if not graph_db.clear_graph():
            print("Warning: Could not clear graph, continuing anyway...")

        load_people()
        load_documents()
        load_knowledge_areas()
        create_relationships()
        graph_db.verify_data()

        print("\nOK Sample data loaded successfully!")
        print("\nYou can now query the graph using: python query_experts.py")

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nPlease make sure:")
        print("1. The database is running: ./start_database.sh")
        print("2. The port 8182 is available")

    finally:
        graph_db.close()


if __name__ == "__main__":
    main()