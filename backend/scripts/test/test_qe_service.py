import json
import requests

def test_qe_logic():
    url = "http://localhost:8000/api/qe"
    
    # Example 1: Index query (Summary)
    payload_index = {
        "user_query": "Please summarise this document for me",
        "graphs": {
            "file_index_graph": {"nodes": [], "edges": []}
        },
        "context": {"project": "Test Project"}
    }
    
    # Example 2: Retrieval query (Specific)
    payload_retrieval = {
        "user_query": "What are the safety requirements in section 4?",
        "graphs": {
            "topic_retrieval_graph": {"nodes": [], "edges": []}
        },
        "context": {"project": "Test Project"}
    }

    print("Testing Index Query (Summary)...")
    try:
        response = requests.post(url, json=payload_index)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting Retrieval Query (Specific)...")
    try:
        response = requests.post(url, json=payload_retrieval)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_qe_logic()
