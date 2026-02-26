#!/usr/bin/env python3
"""
query_experts.py (v1)

Queries the Gremlin graph for subject matter experts, ordered alphabetically
and ranked by breadth of topic coverage.

All graph operations are provided by the gremlin_example package.
"""
import sys
sys.path.insert(0, '../')
from gremlin import graph_db


def main():
    print("Querying Gremlin graph database for subject matter experts...\n")

    try:
        print(f"Connecting to {graph_db.GREMLIN_SERVER}...")
        graph_db.connect()
        print("✅ Connected successfully!")

        # Example 1: Single topic
        print("\n" + "=" * 80)
        print("EXAMPLE 1: Single Topic Query")
        print("=" * 80)
        graph_db.display_experts(
            graph_db.find_experts_by_topic("Machine Learning", limit=5)
        )

        # Example 2: Multiple topics
        print("\n" + "=" * 80)
        print("EXAMPLE 2: Multi-Topic Query")
        print("=" * 80)
        graph_db.display_experts(
            graph_db.find_experts_by_topics(["Machine Learning", "Deep Learning"], limit=5)
        )

        # Example 3: Data-related topics
        print("\n" + "=" * 80)
        print("EXAMPLE 3: Data Topics Query")
        print("=" * 80)
        graph_db.display_experts(
            graph_db.find_experts_by_topics(["Data Engineering", "Cloud Computing"], limit=5)
        )

        print("\n✅ Query examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease make sure:")
        print("1. The database is running: ./start_database.sh")
        print("2. Sample data is loaded: python load_sample_data.py")
        print("3. The port 8182 is available")

    finally:
        graph_db.close()


if __name__ == "__main__":
    main()