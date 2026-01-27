# Run Locally

This guide walks you through running the backend and frontend locally.

## Prerequisites
- git
- Python 3.12+
- Node.js 18.17+ (use `nvm` if you have it)
- `npm`

## Git clone
git clone https://github.com/BharatSharma34/worsley-1769261842505.git

## Git push branch
- Edit the .env file and update the BRANCH and token variables.
- Run `source .env && git push https://${GITHUB_TOKEN}@github.com/BharatSharma34/test_nextjs_test-1769510650464.git ${BRANCH}`


## 1) Backend (FastAPI)

From the repo root:

1. Setup Python virtual environment:
   - `cd backend`
   - `python3 -m venv venv`
   - Activate the environment:
     - Mac/Linux: `source venv/bin/activate`
     - Windows: `venv\Scripts\activate`

2. Install Python dependencies:
   - `python3 -m pip install -r requirements.txt`

3. Start the backend:
   - `python3 -m uvicorn main:app --reload --port 8000`

4. Verify it is running:
   - Open `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

## 2) Frontend (Next.js)

From the repo root:

1. Ensure Node 18 is active:
   - `nvm install 18`
   - `nvm use 18`
   - `node -v`

2. Install frontend dependencies:
   - `cd frontend`
   - `npm install`

3. Start the frontend:
   - `NEXT_PUBLIC_API_BASE_URL="http://localhost:8000/api" npm run dev`

4. Open the UI:
   - `http://localhost:3000/apps/worsley-1769261842505`

## 3) Using the UI

- Click **Chunk document** to chunk the default source file.
- To upload a `.txt` file, use **Choose file** and then **Upload and chunk**.
- The chunk output appears in a copyable text box.

## 4) Output files

The chunker writes JSON output to:

- Default file: `backend/inputs/Defence_Standard_00-056_Part_01.chunked.json`
- Uploaded files: `backend/inputs/uploads/<filename>.chunked.json`

## 5) Common issues

### 422 error on chunking
If you see `422 Unprocessable Entity` or form upload errors, re-install backend deps:

- `python3 -m pip install -r backend/requirements.txt`

### `python-multipart` missing
File uploads require `python-multipart`. It is already listed in `backend/requirements.txt`.

### `next: command not found`
Run `npm install` in the `frontend` folder and ensure Node 18+ is active.

hello Jon