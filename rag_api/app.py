"""
FastAPI app providing a simple RAG endpoint.

このモジュールは、FastAPIを利用して簡易的なRAG (Retrieval-Augmented Generation) エンドポイント(/ask)を提供します。
"""
from fastapi import FastAPI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import os

load_dotenv()  # .envファイルから環境変数を読み込む

# FastAPIアプリケーションの初期化
app = FastAPI(title="Sample RAG API")

# 埋め込みモデル(OpenAIEmbeddings)の初期化
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
try:
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", 1536))
except (TypeError, ValueError):
    print("[ERROR] EMBEDDING_DIMENSIONS must be an integer. Using default value 1536.")
    EMBEDDING_DIMENSIONS = 1536
embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSIONS)
print("[INFO] Using OpenAI Embeddings model:", EMBEDDING_MODEL + f" (dimensions: {EMBEDDING_DIMENSIONS})")

# Chromaベクターストアの読み込み
CODE_INDEX_DIR = os.getenv("CODE_INDEX_DIR", "code_index")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "code_index")
db = Chroma(collection_name=COLLECTION_NAME, embedding_function=embedder, persist_directory=CODE_INDEX_DIR)
# ベクトル検索用retrieverを取得 (上位k件を返す)
retriever = db.as_retriever(search_kwargs={"k": 200})
# LLM(ChatOpenAI)の初期化
llm = ChatOpenAI(model="gpt-4.1", temperature=0.2)
# RetrievalQAチェーンの構築
qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

@app.post("/ask")
def ask(question: str):
    """
    質問を受け取り、RetrievalQAチェーンを実行して応答結果を返すエンドポイント。

    Args:
        question (str): ユーザーからの問い合わせクエリ

    Returns:
        dict: チェーンの返答結果を含む辞書
    """
    # QAチェーンを実行して結果を取得
    result = qa_chain({"query": question})
    return result
