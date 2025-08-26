# --- Large Files ---

from replicheck.utils import compute_severity


class LargeFileDetector:
    def __init__(self):
        from replicheck.parser import CodeParser

        self.parser = CodeParser()
        self.results = []

    def _token_count_python(self, file_path):
        import tokenize

        try:
            with open(file_path, "rb") as f:
                tokens = list(tokenize.tokenize(f.readline))
            return sum(
                1
                for t in tokens
                if t.type not in (tokenize.ENCODING, tokenize.ENDMARKER)
            )
        except Exception:
            return 0

    def _token_count_js(self, code):
        import re

        return len(re.findall(r"\w+|[^\s\w]", code, re.UNICODE))

    def _token_count_ts(self, code, file_path, lang):
        blocks = self.parser._parse_with_tree_sitter(code, file_path, lang)
        return sum(len(block["tokens"]) for block in blocks)

    def _token_count_cs(self, content, file_path):
        import re

        blocks = self.parser._parse_with_tree_sitter(content, file_path, "csharp")
        block_token_count = (
            sum(len(block["tokens"]) for block in blocks) if blocks else 0
        )
        raw_tokens = re.findall(r"\w+|[^\s\w]", content, re.UNICODE)
        fallback_count = len(raw_tokens)
        if block_token_count >= 10 and block_token_count >= 0.1 * fallback_count:
            return block_token_count
        else:
            return fallback_count

    def find_large_files(self, files, token_threshold=500, top_n=None):
        """
        Find files whose total token count exceeds the threshold.
        Returns a list of dicts with file path and token count, including threshold and top_n for reporting.
        Also sets self.results to the list of large files found.
        """
        large_files = []
        for file_path in files:
            suffix = str(file_path).lower()
            token_count = 0
            if suffix.endswith(".py"):
                token_count = self._token_count_python(file_path)
            elif suffix.endswith((".js", ".jsx", ".ts", ".tsx")):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    if suffix.endswith(".ts") or suffix.endswith(".tsx"):
                        lang = "tsx" if suffix.endswith(".tsx") else "typescript"
                        token_count = self._token_count_ts(code, file_path, lang)
                    else:
                        token_count = self._token_count_js(code)
                except Exception:
                    token_count = 0
            elif suffix.endswith(".cs"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    token_count = self._token_count_cs(content, file_path)
                except Exception:
                    token_count = 0
            if token_count >= token_threshold:
                large_files.append(
                    {
                        "file": str(file_path),
                        "token_count": token_count,
                        "severity": compute_severity(token_count, token_threshold),
                    }
                )
        large_files = sorted(large_files, key=lambda x: x["token_count"], reverse=True)
        if top_n is not None:
            large_files = large_files[:top_n]
        self.results = large_files
