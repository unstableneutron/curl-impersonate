import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKPORT_PATCH = "patches/curl-websocket-readfunction-backport.patch"
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_backport_patch_is_applied_after_main_curl_patch() -> None:
    makefile = read("Makefile.in")

    curl_patch = "$(srcdir)/patches/curl.patch"
    backport_patch = f"$(srcdir)/{BACKPORT_PATCH}"

    assert curl_patch in makefile
    assert backport_patch in makefile
    assert makefile.index(curl_patch) < makefile.index(backport_patch)


def test_windows_build_applies_backport_patch_after_main_curl_patch() -> None:
    deps = read("win/deps.sh")

    curl_patch = 'patch -p1 -d "$PWD/deps/curl" < "$PWD/patches/curl.patch"'
    backport_patch = (
        'patch -p1 -d "$PWD/deps/curl" '
        f'< "$PWD/{BACKPORT_PATCH}"'
    )

    assert curl_patch in deps
    assert backport_patch in deps
    assert deps.index(curl_patch) < deps.index(backport_patch)


def test_websocket_backport_patch_documents_upstream_scope() -> None:
    patch = read(BACKPORT_PATCH)

    assert "Backport WebSocket read-callback upload support" in patch
    assert "curl 8.16" in patch
    assert "curl 8.18" in patch


def test_websocket_backport_patch_has_no_noop_hunks() -> None:
    """GNU/Git patch parsers reject hunks that contain only context lines."""
    hunk_lines: list[str] = []
    hunk_header = ""

    for line in read(BACKPORT_PATCH).splitlines():
        if HUNK_RE.match(line):
            if hunk_lines:
                assert any(l.startswith(('-', '+')) for l in hunk_lines), hunk_header
            hunk_header = line
            hunk_lines = []
            continue
        if hunk_header and not line.startswith("diff -ruN "):
            hunk_lines.append(line)

    assert any(l.startswith(('-', '+')) for l in hunk_lines), hunk_header


def test_websocket_backport_patch_exports_start_frame_api() -> None:
    patch = read(BACKPORT_PATCH)

    assert "include/curl/websockets.h" in patch
    assert "curl_ws_start_frame(CURL *curl" in patch
    assert "lib/libcurl.def" in patch
    assert "+curl_ws_start_frame" in patch
    assert "scripts/singleuse.pl" in patch
    assert "'curl_ws_start_frame' => 'API'" in patch


def test_websocket_backport_patch_adds_readfunction_frame_encoder() -> None:
    patch = read(BACKPORT_PATCH)

    assert "lib/ws.c" in patch
    assert "static const struct Curl_crtype ws_cr_encode" in patch
    assert "curl_ws_start_frame(CURL *d" in patch
    assert 'infof(data, "[WS] Received 101, switch to WebSocket")' in patch
    assert "httpreq = HTTPREQ_GET" in patch
    assert "Curl_creader_set_fread(data, -1)" in patch
    assert "Curl_creader_create(&ws_enc_reader, data, &ws_cr_encode" in patch
    assert "CLIENTWRITE_0LEN" in patch
    assert "data->conn && data->conn->handler->flags & PROTOPT_NONETWORK" in patch


def test_websocket_backport_patch_includes_curl_regression_tests() -> None:
    patch = read(BACKPORT_PATCH)

    assert "tests/libtest/cli_ws_data.c" in patch
    assert "curl_ws_start_frame(ctx->curl, CURLWS_BINARY" in patch
    assert "calloc(1, plen_max + 1)" in patch
    assert "curlx_calloc" not in patch
    assert "tests/libtest/cli_ws_pingpong.c" in patch
    assert "ws_send_ping(curl, payload)" in patch
    assert "tests/libtest/first.c" in patch
    assert "int cgetopt(int argc, char * const argv[]" in patch
    assert "tests/http/test_20_websockets.py" in patch
    assert "class WebSocketClient(LocalClient)" in patch
    assert "tests/libtest/libtests" in patch
    assert "name='cli_ws_data'" in patch
    assert "name='cli_ws_pingpong'" in patch
