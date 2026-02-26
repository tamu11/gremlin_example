#!/usr/bin/env python3
"""
Script to query the Gremlin graph database for subject matter experts.

This script finds people most strongly associated with a given knowledge topic
by traversing the graph: KnowledgeArea <-COVERS- Document <-AUTHORED- Person

V2 differences from V1: experts are ranked by an association score (number of
documents they authored that cover the requested topic(s)), rather than
alphabetically.
"""

import sys
from gremlin_python.driver import client as gremlin_driver
from gremlin_python.driver.protocol import GremlinServerError
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

# Configuration
GREMLIN_SERVER = "ws://localhost:8182/gremlin"

# Module-level client, set in main()
gremlin_client = None


def submit(query, bindings=None):
    """Submit a Gremlin query and return results."""
    return gremlin_client.submit(query, bindings=bindings).all().result()


def find_experts_by_knowledge(knowledge_topic, limit=10):
    """
    Find experts associated with a knowledge topic, ranked by document count.

    Args:
        knowledge_topic (str): The knowledge topic to search for
        limit (int): Maximum number of experts to return

    Returns:
        list: List of expert dicts with association_score
    """
    print(f"Finding experts for: '{knowledge_topic}'")

    # From KnowledgeArea, traverse in() along COVERS to Documents,
    # then in() along AUTHORED to Persons, and groupCount() by person vertex.
    # unfold() turns the map into key/value pairs so we can order and limit.
    try:
        result = submit(
            "g.V().has('KnowledgeArea', 'name', topic)"
            ".in('COVERS').in('AUTHORED')"
            ".groupCount().unfold()"
            ".order().by(values, decr).limit(lim)",
            bindings={"topic": knowledge_topic, "lim": limit}
        )

        experts = []
        for entry in result:
            # Each entry is a dict with one key (the Vertex) and count as value
            vertex = list(entry.keys())[0]
            score = list(entry.values())[0]
            person = get_person_details_by_vertex(vertex)
            if person:
                person["association_score"] = score
                person["knowledge_topic"] = knowledge_topic
                experts.append(person)

        return experts

    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []


def find_experts_by_knowledge_list(knowledge_topics, limit=10):
    """
    Find experts across multiple knowledge topics, ranked by total score.

    Args:
        knowledge_topics (list): List of knowledge topics to search for
        limit (int): Maximum number of experts to return

    Returns:
        list: List of expert dicts with total association_score
    """
    print(f"Finding experts for multiple topics: {', '.join(knowledge_topics)}")

    combined_scores = {}

    for topic in knowledge_topics:
        experts = find_experts_by_knowledge(topic, limit=limit)
        for expert in experts:
            pid = expert["person_id"]
            if pid in combined_scores:
                combined_scores[pid]["association_score"] += expert["association_score"]
                combined_scores[pid]["knowledge_topics"].append(topic)
            else:
                expert["knowledge_topics"] = [topic]
                combined_scores[pid] = expert

    sorted_experts = sorted(
        combined_scores.values(),
        key=lambda x: x["association_score"],
        reverse=True
    )
    return sorted_experts[:limit]


def get_person_details_by_vertex(vertex):
    """
    Fetch valueMap for a vertex object already in hand.

    Args:
        vertex: A Gremlin Vertex object

    Returns:
        dict: Person properties, or None
    """
    try:
        # Use the internal vertex id to look it up
        result = submit(
            "g.V(vid).valueMap()",
            bindings={"vid": vertex.id}
        )
        if result:
            props = result[0]
            return {
                "person_id": props.get('id', ['N/A'])[0],
                "name":       props.get('name', ['N/A'])[0],
                "email":      props.get('email', ['N/A'])[0],
                "department": props.get('department', ['N/A'])[0],
            }
        return None
    except GremlinServerError:
        return None


def display_experts(experts):
    """
    Display experts in a readable format.

    Args:
        experts (list): List of expert dictionaries
    """
    if not experts:
        print("No experts found.")
        return

    print("\n" + "="*80)
    print("SUBJECT MATTER EXPERTS")
    print("="*80)

    for i, expert in enumerate(experts, 1):
        print(f"\n#{i}")
        print(f"Name:              {expert.get('name', 'N/A')}")
        print(f"ID:                {expert.get('person_id', 'N/A')}")
        print(f"Email:             {expert.get('email', 'N/A')}")
        print(f"Department:        {expert.get('department', 'N/A')}")
        print(f"Association Score: {expert.get('association_score', 0)}")
        topics = expert.get('knowledge_topics', [expert.get('knowledge_topic', 'N/A')])
        print(f"Topics:            {', '.join(str(t) for t in topics)}")
        print("-"*80)


def main():
    """Main function to query for experts"""
    global gremlin_client

    print("Querying Gremlin graph database for subject matter experts...\n")

    try:
        print(f"Connecting to Gremlin Server at {GREMLIN_SERVER}...")
        gremlin_client = gremlin_driver.Client(
            GREMLIN_SERVER, 'g',
            message_serializer=GraphSONSerializersV3d0()
        )
        print("✓ Connected to Gremlin Server\n")

        print("Example 1: Finding experts for 'Machine Learning'")
        experts = find_experts_by_knowledge("Machine Learning", limit=5)
        display_experts(experts)

        print("\n\nExample 2: Finding experts for multiple AI/ML topics")
        experts = find_experts_by_knowledge_list(
            ["Machine Learning", "Deep Learning"], limit=5
        )
        display_experts(experts)

        print("\n\nExample 3: Finding experts for 'Cloud Computing'")
        experts = find_experts_by_knowledge("Cloud Computing", limit=5)
        display_experts(experts)

        print("\n✓ Query completed successfully!")
        return 0

    except GremlinServerError as e:
        print(f"Error connecting to Gremlin Server: {e}")
        print("Make sure the database is running: ./scripts/start_database.sh")
        print("And that data has been loaded: python scripts/load_sample_data.py")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    finally:
        if gremlin_client:
            gremlin_client.close()


if __name__ == "__main__":
    sys.exit(main())