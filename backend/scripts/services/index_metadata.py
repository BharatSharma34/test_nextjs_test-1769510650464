"""
Index Metadata and Capabilities

Defines what each index type contains and when to use it.
Helps the LLM make intelligent decisions about which indices to load.
"""

INDEX_CAPABILITIES = {
    "index_chapter": {
        "name": "Chapter Index",
        "node_count": "~7 nodes",
        "token_size": "~3,500 tokens",
        "description": "Top-level chapter structure of the document",
        "contains": [
            "Chapter titles and numbers",
            "1-2 sentence summaries per chapter",
            "Page ranges for each chapter",
            "3-5 keywords per chapter",
            "High-level document organization"
        ],
        "best_for": [
            "Document overview queries",
            "Understanding overall structure",
            "High-level navigation",
            "Broad topic identification",
            "Chapter-level summaries"
        ],
        "examples": [
            "What is this document about?",
            "Summarize the document structure",
            "What chapters are included?"
        ]
    },

    "index_file": {
        "name": "Query Classification Index (File Index)",
        "node_count": "~25-40 nodes",
        "token_size": "~13,500 tokens",
        "description": "Comprehensive section-level index for query routing",
        "contains": [
            "All major sections and subsections",
            "2-3 sentence summaries per section (detailed)",
            "5-7 keywords per section",
            "Content type classification (definitional, procedural, requirements, etc.)",
            "Page ranges and section numbers",
            "Routing guidance for detailed queries"
        ],
        "best_for": [
            "Understanding what topics are covered",
            "Section purpose and content classification",
            "Identifying which sections discuss specific topics",
            "Content type analysis (procedures vs requirements vs definitions)",
            "Query routing decisions"
        ],
        "examples": [
            "Which sections cover safety requirements?",
            "What types of content does this document include?",
            "Where can I find procedural guidance?"
        ]
    },

    "index_topic": {
        "name": "Topic Index",
        "node_count": "~30-50 nodes",
        "token_size": "~8,000 tokens",
        "description": "Key concepts, themes, and topics across the document",
        "contains": [
            "Major topics and concepts",
            "Topic definitions and explanations",
            "Cross-cutting themes (appear in multiple sections)",
            "Topic relationships and dependencies",
            "Pages where each topic is discussed",
            "Related concepts and terminology"
        ],
        "best_for": [
            "Conceptual queries and definitions",
            "Understanding key themes",
            "Topic exploration",
            "Thematic analysis across sections",
            "Finding related concepts",
            "Terminology and glossary-type queries"
        ],
        "examples": [
            "What is hazard analysis?",
            "Define safety case",
            "What topics are related to verification?",
            "Explain the key concepts in this document"
        ]
    },

    "index_section": {
        "name": "Section Index",
        "node_count": "~61 nodes",
        "token_size": "~12,000 tokens",
        "description": "Detailed section-level navigation and content",
        "contains": [
            "All substantive sections and subsections",
            "Detailed technical content descriptions",
            "Requirements and guidelines per section",
            "Section relationships and dependencies",
            "Technical terminology and processes",
            "Page ranges and section hierarchies"
        ],
        "best_for": [
            "Specific section content queries",
            "Technical details and specifications",
            "Understanding section scope and boundaries",
            "Requirements identification",
            "Detailed procedural content",
            "Section-to-section relationships"
        ],
        "examples": [
            "What does section 2.3 cover?",
            "What are the requirements in the verification section?",
            "How does section 4.1 relate to 4.2?"
        ]
    },

    "index_reference": {
        "name": "Reference Index",
        "node_count": "~31 nodes",
        "token_size": "~8,000 tokens",
        "description": "All external standards, regulations, and citations",
        "contains": [
            "External document titles and identifiers",
            "Reference summaries and purposes",
            "Pages where each reference is cited",
            "Sections that reference external documents",
            "Citation frequency and context",
            "Related standards and dependencies"
        ],
        "best_for": [
            "External document identification",
            "Citation mapping",
            "Finding which standards are referenced",
            "Understanding external dependencies",
            "Cross-referencing with other standards"
        ],
        "examples": [
            "What external documents are referenced?",
            "List all standards cited",
            "Where is ISO 9001 referenced?",
            "What Defence Standards are mentioned?"
        ]
    }
}


def get_index_description(index_type: str) -> str:
    """Get human-readable description of an index type."""
    if index_type in INDEX_CAPABILITIES:
        cap = INDEX_CAPABILITIES[index_type]
        return f"{cap['name']} ({cap['node_count']}, {cap['token_size']}): {cap['description']}"
    return f"Unknown index type: {index_type}"


def format_capabilities_for_prompt() -> str:
    """
    Format index capabilities as a prompt section for the LLM.
    This helps the LLM understand what each index contains and when to request it.
    """
    sections = []

    sections.append("=" * 80)
    sections.append("AVAILABLE INDEX TYPES AND CAPABILITIES")
    sections.append("=" * 80)
    sections.append("")

    for index_type, cap in INDEX_CAPABILITIES.items():
        sections.append(f"### {cap['name']} (`{index_type}`)")
        sections.append(f"Size: {cap['node_count']}, {cap['token_size']}")
        sections.append(f"Description: {cap['description']}")
        sections.append("")

        sections.append("Contains:")
        for item in cap['contains']:
            sections.append(f"  - {item}")
        sections.append("")

        sections.append("Best for:")
        for use_case in cap['best_for']:
            sections.append(f"  - {use_case}")
        sections.append("")

        sections.append("Example queries:")
        for example in cap['examples']:
            sections.append(f'  - "{example}"')
        sections.append("")
        sections.append("-" * 80)
        sections.append("")

    return "\n".join(sections)


def get_recommended_indices(query_type: str) -> list:
    """
    Get recommended starting indices based on query type.
    These are just suggestions - the adaptive agent can request more.
    """
    recommendations = {
        "high-level-overview": ["index_chapter"],
        "section-navigation": ["index_section"],
        "conceptual": ["index_topic"],
        "specific-requirement": ["index_section", "index_topic"],
        "cross-reference": ["index_reference"],
        "procedural": ["index_section"],
        "comparative": ["index_topic", "index_section"]
    }

    return recommendations.get(query_type, ["index_chapter"])
