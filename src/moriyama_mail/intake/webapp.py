from __future__ import annotations

import logging
import socket
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, render_template_string, request
from werkzeug.utils import secure_filename

from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import CampaignRequest
from moriyama_mail.services.campaign_service import CampaignService

FORM_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>メルマガ配信依頼</title>
  <style>
    body { font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif; margin: 0; background: #f4f1ea; color: #222; }
    main { max-width: 720px; margin: 32px auto; background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    h1 { font-size: 22px; margin: 0 0 8px; }
    p.note { color: #555; line-height: 1.6; }
    label { display: block; margin: 16px 0 6px; font-weight: 600; }
    input[type=text], textarea, input[type=file] { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
    textarea { min-height: 180px; }
    textarea.signature { min-height: 140px; }
    .plans { display: flex; gap: 16px; }
    pre.preview { background: #f7f4ee; padding: 12px; border-radius: 8px; white-space: pre-wrap; min-height: 160px; font-family: inherit; font-size: 14px; line-height: 1.6; }
    .error { background: #fde8e8; color: #8b0000; padding: 10px 12px; border-radius: 8px; white-space: pre-wrap; }
    button { margin-top: 20px; background: #1f4e79; color: #fff; border: 0; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; }
    button:hover { background: #163a5c; }
  </style>
</head>
<body>
  <main>
    <h1>メルマガ配信の依頼</h1>
    <p class="note">この画面は担当者への依頼窓口です。送る前に宛先ファイルなどを確認します。ここから読者への配信は行いません。</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post" action="{{ url_for('submit_request') }}" enctype="multipart/form-data">
      <label>MyASPプラン（必須）</label>
      <div class="plans">
        {% for plan in plans %}
        <label><input type="radio" name="myasp_plan_key" value="{{ plan.key }}" required{% if plan.key == 'test_plan' %} checked{% endif %}> {{ plan.label() }}</label>
        {% endfor %}
      </div>
      <label>メール件名</label>
      <input type="text" name="subject" required>
      <label>メール本文</label>
      <textarea name="body" id="body" required></textarea>
      <p class="note">本文だけ書いてください。署名は次の欄で編集できます。</p>
      <label>署名</label>
      <textarea name="signature" id="signature" class="signature">{{ signature }}</textarea>
      <p class="note">直した署名は、次に開いたときもこの内容が入ります。</p>
      <label>プレビュー（読者へ届く形・共有URL入り）</label>
      <pre class="preview" id="preview"></pre>
      <label>備考</label>
      <input type="text" name="notes">
      <label>配信用資料（必須。読者がドライブで見るファイル）</label>
      <input type="file" name="material" required>
      <label>宛先のファイル（必須・CSV）</label>
      <input type="file" name="additions_csv" accept=".csv" required>
      <p class="note">宛先ファイルはCSV（.csv）だけです。MyASPからダウンロードしたユーザーリストを、追加や修正したうえで付けてください。</p>
      <button type="submit">送信</button>
    </form>
    <script>
    (function () {
      var body = document.getElementById('body');
      var signatureBox = document.getElementById('signature');
      var preview = document.getElementById('preview');
      var label = {{ drive_link_label|tojson }};
      var placeholder = {{ '{{DRIVE_SHARE_URL}}'|tojson }};
      function assemble(text, signature) {
        var mid = (text || '').replace(/\\s+$/, '');
        var sig = (signature || '').replace(/^\\s+|\\s+$/g, '');
        if (mid.indexOf(placeholder) === -1) {
          mid = (mid ? mid + '\\n\\n' : '') + label + ': ' + placeholder;
        }
        if (sig) {
          return mid + '\\n\\n' + sig + '\\n';
        }
        return mid;
      }
      function refresh() {
        preview.textContent = assemble(body.value, signatureBox.value);
      }
      body.addEventListener('input', refresh);
      signatureBox.addEventListener('input', refresh);
      refresh();
    })();
    </script>
  </main>
</body>
</html>
"""

THANKS_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>依頼を受け付けました</title>
  <style>
    body { font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif; margin: 0; background: #f4f1ea; }
    main { max-width: 640px; margin: 48px auto; background: #fff; padding: 28px; border-radius: 12px; }
  </style>
</head>
<body>
  <main>
    <h1>依頼を受け付けました</h1>
    <p>担当者へ届けました。受付番号は {{ campaign_id }} です。宛先ファイルなどは送信前に確認済みです。</p>
    {% if draft_failed %}
    <p>MyASPへの下書き保存は後で担当者がやり直します。配信はしていません。</p>
    {% else %}
    <p>MyASPへ下書き保存まで進めています。配信はしていません。</p>
    {% endif %}
    <p>ここから読者への配信は行いません。</p>
    <p><a href="{{ url_for('show_form') }}">別の依頼を送る</a></p>
  </main>
</body>
</html>
"""


def _save_upload(storage, dest_dir: Path, prefix: str) -> Path | None:
    if storage is None or not storage.filename:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = secure_filename(storage.filename) or "upload.bin"
    path = dest_dir / f"{prefix}_{uuid4().hex[:8]}_{name}"
    storage.save(path)
    return path


def _signature_path(service: CampaignService) -> Path:
    return service.settings.data_dir / "mail_signature.txt"


def _current_signature(service: CampaignService) -> str:
    path = _signature_path(service)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return service.settings.mail_signature


def create_app(service: CampaignService) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
    app.secret_key = "local-intake-form"

    def _form(error=None, status=200):
        html = render_template_string(
            FORM_HTML,
            plans=service.settings.myasp_plans,
            error=error,
            signature=_current_signature(service),
            drive_link_label=service.settings.drive_link_label,
        )
        return (html, status) if status != 200 else html

    @app.get("/")
    def show_form():
        return _form()

    @app.post("/request")
    def submit_request():
        upload_dir = service.settings.data_dir / "intake_uploads"
        additions_upload = request.files.get("additions_csv")
        additions_name = (additions_upload.filename or "") if additions_upload is not None else ""
        request_payload = CampaignRequest(
            subject=(request.form.get("subject") or "").strip(),
            body=(request.form.get("body") or "").strip(),
            notes=(request.form.get("notes") or "").strip(),
            signature=(request.form.get("signature") or "").strip(),
            myasp_plan_key=(request.form.get("myasp_plan_key") or "").strip(),
            material_path=_save_upload(request.files.get("material"), upload_dir, "material"),
            additions_csv=_save_upload(additions_upload, upload_dir, "add"),
            source_channel="dedicated_form",
        )
        if not request_payload.myasp_plan_key:
            return _form("プランを選んでください。", 400)
        if not request_payload.material_path:
            return _form("配信用資料は必須です。読者がドライブで見るファイルを付けてください。", 400)
        if not request_payload.additions_csv:
            return _form("宛先CSVは必須です。", 400)
        if request_payload.additions_csv:
            from moriyama_mail.audience.myasp_list import additions_format_error

            format_error = additions_format_error(
                Path(request_payload.additions_csv).read_bytes(),
                additions_name or Path(request_payload.additions_csv).name,
            )
            if format_error:
                return _form(format_error, 400)
        try:
            campaign = service.submit_request(request_payload)
            _signature_path(service).write_text(request_payload.signature, encoding="utf-8")
        except SafetyError as exc:
            return _form(str(exc), 400)
        except Exception:
            logging.getLogger("moriyama_mail").exception("intake form submit failed")
            return _form("送信に失敗しました。担当者へご連絡ください。", 500)
        try:
            from moriyama_mail.notify.mailer import notify_campaign_registered

            notify_campaign_registered(campaign, request_payload)
        except Exception:
            logging.getLogger("moriyama_mail").exception("shared notify failed")
        return render_template_string(
            THANKS_HTML,
            campaign_id=campaign.id,
            draft_failed=bool(campaign.error_message),
        )

    return app


_started_url: str | None = None


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _pick_port(host: str, preferred: int) -> int:
    if _port_is_free(host, preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _wait_listening(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)


def start_background(service: CampaignService) -> str:
    """Start the dedicated web form on this PC and return the local URL."""
    global _started_url
    if _started_url:
        return _started_url
    import threading

    app = create_app(service)
    host = service.settings.intake_host or "127.0.0.1"
    port = _pick_port(host, service.settings.intake_port)
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
        name="web-form",
    )
    thread.start()
    _wait_listening(host, port)
    _started_url = f"http://127.0.0.1:{port}/"
    return _started_url


def main() -> int:
    from moriyama_mail.bootstrap import build_service

    service = build_service()
    app = create_app(service)
    host = service.settings.intake_host
    port = service.settings.intake_port
    print(f"web form: http://127.0.0.1:{port}/")
    app.run(host=host, port=port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
