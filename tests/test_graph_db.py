"""
test_graph_db.py — Comprehensive pytest test suite for graph_db.py

All tests mock the gremlin_python driver so no live server is required.

Test structure:
  - TestConnect             : connect() / close() lifecycle
  - TestSubmit              : submit() error paths
  - TestSubmitWithRetry     : retry + backoff logic
  - TestClearGraph          : clear_graph()
  - TestAddVertex           : add_vertex() query construction
  - TestAddEdge             : add_edge()
  - TestVerifyData          : verify_data() output
  - TestFindExpertsByTopic  : find_experts_by_topic() (v1 single)
  - TestFindExpertsByTopics : find_experts_by_topics() (v1 multi)
  - TestGetPersonDetails    : _get_person_details_by_vertex()
  - TestFindExpertsByKnowledge     : find_experts_by_knowledge() (v2 single)
  - TestFindExpertsByKnowledgeList : find_experts_by_knowledge_list() (v2 multi)
  - TestDisplayExperts      : display_experts() console output
"""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Module under test — imported after patching the heavy gremlin dependency
# ---------------------------------------------------------------------------

# Patch the gremlin driver before graph_db is imported so that the import
# itself never tries to open a network connection.
import sys
from unittest.mock import MagicMock

# Stub out gremlin_python entirely
gremlin_stub = MagicMock()
sys.modules.setdefault("gremlin_python", gremlin_stub)
sys.modules.setdefault("gremlin_python.driver", gremlin_stub)
sys.modules.setdefault("gremlin_python.driver.client", gremlin_stub)
sys.modules.setdefault("gremlin_python.driver.protocol", gremlin_stub)
sys.modules.setdefault("gremlin_python.driver.serializer", gremlin_stub)

# Make GremlinServerError a real exception subclass so `raise` / `except` work
class _FakeGremlinServerError(Exception):
    """Real Exception subclass so raise/except/pytest.raises all work."""

# The attribute must live on the stub itself — every sys.modules entry points
# to the same object, so .GremlinServerError is found however it is accessed.
gremlin_stub.GremlinServerError = _FakeGremlinServerError

for _mod in (
    "gremlin_python",
    "gremlin_python.driver",
    "gremlin_python.driver.client",
    "gremlin_python.driver.protocol",
    "gremlin_python.driver.serializer",
):
    sys.modules.setdefault(_mod, gremlin_stub)

# ---------------------------------------------------------------------------
# Put the source tree on sys.path so `import graph_db` resolves correctly
# regardless of where pytest is invoked from.
# Adjust the path below if your layout differs.
# ---------------------------------------------------------------------------
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src" / "gremlin"))

import graph_db  # noqa: E402

