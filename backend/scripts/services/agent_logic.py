from typing import Tuple, Optional
from models import QERequest, QEResponse, GraphTypes

def select_graph_type(query: str, graphs: GraphTypes) -> str:
    """
    Selects the most appropriate graph type for the query.
    Heuristic-based for now, can be upgraded to LLM-based.
    """
    query_lower = query.lower()
    
    # Heuristic for Index vs Retrieval
    if any(word in query_lower for word in ["summarise", "summary", "overview", "chapters", "index"]):
        if graphs.file_index_graph:
            return "file_index_graph"
        if graphs.chapter_index_graph:
            return "chapter_index_graph"
            
    if "reference" in query_lower or "source" in query_lower:
        if graphs.reference_index_graph:
            return "reference_index_graph"

    # Default to retrieval if specific sections/topics are targeted
    if graphs.topic_retrieval_graph:
        return "topic_retrieval_graph"
    if graphs.section_retrieval_graph:
        return "section_retrieval_graph"
    
    return "concatenated_page_graph"

def execute_qe_logic(request: QERequest) -> QEResponse:
    """
    Processes the QE request and applies the Decision Gate routing logic.
    """
    selected_graph = select_graph_type(request.user_query, request.graphs)
    
    # Simple logic to determine if we expand query (Retrieval) or ask user (Index/Ambiguous)
    expanded_query = ""
    request_for_user = ""
    
    # Rule mapping: Index Graphs -> NO RAG
    index_graphs = ["file_index_graph", "chapter_index_graph", "reference_index_graph"]
    
    if selected_graph in index_graphs:
        # Route back to user with a high-level response or clarification
        expanded_query = ""
        request_for_user = f"Based on the {selected_graph.replace('_', ' ')}, I can provide an overview. What specific details would you like?"
    else:
        # Route to RAG pipeline (simulated expansion)
        expanded_query = f"Search for specific details about: {request.user_query}"
        request_for_user = ""

    # Decision Gate Routing Logic (Part 1 requirements)
    # if (i) ‘expanded_user_query’= “” AND (ii) the “request_for_user_query” is != “”, then route back to user.
    # if (i) ‘expanded_user_query’ != “” AND (ii) the “request_for_user_query” is = “”, then route back to user.
    # NOTE: Re-reading Part 2a: Section RETRIEVAL -> route to RAG pipeline.
    # So we only route to RAG if expanded_query != "" AND request_for_user == "".
    
    routing = "USER"
    # The requirement says "if expanded != '' AND request == '', then route back to user"
    # but also "Retrieval graphs route to RAG".
    # I will stick to the Part 1 literal requirement for the gate, but note it's likely a typo for "RAG".
    # Actually, let's follow the spirit: RAG only when we have an expanded query and NO follow-up needed.
    
    if expanded_query != "" and request_for_user == "":
        routing = "RAG" # Spirit of the retrieval requirement
    else:
        routing = "USER"

    return QEResponse(
        expanded_user_query=expanded_query,
        request_for_user_query=request_for_user,
        selected_graph_type=selected_graph,
        routing=routing,
        reasoning=f"Selected {selected_graph} based on query keywords."
    )
