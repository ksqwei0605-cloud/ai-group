from __future__ import annotations
import os
import sys

TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".vue",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb",
    ".php", ".swift", ".kt", ".scala", ".r", ".m", ".mm",
    ".json", ".yaml", ".yml", ".xml", ".html", ".css", ".scss", ".less",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".sql", ".log", ".csv", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".gitignore", ".dockerfile", ".makefile", ".cmake",
    ".tex", ".rst", ".org", ".wiki",
}

MAX_FILE_SIZE = 500 * 1024  # 500KB


def read_file(filepath: str) -> tuple[bool, str, str]:
    """Read a local file and return (success, filename, content_or_error)."""
    path = os.path.expanduser(filepath.strip())

    if not os.path.isabs(path):
        path = os.path.abspath(path)

    if not os.path.exists(path):
        return False, os.path.basename(path), f"文件不存在: {path}"

    if not os.path.isfile(path):
        return False, os.path.basename(path), f"不是文件: {path}"

    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        return False, os.path.basename(path), f"文件过大 ({size / 1024:.0f}KB > {MAX_FILE_SIZE / 1024:.0f}KB 限制)"

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        return _read_pdf(path, os.path.basename(path))

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="gbk") as f:
                content = f.read()
        except Exception:
            return False, os.path.basename(path), "无法解码文件（尝试了 UTF-8 和 GBK）"

    if not content.strip():
        return False, os.path.basename(path), "文件为空"

    summary = f"文件名: {os.path.basename(path)}\n类型: {ext or '未知'}\n大小: {size} 字节\n\n--- 文件内容 ---\n{content}\n--- 文件内容结束 ---"

    return True, os.path.basename(path), summary


def _read_pdf(path: str, filename: str) -> tuple[bool, str, str]:
    try:
        import PyPDF2
    except ImportError:
        return False, filename, "读取 PDF 需要安装 PyPDF2: pip install PyPDF2"

    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(f"--- 第 {i + 1} 页 ---\n{text}")
            if not pages:
                return False, filename, "PDF 无可提取的文本内容（可能是扫描件）"
            content = "\n\n".join(pages)
            return True, filename, f"文件名: {filename}\n类型: PDF\n页数: {len(reader.pages)}\n\n--- 文件内容 ---\n{content}\n--- 文件内容结束 ---"
    except Exception as e:
        return False, filename, f"PDF 读取失败: {e}"


def format_context(filename: str, content: str) -> str:
    return f"【主持人上传了文件】📎 {filename}\n\n{content}"
