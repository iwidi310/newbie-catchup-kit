"""
Chunker using pre-built grammars from tree_sitter_languages (Python only).

このモジュールは、tree_sitterを利用してPythonソースコードを関数定義やクラス定義単位でチャンク化し、
解析や埋め込み処理に適したテキストチャンクを生成します。
"""

import codecs
import pathlib
from tree_sitter import Parser
from tree_sitter_languages import get_language

parser = Parser()
parser.set_language(get_language("python"))

def _decode_bytes(b: bytes) -> str:
    # 与えられたバイト列を複数の文字コードでデコードし、UnicodeDecodeError発生時は順次他のエンコーディングを試行。
    # 最終手段では不明バイトを置換文字にしてデコードします。
    """decode with utf-8 → cp932 → latin-1 → fallback"""
    for enc in ("euc_jp", "utf-8", "cp932", "shift_jis", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最後の手段：未知バイトは�に置換
    return b.decode("utf-8", errors="replace")

def chunk_file(file_path: pathlib.Path):
    """
    Pythonソースファイルを読み込み、関数定義およびクラス定義ごとにチャンクを生成する。

    Args:
        file_path (pathlib.Path): チャンク対象のPythonソースファイルのパス

    Yields:
        Tuple[str, int]: チャンク化されたソースコード文字列とその開始行番号
    """
    source = file_path.read_bytes()
    tree   = parser.parse(source)
    root   = tree.root_node

    yielded = False
    for n in root.children:
        if n.type in {"function_definition", "class_definition"}:
            yielded = True
            start = n.start_point[0] + 1
            yield _decode_bytes(source[n.start_byte:n.end_byte]), start
    if not yielded:
        # 関数定義やクラス定義が見つからない場合はファイル全体を1チャンクとして返す
        yield _decode_bytes(source), 1