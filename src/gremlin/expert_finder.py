"""
Expert finder module that uses the graph database to find experts.
"""

import src.gremlin.graph_db as graph_db


def find_experts(knowledge_area, limit=10):
    """
    Find experts based on knowledge area.

    Args:
        knowledge_area: Single topic string or list of topics
        limit: Maximum number of experts to return

    Returns:
        List of expert dictionaries with person_id, name, email, department, topic
    """
    if isinstance(knowledge_area, str):
        knowledge_area = [knowledge_area]

    print(f"Finding experts for: {', '.join(knowledge_area)}")

    all_experts = []

    for topic in knowledge_area:
        print(f"Finding experts for: '{topic}'")
        experts = graph_db.find_experts_by_topic(topic, limit)
        all_experts.extend(experts)

    if not all_experts:
        print("No experts found.")
        return []

    # Remove duplicates
    unique_experts = {}
    for expert in all_experts:
        person_id = expert["person_id"]
        if person_id not in unique_experts:
            unique_experts[person_id] = expert

    experts_list = list(unique_experts.values())

    print(f"Found {len(experts_list)} unique expert(s)")

    return experts_list


def find_experts_by_knowledge(knowledge_area, limit=10):
    """
    Find experts based on their knowledge associations (documents they authored).

    Args:
        knowledge_area: Single topic string or list of topics
        limit: Maximum number of experts to return

    Returns:
        List of expert dictionaries with person_id, name, email, department,
        association_score, and knowledge_topics
    """
    if isinstance(knowledge_area, str):
        knowledge_area = [knowledge_area]

    print(f"Finding experts by knowledge for: {', '.join(knowledge_area)}")

    experts = graph_db.find_experts_by_knowledge_list(knowledge_area, limit)

    if not experts:
        print("No experts found by knowledge analysis.")
        return []

    print(f"Found {len(experts)} expert(s) by knowledge analysis")

    return experts


def find_all_experts():
    """
    Find all experts across all knowledge areas.

    Returns:
        List of all experts with their knowledge areas
    """
    print("Finding all experts...")

    # This would be implemented by querying all knowledge areas
    # For now, return empty list
    return []
