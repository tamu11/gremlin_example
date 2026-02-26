#!/usr/bin/env python3
"""
Standalone NetworkX demo to simulate a graph database.
This demonstrates the same concepts without requiring Docker.
"""

import networkx as nx
import matplotlib.pyplot as plt

def create_expert_graph():
    """Create a graph of experts, documents, and knowledge areas."""
    G = nx.DiGraph()

    # Add nodes
    people = [
        ('p1', {'name': 'Alice Johnson', 'role': 'Data Scientist', 'email': 'alice.johnson@company.com'}),
        ('p2', {'name': 'Bob Smith', 'role': 'Software Engineer', 'email': 'bob.smith@company.com'}),
        ('p3', {'name': 'Carol Davis', 'role': 'Product Manager', 'email': 'carol.davis@company.com'}),
        ('p4', {'name': 'David Wilson', 'role': 'Data Engineer', 'email': 'david.wilson@company.com'}),
        ('p5', {'name': 'Eve Brown', 'role': 'ML Engineer', 'email': 'eve.brown@company.com'}),
        ('p6', {'name': 'Frank Miller', 'role': 'Cloud Architect', 'email': 'frank.miller@company.com'}),
        ('p7', {'name': 'Grace Lee', 'role': 'DevOps Engineer', 'email': 'grace.lee@company.com'})
    ]

    documents = [
        ('doc1', {'title': 'Machine Learning Research Paper', 'type': 'Research Paper'}),
        ('doc2', {'title': 'Cloud Migration Guide', 'type': 'Technical Guide'}),
        ('doc3', {'title': 'Data Governance Best Practices', 'type': 'White Paper'}),
        ('doc4', {'title': 'Deep Learning Applications', 'type': 'Research Paper'}),
        ('doc5', {'title': 'Kubernetes Operations Manual', 'type': 'Technical Guide'}),
        ('doc6', {'title': 'Data Engineering Patterns', 'type': 'White Paper'})
    ]

    knowledge = [
        ('ml', {'topic': 'Machine Learning'}),
        ('dl', {'topic': 'Deep Learning'}),
        ('de', {'topic': 'Data Engineering'}),
        ('cc', {'topic': 'Cloud Computing'}),
        ('do', {'topic': 'DevOps'}),
        ('dg', {'topic': 'Data Governance'})
    ]

    # Add all nodes to the graph
    G.add_nodes_from(people, type='person')
    G.add_nodes_from(documents, type='document')
    G.add_nodes_from(knowledge, type='knowledge')

    # Add edges (relationships)
    # Alice authored doc1 and doc4, which cover Machine Learning and Deep Learning
    G.add_edge('p1', 'doc1', relationship='AUTHORED')
    G.add_edge('p1', 'doc4', relationship='AUTHORED')
    G.add_edge('doc1', 'ml', relationship='COVERS')
    G.add_edge('doc4', 'dl', relationship='COVERS')

    # Bob authored doc1 and doc6, which cover Machine Learning and Data Engineering
    G.add_edge('p2', 'doc1', relationship='AUTHORED')
    G.add_edge('p2', 'doc6', relationship='AUTHORED')
    G.add_edge('doc6', 'de', relationship='COVERS')

    # Carol authored doc3, which covers Data Governance
    G.add_edge('p3', 'doc3', relationship='AUTHORED')
    G.add_edge('doc3', 'dg', relationship='COVERS')

    # David authored doc6, which covers Data Engineering
    G.add_edge('p4', 'doc6', relationship='AUTHORED')

    # Eve authored doc1 and doc4, which cover Machine Learning and Deep Learning
    G.add_edge('p5', 'doc1', relationship='AUTHORED')
    G.add_edge('p5', 'doc4', relationship='AUTHORED')

    # Frank authored doc2 and doc5, which cover Cloud Computing and DevOps
    G.add_edge('p6', 'doc2', relationship='AUTHORED')
    G.add_edge('p6', 'doc5', relationship='AUTHORED')
    G.add_edge('doc2', 'cc', relationship='COVERS')
    G.add_edge('doc5', 'do', relationship='COVERS')

    # Grace authored doc5, which covers DevOps
    G.add_edge('p7', 'doc5', relationship='AUTHORED')

    return G

def query_experts_by_topic(G, topic):
    """Find experts for a given topic by traversing the graph."""
    print(f"  Querying for topic: {topic}")
    experts = []

    # Find knowledge node
    knowledge_node = None
    for node, data in G.nodes(data=True):
        if data.get('type') == 'knowledge' and data.get('topic') == topic:
            knowledge_node = node
            print(f"  Found knowledge node: {knowledge_node}")
            break

    if knowledge_node is None:
        print(f"  No knowledge node found for topic '{topic}'")
        return []

    # Find documents that cover this topic
    covering_docs = []
    for doc_node in G.nodes():
        doc_data = G.nodes[doc_node]
        if doc_data.get('type') == 'document':
            for neighbor in G.neighbors(doc_node):
                if neighbor == knowledge_node and G.edges[doc_node, knowledge_node].get('relationship') == 'COVERS':
                    covering_docs.append(doc_node)
                    print(f"  Found covering document: {doc_node} -> {knowledge_node}")
                    break

    print(f"  Found {len(covering_docs)} covering documents")

    # Find people who authored these documents
    for doc_node in covering_docs:
        print(f"  Checking document: {doc_node}")
        for person_node in G.nodes():
            person_data = G.nodes[person_node]
            if person_data.get('type') == 'person':
                for neighbor in G.neighbors(person_node):
                    if neighbor == doc_node and G.edges[person_node, doc_node].get('relationship') == 'AUTHORED':
                        print(f"  Found author: {person_node} -> {doc_node}")
                        experts.append({
                            'id': person_node,
                            'name': person_data.get('name', 'Unknown'),
                            'role': person_data.get('role', 'Unknown'),
                            'email': person_data.get('email', 'Unknown'),
                            'topic': topic
                        })
                        break

    return experts

def main():
    print("Creating expert graph using NetworkX...")
    G = create_expert_graph()

    print(f"Graph created with {len(G.nodes())} nodes and {len(G.edges())} edges")

    # Query for different topics
    topics = ['Machine Learning', 'Deep Learning', 'Cloud Computing', 'DevOps']

    for topic in topics:
        print(f"\n=== Experts in {topic} ===")
        experts = query_experts_by_topic(G, topic)

        if experts:
            for i, expert in enumerate(experts, 1):
                print(f"  {i}. {expert['name']} ({expert['role']}) - {expert['email']}")
        else:
            print(f"  No experts found for {topic}")

    # Visualize the graph
    print("\nGenerating visualization...")
    plt.figure(figsize=(12, 8))

    # Get positions for layout
    pos = nx.spring_layout(G, seed=42)

    # Draw nodes
    node_colors = []
    for node in G.nodes():
        if G.nodes[node]['type'] == 'person':
            node_colors.append('lightblue')
        elif G.nodes[node]['type'] == 'document':
            node_colors.append('lightgreen')
        else:
            node_colors.append('pink')

    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=2000, font_size=10, font_weight='bold')

    # Draw edges with labels
    edge_labels = nx.get_edge_attributes(G, 'relationship')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

    plt.title('Expert Graph: People, Documents, and Knowledge Areas')
    plt.savefig('expert_graph.png', dpi=150, bbox_inches='tight')
    print("Graph visualization saved as 'expert_graph.png'")

    print("\nDemo completed successfully!")

if __name__ == '__main__':
    main()
