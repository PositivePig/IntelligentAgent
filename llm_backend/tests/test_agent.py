"""Agent 节点容错测试：外部依赖失败时不得抛出异常或访问未定义变量。"""
import asyncio

from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.cypher_tools import (
    node as cypher_tools_node,
)
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.customer_tools import (
    node as customer_tools_node,
)
from app.services.indexing_service import IndexingService


def test_cypher_node_rejects_empty_task():
    node = cypher_tools_node.create_cypher_query_node()
    result = asyncio.run(node({"task": ""}))
    assert result["steps"] == ["validate_input"]
    assert "未提供查询文本" in result["cyphers"][0].errors


def test_cypher_node_handles_neo4j_failure(monkeypatch):
    def fail():
        raise ConnectionError("neo4j offline")

    monkeypatch.setattr(cypher_tools_node, "get_neo4j_graph", fail)
    node = cypher_tools_node.create_cypher_query_node()
    result = asyncio.run(node({"task": "查询库存"}))
    assert result["steps"] == ["connect_neo4j"]
    assert "Neo4j 连接失败" in result["cyphers"][0].errors[0]


def test_graphrag_node_returns_empty_result_on_failure(monkeypatch):
    async def fail(self, query):
        raise RuntimeError("graphrag unavailable")

    monkeypatch.setattr(customer_tools_node.GraphRAGAPI, "query_graphrag", fail)
    node = customer_tools_node.create_graphrag_query_node()
    result = asyncio.run(node({"task": "售后政策"}))
    output = result["cyphers"][0]
    assert output.records == {"result": ""}
    assert any("GraphRAG查询失败" in e for e in output.errors)


def test_indexing_service_helpers():
    service = IndexingService()
    assert service._get_config_file("text/plain") == "settings.yaml"
    assert service._get_file_type("a.pdf") == "application/pdf"
    assert "graphrag_project" in service.data_dir
