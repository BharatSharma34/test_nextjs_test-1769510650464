import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add SDK path
SDK_PATH = Path("/Users/jd/Development/Barkley/tapestry_sdk_python")
sys.path.append(str(SDK_PATH))

from tapestrysdk import ask_ai_question

def test_ask():
    load_dotenv("/Users/jd/Development/Barkley/worsley-1769261842505/.env", override=True)
    token = os.getenv("TAPESTRY_TOKEN")
    tapestry_id = int(os.getenv("TAPESTRY_ID", 0))
    
    print(f"Testing ask_ai_question with group_ids=[49]...")
    res = ask_ai_question(
        token=token, 
        question="Hello, summarize the document.", 
        tapestry_id=tapestry_id,
        group_ids=[49], 
        document_name="DEFSTAN 00-056 Pt1.pdf",
        ai_type="internal_document_search"
    )
    print(f"Result: {res}")

if __name__ == "__main__":
    test_ask()
