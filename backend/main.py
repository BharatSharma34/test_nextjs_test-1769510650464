import json
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scripts.processing.chunk_document import chunk_document_file
from models import QERequest, QEResponse
from scripts.services.agent_logic import execute_qe_logic
from scripts.processing.advanced_chunking import perform_advanced_chunking
from scripts.generation.generate_all_derived import generate_all_derived_graphs, get_available_derived_graphs

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "inputs" / "Defence_Standard_00-056_Part_01.txt"
DEFAULT_REGEX = BASE_DIR / "inputs" / "regex.txt"
UPLOAD_DIR = BASE_DIR / "inputs" / "uploads"


class ChunkRequest(BaseModel):
    input_path: Optional[str] = None
    regex_path: Optional[str] = None
    output_path: Optional[str] = None
    document_name: Optional[str] = None


def read_default_regex() -> str:
    return DEFAULT_REGEX.read_text(encoding="utf-8").strip()


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Worsley"}


@app.post("/api/chunk")
async def chunk_document(request: Optional[ChunkRequest] = Body(default=None)):
    input_path = (request.input_path if request else None) or str(DEFAULT_INPUT)
    regex_path = (request.regex_path if request else None) or str(DEFAULT_REGEX)
    payload, output_path = chunk_document_file(
        input_path=input_path,
        regex_path=regex_path,
        output_path=request.output_path if request else None,
        document_name=request.document_name if request else None,
    )
    chunks = [
        {
            "page_index": page["page_index"],
            "page_number": page["page_number"],
            **({"page_label": page["page_label"]} if "page_label" in page else {}),
            "text": page["text"],
        }
        for page in payload["pages"]
    ]
    return {
        "status": "ok",
        "output_path": output_path,
        "pages": len(payload["pages"]),
        "chunks": chunks,
    }


