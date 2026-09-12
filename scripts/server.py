import json
import os
import importlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import wcs_schema
from wcs_schema import WCS_FIELDS


ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(ROOT, "wcs_layout.csv")
import build_html


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == "/":
            path = "/wcs_monitor.html"
        fp = os.path.realpath(os.path.join(ROOT, path.lstrip("/")))
        if not fp.startswith(ROOT) or not os.path.isfile(fp):
            self._send(404, "404 not found".encode("utf-8"))
            return
        if os.path.basename(fp).lower() == "wcs_monitor.html":
            importlib.reload(wcs_schema)   # 字段定义改了也要生效
            importlib.reload(build_html)
            html = build_html.render_html(
                build_html.devices_from_rows(build_html.load_rows()))
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        ext = os.path.splitext(fp)[1].lower()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".py": "text/plain; charset=utf-8",
        }.get(ext, "application/octet-stream")
        with open(fp, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/save-layout":
            self._send(404, b"unknown endpoint")
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            if payload.get("format") != "wcs_layout_v1":
                raise ValueError("不支持的保存格式")
            rows = payload.get("rows")
            if not isinstance(rows, list) or not rows:
                raise ValueError("rows 必须是非空数组")

            wanted = list(WCS_FIELDS)
            for r in rows:
                if not isinstance(r, dict):
                    raise ValueError("rows 中存在非对象元素")
                if not str(r.get("itemid", "")).strip():
                    raise ValueError("itemid 不能为空")

            import csv
            tmp = CSV_PATH + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=wanted, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            body = json.dumps({"ok": True, "count": len(rows)}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except PermissionError:
            self._send(409, json.dumps({"ok": False, "error": "CSV 被占用，请先关闭 Excel/WPS 后重试"},
                                       ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")
        except Exception as e:
            self._send(400, json.dumps({"ok": False, "error": str(e)},
                                       ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8734"))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"服务已启动: http://127.0.0.1:{port}/")
    print("保存端点: POST /save-layout -> wcs_layout.csv")
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    t.join()
