import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add SDK path
SDK_PATH = Path("/Users/jd/Development/Barkley/tapestry_sdk_python")
sys.path.append(str(SDK_PATH))

from tapestrysdk import fetch_documents

def test_token():
    load_dotenv("/Users/jd/Development/Barkley/worsley-1769261842505/.env", override=True)
    token = os.getenv("TAPESTRY_TOKEN")
    tapestry_id = int(os.getenv("TAPESTRY_ID", 0))
    user_id = int(os.getenv("USER_ID", 0))
    
    print(f"Testing token for user {user_id} on tapestry {tapestry_id}...")
    res = fetch_documents(token, tapestry_id, user_id)
    print(f"Result: {res}")

if __name__ == "__main__":
    test_token()
