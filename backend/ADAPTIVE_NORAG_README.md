# Adaptive NoRAG System

## Overview

The Adaptive NoRAG system implements **intelligent, iterative index loading** for document queries. Instead of loading all suggested indices upfront, the system starts minimal and requests additional indices only when needed.

## Architecture

### File Structure

```
backend/scripts/services/
├── index_metadata.py          # Index capabilities & documentation
├── adaptive_norag_agent.py    # Adaptive loading logic
└── query_agent.py             # Query routing (uses adaptive agent)
```

### Key Components

#### 1. **Index Metadata** (`index_metadata.py`)

Defines what each index contains and when to use it:

- **Chapter Index** (~3.5K tokens): Top-level structure, chapter summaries
- **File Index** (~13.5K tokens): Query classification, content types, detailed section summaries
- **Topic Index** (~8K tokens): Key concepts, definitions, themes
- **Section Index** (~12K tokens): Detailed technical content, requirements
- **Reference Index** (~8K tokens): External standards, citations

#### 2. **Adaptive Agent** (`adaptive_norag_agent.py`)

Implements the iterative workflow:

1. Load initial indices (suggested by classification)
2. Build prompt with index capabilities documentation
3. LLM analyzes and either:
   - Provides answer ✅
   - Requests additional indices 🔄
4. If indices requested, load them and repeat (max 3 iterations)

#### 3. **Query Agent** (`query_agent.py`)

Routes queries and invokes the adaptive agent for NoRAG workflows.

## How It Works

### Example: "Summarise this document"

**Iteration 1:**
```
Classification → Load: index_chapter
LLM: "I have chapter-level summaries. I can answer!"
Result: Provides summary using 7 chapter nodes (~3.5K tokens)
```

### Example: "What topics relate to verification?"

**Iteration 1:**
```
Classification → Load: index_topic
LLM: "I see 'verification' mentioned in topics but need more detail"
REQUEST_INDICES: ["index_section"]
REASONING: "Topic Index shows verification is discussed, but Section Index
will provide detailed content about what verification covers"
```

**Iteration 2:**
```
Load: index_section (in addition to index_topic)
LLM: "Now I have both topic overview and section details"
Result: Comprehensive answer using both indices
```

### Example: "What external documents are referenced?"

**Iteration 1:**
```
Classification → Load: index_reference
LLM: "Reference Index contains all 31 external documents with summaries"
Result: Lists all references with page locations (~8K tokens)
```

## Benefits

### Token Efficiency
- ✅ Start with **minimum necessary** indices
- ✅ Load more **only when truly needed**
- ✅ Typical queries use **3.5K-13.5K tokens** instead of 25K+

### Intelligence
- ✅ LLM **understands index capabilities**
- ✅ Makes **informed decisions** about what to load
- ✅ Can **synthesize across indices** when needed
- ✅ Makes **inferences from metadata**

### Transparency
- ✅ **Iteration history** tracked and shown to user
- ✅ See **which indices were loaded** and **why**
- ✅ Understand **decision-making process**

## LLM Instructions

The adaptive agent instructs the LLM to:

### Use Metadata Intelligently
- Synthesize information from multiple nodes
- Draw logical conclusions from summaries and keywords
- Connect related concepts across sections
- Use scope information (pages, sections) to understand coverage

### Request Additional Indices When:
- Query asks about topics not covered in current metadata
- Specific details are needed that aren't in summaries
- Query spans domains not represented in current indices
- Additional context would significantly improve answer

### Don't Request When:
- Current metadata provides sufficient information
- Can make reasonable inferences from what's loaded
- Query is high-level or navigational
- Can synthesize answer from current nodes

## Configuration

### Max Iterations
Default: 3 iterations (set in `adaptive_norag_agent.py`)

```python
MAX_ITERATIONS = 3
```

### Index Sizes
Documented in `INDEX_CAPABILITIES` dict in `index_metadata.py`

## Monitoring

Check backend logs for adaptive behavior:

```bash
tail -f /private/tmp/worsley-backend.log | grep "Adaptive NoRAG"
```

Output shows:
```
[Adaptive NoRAG] Starting with indices: ['index_chapter']
[Adaptive NoRAG] Iteration 1/3
[Adaptive NoRAG] Currently loaded: ['index_chapter']
[Adaptive NoRAG] Requesting additional indices: ['index_topic']
[Adaptive NoRAG] Reasoning: Need topic definitions...
[Adaptive NoRAG] Loaded index_topic
[Adaptive NoRAG] Answer generated after 2 iteration(s)
```

## UI Display

The frontend shows:
- **Workflow type**: `norag_adaptive`
- **Iterations count**: e.g., "(2 iterations)"
- **Final indices used**: e.g., "index_chapter, index_topic"
- **Adaptive history** (collapsible): Shows iteration-by-iteration loading

## Future Enhancements

- [ ] Cost tracking per iteration
- [ ] Index caching across queries
- [ ] Parallel index loading when appropriate
- [ ] User preference for iteration depth
- [ ] Analytics on which indices are most commonly requested together
