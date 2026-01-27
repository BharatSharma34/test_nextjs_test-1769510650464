from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class GraphTypes(BaseModel):
    concatenated_page_graph: Optional[Dict[str, Any]] = Field(None, description="The one big graph we have now")
    file_index_graph: Optional[Dict[str, Any]] = Field(None, description="Summary hierarchy, chapter, section, topic info")
    chapter_index_graph: Optional[Dict[str, Any]] = Field(None, description="Major components for navigation")
    section_retrieval_graph: Optional[Dict[str, Any]] = Field(None, description="High-level retrieval graph for query expansion")
    topic_retrieval_graph: Optional[Dict[str, Any]] = Field(None, description="Lower-level retrieval graph for query expansion")
    reference_index_graph: Optional[Dict[str, Any]] = Field(None, description="External references per page or section")

class QueryContext(BaseModel):
    project: Optional[str] = None
    user_roles: List[str] = Field(default_factory=list)
    chat_history: List[Dict[str, str]] = Field(default_factory=list)

class QERequest(BaseModel):
    user_query: str
    graphs: GraphTypes
    context: Optional[QueryContext] = None

class QEResponse(BaseModel):
    expanded_user_query: str = ""
    request_for_user_query: str = ""
    selected_graph_type: Optional[str] = None
    routing: str = Field(..., description="EITHER 'RAG' OR 'USER'")
    reasoning: Optional[str] = None
