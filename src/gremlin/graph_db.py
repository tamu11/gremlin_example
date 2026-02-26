"""
graph_db.py — shared Gremlin graph database library.

Provides connection management, low-level graph operations, and
expert-finding query functions used by load_sample_data.py,
query_experts.py, and query_experts_v2.py.
"""

import time
import random

from gremlin_python.driver import client as gremlin_driver
from gremlin_python.driver.protocol import GremlinServerError
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GREMLIN_SERVER = "ws://localhost:8182/gremlin"
MAX_RETRIES = 5

# Module-level client instance, set by connect()
_client = None


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def connect(url=GREMLIN_SERVER):
    """
    Open a connection to the Gremlin server.

    Args:
        url (str): WebSocket URL of the Gremlin server.

    Returns:
        The gremlin client instance.
    """
    global _client
    _client = gremlin_driver.Client(
        url, 'g',
        message_serializer=GraphSONSerializersV3d0()
    )
    return _client


def close():
    """Close the active Gremlin connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def submit(query, bindings=None):
    """
    Submit a Gremlin query and return results as a list.

    Args:
        query (str): Gremlin query string.
        bindings (dict): Optional variable bindings.

    Returns:
        list: Query results.

    Raises:
        GremlinServerError: On server-side errors.
        RuntimeError: If called before connect().
    """
    if _client is None:
        raise RuntimeError("Not connected — call graph_db.connect() first.")
    return _client.submit(query, bindings=bindings).all().result()


def submit_with_retry(query, bindings=None):
    """
    Submit a Gremlin query with exponential-backoff retry on deadlocks.

    JanusGraph's BerkeleyDB backend can produce deadlocks under concurrent
    writes. This helper retries transparently up to MAX_RETRIES times.

    Args:
        query (str): Gremlin query string.
        bindings (dict): Optional variable bindings.

    Returns:
        list: Query results.

    Raises:
        GremlinServerError: When retries are exhausted or a non-deadlock
                            error occurs.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return submit(query, bindings=bindings)
        except GremlinServerError as e:
            if "DeadlockException" in str(e) and attempt < MAX_RETRIES - 1:
                wait = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                print(
                    f"  Deadlock detected, retrying in {wait:.2f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Low-level graph operations
# ---------------------------------------------------------------------------

def clear_graph():
    """
    Drop all vertices (and their edges) from the graph.

    Returns:
        bool: True on success, False on failure.
    """
    print("Clearing existing graph data...")
    try:
        submit_with_retry("g.V().drop().iterate()")
        print("OK Graph cleared successfully!")
        return True
    except GremlinServerError as e:
        print(f"ERROR clearing graph: {e}")
        return False


def add_vertex(label, properties):
    """
    Add a vertex with the given label and property dict.

    Property keys are embedded literally in the query string (they come from
    trusted application code); values are passed as bindings so they are
    serialised safely.

    Args:
        label (str): Vertex label (e.g. 'Person', 'Document').
        properties (dict): Property key→value pairs.

    Raises:
        GremlinServerError: On server-side errors (after retry).
    """
    # Build the query with keys in the string, values as bound parameters.
    # e.g. "g.addV(vlabel).property('id', pval0).property('name', pval1)"
    bindings = {"vlabel": label}
    parts = ["g.addV(vlabel)"]
    for i, (key, value) in enumerate(properties.items()):
        param = f"pval{i}"
        parts.append(f".property('{key}', {param})")
        bindings[param] = value
    submit_with_retry("".join(parts), bindings)


def add_edge(from_id, to_id, relation_type):
    """
    Add a directed edge between two vertices identified by their 'id' property.

    Args:
        from_id (str): Source vertex 'id' property value.
        to_id (str):   Target vertex 'id' property value.
        relation_type (str): Edge label (e.g. 'AUTHORED', 'COVERS').

    Raises:
        GremlinServerError: On server-side errors (after retry).
    """
    submit_with_retry(
        "g.V().has('id', from_id).as('a')"
        ".V().has('id', to_id)"
        ".addE(rel).from('a')",
        {"from_id": from_id, "to_id": to_id, "rel": relation_type}
    )


def verify_data():
    """Print a summary of vertex and edge counts in the graph."""
    print("\nVerifying data...")
    try:
        person_count = submit_with_retry("g.V().hasLabel('Person').count()")[0]
        doc_count    = submit_with_retry("g.V().hasLabel('Document').count()")[0]
        area_count   = submit_with_retry("g.V().hasLabel('KnowledgeArea').count()")[0]
        edge_count   = submit_with_retry("g.E().count()")[0]

        print(f"  People:          {person_count}")
        print(f"  Documents:       {doc_count}")
        print(f"  Knowledge Areas: {area_count}")
        print(f"  Relationships:   {edge_count}")
        print("OK Data verification complete!")
    except GremlinServerError as e:
        print(f"ERROR verifying data: {e}")


# ---------------------------------------------------------------------------
# Expert query functions
# ---------------------------------------------------------------------------

def find_experts_by_topic(topic_name, limit=10):
    """
    Find experts for a single topic (v1 — ordered alphabetically).

    Traversal: KnowledgeArea <-COVERS- Document <-AUTHORED- Person

    Args:
        topic_name (str): Knowledge area name to search.
        limit (int): Maximum results to return.

    Returns:
        list[dict]: Expert records with keys: person_id, name, email,
                    department, topic.
    """
    print(f"Finding experts for: '{topic_name}'")
    try:
        result = submit(
            "g.V().has('KnowledgeArea', 'name', topic_name)"
            ".in('COVERS').in('AUTHORED').dedup()"
            ".order().by('name').limit(lim).valueMap()",
            bindings={"topic_name": topic_name, "lim": limit}
        )
        return [
            {
                "person_id":  props.get("id",         ["N/A"])[0],
                "name":       props.get("name",       ["N/A"])[0],
                "email":      props.get("email",      ["N/A"])[0],
                "department": props.get("department", ["N/A"])[0],
                "topic":      topic_name,
            }
            for props in result
        ]
    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []


def find_experts_by_topics(topic_list, limit=10):
    """
    Find experts across multiple topics (v1 — ranked by topic coverage breadth).

    Args:
        topic_list (list[str]): Knowledge area names to search.
        limit (int): Maximum results to return.

    Returns:
        list[dict]: Expert records, each with a 'topics' list.
    """
    print(f"Finding experts for topics: {', '.join(topic_list)}")
    all_experts = {}
    for topic in topic_list:
        for expert in find_experts_by_topic(topic, limit):
            pid = expert["person_id"]
            if pid in all_experts:
                all_experts[pid]["topics"].append(topic)
            else:
                expert["topics"] = [topic]
                all_experts[pid] = expert

    return sorted(
        all_experts.values(),
        key=lambda x: len(x["topics"]),
        reverse=True
    )[:limit]


def _get_person_details_by_vertex(vertex):
    """
    Fetch property map for a Vertex object returned by a traversal.

    Args:
        vertex: A gremlin_python Vertex object.

    Returns:
        dict | None: Keys: person_id, name, email, department.
    """
    try:
        result = submit("g.V(vid).valueMap()", bindings={"vid": vertex.id})
        if result:
            props = result[0]
            return {
                "person_id":  props.get("id",         ["N/A"])[0],
                "name":       props.get("name",       ["N/A"])[0],
                "email":      props.get("email",      ["N/A"])[0],
                "department": props.get("department", ["N/A"])[0],
            }
        return None
    except GremlinServerError:
        return None


def find_experts_by_knowledge(knowledge_topic, limit=10):
    """
    Find experts for a single topic (v2 — ranked by document-count score).

    Traversal: KnowledgeArea <-COVERS- Document <-AUTHORED- Person
    Score = number of documents the person authored that cover the topic.

    Args:
        knowledge_topic (str): Knowledge area name to search.
        limit (int): Maximum results to return.

    Returns:
        list[dict]: Expert records with keys: person_id, name, email,
                    department, association_score, knowledge_topic.
    """
    print(f"Finding experts for: '{knowledge_topic}'")
    try:
        result = submit(
            "g.V().has('KnowledgeArea', 'name', topic)"
            ".in('COVERS').in('AUTHORED')"
            ".hasLabel('Person')"          # ← enforces node type
            ".groupCount().unfold()"
            ".order().by(values, decr).limit(lim)",
            bindings={"topic": knowledge_topic, "lim": limit}
        )
        experts = []
        for entry in result:
            vertex = list(entry.keys())[0]
            score  = list(entry.values())[0]
            person = _get_person_details_by_vertex(vertex)
            if person:
                person["association_score"] = score
                person["knowledge_topic"]   = knowledge_topic
                experts.append(person)
        return experts
    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []


def find_experts_by_knowledge_list(knowledge_topics, limit=10):
    """
    Find experts across multiple topics (v2 — ranked by total score).

    Args:
        knowledge_topics (list[str]): Knowledge area names to search.
        limit (int): Maximum results to return.

    Returns:
        list[dict]: Expert records with accumulated association_score.
    """
    print(f"Finding experts for multiple topics: {', '.join(knowledge_topics)}")
    combined = {}
    for topic in knowledge_topics:
        for expert in find_experts_by_knowledge(topic, limit=limit):
            pid = expert["person_id"]
            if pid in combined:
                combined[pid]["association_score"] += expert["association_score"]
                combined[pid]["knowledge_topics"].append(topic)
            else:
                expert["knowledge_topics"] = [topic]
                combined[pid] = expert

    return sorted(
        combined.values(),
        key=lambda x: x["association_score"],
        reverse=True
    )[:limit]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_experts(experts):
    """
    Print a formatted expert list to stdout.

    Args:
        experts (list[dict]): Expert records from any find_experts_* function.
    """
    if not experts:
        print("No experts found.")
        return

    print("\n" + "=" * 80)
    print("SUBJECT MATTER EXPERTS")
    print("=" * 80)

    for i, expert in enumerate(experts, 1):
        print(f"\n#{i}")
        print(f"Name:       {expert.get('name', 'N/A')}")
        print(f"ID:         {expert.get('person_id', 'N/A')}")
        print(f"Email:      {expert.get('email', 'N/A')}")
        print(f"Department: {expert.get('department', 'N/A')}")

        if "association_score" in expert:
            print(f"Score:      {expert['association_score']}")

        topics = expert.get(
            "topics",
            expert.get("knowledge_topics", [expert.get("topic", "N/A")])
        )
        print(f"Topics:     {', '.join(str(t) for t in topics)}")
        print("-" * 80)