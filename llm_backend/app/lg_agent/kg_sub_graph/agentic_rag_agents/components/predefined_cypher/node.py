from typing import Any, Callable, Coroutine, Dict, List

from langchain_neo4j import Neo4jGraph
from langchain_core.language_models import BaseChatModel

from app.lg_agent.kg_sub_graph.agentic_rag_agents.constants import NO_CYPHER_RESULTS
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.state import PredefinedCypherInputState
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.text2cypher.state import CypherOutputState
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.utils import create_vector_query_matcher
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.descriptions import QUERY_DESCRIPTIONS


def create_predefined_cypher_node(
    graph: Neo4jGraph, predefined_cypher_dict: Dict[str, str]
) -> Callable[
    [PredefinedCypherInputState],
    Coroutine[Any, Any, Dict[str, List[CypherOutputState] | List[str]]],
]:
    """
    Create a predefined Cypher execution node for a LangGraph workflow.

    Parameters
    ----------
    graph : Neo4jGraph
        The Neo4j graph wrapper.
    predefined_cypher_dict : Dict[str, str]
        A Python dictionary with Cypher query names as keys and parameterized Cypher queries as values.

    Returns
    -------
    Callable[[PredefinedCypherInputState], Dict[str, List[CypherOutputState] | List[str]]]
        The LangGraph node named `predefined_cypher`.
    """
    async def predefined_cypher(
        state: PredefinedCypherInputState,
    ) -> Dict[str, List[CypherOutputState] | List[str]]:
        """
        Executes a predefined Cypher statement with found parameters.
        """
        errors = list()

        statement_name = state.get("query_name", "")
        params = state.get(
            "query_parameters", dict()
        )  
        print("statement_name", statement_name)
        print("params", params)
        
        # 将parameters中的每个值转换为字符串；LLM 可能把参数键写成 "$product_name"（带占位符前缀），需去掉 $ 使其与 Cypher 参数名匹配
        parameters = {k.lstrip("$"): str(v) for k, v in params.get("parameters", {}).items()}
        
        statement = predefined_cypher_dict.get(params.get("query"))
        print("statement", statement)
        if statement is not None:
            try:
                records = graph.query(query=statement, params=parameters)
            except Exception as e:
                # 缺参或查询执行失败时记录错误，交给 summarize 节点兜底，避免异常中断整个请求流
                errors.append(f"Failed to execute predefined Cypher `{params.get('query')}`: {e}")
                records = NO_CYPHER_RESULTS
            print(f"records: {records}")
            
        else:
            errors.append(
                f"Unable to find the specified Cypher statement: {statement_name}"
            )
            records = list()

        return {
            "cyphers": [
                CypherOutputState(
                    **{
                        "task": state.get("task", ""),
                        "statement": statement or "",
                        "parameters": params,
                        "errors": errors,
                        "records": records or NO_CYPHER_RESULTS,
                        "steps": ["execute_predefined_cypher"],
                    }
                )
            ],
            "steps": ["execute_predefined_cypher"],
        }

    return predefined_cypher
