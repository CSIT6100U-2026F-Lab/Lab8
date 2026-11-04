"""
Shared data layer for Online Code Explorer.
"""

import os
from datetime import datetime, timezone
from typing import List, NamedTuple

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

MAX_FILE_SIZE = 5 * 1024 * 1024
UNSAFE_FILENAME_CHARS = ("..", "/", "\\")


class FileInfo(NamedTuple):
    name: str
    size: int
    last_modified: str


class FileContent(NamedTuple):
    content: str


class InvalidFilenameError(Exception):
    def __init__(self, message: str = "Invalid filename") -> None:
        super().__init__(message)


class DataFileNotFoundError(Exception):
    def __init__(self, message: str = "File not found") -> None:
        super().__init__(message)


class DataFileExistsError(Exception):
    def __init__(self, message: str = "File already exists") -> None:
        super().__init__(message)


class FileTooLargeError(Exception):
    def __init__(self, message: str = "File too large. Maximum size is 5MB.") -> None:
        super().__init__(message)


class InvalidUtf8Error(Exception):
    def __init__(self, message: str = "File is not valid UTF-8") -> None:
        super().__init__(message)


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _validate_filename(filename: str) -> None:
    if (
        not filename
        or filename in (".", "..")
        or any(token in filename for token in UNSAFE_FILENAME_CHARS)
    ):
        raise InvalidFilenameError()


def _file_path(filename: str) -> str:
    _validate_filename(filename)
    ensure_data_dir()
    path = os.path.realpath(os.path.join(DATA_DIR, filename))
    data_root = os.path.realpath(DATA_DIR)
    if os.path.commonpath([data_root, path]) != data_root:
        raise InvalidFilenameError()
    return path


def _build_file_info(filename: str, path: str) -> FileInfo:
    mtime = os.path.getmtime(path)
    last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    return FileInfo(
        name=filename,
        size=os.path.getsize(path),
        last_modified=last_modified,
    )


def _require_existing_file(filename: str) -> str:
    path = _file_path(filename)
    if not os.path.isfile(path):
        raise DataFileNotFoundError()
    return path


def _check_content_size(content: str) -> None:
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise FileTooLargeError()


def _write_text_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def list_files() -> List[FileInfo]:
    ensure_data_dir()
    result: List[FileInfo] = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if os.path.isfile(path):
            result.append(_build_file_info(name, path))
        else:
            pass
    return result


def read_file(filename: str) -> FileContent:
    path = _require_existing_file(filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except UnicodeDecodeError:
        raise InvalidUtf8Error()
    return FileContent(content=content)


def create_file(filename: str, content: str) -> FileInfo:
    path = _file_path(filename)
    if os.path.exists(path):
        raise DataFileExistsError()
    _check_content_size(content)
    _write_text_file(path, content)
    return _build_file_info(filename, path)


def update_file(filename: str, content: str) -> FileInfo:
    path = _require_existing_file(filename)
    _check_content_size(content)
    _write_text_file(path, content)
    return _build_file_info(filename, path)


def delete_file(filename: str) -> None:
    path = _require_existing_file(filename)
    os.remove(path)
