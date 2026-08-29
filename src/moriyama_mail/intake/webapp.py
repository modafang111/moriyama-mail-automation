from __future__ import annotations

import logging
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
    .plans { display: flex; gap: 16px; }
    .error { background: #fde8e8; color: #8b0000; padding: 10px 12px; border-radius: 8px; }
    button { margin-top: 20px; background: #1f4e79; color: #fff; border: 0; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; }
    button:hover { background: #163a5c; }
  </style>
</head>
<body>
  <main>
    <h1>メルマガ配信の依頼</h1>
    <p class="note">この画面から依頼を送ると、担当者に届きます。配信そのものは、担当者が内容を確認してから行います。</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post" action="{{ url_for('submit_request') }}" enctype="multipart/form-data">
      <label>MyASPプラン（必須）</label>
      <div class="plans">
        {% for plan in plans %}
        <label><input type="radio" name="myasp_plan_key" value="{{ plan.key }}" required> {{ plan.label() }}</label>
        {% endfor %}
      </div>
      <label>メール件名</label>
      <input type="text" name="subject" required>
      <label>メール本文</label>
      <textarea name="body" required></textarea>
      <label>備考</label>
      <input type="text" name="notes">
      <label>配信用資料（PDFなど）</label>
      <input type="file" name="material">
      <label>追加する宛先のファイル</label>
      <input type="file" name="additions_csv" accept=".csv,.txt">
      <label>今回だけ送らない宛先のファイル</label>
      <input type="file" name="exclusions_csv" accept=".csv,.txt">
      <p class="note">「今回だけ送らない」は、その配信のときだけ送らない指定です。リストから名前は消しません。</p>
      <button type="submit">担当者へ依頼を送る</button>
    </form>
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
    <p>担当者へ送りました。受付番号は {{ campaign_id }} です。</p>
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


def create_app(service: CampaignService) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
    app.secret_key = "local-intake-form"

    @app.get("/")
    def show_form():
        return render_template_string(FORM_HTML, plans=service.settings.myasp_plans, error=None)

    @app.post("/request")
    def submit_request():
        upload_dir = service.settings.data_dir / "intake_uploads"
        request_payload = CampaignRequest(
            subject=(request.form.get("subject") or "").strip(),
            body=(request.form.get("body") or "").strip(),
            notes=(request.form.get("notes") or "").strip(),
            myasp_plan_key=(request.form.get("myasp_plan_key") or "").strip(),
            material_path=_save_upload(request.files.get("material"), upload_dir, "material"),
            additions_csv=_save_upload(request.files.get("additions_csv"), upload_dir, "add"),
            exclusions_csv=_save_upload(request.files.get("exclusions_csv"), upload_dir, "exclude"),
            source_channel="dedicated_form",
        )
        try:
            campaign, _notify = service.submit_request(request_payload)
        except SafetyError as exc:
            return render_template_string(FORM_HTML, plans=service.settings.myasp_plans, error=str(exc)), 400
        except Exception:
            logging.getLogger("moriyama_mail").exception("intake form submit failed")
            return render_template_string(
                FORM_HTML,
                plans=service.settings.myasp_plans,
                error="送信に失敗しました。担当者へご連絡ください。",
            ), 500
        return render_template_string(THANKS_HTML, campaign_id=campaign.id)

    return app


_started_url: str | None = None


def start_background(service: CampaignService) -> str:
    """Start the customer form once and return a local URL."""
    global _started_url
    if _started_url:
        return _started_url
    import threading

    app = create_app(service)
    host = service.settings.intake_host
    port = service.settings.intake_port
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
        name="intake-form",
    )
    thread.start()
    _started_url = f"http://127.0.0.1:{port}/"
    return _started_url


def main() -> int:
    from moriyama_mail.bootstrap import build_service

    service = build_service()
    app = create_app(service)
    host = service.settings.intake_host
    port = service.settings.intake_port
    print(f"顧客向けフォーム: http://127.0.0.1:{port}/")
    app.run(host=host, port=port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
