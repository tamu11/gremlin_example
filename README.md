# Gremlin Expert Finder — Developer & Coding Agent Reference

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Graph Data Model](#3-graph-data-model)
4. [Connection Management](#4-connection-management)
5. [Query Construction Rules](#5-query-construction-rules)
6. [Serialization & the GraphSON V3 Contract](#6-serialization--the-graphson-v3-contract)
7. [JanusGraph-Specific Considerations](#7-janusgraph-specific-considerations)
8. [Deadlock Handling & Retry Strategy](#8-deadlock-handling--retry-strategy)
9. [Existing Query Patterns (Annotated)](#9-existing-query-patterns-annotated)
10. [How to Write New Queries](#10-how-to-write-new-queries)
11. [Adding New Features to the Graph](#11-adding-new-features-to-the-graph)
12. [Error Handling Conventions](#12-error-handling-conventions)
13. [Testing Approach](#13-testing-approach)
14. [Operational Runbook](#14-operational-runbook)

---

## 1. Project Overview

This project implements a **knowledge-graph-backed expert finder** using:

- **JanusGraph** as the property graph database (accessed over WebSockets via the Gremlin Server protocol).
- **gremlin-python** (`gremlinpython 3.8.x`) as the Gremlin traversal and network client.
- **GraphSON V3** serialization over the binary WebSocket transport.

The graph answers questions of the form *"Who in this organization is an expert in topic X?"* by traversing the path:

```
KnowledgeArea <--COVERS-- Document <--AUTHORED-- Person
```

There are two ranking strategies:

| Version | Function | Ranking |
|---------|----------|---------|
| v1 | `find_experts_by_topic` / `find_experts_by_topics` | Alphabetical; multi-topic ranked by breadth (# of topics covered) |
| v2 | `find_experts_by_knowledge` / `find_experts_by_knowledge_list` | Ranked by association score (# of documents authored per topic) |

---

## 2. Repository Layout

```
graph_db.py          — All Gremlin connection, query, and display logic (single source of truth)
load_sample_data.py  — One-shot script to populate the graph
query_experts.py     — Demo driver for v1 queries
query_experts_v2.py  — Demo driver for v2 queries
data_loader.py       — Alternative loader used by tests / alternate import path
expert_finder.py     — High-level façade (wraps graph_db for application callers)
requirements.txt     — Pinned runtime dependencies
pyproject.toml       — Poetry project definition
```

**Single-source-of-truth rule:** All Gremlin queries and all connection state live in `graph_db.py`. Do not add new Gremlin queries anywhere else. Higher-level modules (`expert_finder.py`, loaders, drivers) call only functions from `graph_db`.

---

## 3. Graph Data Model

### Vertex Labels and Required Properties

| Label | Required Properties | Notes |
|-------|---------------------|-------|
| `Person` | `id` (str), `name` (str), `email` (str), `department` (str) | `id` is the application-level unique key |
| `Document` | `id` (str), `title` (str), `date` (str), `type` (str) | `date` is an ISO 8601 string `YYYY-MM-DD` |
| `KnowledgeArea` | `id` (str), `name` (str) | `name` is the human-readable topic used in queries |

> **Important:** JanusGraph does **not** enforce `id` as a primary key automatically. All vertex lookups use `.has('id', value)`, not `.hasId(value)`. Never rely on JanusGraph's internal vertex ID for application lookups.

### Edge Labels and Direction

| Label | From | To | Semantics |
|-------|------|----|-----------|
| `AUTHORED` | `Person` | `Document` | A person wrote the document |
| `COVERS` | `Document` | `KnowledgeArea` | The document addresses this topic |

Edge direction matters for traversal. The key traversal is always:

```groovy
// Start at a KnowledgeArea, walk backwards along COVERS, then backwards along AUTHORED
g.V().has('KnowledgeArea', 'name', topic)
     .in('COVERS')      // -> Document vertices
     .in('AUTHORED')    // -> Person vertices
```

### Property Naming Convention

- Use **camelCase** for all property keys (`person_id` is fine in Python dicts but map to camelCase at the DB layer if you add schema later).
- `id` is reserved as the logical application key. **Do not** use it for anything other than vertex identity.
- When reading `valueMap()` results, every property value is returned as a **list** (JanusGraph multi-valued properties). Always index `[0]`: `props.get("name", ["N/A"])[0]`.

---

## 4. Connection Management

```python
# graph_db.py
_client = None  # module-level singleton

def connect(url=GREMLIN_SERVER):
    global _client
    _client = gremlin_driver.Client(
        url, 'g',
        message_serializer=GraphSONSerializersV3d0()
    )
    return _client

def close():
    global _client
    if _client is not None:
        _client.close()
        _client = None
```

### Rules

1. **Always call `connect()` before any query and `close()` in a `finally` block.** The client is not thread-safe; do not share it across threads.
2. **One client per process.** The module-level `_client` singleton is intentional. If you need concurrent access, instantiate separate `graph_db`-equivalent modules per thread/process.
3. **`close()` is idempotent.** Safe to call even if already closed.
4. **Do not hard-code the URL** in new code. Reference `graph_db.GREMLIN_SERVER` so the URL can be changed in one place.

---

## 5. Query Construction Rules

This is the most critical section. JanusGraph + gremlin-python has very specific requirements for how queries must be constructed.

### 5.1 Always Use Bindings for Values — Never f-strings or Concatenation

**BAD — SQL-injection equivalent, will cause serialization errors:**
```python
# DO NOT DO THIS
submit(f"g.V().has('KnowledgeArea', 'name', '{topic}')")
submit("g.V().has('KnowledgeArea', 'name', '" + topic + "')")
```

**GOOD — values go in the `bindings` dict:**
```python
submit(
    "g.V().has('KnowledgeArea', 'name', topic)",
    bindings={"topic": topic_name}
)
```

The binding name in the Groovy string must exactly match the key in the `bindings` dict. The gremlin-python client serializes the binding values as GraphSON V3 and passes them alongside the query string to the server. The server substitutes them safely.

### 5.2 Vertex Labels and Property Keys Go in the Query String (Not Bindings)

Property **keys** and vertex **labels** are Groovy symbols — they cannot be passed as value bindings. Only property **values** and numeric parameters can be bound.

**GOOD:**
```python
bindings = {"vlabel": label}  # label CAN be bound — it's a string value for addV()
parts = ["g.addV(vlabel)"]
for i, (key, value) in enumerate(properties.items()):
    param = f"pval{i}"
    parts.append(f".property('{key}', {param})")  # key is embedded, value is bound
    bindings[param] = value
submit_with_retry("".join(parts), bindings)
```

> **Rationale:** `addV(vlabel)` works because the Gremlin step `addV()` accepts a string-valued binding as the label argument. But `.has('label', key, value)` requires `key` to be a literal string in the Groovy query — it is a property **key token**, not a runtime string value.

### 5.3 Integer Parameters Must Be Bound, Not Embedded

```python
# GOOD
submit("...limit(lim)", bindings={"lim": limit})

# BAD — integer formatting inconsistencies across Python/Groovy
submit(f"...limit({limit})")
```

### 5.4 Always Use `valueMap()` to Read Properties — Never Rely on Raw Vertex Objects

```python
# GOOD — returns {propKey: [value, ...], ...}
result = submit("g.V().has('id', vid).valueMap()", bindings={"vid": vertex_id})
props = result[0]
name = props.get("name", ["N/A"])[0]

# RISKY — Vertex objects don't carry property data; requires extra round-trip anyway
result = submit("g.V().has('id', vid)", bindings={"vid": vertex_id})
vertex = result[0]  # This is a Vertex object, not a dict
```

### 5.5 Always Call `.dedup()` After Multi-Step Traversals

When a traversal can reach the same vertex via multiple paths (e.g., a person who authored multiple documents covering the same topic), add `.dedup()` to avoid counting the same person multiple times:

```python
"g.V().has('KnowledgeArea', 'name', topic_name)"
".in('COVERS').in('AUTHORED').dedup()"
".order().by('name').limit(lim).valueMap()"
```

Without `.dedup()`, a Person vertex reachable via N documents will appear N times in the result.

### 5.6 Multi-line Strings: Use Implicit Concatenation, Not `\` Continuations

```python
# GOOD — Python implicit string concatenation, no newlines injected into Groovy
result = submit(
    "g.V().has('KnowledgeArea', 'name', topic)"
    ".in('COVERS').in('AUTHORED')"
    ".groupCount().unfold()"
    ".order().by(values, decr).limit(lim)",
    bindings={"topic": knowledge_topic, "lim": limit}
)
```

Backslash continuations can inject whitespace; triple-quoted strings inject newlines. Both can cause Gremlin Server parse errors. Use adjacent string literals only.

### 5.7 `groupCount()` Returns `Map<Vertex, Long>` — Unpack Carefully

```python
result = submit(
    "g.V()...groupCount().unfold().order().by(values, decr).limit(lim)",
    bindings={...}
)
for entry in result:
    vertex = list(entry.keys())[0]    # gremlin_python Vertex object
    score  = list(entry.values())[0]  # Long (Python int)
    person = _get_person_details_by_vertex(vertex)  # second query using vertex.id
```

`groupCount()` returns a Python dict with one key-value pair per entry after `.unfold()`. The key is a `Vertex` object (not a string ID). You must do a second query using `vertex.id` (the JanusGraph internal ID) to retrieve properties:

```python
def _get_person_details_by_vertex(vertex):
    result = submit("g.V(vid).valueMap()", bindings={"vid": vertex.id})
    ...
```

Note that `vertex.id` here is the JanusGraph-internal long ID, not the application-level `"id"` property. `g.V(vid)` with an internal ID is the correct Gremlin syntax for direct vertex lookup by JanusGraph ID.

---

## 6. Serialization & the GraphSON V3 Contract

### Serializer Instantiation

```python
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

_client = gremlin_driver.Client(
    url, 'g',
    message_serializer=GraphSONSerializersV3d0()
)
```

**Always use `GraphSONSerializersV3d0`.** JanusGraph 0.6+ defaults to GraphSON V3. Using the default serializer (GraphSON V2) will cause type deserialization mismatches for `Long`, `UUID`, and collection types.

### What GraphSON V3 Serializes Correctly as Bindings

| Python Type | GraphSON V3 Wire Type | Safe as Binding? |
|-------------|----------------------|------------------|
| `str` | `String` | ✅ Yes |
| `int` / `long` | `Long` | ✅ Yes |
| `float` | `Double` | ✅ Yes |
| `bool` | `Boolean` | ✅ Yes |
| `list` | `List` | ✅ Yes |
| `dict` | Not directly | ⚠️ Avoid — use individual properties |

### `valueMap()` Return Format

Every property from `valueMap()` is returned as a Python `list`, even for single-valued properties:

```python
props = {"name": ["Alice Johnson"], "id": ["p1"], "department": ["Engineering"]}
name = props.get("name", ["N/A"])[0]  # Always index [0]
```

This is a JanusGraph/GraphSON behavior, not a bug. Always use `[0]`.

### Internal vs. Application IDs

| | JanusGraph Internal ID | Application `id` Property |
|--|------------------------|---------------------------|
| How stored | JanusGraph auto-assigned `Long` | String property on vertex |
| How accessed | `vertex.id` on Vertex object | `.has('id', value)` in traversal |
| Use for | `g.V(internal_id)` direct lookup | All application-level lookups |
| Stable across restarts? | ⚠️ Not guaranteed | ✅ Yes (you control it) |

**Rule:** Never store or expose JanusGraph internal IDs outside of `graph_db.py`. Use application `id` properties everywhere else.

---

## 7. JanusGraph-Specific Considerations

### 7.1 BerkeleyDB Backend Constraints

The default JanusGraph embedded configuration uses BerkeleyDB as the storage backend. Key implications:

- **Concurrent writes produce `DeadlockException` errors.** This is expected behavior, not a JanusGraph bug. The retry strategy in `submit_with_retry()` handles this.
- **Single-writer performance:** BerkeleyDB is not designed for high write throughput. For production, switch to Cassandra or HBase backend. The query code in `graph_db.py` is backend-agnostic.
- **No automatic schema enforcement:** JanusGraph in schema-free mode (default) will happily store any property on any vertex. Enforce schema at the application layer (in `add_vertex`) or define a JanusGraph schema management script separately.

### 7.2 Graph Traversal Source is Always `g`

The client is initialized with `'g'` as the traversal source alias:

```python
_client = gremlin_driver.Client(url, 'g', ...)
```

All Gremlin queries must start with `g.` and use only traversal steps available in the standard Gremlin language. Do not use `graph.` (Gremlin Console API) — it is not available over the Gremlin Server WebSocket protocol.

### 7.3 `g.V().drop().iterate()` — Graph Clear Behavior

```python
submit_with_retry("g.V().drop().iterate()")
```

- `.iterate()` forces execution without materializing results. **Required** for write operations that don't return a meaningful value (like `drop()`).
- This drops all vertices and their incident edges atomically.
- On large graphs this can time out. For production use, batch drops or use JanusGraph management API.

### 7.4 Step Ordering for Correct JanusGraph Query Plans

JanusGraph uses a query optimizer. Always start traversals with the most selective step to trigger index usage:

```groovy
// GOOD — starts with has() on an indexed label+property combination
g.V().has('KnowledgeArea', 'name', topic)

// LESS GOOD — forces a full vertex scan
g.V().hasLabel('KnowledgeArea').has('name', topic)
```

The two-argument form `has('Label', 'property', value)` is the canonical JanusGraph pattern and is most likely to use a composite index if one is defined.

### 7.5 Defining Composite Indexes (For Future Schema Work)

If you add JanusGraph schema management, define composite indexes for every property used in `.has()` filters:

```groovy
// Run once via Gremlin Console or management script
mgmt = graph.openManagement()
name = mgmt.getPropertyKey('name') ?: mgmt.makePropertyKey('name').dataType(String.class).make()
mgmt.buildIndex('byKnowledgeAreaName', Vertex.class).addKey(name).indexOnly(mgmt.getVertexLabel('KnowledgeArea')).buildCompositeIndex()
mgmt.commit()
```

Without an index, all `.has()` queries do a full graph scan. For the current sample dataset this is fine; for production it is not.

---

## 8. Deadlock Handling & Retry Strategy

```python
MAX_RETRIES = 5

def submit_with_retry(query, bindings=None):
    for attempt in range(MAX_RETRIES):
        try:
            return submit(query, bindings=bindings)
        except GremlinServerError as e:
            if "DeadlockException" in str(e) and attempt < MAX_RETRIES - 1:
                wait = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                time.sleep(wait)
            else:
                raise
```

### When to Use Which Submit Function

| Function | Use For |
|----------|---------|
| `submit_with_retry()` | All **write** operations (`addV`, `addE`, `drop`) |
| `submit()` | Read-only queries where deadlocks are not possible |

The jitter (`random.uniform(0, 0.1)`) in the backoff prevents retry storms when multiple processes hit deadlocks simultaneously.

### Backoff Schedule

| Attempt | Base Wait | Max Jitter | Max Total |
|---------|-----------|------------|-----------|
| 1 | 0.1s | 0.1s | 0.2s |
| 2 | 0.2s | 0.1s | 0.3s |
| 3 | 0.4s | 0.1s | 0.5s |
| 4 | 0.8s | 0.1s | 0.9s |

After 5 failed attempts, the `GremlinServerError` is re-raised.

---

## 9. Existing Query Patterns (Annotated)

### Pattern A: Find Persons via KnowledgeArea (v1 — deduped, alphabetical)

```python
submit(
    "g.V().has('KnowledgeArea', 'name', topic_name)"   # 1. Select KA vertex by name
    ".in('COVERS')"                                     # 2. Walk to Documents covering it
    ".in('AUTHORED')"                                   # 3. Walk to Persons who authored those docs
    ".dedup()"                                          # 4. Remove duplicate Person vertices
    ".order().by('name')"                               # 5. Sort alphabetically by name property
    ".limit(lim)"                                       # 6. Cap results
    ".valueMap()",                                      # 7. Return all properties as dict
    bindings={"topic_name": topic_name, "lim": limit}
)
```

### Pattern B: Find Persons Ranked by Document Count (v2 — scored)

```python
submit(
    "g.V().has('KnowledgeArea', 'name', topic)"   # 1. Select KA vertex
    ".in('COVERS')"                                # 2. Documents covering it
    ".in('AUTHORED')"                              # 3. Persons (with duplicates — intentional)
    ".groupCount()"                                # 4. Count occurrences: {Vertex -> Long}
    ".unfold()"                                    # 5. Emit Map.Entry objects one at a time
    ".order().by(values, decr)"                    # 6. Sort by count descending
    ".limit(lim)",                                 # 7. Cap results
    bindings={"topic": knowledge_topic, "lim": limit}
)
```

Note: `.dedup()` is intentionally **absent** here. Duplicates before `groupCount()` are the scoring mechanism — each time a Person vertex appears, it increments their count.

### Pattern C: Vertex Lookup by Internal ID (for groupCount result unpacking)

```python
submit("g.V(vid).valueMap()", bindings={"vid": vertex.id})
```

`vertex.id` is the JanusGraph-internal long integer. `g.V(id)` with an internal ID bypasses property lookup and is the fastest possible vertex access. Only use this pattern when you have a Vertex object from a prior result — never store these IDs externally.

### Pattern D: Add Vertex with Dynamic Properties

```python
bindings = {"vlabel": label}
parts = ["g.addV(vlabel)"]
for i, (key, value) in enumerate(properties.items()):
    param = f"pval{i}"
    parts.append(f".property('{key}', {param})")
    bindings[param] = value
submit_with_retry("".join(parts), bindings)
```

Property keys are embedded as Groovy string literals. Property values are passed as `pval0`, `pval1`, ... bindings. This is the only safe pattern for dynamic property insertion.

### Pattern E: Add Edge by Application ID

```python
submit_with_retry(
    "g.V().has('id', from_id).as('a')"
    ".V().has('id', to_id)"
    ".addE(rel).from('a')",
    {"from_id": from_id, "to_id": to_id, "rel": relation_type}
)
```

Key points:
- Uses `.as('a')` to label the source vertex for later reference.
- `.addE(rel)` takes the edge label as a bound string.
- `.from('a')` wires the edge from the labeled vertex.
- Both vertex lookups use the application `id` property, not internal IDs.

---

## 10. How to Write New Queries

Follow this checklist for every new query function added to `graph_db.py`:

### Checklist

- [ ] Add the function to `graph_db.py` only.
- [ ] Use `submit()` for read queries, `submit_with_retry()` for writes.
- [ ] All user-supplied string values go in `bindings={}`, never in the query string.
- [ ] Property keys and labels are embedded as string literals in the query string.
- [ ] Use the two-argument `has('Label', 'property', binding)` form for selectivity.
- [ ] Add `.dedup()` unless duplicates are intentional (e.g., for `groupCount()` scoring).
- [ ] Use `.valueMap()` to read properties; always index `[0]` on each property.
- [ ] Return a plain Python `list` of `dict` objects — no Gremlin objects should leak out.
- [ ] Catch `GremlinServerError`, log it, and return `[]` on failure.
- [ ] Add a docstring with Args, Returns, and the traversal path described in plain English.

### Template for a New Read Query

```python
def find_X_by_Y(param, limit=10):
    """
    Find X vertices related to Y.

    Traversal: LabelA <--EDGE_A-- LabelB <--EDGE_B-- LabelC

    Args:
        param (str): The Y property value to filter on.
        limit (int): Maximum number of results.

    Returns:
        list[dict]: Records with keys: id, name, ...
    """
    print(f"Finding X for: '{param}'")
    try:
        result = submit(
            "g.V().has('LabelA', 'property', pval)"
            ".in('EDGE_A')"
            ".in('EDGE_B')"
            ".dedup()"
            ".order().by('name')"
            ".limit(lim)"
            ".valueMap()",
            bindings={"pval": param, "lim": limit}
        )
        return [
            {
                "id":   props.get("id",   ["N/A"])[0],
                "name": props.get("name", ["N/A"])[0],
            }
            for props in result
        ]
    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []
```

### Template for a Scored (groupCount) Query

```python
def find_X_scored(param, limit=10):
    """..."""
    try:
        result = submit(
            "g.V().has('LabelA', 'property', pval)"
            ".in('EDGE_A').in('EDGE_B')"   # duplicates intentional for scoring
            ".groupCount().unfold()"
            ".order().by(values, decr).limit(lim)",
            bindings={"pval": param, "lim": limit}
        )
        records = []
        for entry in result:
            vertex = list(entry.keys())[0]
            score  = list(entry.values())[0]
            detail = _get_person_details_by_vertex(vertex)
            if detail:
                detail["score"] = score
                records.append(detail)
        return records
    except GremlinServerError as e:
        print(f"Gremlin Server Error: {e}")
        return []
```

---

## 11. Adding New Features to the Graph

### Adding a New Vertex Label

1. Define the data as a list of dicts in the appropriate loader (`load_sample_data.py` or `data_loader.py`).
2. Call `graph_db.add_vertex("NewLabel", properties_dict)` for each record. The `id` property is mandatory.
3. If the new label will be used in `.has()` filters, consider adding a JanusGraph composite index (see §7.5).
4. Document the label and its required properties in §3 of this README.

### Adding a New Edge Type

1. Define `(from_id, to_id)` pairs in the loader.
2. Call `graph_db.add_edge(from_id, to_id, "NEW_EDGE_LABEL")` for each pair.
3. Decide on edge direction convention and document it in the Edge Labels table (§3).
4. Write traversal tests (see §13) to verify the edges are reachable in both directions.

### Adding a New Query Function

1. Determine the traversal path using the vertex/edge model.
2. Write the Gremlin traversal string using implicit concatenation.
3. Follow the template in §10.
4. Add a corresponding `display_*` helper or extend `display_experts()` if the return shape differs.
5. Add an example call to `query_experts.py` or `query_experts_v2.py`.

### Extending Person, Document, or KnowledgeArea Properties

1. Add the new key-value to the data definitions in the loader.
2. `add_vertex()` handles arbitrary property dicts dynamically — no changes needed there.
3. Update `find_experts_*` return dict construction to include the new field.
4. Update `display_experts()` to print the new field.
5. Update the Vertex Labels table in §3.

---

## 12. Error Handling Conventions

All public functions in `graph_db.py` follow this pattern:

```python
try:
    result = submit(...)         # or submit_with_retry for writes
    return [parsed records]
except GremlinServerError as e:
    print(f"Gremlin Server Error: {e}")
    return []                    # empty list, never None
```

**Rules:**
- Never let `GremlinServerError` propagate out of `graph_db.py` from query functions (callers expect `list`).
- Connection-level functions (`connect`, `close`, `clear_graph`) may surface errors to the caller — they are explicitly called with error-handling context.
- Always return `[]` (not `None`) on failure so callers can do `for expert in result:` safely.
- Print errors with `"Gremlin Server Error: "` prefix for grep-ability.

---

## 13. Testing Approach

There is no test suite in the current repo. When adding tests, follow these guidelines:

### Unit Tests (No DB Required)

Mock `graph_db.submit` to return pre-built `valueMap` responses:

```python
from unittest.mock import patch

MOCK_PERSON = [{"id": ["p1"], "name": ["Alice"], "email": ["a@b.com"], "department": ["Eng"]}]

def test_find_experts_by_topic_parses_results():
    with patch("graph_db.submit", return_value=MOCK_PERSON):
        result = graph_db.find_experts_by_topic("Machine Learning", limit=5)
    assert result[0]["name"] == "Alice"
    assert result[0]["person_id"] == "p1"
```

### Integration Tests (DB Required)

Use `data_loader.py` to seed a known dataset, then assert on query results:

```python
def test_expert_count_for_machine_learning():
    graph_db.connect()
    graph_db.clear_graph()
    data_loader.load_test_data()
    experts = graph_db.find_experts_by_topic("Machine Learning")
    assert len(experts) >= 1
    graph_db.close()
```

### Key Assertions to Cover

- `valueMap()` results are always indexed at `[0]`.
- `find_experts_by_topics()` deduplicates correctly when a person spans multiple topics.
- `groupCount()` scoring is monotonically consistent (more docs → higher score).
- `add_edge()` fails gracefully if either vertex does not exist.

---

## 14. Operational Runbook

### Start the Database

```bash
./start_database.sh        # starts JanusGraph + Gremlin Server on ws://localhost:8182/gremlin
```

### Load Sample Data

```bash
python load_sample_data.py
```

Expected output ends with:

```
  People:          7
  Documents:       6
  Knowledge Areas: 6
  Relationships:   17
OK Data verification complete!
OK Sample data loaded successfully!
```

### Run Example Queries

```bash
python query_experts.py      # v1: alphabetical ranking
python query_experts_v2.py   # v2: scored ranking
```

### Verify Graph State Manually

Using the Gremlin Console (if available):

```groovy
// Count all vertices by label
g.V().groupCount().by(label)

// List all KnowledgeArea names
g.V().hasLabel('KnowledgeArea').values('name').fold()

// Full traversal for a topic
g.V().has('KnowledgeArea', 'name', 'Machine Learning')
     .in('COVERS').in('AUTHORED').dedup().values('name')
```

### Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Not connected` | `connect()` not called | Call `graph_db.connect()` before queries |
| `GremlinServerError: DeadlockException` | BerkeleyDB concurrent write | Handled by `submit_with_retry`; if persistent, reduce write concurrency |
| `result[0]` KeyError on property | Used `[0]` omitted from `valueMap` access | Always use `props.get("key", ["N/A"])[0]` |
| Empty results for known topic | Topic name case mismatch | `has('name', ...)` is case-sensitive; check exact name string |
| `ConnectionRefusedError` on port 8182 | Gremlin Server not running | Run `./start_database.sh` |
| `IndexError` on `list(entry.keys())[0]` | `groupCount().unfold()` returned empty entry | Add null check before unpacking `groupCount` entries |