@app.post("/api/chunk/upload")
async def chunk_document_upload(
    file: UploadFile = File(...),
    regex_path: Optional[str] = Form(default=None),
    regex_text: Optional[str] = Form(default=None),
    document_name: Optional[str] = Form(default=None),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    input_path = UPLOAD_DIR / safe_name

    contents = await file.read()
    input_path.write_bytes(contents)

    regex_source_path = regex_path or str(DEFAULT_REGEX)
    if regex_text and regex_text.strip():
        regex_source_path = str(UPLOAD_DIR / f"{safe_name}.regex.txt")
        Path(regex_source_path).write_text(regex_text.strip(), encoding="utf-8")

    payload, output_path = chunk_document_file(
        input_path=str(input_path),
        regex_path=regex_source_path,
        output_path=None,
        document_name=document_name or safe_name,
    )
    chunks = [
        {
            "page_index": page["page_index"],
            "page_number": page["page_number"],
            **({"page_label": page["page_label"]} if "page_label" in page else {}),
            "text": page["text"],
        }
        for page in payload["pages"]
    ]
    return {
        "status": "ok",
        "input_path": str(input_path),
        "output_path": output_path,
        "pages": len(payload["pages"]),
        "chunks": chunks,
    }


@app.get("/api/regex")
async def get_default_regex():
    return {"regex": read_default_regex()}


@app.get("/api/prompts")
async def list_prompts():
    """List master graph prompts (starting with 'main_')"""
    prompt_dir = BASE_DIR / "inputs" / "promtps"
    if not prompt_dir.exists():
        return {"prompts": []}
    files = [f.name for f in prompt_dir.iterdir()
             if f.is_file() and f.suffix == ".txt" and f.name.startswith("main_")]
    return {"prompts": files}


@app.get("/api/derived-graphs")
async def list_derived_graphs():
    """List available derived graph types with descriptions"""
    return {"graphs": get_available_derived_graphs()}


@app.post("/api/chunk/advanced")
async def chunk_advanced(
    document_name: str = Form(...),
    prompt_filename: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    # If a file is uploaded, save it, otherwise use default
    if file:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename).name
        input_path = UPLOAD_DIR / safe_name
        contents = await file.read()
        input_path.write_bytes(contents)
    else:
        input_path = DEFAULT_INPUT
    
    prompt_path = BASE_DIR / "inputs" / "promtps" / prompt_filename
    if not prompt_path.exists():
        return {"status": "error", "message": "Prompt not found"}

    results = await perform_advanced_chunking(
        input_path=str(input_path),
        prompt_path=str(prompt_path),
        document_name=document_name
    )
    
    return {
        "status": "ok",
        "mermaid": results.get("mermaid", ""),
        "json": results.get("json", {})
    }


@app.get("/api/chunk/advanced/results")
async def get_advanced_results(document_name: str, file_name: Optional[str] = "master"):
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    output_dir = BASE_DIR / "outputs" / safe_doc_name

    # Determine which file to fetch (master or page_X)
    file_base = file_name if file_name else "master"

    mermaid_path = output_dir / "mermaid" / f"{file_base}.mermaid"
    json_path = output_dir / "json" / f"{file_base}.json"

    result = {"status": "ok", "mermaid": None, "json": None}

    if mermaid_path.exists():
        result["mermaid"] = mermaid_path.read_text(encoding="utf-8")

    if json_path.exists():
        try:
            result["json"] = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return result


@app.get("/api/chunk/advanced/files")
async def list_advanced_files(document_name: str):
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    output_dir = BASE_DIR / "outputs" / safe_doc_name
    mermaid_dir = output_dir / "mermaid"

    if not mermaid_dir.exists():
        return {"status": "ok", "files": []}

    # Get all page files and sort them naturally
    import re
    def natural_sort_key(filename):
        nums = re.findall(r'\d+', filename)
        return int(nums[0]) if nums else 0

    page_files = [
        f.stem for f in mermaid_dir.iterdir()
        if f.is_file() and f.stem.startswith("page_") and f.suffix == ".mermaid"
    ]
    page_files.sort(key=natural_sort_key)

    # Build files list: master, then specialized graphs (if exist), then pages
    files = ["master"]

    # Check for specialized graph files (derived graphs use "index_" prefix)
    specialized_graphs = [
        "index_file",
        "index_chapter",
        "index_reference",
        "index_section",
        "index_topic"
    ]

    for graph_name in specialized_graphs:
        graph_path = mermaid_dir / f"{graph_name}.mermaid"
        if graph_path.exists():
            files.append(graph_name)

    files.extend(page_files)

    return {"status": "ok", "files": files}


class DerivedGraphRequest(BaseModel):
    document_name: str
    selected_types: Optional[list] = None


@app.post("/api/chunk/advanced/generate-derived")
async def generate_derived(request: DerivedGraphRequest):
    """
    Generate selected derived graphs from the master graph.
    Returns token usage statistics.

    Args:
        document_name: Name of the document
        selected_types: Optional list of graph types to generate. If None, generates all.
    """
    result = generate_all_derived_graphs(
        document_name=request.document_name,
        selected_types=request.selected_types
    )
    return result


@app.post("/api/qe", response_model=QEResponse)
async def query_expansion(request: QERequest):
    """
    Agentic process for Graph Selection and Decision Gate.
    """
    return execute_qe_logic(request)


# Query Classification and Workflow Endpoints

class QueryClassificationRequest(BaseModel):
    user_query: str
    document_name: str
    chat_history: list
    available_indices: list


class NoRAGRequest(BaseModel):
    normalized_query: str
    document_name: str
    suggested_indices: list
    chat_history: list


class RAGRequest(BaseModel):
    normalized_query: str
    document_name: str
    suggested_indices: list
    chat_history: list


@app.post("/api/query/classify")
async def classify_query(request: QueryClassificationRequest):
    """
    Step 1: Classify and normalize the user query.
    Returns classification with workflow determination (RAG vs NoRAG).
    """
    from scripts.services.query_agent import classify_user_query

    result = classify_user_query(
        user_query=request.user_query,
        document_name=request.document_name,
        chat_history=request.chat_history,
        available_indices=request.available_indices
    )
    return result


@app.post("/api/query/norag")
async def norag_workflow(request: NoRAGRequest):
    """
    Step 2a: NoRAG workflow - answer query using index graphs only.
    """
    from scripts.services.query_agent import execute_norag_workflow

    result = execute_norag_workflow(
        normalized_query=request.normalized_query,
        document_name=request.document_name,
        suggested_indices=request.suggested_indices,
        chat_history=request.chat_history
    )
    return result


@app.post("/api/query/rag")
async def rag_workflow(request: RAGRequest):
    """
    Step 2b: RAG workflow - generate retrieval plan and answer with Weaviate.
    """
    from scripts.services.query_agent import execute_rag_workflow

    result = execute_rag_workflow(
        normalized_query=request.normalized_query,
        document_name=request.document_name,
        suggested_indices=request.suggested_indices,
        chat_history=request.chat_history
    )
    return result