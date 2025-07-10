"""
Ingest local Git repository files, embed with OpenAI, and store in Chroma.

このモジュールは、指定したGitリポジトリ内のソースコードをチャンク化し、
OpenAI Embeddingsで埋め込みを生成してChromaベクターストアに保存する機能を提供します。
"""
import os
import pathlib
import git
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document
from .chunker import chunk_file
import tiktoken

def _recursive_split_page_content(text: str, encoder, max_tokens: int):
    # テキストを再帰的に分割し、各チャンクがmax_tokens以内になるようにする
    # Args:
    #     text (str): 分割対象のテキスト
    #     encoder: トークン化用のエンコーダ
    #     max_tokens (int): チャンクあたりの最大トークン数
    # Returns:
    #     List[str]: 分割されたテキストチャンクのリスト
    """Recursively split text into chunks so that each chunk has at most max_tokens tokens."""
    if len(encoder.encode(text)) <= max_tokens:
        return [text]
    mid = len(text) // 2
    left = text[:mid]
    right = text[mid:]
    return (_recursive_split_page_content(left, encoder, max_tokens)
            + _recursive_split_page_content(right, encoder, max_tokens))

def _split_document(doc: Document, encoder, max_tokens: int):
    # Documentをmax_tokens制限に基づいて分割し、新たなDocumentリストを生成する
    # Args:
    #     doc (Document): 分割対象のドキュメント
    #     encoder: トークン化用のエンコーダ
    #     max_tokens (int): チャンクあたりの最大トークン数
    # Returns:
    #     List[Document]: 分割後のドキュメントリスト
    """Split a Document into smaller Documents based on max_tokens per chunk."""
    chunks = _recursive_split_page_content(doc.page_content, encoder, max_tokens)
    docs = []
    for idx, chunk in enumerate(chunks):
        meta = doc.metadata.copy()
        meta['chunk_index'] = idx
        docs.append(Document(page_content=chunk, metadata=meta))
    return docs
load_dotenv()  # .envファイルから環境変数を読み込む
REPO_PATH = pathlib.Path(os.getenv('CODE_REPO_PATH', '.')).resolve()  # 対象Gitリポジトリのパス取得（デフォルトはカレントディレクトリ）
assert REPO_PATH.exists(), f"Repository path {REPO_PATH} does not exist"  # リポジトリパスの存在確認
print("[INFO] Using repository path:", REPO_PATH)

"""OpenAI埋め込みモデルおよびChroma設定"""
# OpenAI埋め込みモデルの初期化
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
try:
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", 1536))
except (TypeError, ValueError):
    print("[ERROR] EMBEDDING_DIMENSIONS must be an integer. Using default value 1536.")
    EMBEDDING_DIMENSIONS = 1536
embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSIONS)
print("[INFO] Using OpenAI Embeddings model:", EMBEDDING_MODEL + f" (dimensions: {EMBEDDING_DIMENSIONS})")
# 埋め込みAPIの1リクエストあたりの最大トークン数制限（OpenAI上限: 300,000トークン）
MAX_TOKENS_PER_BATCH = 300_000

# 対象ファイル拡張子リストを環境変数EXTENSIONSから取得・整形
exts_env = os.getenv("EXTENSIONS", "cpp")
EXTENSIONS = tuple(
    e if e.startswith('.') else f'.{e}'
    for e in (s.strip() for s in exts_env.split(',') if s.strip())
)
print(f"[INFO] EXTENSIONS: {EXTENSIONS}")

# Chromaベクターストアの初期化
CODE_INDEX_DIR = os.getenv("CODE_INDEX_DIR", "code_index")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "code_index")
db = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embedder,
    persist_directory=CODE_INDEX_DIR
)

def ingest():
    """
    リポジトリ内のソースコードファイルを検索し、チャンク化およびトークン制限に基づく分割を行い、
    Chromaベクターストアに埋め込みをバッチ追加する。

    環境変数:
        CODE_REPO_PATH (str): 対象のGitリポジトリパス
        EXTENSIONS (str): 対象ファイルの拡張子リスト（カンマ区切り）
    """
    # Gitリポジトリを開く
    repo = git.Repo(REPO_PATH)
    # 対象拡張子のファイルパスリストを取得
    files = [REPO_PATH / f for f in repo.git.ls_files().split('\n') if f.endswith(EXTENSIONS)]
    docs = []
    # 各ファイルをチャンク化し、Documentオブジェクトを生成
    for path in files:
        for code, start_line in chunk_file(path):
            metadata = {
                "file_path": str(path.relative_to(REPO_PATH)),
                "start_line": start_line,
            }
            docs.append(Document(page_content=code, metadata=metadata))
    # チャンク対象のファイルが存在しない場合は処理を終了
    if not docs:
        print("No files indexed.")
        return

    # tiktokenエンコーダを取得し、サイズ超過ドキュメントを再分割
    try:
        encoder = tiktoken.encoding_for_model(embedder.model)
    except Exception:
        encoder = tiktoken.get_encoding("cl100k_base")

    split_docs = []
    for doc in docs:
        tok_count = len(encoder.encode(doc.page_content))
        if tok_count > MAX_TOKENS_PER_BATCH:
            sub_docs = _split_document(doc, encoder, MAX_TOKENS_PER_BATCH)
            print(f"Splitting document {doc.metadata.get('file_path')} starting at line {doc.metadata.get('start_line')} into {len(sub_docs)} chunks")
            split_docs.extend(sub_docs)
        else:
            split_docs.append(doc)
    docs = split_docs

    # バッチのトークン合計数を監視し、埋め込みAPIの制限内で分割してChromaに追加
    batch, batch_tokens = [], 0
    for doc in docs:
        tok_count = len(encoder.encode(doc.page_content))
        if batch_tokens + tok_count > MAX_TOKENS_PER_BATCH and batch:
            db.add_documents(batch)
            batch, batch_tokens = [], 0
        batch.append(doc)
        batch_tokens += tok_count
    if batch:
        db.add_documents(batch)

    print(f"Indexed {len(docs)} chunks from {len(files)} files.")

if __name__ == "__main__":
    ingest()
