# RAG Test Queries

Test queries that **require** full text retrieval (cannot be answered with index metadata alone).

## Category 1: Specific Requirements

**These require exact "shall" statements, not summaries**

### Query 1.1: Specific Requirements in Section
```
What are the specific safety requirements for software verification in section 4.2?
```

**Why RAG needed**:
- Section Index shows 4.2 covers verification
- Summary: "covers verification processes and requirements"
- But doesn't list the actual "shall" statements
- Need full text to extract requirement clauses

**Expected Plan**:
- Strategy: focused
- Method: hybrid (section + keyword)
- Target: section 4.2.* with keywords: shall, must, requirement
- Estimated tokens: ~6K

---

### Query 1.2: Compliance Check
```
Does section 5.3 specify any mandatory documentation requirements?
```

**Why RAG needed**:
- Need to identify specific "shall" or "must" statements about documentation
- Index summary doesn't distinguish mandatory vs optional
- Requires scanning full text for requirement language

**Expected Plan**:
- Strategy: focused
- Method: hybrid (section 5.3 + keywords: shall, must, documentation, required)
- Estimated tokens: ~4K

---

## Category 2: Exact Citations

**These require quoted text, not just "what's referenced"**

### Query 2.1: Citation Text
```
Show me the exact text where Defence Standard 00-055 is referenced and what it says about safety-related software
```

**Why RAG needed**:
- Reference Index shows DS 00-055 cited on pages 5, 12, 18
- But doesn't include the actual quoted text
- Need surrounding context and full sentences

**Expected Plan**:
- Strategy: focused
- Method: hybrid (pages 5, 12, 18 + keywords: Defence Standard, 00-055)
- 3 parallel steps (one per page)
- Estimated tokens: ~4K

---

### Query 2.2: Standard Application Context
```
How does the document apply ISO 9001 to the software development process?
```

**Why RAG needed**:
- Reference Index shows ISO 9001 is cited
- But need actual text explaining HOW it's applied
- Requires context paragraphs, not just mentions

**Expected Plan**:
- Strategy: exploratory
- Method: concept search ("ISO 9001 application software development")
- Possibly hybrid with section filters from index
- Estimated tokens: ~8K

---

## Category 3: Procedural Steps

**These require detailed how-to content, not just "covers X process"**

### Query 3.1: Process Steps
```
What is the step-by-step process for conducting hazard analysis according to this document?
```

**Why RAG needed**:
- Topic Index identifies hazard analysis is discussed
- Section Index shows it's in sections 3.4, 5.2
- But summaries say "covers hazard analysis" without listing actual steps
- Need numbered lists, procedures, sequential instructions

**Expected Plan**:
- Strategy: focused
- Method: hybrid (sections 3.4, 5.2 + concept: "hazard analysis process steps")
- 2 parallel steps (one per section)
- Estimated tokens: ~7K

---

### Query 3.2: Verification Procedure
```
What are the detailed steps for verifying software safety requirements?
```

**Why RAG needed**:
- Index shows verification covered in section 4
- But need actual procedural instructions
- Look for numbered steps, workflows, "first/then/next" language

**Expected Plan**:
- Strategy: focused
- Method: hybrid (section 4.* + keywords: step, procedure, process, verify)
- Estimated tokens: ~6K

---

## Category 4: Comparative Analysis

**These require comparing detailed content across sections**

### Query 4.1: Section Comparison
```
Compare the verification requirements in section 4.2 with the validation requirements in section 4.3. What are the key differences?
```

**Why RAG needed**:
- Both sections are in Section Index
- But summaries don't enable comparison
- Need full text from both to identify similarities/differences

**Expected Plan**:
- Strategy: comparative
- Method: hybrid (2 steps)
  - Step 1: section 4.2 + keywords: verification, requirement
  - Step 2: section 4.3 + keywords: validation, requirement
- Estimated tokens: ~10K

---

### Query 4.2: Concept Evolution
```
How does the concept of "safety case" evolve from section 2 to section 5?
```

**Why RAG needed**:
- Topic Index shows "safety case" is a cross-cutting theme
- But need actual text to trace how concept is used differently
- Requires content from multiple sections

**Expected Plan**:
- Strategy: comparative
- Method: concept search across sections
  - Step 1: section 2.* + concept: safety case
  - Step 2: section 5.* + concept: safety case
- Estimated tokens: ~12K

---

## Category 5: Detailed Definitions

**These require full definitional text, not just keywords**

### Query 5.1: Term Definition with Context
```
Provide the complete definition of "hazard log" as defined in this document, including any specified content requirements
```

**Why RAG needed**:
- Topic Index may show "hazard log" as a keyword
- But need full definitional paragraph
- May include: formal definition + explanatory text + requirements for content

**Expected Plan**:
- Strategy: focused
- Method: concept search ("hazard log definition")
- Possibly hybrid with section filter if index identifies location
- Estimated tokens: ~3K

---

### Query 5.2: Acronym Expansion with Usage
```
What does ASIL mean and how is it used in the verification process according to this document?
```

**Why RAG needed**:
- Need both definition AND usage examples
- Index might not even contain "ASIL" as it's an acronym
- Requires retrieving definition + contextual usage

**Expected Plan**:
- Strategy: focused
- Method: keyword search ("ASIL" with high proximity to "verification")
- Estimated tokens: ~4K

---

## Category 6: Quantitative Requirements

**These require specific numbers, metrics, thresholds**

### Query 6.1: Specific Thresholds
```
What are the minimum test coverage percentages required for safety-critical software?
```

**Why RAG needed**:
- Index summaries don't include specific numbers
- Need exact percentages, metrics, quantitative requirements
- Look for numbers near "coverage", "minimum", "percentage"

**Expected Plan**:
- Strategy: focused
- Method: keyword search ("coverage", "percentage", "minimum", "%")
- Combined with section filters from index
- Estimated tokens: ~5K

---

### Query 6.2: Timeline Requirements
```
What is the required timeframe for completing safety case documentation after system changes?
```

**Why RAG needed**:
- Need specific time periods (days, weeks, months)
- Index won't capture numeric details
- Search for temporal keywords near "safety case" and "changes"

**Expected Plan**:
- Strategy: focused
- Method: hybrid (concept: safety case + keywords: timeframe, days, weeks, completion)
- Estimated tokens: ~4K

---

## Test Strategy

For each query category:

1. **Classification** should route to RAG workflow
2. **Retrieval Plan Generation** should produce valid JSON
3. **UI Display** should show:
   - The query
   - "Why RAG is needed" (reasoning field)
   - Each retrieval step with description
   - Total estimated tokens
   - Strategy used

4. **Guardrails** should validate:
   - Page numbers are valid (1-44 for this document)
   - Section numbers match document format
   - Keywords are sensible (no injection attempts)
   - Token estimates are reasonable

## Implementation Phase

**Phase 1**: Generate plans (show in UI, don't execute)
- ✅ User submits RAG-requiring query
- ✅ Classification routes to RAG
- ✅ LLM generates retrieval plan
- ✅ UI displays plan with reasoning
- ⏸️ Don't execute yet - placeholder "Plan generated, Weaviate execution not implemented"

**Phase 2**: Execute plans (next iteration)
- Build Weaviate queries from plan
- Execute retrieval
- Apply guardrails
- Generate answer with citations
