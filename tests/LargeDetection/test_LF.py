from replicheck.tools.LargeDetection.LF import LargeFileDetector


def create_file(tmp_path, name, content):
    file = tmp_path / name
    file.write_text(content, encoding="utf-8")
    return file


def test_token_count_python(tmp_path):
    code = "a = 1\nb = 2\n"
    file = create_file(tmp_path, "foo.py", code)
    detector = LargeFileDetector()
    count = detector._token_count_python(file)
    assert isinstance(count, int)
    assert count > 0


def test_token_count_python_handles_error(tmp_path):
    file = tmp_path / "doesnotexist.py"
    detector = LargeFileDetector()
    count = detector._token_count_python(file)
    assert count == 0


def test_token_count_js():
    code = "function foo() { return 1; }"
    detector = LargeFileDetector()
    count = detector._token_count_js(code)
    assert isinstance(count, int)
    assert count > 0


def test_token_count_cs_fallback(tmp_path):
    code = "public class Foo { int x = 1; }"
    file = create_file(tmp_path, "foo.cs", code)
    detector = LargeFileDetector()
    # Force fallback by monkeypatching parser
    detector.parser._parse_with_tree_sitter = lambda *a, **k: []
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    count = detector._token_count_cs(content, file)
    assert isinstance(count, int)
    assert count > 0


def test_find_large_files_python(tmp_path):
    code = "a = 1\n" * 100
    file = create_file(tmp_path, "foo.py", code)
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=10)
    results = detector.results
    assert isinstance(results, list)
    assert results and results[0]["file"].endswith("foo.py")


def test_find_large_files_js(tmp_path):
    code = "function foo() { return 1; }" * 50
    file = create_file(tmp_path, "foo.js", code)
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=10)
    results = detector.results
    assert isinstance(results, list)
    assert results and results[0]["file"].endswith("foo.js")


def test_find_large_files_cs(tmp_path):
    code = "public class Foo { int x = 1; int y = 2; }" * 20
    file = create_file(tmp_path, "foo.cs", code)
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=10)
    results = detector.results
    assert isinstance(results, list)
    assert results and results[0]["file"].endswith("foo.cs")


def test_find_large_files_empty(tmp_path):
    file = create_file(tmp_path, "empty.py", "")
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=1)
    assert detector.results == []


def test_find_large_files_nonexistent_file(tmp_path):
    file = tmp_path / "doesnotexist.py"
    detector = LargeFileDetector()
    detector.find_large_files([file], token_threshold=1)
    assert isinstance(detector.results, list)


def test_find_large_files_top_n(tmp_path):
    files = []
    for i in range(5):
        code = "a = 1\n" * (20 + i)
        files.append(create_file(tmp_path, f"file{i}.py", code))
    detector = LargeFileDetector()
    detector.find_large_files(files, token_threshold=10, top_n=2)
    results = detector.results
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["token_count"] >= results[1]["token_count"]
