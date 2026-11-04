"""
HTTP tests for Lab 8 REST (Lab 3 cases).

    python3 -m coverage run test.py
    python3 -m coverage report -m
"""

import os
import sys
import unittest

_LAB_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_LAB_ROOT, "backend")
sys.path.insert(0, _BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

import rest_service  # noqa: E402

client = TestClient(rest_service.app)

MAX_FILE_SIZE = 5 * 1024 * 1024
DATA_DIR = os.path.join(_LAB_ROOT, "data")

PROTECTED = ("main.py", "utils.js")
TEST_PREFIX = "lab8_test_"

MAIN_PY = (
    "def greet(name):\n"
    '    return f"Hello, {name}!"\n'
    "\n"
    'print(greet("World"))\n'
)
UTILS_JS = (
    "export const add = (a, b) => a + b;\n"
    "console.log(add(2, 3));\n"
)


def rest(method, path, payload=None):
    """Call the REST API. Returns (status_code, parsed_json_or_None, raw_bytes)."""
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    response = client.request(method, path, **kwargs)
    raw = response.content
    parsed = None
    if raw:
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
    return response.status_code, parsed, raw


def data_path(name):
    return os.path.join(DATA_DIR, name)


def remove_test_file(name):
    if name in PROTECTED or not name.startswith(TEST_PREFIX):
        raise RuntimeError("refusing to delete non-test file: {}".format(name))
    path = data_path(name)
    if os.path.isfile(path):
        os.remove(path)


class RestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._protected_bytes = {}
        for name in PROTECTED:
            with open(data_path(name), "rb") as handle:
                cls._protected_bytes[name] = handle.read()

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(DATA_DIR):
            for name in os.listdir(DATA_DIR):
                if name.startswith(TEST_PREFIX):
                    path = data_path(name)
                    if os.path.isfile(path):
                        os.remove(path)
        cls._assert_protected_unchanged()

    @classmethod
    def _assert_protected_unchanged(cls):
        for name, original in cls._protected_bytes.items():
            with open(data_path(name), "rb") as handle:
                current = handle.read()
            if current != original:
                raise AssertionError(
                    "{} was modified; tests must leave it unchanged".format(name)
                )

    def setUp(self):
        self._created = []

    def tearDown(self):
        for name in self._created:
            try:
                remove_test_file(name)
            except OSError:
                pass
        self._assert_protected_unchanged()

    def track(self, name):
        self._created.append(name)
        return name

    def test_list_files_ok(self):
        status, body, _raw = rest("GET", "/files")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        names = [item["name"] for item in body]
        self.assertIn("main.py", names)
        self.assertIn("utils.js", names)
        self.assertEqual(names, sorted(names))
        by_name = {item["name"]: item for item in body}
        self.assertEqual(by_name["main.py"]["size"], len(MAIN_PY.encode("utf-8")))
        self.assertEqual(by_name["utils.js"]["size"], len(UTILS_JS.encode("utf-8")))
        for item in body:
            self.assertIn("last_modified", item)

    def test_get_file_ok(self):
        status, body, _raw = rest("GET", "/file/main.py")
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], MAIN_PY)

        status, body, _raw = rest("GET", "/file/utils.js")
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], UTILS_JS)

    def test_get_file_404(self):
        status, body, _raw = rest("GET", "/file/{}missing.txt".format(TEST_PREFIX))
        self.assertEqual(status, 404)
        self.assertIn("detail", body)

    def test_get_file_400_traversal_and_separators(self):
        # "%2e%2e" is ".." — the test client would otherwise collapse "/file/.."
        status, body, _raw = rest("GET", "/file/%2e%2e")
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

        status, body, _raw = rest("GET", "/file/foo/bar")
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

        status, body, _raw = rest("GET", "/file/foo\\bar")
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

    def test_get_file_400_invalid_utf8(self):
        name = self.track("{}not_utf8.txt".format(TEST_PREFIX))
        with open(data_path(name), "wb") as handle:
            handle.write(b"\xff\xfe not utf-8")
        status, body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

    def test_create_file_ok(self):
        name = self.track("{}create.txt".format(TEST_PREFIX))
        content = "hello lab8\n"
        status, body, _raw = rest(
            "POST", "/create/{}".format(name), {"content": content}
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["name"], name)
        self.assertEqual(body["size"], len(content.encode("utf-8")))
        self.assertIn("last_modified", body)

        status, body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], content)

        status, listing, _raw = rest("GET", "/files")
        self.assertEqual(status, 200)
        self.assertIn(name, [item["name"] for item in listing])

    def test_create_empty_file_ok(self):
        name = self.track("{}empty.txt".format(TEST_PREFIX))
        status, body, _raw = rest("POST", "/create/{}".format(name), {"content": ""})
        self.assertEqual(status, 201)
        self.assertEqual(body["size"], 0)

    def test_create_file_409_existing_sample(self):
        status, body, _raw = rest(
            "POST", "/create/main.py", {"content": "must not overwrite"}
        )
        self.assertEqual(status, 409)
        self.assertIn("detail", body)

    def test_create_file_409_duplicate(self):
        name = self.track("{}dup.txt".format(TEST_PREFIX))
        status, _body, _raw = rest("POST", "/create/{}".format(name), {"content": "a"})
        self.assertEqual(status, 201)
        status, body, _raw = rest("POST", "/create/{}".format(name), {"content": "b"})
        self.assertEqual(status, 409)
        self.assertIn("detail", body)
        status, body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], "a")

    def test_create_file_400_invalid_name(self):
        status, body, _raw = rest("POST", "/create/foo/bar", {"content": "x"})
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

        status, body, _raw = rest("POST", "/create/%2e%2e", {"content": "x"})
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

    def test_create_file_413_too_large(self):
        name = self.track("{}huge.txt".format(TEST_PREFIX))
        oversized = "x" * (MAX_FILE_SIZE + 1)
        status, body, _raw = rest(
            "POST", "/create/{}".format(name), {"content": oversized}
        )
        self.assertEqual(status, 413)
        self.assertIn("detail", body)
        self.assertFalse(os.path.isfile(data_path(name)))

    def test_update_file_ok(self):
        name = self.track("{}update.txt".format(TEST_PREFIX))
        status, _body, _raw = rest("POST", "/create/{}".format(name), {"content": "old"})
        self.assertEqual(status, 201)
        status, body, _raw = rest(
            "POST", "/update/{}".format(name), {"content": "new text"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["name"], name)
        self.assertEqual(body["size"], len("new text".encode("utf-8")))
        status, body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], "new text")

    def test_update_file_404(self):
        status, body, _raw = rest(
            "POST",
            "/update/{}missing.txt".format(TEST_PREFIX),
            {"content": "nope"},
        )
        self.assertEqual(status, 404)
        self.assertIn("detail", body)

    def test_update_file_400_invalid_name(self):
        status, body, _raw = rest("POST", "/update/foo/bar", {"content": "x"})
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

    def test_update_file_413_too_large(self):
        name = self.track("{}update_huge.txt".format(TEST_PREFIX))
        status, _body, _raw = rest("POST", "/create/{}".format(name), {"content": "ok"})
        self.assertEqual(status, 201)
        oversized = "y" * (MAX_FILE_SIZE + 1)
        status, body, _raw = rest(
            "POST", "/update/{}".format(name), {"content": oversized}
        )
        self.assertEqual(status, 413)
        self.assertIn("detail", body)
        status, body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 200)
        self.assertEqual(body["content"], "ok")

    def test_delete_file_ok(self):
        name = self.track("{}delete.txt".format(TEST_PREFIX))
        status, _body, _raw = rest("POST", "/create/{}".format(name), {"content": "bye"})
        self.assertEqual(status, 201)
        status, body, _raw = rest("DELETE", "/file/{}".format(name))
        self.assertEqual(status, 200)
        self.assertEqual(body, {"message": "deleted"})
        status, _body, _raw = rest("GET", "/file/{}".format(name))
        self.assertEqual(status, 404)
        self.assertFalse(os.path.isfile(data_path(name)))

    def test_delete_file_404(self):
        status, body, _raw = rest("DELETE", "/file/{}missing.txt".format(TEST_PREFIX))
        self.assertEqual(status, 404)
        self.assertIn("detail", body)

    def test_delete_file_400_invalid_name(self):
        status, body, _raw = rest("DELETE", "/file/foo/bar")
        self.assertEqual(status, 400)
        self.assertIn("detail", body)

        status, body, _raw = rest("DELETE", "/file/%2e%2e")
        self.assertEqual(status, 400)
        self.assertIn("detail", body)
        
    # TODO: You can add test cases here.
    
# TODO: Or you can also define your own test class.


if __name__ == "__main__":
    unittest.main(verbosity=2)
