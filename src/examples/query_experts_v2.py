#!/usr/bin/env python3
"""
query_experts_v2.py

Queries the Gremlin graph for subject matter experts, ranked by association
score (number of documents authored per topic).

All graph operations are provided by the gremlin_example package.
"""

import sys
sys.path.insert(0, '../')
from gremlin import graph_db


def main():
    print("Querying Gremlin graph database for subject matter experts...\n")

    try:
        print(f"Connecting to Gremlin Server at {graph_db.GREMLIN_SERVER}...")
        graph_db.connect()
        print("✓ Connected to Gremlin Server\n")

        # Example 1: Single topic, scored
        print("Example 1: Finding experts for 'Machine Learning'")
        graph_db.display_experts(
            graph_db.find_experts_by_knowledge("Machine Learning", limit=5)
        )

        # Example 2: Multiple topics, scored
        print("\n\nExample 2: Finding experts for multiple AI/ML topics")
        graph_db.display_experts(
            graph_db.find_experts_by_knowledge_list(
                ["Machine Learning", "Deep Learning"], limit=5
            )
        )

        # Example 3: Cloud topic, scored
        print("\n\nExample 3: Finding experts for 'Cloud Computing'")
        graph_db.display_experts(
            graph_db.find_experts_by_knowledge("Cloud Computing", limit=5)
        )

        print("\n✓ Query completed successfully!")
        return 0

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Make sure the database is running: ./start_database.sh")
        print("And that data has been loaded: python load_sample_data.py")
        return 1

    finally:
        graph_db.close()


if __name__ == "__main__":
    sys.exit(main())