from graph_db import (  # noqa: E402
    GremlinServerError,
    connect, close, submit, submit_with_retry,
    clear_graph, add_vertex, add_edge, verify_data,
    find_experts_by_topic, find_experts_by_topics,
    find_experts_by_knowledge, find_experts_by_knowledge_list,
    _get_person_details_by_vertex, display_experts,
    MAX_RETRIES,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_vertex(vid=1):
    """Return a minimal fake Vertex object."""
    v = MagicMock()
    v.id = vid
    return v


def _make_props(**kwargs):
    """
    Return a valueMap-style dict where every value is a single-element list,
    mirroring what JanusGraph/Gremlin returns from .valueMap().
    """
    return {k: [v] for k, v in kwargs.items()}


def _mock_client(return_value=None, side_effect=None):
    """
    Build a mock gremlin Client whose .submit().all().result() chain
    returns *return_value* or raises *side_effect*.
    """
    client = MagicMock()
    future = MagicMock()
    if side_effect is not None:
        future.result.side_effect = side_effect
    else:
        future.result.return_value = return_value if return_value is not None else []
    client.submit.return_value.all.return_value = future
    return client


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def reset_client():
    """Reset module-level _client before every test."""
    graph_db._client = None
    yield
    graph_db._client = None


@pytest.fixture()
def connected_client():
    """Inject a mock client as if connect() had been called."""
    client = _mock_client(return_value=[])
    graph_db._client = client
    return client


# ===========================================================================
# TestConnect
# ===========================================================================

class TestConnect:
    def test_connect_sets_module_client(self):
        mock_cls = MagicMock(return_value=MagicMock())
        with patch("graph_db.gremlin_driver.Client", mock_cls):
            result = connect("ws://fake:8182/gremlin")
        assert graph_db._client is result
        mock_cls.assert_called_once()

    def test_connect_uses_default_url(self):
        mock_cls = MagicMock(return_value=MagicMock())
        with patch("graph_db.gremlin_driver.Client", mock_cls):
            connect()
        args, _ = mock_cls.call_args
        assert args[0] == graph_db.GREMLIN_SERVER

    def test_connect_returns_client(self):
        fake = MagicMock()
        with patch("graph_db.gremlin_driver.Client", return_value=fake):
            result = connect()
        assert result is fake

    def test_connect_overrides_existing_client(self):
        old = MagicMock()
        graph_db._client = old
        new = MagicMock()
        with patch("graph_db.gremlin_driver.Client", return_value=new):
            connect()
        assert graph_db._client is new


class TestClose:
    def test_close_calls_client_close(self, connected_client):
        close()
        connected_client.close.assert_called_once()

    def test_close_sets_client_none(self, connected_client):
        close()
        assert graph_db._client is None

    def test_close_when_already_none_is_safe(self):
        graph_db._client = None   # already None
        close()                   # must not raise
        assert graph_db._client is None


# ===========================================================================
# TestSubmit
# ===========================================================================

class TestSubmit:
    def test_submit_raises_when_not_connected(self):
        with pytest.raises(RuntimeError, match="Not connected"):
            submit("g.V()")

    def test_submit_passes_query_and_bindings(self, connected_client):
        connected_client.submit.return_value.all.return_value.result.return_value = [42]
        result = submit("g.V().count()", bindings={"x": 1})
        connected_client.submit.assert_called_once_with("g.V().count()", bindings={"x": 1})
        assert result == [42]

    def test_submit_with_no_bindings(self, connected_client):
        connected_client.submit.return_value.all.return_value.result.return_value = []
        submit("g.V().drop().iterate()")
        connected_client.submit.assert_called_once_with(
            "g.V().drop().iterate()", bindings=None
        )

    def test_submit_propagates_gremlin_error(self, connected_client):
        connected_client.submit.return_value.all.return_value.result.side_effect = (
            GremlinServerError("boom")
        )
        with pytest.raises(GremlinServerError):
            submit("g.V()")


# ===========================================================================
# TestSubmitWithRetry
# ===========================================================================

class TestSubmitWithRetry:
    def test_success_on_first_attempt(self, connected_client):
        connected_client.submit.return_value.all.return_value.result.return_value = [1]
        result = submit_with_retry("g.V().count()")
        assert result == [1]
        assert connected_client.submit.call_count == 1

    def test_retries_on_deadlock(self, connected_client):
        """Should retry on DeadlockException and eventually succeed."""
        result_mock = connected_client.submit.return_value.all.return_value.result
        deadlock = GremlinServerError("DeadlockException occurred")
        result_mock.side_effect = [deadlock, deadlock, [99]]

        with patch("time.sleep"):
            result = submit_with_retry("g.V().count()")

        assert result == [99]
        assert connected_client.submit.call_count == 3

    def test_does_not_retry_non_deadlock_error(self, connected_client):
        result_mock = connected_client.submit.return_value.all.return_value.result
        result_mock.side_effect = GremlinServerError("SomeOtherError")

        with pytest.raises(GremlinServerError, match="SomeOtherError"):
            submit_with_retry("g.V().count()")

        assert connected_client.submit.call_count == 1

    def test_raises_after_max_retries_exhausted(self, connected_client):
        result_mock = connected_client.submit.return_value.all.return_value.result
        result_mock.side_effect = GremlinServerError("DeadlockException")

        with patch("time.sleep"):
            with pytest.raises(GremlinServerError):
                submit_with_retry("g.V().count()")

        assert connected_client.submit.call_count == MAX_RETRIES

    def test_backoff_sleep_called_between_retries(self, connected_client):
        result_mock = connected_client.submit.return_value.all.return_value.result
        deadlock = GremlinServerError("DeadlockException")
        result_mock.side_effect = [deadlock, []]

        with patch("time.sleep") as mock_sleep:
            submit_with_retry("g.V()")

        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration >= 0


# ===========================================================================
# TestClearGraph
# ===========================================================================

class TestClearGraph:
    def test_clear_graph_submits_drop(self, connected_client):
        with patch("graph_db.submit_with_retry", return_value=[]) as mock_swr:
            result = clear_graph()
        mock_swr.assert_called_once_with("g.V().drop().iterate()")
        assert result is True

    def test_clear_graph_returns_false_on_error(self):
        with patch(
            "graph_db.submit_with_retry",
            side_effect=GremlinServerError("error")
        ):
            result = clear_graph()
        assert result is False


# ===========================================================================
# TestAddVertex
# ===========================================================================

class TestAddVertex:
    # TestAddVertex.test_add_vertex_single_property
    def test_add_vertex_single_property(self):
        with patch("graph_db.submit_with_retry") as mock_swr:
            add_vertex("Person", {"name": "Alice"})

        args = mock_swr.call_args[0]          # positional args tuple
        query, bindings = args[0], args[1]    # (query_str, bindings_dict)
        assert "g.addV(vlabel)" in query
        assert ".property('name', pval0)" in query
        assert bindings["vlabel"] == "Person"
        assert bindings["pval0"] == "Alice"

    # TestAddVertex.test_add_vertex_multiple_properties
    def test_add_vertex_multiple_properties(self):
        props = {"id": "p1", "name": "Bob", "email": "b@x.com"}
        with patch("graph_db.submit_with_retry") as mock_swr:
            add_vertex("Person", props)

        args = mock_swr.call_args[0]
        query, bindings = args[0], args[1]
        assert ".property('id', pval0)" in query
        assert ".property('name', pval1)" in query
        assert ".property('email', pval2)" in query
        assert bindings["vlabel"] == "Person"
        assert bindings["pval0"] == "p1"
        assert bindings["pval1"] == "Bob"
        assert bindings["pval2"] == "b@x.com"

    def test_add_vertex_empty_properties(self):
        with patch("graph_db.submit_with_retry") as mock_swr:
            add_vertex("EmptyLabel", {})
        query = mock_swr.call_args[0][0]
        assert query == "g.addV(vlabel)"

    def test_add_vertex_propagates_gremlin_error(self):
        with patch(
            "graph_db.submit_with_retry",
            side_effect=GremlinServerError("fail")
        ):
            with pytest.raises(GremlinServerError):
                add_vertex("Person", {"name": "X"})


# ===========================================================================
# TestAddEdge
# ===========================================================================

class TestAddEdge:
    def test_add_edge_correct_bindings(self):
        with patch("graph_db.submit_with_retry") as mock_swr:
            add_edge("p1", "d1", "AUTHORED")

        args = mock_swr.call_args[0]
        _, bindings = args[0], args[1]
        assert bindings["from_id"] == "p1"
        assert bindings["to_id"]   == "d1"
        assert bindings["rel"]     == "AUTHORED"

    def test_add_edge_query_shape(self):
        with patch("graph_db.submit_with_retry") as mock_swr:
            add_edge("a", "b", "COVERS")
        query = mock_swr.call_args[0][0]
        assert "addE(rel)" in query
        assert "from('a')" in query

    def test_add_edge_propagates_error(self):
        with patch(
            "graph_db.submit_with_retry",
            side_effect=GremlinServerError("edge fail")
        ):
            with pytest.raises(GremlinServerError):
                add_edge("x", "y", "RELATED")


# ===========================================================================
# TestVerifyData
# ===========================================================================

class TestVerifyData:
    def test_verify_data_prints_counts(self, capsys):
        # verify_data does submit_with_retry(...)[0], so each return value
        # must be a subscriptable list, not a bare int
        with patch("graph_db.submit_with_retry", side_effect=[[3], [10], [5], [42]]):
            verify_data()

        out = capsys.readouterr().out
        for expected in ("3", "10", "5", "42"):
            assert expected in out

    def test_verify_data_handles_error(self, capsys):
        with patch(
            "graph_db.submit_with_retry",
            side_effect=GremlinServerError("db down")
        ):
            verify_data()   # must not raise

        out = capsys.readouterr().out
        assert "ERROR" in out


# ===========================================================================
# TestFindExpertsByTopic  (v1, single topic)
# ===========================================================================

class TestFindExpertsByTopic:
    def _setup(self, props_list):
        """Patch submit to return a list of property dicts."""
        with patch("graph_db.submit", return_value=props_list) as mock_sub:
            result = find_experts_by_topic("Machine Learning", limit=5)
        return result, mock_sub

    def test_returns_expert_records(self):
        props = [_make_props(id="p1", name="Alice", email="a@b.com", department="R&D")]
        result, _ = self._setup(props)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["email"] == "a@b.com"
        assert result[0]["topic"] == "Machine Learning"

    def test_multiple_experts(self):
        props = [
            _make_props(id="p1", name="Alice", email="a@a.com", department="Eng"),
            _make_props(id="p2", name="Bob",   email="b@b.com", department="Sci"),
        ]
        result, _ = self._setup(props)
        assert len(result) == 2

    def test_empty_result(self):
        result, _ = self._setup([])
        assert result == []

    def test_bindings_include_topic_and_limit(self):
        with patch("graph_db.submit", return_value=[]) as mock_sub:
            find_experts_by_topic("NLP", limit=7)
        _, kwargs = mock_sub.call_args
        assert kwargs["bindings"]["topic_name"] == "NLP"
        assert kwargs["bindings"]["lim"] == 7

    def test_missing_properties_use_na(self):
        props = [{}]   # completely empty valueMap
        result, _ = self._setup(props)
        assert result[0]["name"] == "N/A"
        assert result[0]["person_id"] == "N/A"

    def test_gremlin_error_returns_empty(self):
        with patch("graph_db.submit", side_effect=GremlinServerError("err")):
            result = find_experts_by_topic("AI")
        assert result == []


# ===========================================================================
# TestFindExpertsByTopics  (v1, multi-topic)
# ===========================================================================

class TestFindExpertsByTopics:
    def _expert(self, pid, name, topic):
        return {"person_id": pid, "name": name, "email": f"{pid}@x.com",
                "department": "Eng", "topic": topic}

    def test_aggregates_across_topics(self):
        expert_a_ml = self._expert("p1", "Alice", "ML")
        expert_a_nlp = self._expert("p1", "Alice", "NLP")
        expert_b_ml  = self._expert("p2", "Bob",   "ML")

        def fake_find(topic, limit=10):
            if topic == "ML":
                return [expert_a_ml, expert_b_ml]
            if topic == "NLP":
                return [expert_a_nlp]
            return []

        with patch("graph_db.find_experts_by_topic", side_effect=fake_find):
            result = find_experts_by_topics(["ML", "NLP"], limit=10)

        # Alice covers 2 topics, Bob covers 1 → Alice ranks first
        assert result[0]["person_id"] == "p1"
        assert len(result[0]["topics"]) == 2

    def test_respects_limit(self):
        def fake_find(topic, limit=10):
            return [self._expert(f"p{i}", f"Person{i}", topic) for i in range(5)]

        with patch("graph_db.find_experts_by_topic", side_effect=fake_find):
            result = find_experts_by_topics(["ML"], limit=3)

        assert len(result) <= 3

    def test_empty_topic_list(self):
        result = find_experts_by_topics([])
        assert result == []


# ===========================================================================
# TestGetPersonDetails
# ===========================================================================

class TestGetPersonDetails:
    def test_returns_person_dict(self):
        props = _make_props(id="p1", name="Carol", email="c@c.com", department="Ops")
        vertex = _make_vertex(vid=42)
        with patch("graph_db.submit", return_value=[props]):
            result = _get_person_details_by_vertex(vertex)

        assert result["person_id"] == "p1"
        assert result["name"] == "Carol"

    def test_returns_none_when_no_result(self):
        vertex = _make_vertex()
        with patch("graph_db.submit", return_value=[]):
            result = _get_person_details_by_vertex(vertex)
        assert result is None

    def test_returns_none_on_gremlin_error(self):
        vertex = _make_vertex()
        with patch("graph_db.submit", side_effect=GremlinServerError("err")):
            result = _get_person_details_by_vertex(vertex)
        assert result is None

    def test_uses_vertex_id_in_query(self):
        vertex = _make_vertex(vid=99)
        with patch("graph_db.submit", return_value=[]) as mock_sub:
            _get_person_details_by_vertex(vertex)
        _, kwargs = mock_sub.call_args
        assert kwargs["bindings"]["vid"] == 99


# ===========================================================================
# TestFindExpertsByKnowledge  (v2, single topic)
# ===========================================================================

class TestFindExpertsByKnowledge:
    def _vertex_entry(self, vid, score):
        """Simulate one entry from groupCount().unfold()."""
        v = _make_vertex(vid)
        return {v: score}

    def test_returns_ranked_experts(self):
        v1, v2 = _make_vertex(1), _make_vertex(2)
        gremlin_result = [{v1: 5}, {v2: 2}]

        p1_props = _make_props(id="p1", name="Alice", email="a@a.com", department="AI")
        p2_props = _make_props(id="p2", name="Bob",   email="b@b.com", department="ML")

        def fake_submit(query, bindings=None):
            if "vid" in (bindings or {}):
                vid = bindings["vid"]
                return [p1_props] if vid == 1 else [p2_props]
            return gremlin_result

        with patch("graph_db.submit", side_effect=fake_submit):
            result = find_experts_by_knowledge("Deep Learning", limit=5)

        assert len(result) == 2
        assert result[0]["association_score"] == 5
        assert result[0]["name"] == "Alice"
        assert result[1]["association_score"] == 2

    def test_skips_unresolvable_vertex(self):
        v = _make_vertex(999)
        with patch("graph_db.submit", return_value=[{v: 3}]):
            with patch("graph_db._get_person_details_by_vertex", return_value=None):
                result = find_experts_by_knowledge("Topic")
        assert result == []

    def test_gremlin_error_returns_empty(self):
        with patch("graph_db.submit", side_effect=GremlinServerError("fail")):
            result = find_experts_by_knowledge("Topic")
        assert result == []

    def test_knowledge_topic_added_to_result(self):
        v = _make_vertex(1)
        props = _make_props(id="p1", name="X", email="x@x.com", department="Y")
        with patch("graph_db.submit", return_value=[{v: 1}]):
            with patch("graph_db._get_person_details_by_vertex", return_value={
                "person_id": "p1", "name": "X", "email": "x@x.com", "department": "Y"
            }):
                result = find_experts_by_knowledge("Graphs")
        assert result[0]["knowledge_topic"] == "Graphs"


# ===========================================================================
# TestFindExpertsByKnowledgeList  (v2, multi-topic)
# ===========================================================================

class TestFindExpertsByKnowledgeList:
    def _expert(self, pid, name, topic, score):
        return {
            "person_id": pid, "name": name,
            "email": f"{pid}@x.com", "department": "Eng",
            "association_score": score, "knowledge_topic": topic,
        }

    def test_accumulates_scores(self):
        a_ml  = self._expert("p1", "Alice", "ML",  10)
        a_nlp = self._expert("p1", "Alice", "NLP",  5)
        b_ml  = self._expert("p2", "Bob",   "ML",   8)

        def fake_find(topic, limit=10):
            return {"ML": [a_ml, b_ml], "NLP": [a_nlp]}.get(topic, [])

        with patch("graph_db.find_experts_by_knowledge", side_effect=fake_find):
            result = find_experts_by_knowledge_list(["ML", "NLP"], limit=10)

        alice = next(r for r in result if r["person_id"] == "p1")
        assert alice["association_score"] == 15   # 10 + 5
        assert "ML" in alice["knowledge_topics"]
        assert "NLP" in alice["knowledge_topics"]

    def test_sorted_by_score_descending(self):
        a = self._expert("p1", "Alice", "ML", 20)
        b = self._expert("p2", "Bob",   "ML",  5)

        with patch("graph_db.find_experts_by_knowledge", return_value=[a, b]):
            result = find_experts_by_knowledge_list(["ML"])

        assert result[0]["person_id"] == "p1"

    def test_respects_limit(self):
        experts = [self._expert(f"p{i}", f"P{i}", "ML", i) for i in range(10)]
        with patch("graph_db.find_experts_by_knowledge", return_value=experts):
            result = find_experts_by_knowledge_list(["ML"], limit=3)
        assert len(result) <= 3

    def test_empty_list(self):
        result = find_experts_by_knowledge_list([])
        assert result == []


# ===========================================================================
# TestDisplayExperts
# ===========================================================================

class TestDisplayExperts:
    def _expert(self, **kwargs):
        base = {
            "person_id": "p1", "name": "Alice",
            "email": "a@a.com", "department": "R&D",
        }
        base.update(kwargs)
        return base

    def test_prints_no_experts_message(self, capsys):
        display_experts([])
        assert "No experts found" in capsys.readouterr().out

    def test_prints_expert_name_and_email(self, capsys):
        display_experts([self._expert()])
        out = capsys.readouterr().out
        assert "Alice" in out
        assert "a@a.com" in out

    def test_prints_association_score_when_present(self, capsys):
        display_experts([self._expert(association_score=42)])
        assert "42" in capsys.readouterr().out

    def test_no_score_field_when_absent(self, capsys):
        display_experts([self._expert()])
        assert "Score" not in capsys.readouterr().out

    def test_single_topic_string(self, capsys):
        display_experts([self._expert(topic="NLP")])
        assert "NLP" in capsys.readouterr().out

    def test_topics_list(self, capsys):
        display_experts([self._expert(topics=["ML", "NLP", "CV"])])
        out = capsys.readouterr().out
        assert "ML" in out and "NLP" in out and "CV" in out

    def test_knowledge_topics_list(self, capsys):
        display_experts([self._expert(knowledge_topics=["Graphs", "Search"])])
        out = capsys.readouterr().out
        assert "Graphs" in out and "Search" in out

    def test_numbering_starts_at_1(self, capsys):
        display_experts([self._expert(), self._expert(person_id="p2", name="Bob")])
        out = capsys.readouterr().out
        assert "#1" in out
        assert "#2" in out

    def test_separator_lines_printed(self, capsys):
        display_experts([self._expert()])
        out = capsys.readouterr().out
        assert "=" * 10 in out   # header separator
        assert "-" * 10 in out   # row separator


# ===========================================================================
# Integration-style: constants and configuration
# ===========================================================================

class TestModuleConstants:
    def test_default_gremlin_server_url(self):
        assert graph_db.GREMLIN_SERVER == "ws://localhost:8182/gremlin"

    def test_max_retries_positive(self):
        assert graph_db.MAX_RETRIES >= 1