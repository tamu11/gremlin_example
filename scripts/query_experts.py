#!/usr/bin/env python3
"""
Script to query the Gremlin graph database for subject matter experts.

This script finds people most strongly associated with a given knowledge topic
by traversing the graph: KnowledgeArea <-COVERS- Document <-AUTHORED- Person
"""

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


def find_experts_by_topic(topic_name, limit=10):
    """
    Find experts associated with a knowledge topic.

    Args:
        topic_name (str): The knowledge topic to search for
        limit (int): Maximum number of experts to return

    Returns:
        list: List of expert dictionaries
    """
    print(f"Finding experts for: '{topic_name}'")

    # Edges: Person -AUTHORED-> Document -COVERS-> KnowledgeArea
    # So from KnowledgeArea we traverse in() on both edges to reach Person
    try:
        result = submit(
            "g.V().has('KnowledgeArea', 'name', topic_name)"
            ".in('COVERS').in('AUTHORED').dedup()"
            ".order().by('name').limit(lim).valueMap()",
            bindings={"topic_name": topic_name, "lim": limit}
        )

        experts = []
        for props in result:
            experts.append({
                "person_id": props.get('id', ['N/A'])[0],
                "name":       props.get('name', ['N/A'])[0],
                "email":      props.get('email', ['N/A'])[0],
                "department": props.get('department', ['N/A'])[0],
                "topic": topic_name,
            })
        return experts

    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []


def find_experts_by_topics(topic_list, limit=10):
    """
    Find experts associated with multiple knowledge topics.

    Args:
        topic_list (list): List of knowledge topics to search for
        limit (int): Maximum number of experts to return

    Returns:
        list: List of expert dictionaries with their total topic coverage
    """
    print(f"Finding experts for topics: {', '.join(topic_list)}")

    all_experts = {}
    for topic in topic_list:
        experts = find_experts_by_topic(topic, limit)
        for expert in experts:
            pid = expert["person_id"]
            if pid in all_experts:
                all_experts[pid]["topics"].append(topic)
            else:
                expert["topics"] = [topic]
                all_experts[pid] = expert

    sorted_experts = sorted(
        all_experts.values(), key=lambda x: len(x["topics"]), reverse=True
    )
    return sorted_experts[:limit]


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
        print(f"Name:       {expert.get('name', 'N/A')}")
        print(f"ID:         {expert['person_id']}")
        print(f"Email:      {expert.get('email', 'N/A')}")
        print(f"Department: {expert.get('department', 'N/A')}")
        topics = expert.get('topics', [expert.get('topic', 'N/A')])
        print(f"Topics:     {', '.join(topics)}")
        print("-"*80)


def main():
    """Main function to query for experts"""
    global gremlin_client

    print("Querying Gremlin graph database for subject matter experts...\n")

    try:
        print(f"Connecting to {GREMLIN_SERVER}...")
        gremlin_client = gremlin_driver.Client(
            GREMLIN_SERVER, 'g',
            message_serializer=GraphSONSerializersV3d0()
        )
        print("✅ Connected successfully!")

        # Example 1: Single topic
        print("\n" + "="*80)
        print("EXAMPLE 1: Single Topic Query")
        print("="*80)
        experts = find_experts_by_topic('Machine Learning', 5)
        display_experts(experts)

        # Example 2: Multiple topics
        print("\n" + "="*80)
        print("EXAMPLE 2: Multi-Topic Query")
        print("="*80)
        multi_experts = find_experts_by_topics(['Machine Learning', 'Deep Learning'], 5)
        display_experts(multi_experts)

        # Example 3: Data-related topics
        print("\n" + "="*80)
        print("EXAMPLE 3: Data Topics Query")
        print("="*80)
        data_experts = find_experts_by_topics(['Data Engineering', 'Cloud Computing'], 5)
        display_experts(data_experts)

        print("\n✅ Query examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease make sure:")
        print("1. The database is running: ./scripts/start_database.sh")
        print("2. Sample data is loaded: python scripts/load_sample_data.py")
        print("3. The port 8182 is available")

    finally:
        if gremlin_client:
            gremlin_client.close()


if __name__ == "__main__":
    main()