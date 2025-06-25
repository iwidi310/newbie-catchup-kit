"""
FastAPI app providing a simple RAG endpoint.

このモジュールは、FastAPIを利用して簡易的なRAG (Retrieval-Augmented Generation) エンドポイント(/ask)を提供します。
"""
from fastapi import FastAPI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA

# FastAPIアプリケーションの初期化
app = FastAPI(title="Sample RAG API")

# 埋め込みモデル(OpenAIEmbeddings)の初期化
embedder = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1536)

# Chromaベクターストアの読み込み
db = Chroma(collection_name="code_index", embedding_function=embedder, persist_directory="code_index")
# ベクトル検索用retrieverを取得 (上位k件を返す)
retriever = db.as_retriever(search_kwargs={"k": 8})
# LLM(ChatOpenAI)の初期化
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
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
