from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path

from moriyama_mail.bootstrap import build_service
from moriyama_mail.domain.models import (
    PRODUCTION_CONFIRM_PHRASE,
    AudienceAction,
    Campaign,
    DeliveryMode,
)
from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.gui.request_form import RequestFormWindow
from moriyama_mail.services.campaign_service import CampaignService


MODE_LABELS = {
    DeliveryMode.TEST: "テスト配信",
    DeliveryMode.PRODUCTION: "本番配信",
}


class App(tk.Tk):
    def __init__(self, service: CampaignService) -> None:
        super().__init__()
        self.service = service
        self.campaign: Campaign | None = None
        self.title("森山メルマガ配信支援")
        self.geometry("1180x760")
        self.minsize(960, 640)
        self._mode_var = tk.StringVar(value=DeliveryMode.TEST.value)
        self._plan_var = tk.StringVar(value="")
        self._campaigns: list[Campaign] = []
        self._build()
        self.refresh_list()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, sticky="nsw")
        ttk.Label(left, text="案件一覧").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=28, height=28)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        ttk.Button(left, text="顧客向けフォームを起動", command=self.open_customer_form).pack(fill="x", pady=(8, 0))
        ttk.Button(left, text="担当者が代わりに入力", command=self.open_request_form).pack(fill="x", pady=(4, 0))
        ttk.Button(left, text="空の案件を作成", command=self.create_campaign).pack(fill="x", pady=(4, 0))
        ttk.Button(left, text="配信履歴を見る", command=self.show_history).pack(fill="x", pady=4)

        right = ttk.Frame(self, padding=8)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        self.progress = ttk.Label(right, text="案件を選択してください", justify="left")
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        form = ttk.Frame(right)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="案件ID").grid(row=0, column=0, sticky="w")
        self.id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.id_var, state="readonly").grid(row=0, column=1, sticky="ew")

        ttk.Label(form, text="状態").grid(row=1, column=0, sticky="w")
        self.status_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.status_var, state="readonly").grid(row=1, column=1, sticky="ew")

        ttk.Label(form, text="MyASPプラン").grid(row=2, column=0, sticky="w")
        plan_row = ttk.Frame(form)
        plan_row.grid(row=2, column=1, sticky="ew")
        for plan in self.service.settings.myasp_plans:
            ttk.Radiobutton(plan_row, text=plan.label(), value=plan.key, variable=self._plan_var).pack(side="left", padx=(0, 8))

        ttk.Label(form, text="メール件名").grid(row=3, column=0, sticky="w")
        self.subject_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.subject_var).grid(row=3, column=1, sticky="ew")

        ttk.Label(form, text="資料").grid(row=4, column=0, sticky="w")
        file_row = ttk.Frame(form)
        file_row.grid(row=4, column=1, sticky="ew")
        file_row.columnconfigure(0, weight=1)
        self.file_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.file_var, state="readonly").grid(row=0, column=0, sticky="ew")
        ttk.Button(file_row, text="資料を選択", command=self.select_material).grid(row=0, column=1, padx=4)
        ttk.Button(file_row, text="Driveへアップロード", command=self.upload_drive).grid(row=0, column=2)

        ttk.Label(form, text="共有URL").grid(row=5, column=0, sticky="w")
        url_row = ttk.Frame(form)
        url_row.grid(row=5, column=1, sticky="ew")
        url_row.columnconfigure(0, weight=1)
        self.url_var = tk.StringVar()
        ttk.Entry(url_row, textvariable=self.url_var, state="readonly").grid(row=0, column=0, sticky="ew")
        ttk.Button(url_row, text="本文へ挿入", command=self.insert_url).grid(row=0, column=1, padx=4)

        ttk.Label(form, text="備考").grid(row=6, column=0, sticky="w")
        self.notes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.notes_var).grid(row=6, column=1, sticky="ew")

        ttk.Label(right, text="メール本文（{{DRIVE_SHARE_URL}} を共有URLに置換できます）").grid(row=2, column=0, sticky="w")
        self.body = tk.Text(right, height=14, wrap="word")
        self.body.grid(row=3, column=0, sticky="nsew", pady=(0, 8))

        actions = ttk.Frame(right)
        actions.grid(row=4, column=0, sticky="ew")
        ttk.Button(actions, text="件名・本文を保存", command=self.save_content).pack(side="left")
        ttk.Button(actions, text="追加する宛先CSV", command=lambda: self.load_csv(AudienceAction.ADD)).pack(side="left", padx=4)
        ttk.Button(actions, text="今回だけ送らないCSV", command=lambda: self.load_csv(AudienceAction.EXCLUDE)).pack(side="left")

        mode_frame = ttk.LabelFrame(right, text="配信モード（初期値はテスト配信です）", padding=8)
        mode_frame.grid(row=5, column=0, sticky="ew", pady=8)
        ttk.Radiobutton(
            mode_frame,
            text="テスト配信（確認用アドレスのみ）",
            value=DeliveryMode.TEST.value,
            variable=self._mode_var,
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame,
            text="本番配信（予約。即時配信は使いません。初期選択しません）",
            value=DeliveryMode.PRODUCTION.value,
            variable=self._mode_var,
        ).pack(anchor="w")
        ttk.Label(
            mode_frame,
            text="本番は確認画面と「本番配信を承認」の入力が必要です。除外した宛先には今回だけ送りません。",
        ).pack(anchor="w", pady=(4, 0))

        bottom = ttk.Frame(right)
        bottom.grid(row=6, column=0, sticky="ew")
        ttk.Button(bottom, text="配信前の内容を確認", command=self.preview).pack(side="left")
        ttk.Button(bottom, text="配信を実行", command=self.execute).pack(side="left", padx=8)
        self.counts_var = tk.StringVar(value="追加 0 / 今回除外 0")
        ttk.Label(bottom, textvariable=self.counts_var).pack(side="left")

    def _require_campaign(self) -> Campaign | None:
        if self.campaign is None:
            messagebox.showinfo("案件", "先に案件を作成または選択してください。")
            return None
        return self.campaign

    def refresh_list(self, select_id: str | None = None) -> None:
        self.listbox.delete(0, tk.END)
        campaigns = self.service.list_campaigns()
        self._campaigns = campaigns
        for item in campaigns:
            self.listbox.insert(tk.END, f"{item.id}  {item.subject or '（無題）'}")
        if select_id:
            for index, item in enumerate(campaigns):
                if item.id == select_id:
                    self.listbox.selection_set(index)
                    self.campaign = item
                    self._fill(item)
                    break

    def open_customer_form(self) -> None:
        import webbrowser

        from moriyama_mail.intake.webapp import start_background

        url = start_background(self.service)
        webbrowser.open(url)
        messagebox.showinfo(
            "顧客向けフォーム",
            "顧客がブラウザで開き、担当者へ送る画面です。\n"
            f"{url}\n\n"
            "このフォームから配信は実行されません。",
        )

    def open_request_form(self) -> None:
        def after(campaign: Campaign) -> None:
            self.refresh_list(campaign.id)

        RequestFormWindow(self, self.service, after)

    def create_campaign(self) -> None:
        campaign = self.service.create_campaign()
        self.campaign = campaign
        self.refresh_list(campaign.id)

    def _on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        campaign = self._campaigns[selection[0]]
        self.campaign = self.service.get(campaign.id)
        self._fill(self.campaign)

    def _fill(self, campaign: Campaign) -> None:
        self.id_var.set(campaign.id)
        self.status_var.set(campaign.status.value)
        self.subject_var.set(campaign.subject)
        self.notes_var.set(campaign.notes)
        self.file_var.set(campaign.material_name or campaign.material_path)
        self.url_var.set(campaign.drive_share_url)
        self.body.delete("1.0", tk.END)
        self.body.insert("1.0", campaign.body)
        self._mode_var.set(campaign.delivery_mode.value)
        self._plan_var.set(campaign.myasp_plan_key)
        self.counts_var.set(
            f"追加 {campaign.audience.add_count} / 今回除外 {campaign.audience.exclude_count}"
        )
        flags = campaign.progress()
        plan = campaign.myasp_plan_name or campaign.myasp_plan_key or "未選択"
        lines = [f"状態: {campaign.status.value}", f"MyASPプラン: {plan}", "本番は予約配信（即時なし）"]
        for name, done in flags.items():
            lines.append(f"{'■' if done else '□'} {name}")
        if campaign.test_result:
            lines.append(f"テスト結果: {campaign.test_result}")
        if campaign.production_result:
            lines.append(f"本番結果: {campaign.production_result}")
        self.progress.configure(text="\n".join(lines))

    def _sync_from_form(self) -> Campaign | None:
        campaign = self._require_campaign()
        if campaign is None:
            return None
        mode = DeliveryMode(self._mode_var.get())
        return self.service.save_content(
            campaign,
            self.subject_var.get(),
            self.body.get("1.0", tk.END).rstrip("\n"),
            self.notes_var.get(),
            mode,
            self._plan_var.get(),
        )

    def save_content(self) -> None:
        campaign = self._sync_from_form()
        if campaign is None:
            return
        self.campaign = campaign
        self._fill(campaign)
        messagebox.showinfo("保存", "件名と本文を保存しました。")

    def select_material(self) -> None:
        campaign = self._require_campaign()
        if campaign is None:
            return
        path = filedialog.askopenfilename(
            title="配信用資料を選択",
            filetypes=[("PDF / 資料", "*.pdf *.png *.jpg *.jpeg *.zip"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        self.campaign = self.service.set_material(campaign, Path(path))
        self._fill(self.campaign)

    def upload_drive(self) -> None:
        campaign = self._require_campaign()
        if campaign is None:
            return
        try:
            self.campaign = self.service.upload_to_drive(campaign)
            self._fill(self.campaign)
            mode = "モック" if self.campaign.drive_file_id.startswith("mock-") else "Googleドライブ"
            messagebox.showinfo("アップロード", f"{mode}へ登録し、共有URLを取得しました。")
        except Exception as exc:
            messagebox.showerror("アップロード失敗", str(exc))

    def insert_url(self) -> None:
        campaign = self._require_campaign()
        if campaign is None:
            return
        try:
            self.campaign = self.service.insert_share_url(campaign)
            self._fill(self.campaign)
        except SafetyError as exc:
            messagebox.showwarning("共有URL", str(exc))

    def load_csv(self, action: AudienceAction) -> None:
        campaign = self._require_campaign()
        if campaign is None:
            return
        path = filedialog.askopenfilename(title="配信対象データを選択", filetypes=[("CSV", "*.csv *.txt"), ("すべて", "*.*")])
        if not path:
            return
        column = simpledialog.askstring(
            "列名",
            "メールアドレス列名を入力してください。\n列が1つだけのCSV、またはヘッダー無しの場合は空欄で構いません。",
        )
        try:
            self.campaign = self.service.load_audience_file(campaign, Path(path), action, column or None)
            self._fill(self.campaign)
            messagebox.showinfo("読み込み", "取り込みました。アドレス一覧は画面に表示しません。今回除外は、その配信だけ送らない処理です。")
        except Exception as exc:
            messagebox.showerror("読み込み失敗", str(exc))

    def preview(self) -> None:
        campaign = self._sync_from_form()
        if campaign is None:
            return
        self.campaign = campaign
        try:
            preview = self.service.preview_delivery(campaign, DeliveryMode(self._mode_var.get()))
        except SafetyError as exc:
            messagebox.showwarning("確認できません", str(exc))
            return
        self._show_preview_window(preview, execute=False)

    def execute(self) -> None:
        campaign = self._sync_from_form()
        if campaign is None:
            return
        self.campaign = campaign
        mode = DeliveryMode(self._mode_var.get())
        try:
            preview = self.service.preview_delivery(campaign, mode)
        except SafetyError as exc:
            messagebox.showwarning("実行できません", str(exc))
            return
        if mode is DeliveryMode.PRODUCTION:
            self._show_preview_window(preview, execute=True)
            return
        if not messagebox.askyesno("テスト配信", "確認用アドレスのみにテスト配信します。実行しますか？"):
            return
        self._run_delivery(mode)

    def _show_preview_window(self, preview: dict[str, object], execute: bool) -> None:
        win = tk.Toplevel(self)
        win.title("配信前確認")
        win.geometry("640x520")
        win.transient(self)
        win.grab_set()
        mode = preview["delivery_mode"]
        is_prod = mode is DeliveryMode.PRODUCTION
        banner = tk.Label(
            win,
            text=str(preview["production_banner"]),
            bg="#8B0000" if is_prod else "#1F4E79",
            fg="white",
            font=("Yu Gothic UI", 14, "bold"),
            pady=12,
        )
        banner.pack(fill="x")
        body = tk.Text(win, wrap="word", height=18)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        lines = [
            f"案件ID: {preview['campaign_id']}",
            f"メール件名: {preview['subject']}",
            f"配信モード: {MODE_LABELS[mode]}",
            f"MyASPプラン: {preview.get('myasp_plan') or '（未選択）'}",
            f"配信タイミング: {'予約配信（即時なし）' if preview.get('send_timing') == 'scheduled' else preview.get('send_timing')}",
            f"配信対象件数: {preview['target_count']}",
            f"除外対象件数: {preview['exclude_count']}（{preview.get('exclude_meaning') or '今回の配信だけ送らない'}）",
            f"Googleドライブ共有URL: {preview['drive_share_url'] or '（未取得）'}",
        ]
        if preview.get("replay_warning"):
            lines.append("")
            lines.append("警告: " + str(preview["replay_warning"]))
        if is_prod:
            lines.append("")
            lines.append("本番は予約配信です。即時配信は行いません。")
            lines.append("除外した宛先には、今回の配信だけ送りません。")
            lines.append(f"承認するには、下の欄に「{PRODUCTION_CONFIRM_PHRASE}」と入力してください。")
        body.insert("1.0", "\n".join(lines))
        body.configure(state="disabled")
        phrase_var = tk.StringVar()
        if is_prod and execute:
            ttk.Label(win, text="確認入力").pack(anchor="w", padx=8)
            ttk.Entry(win, textvariable=phrase_var).pack(fill="x", padx=8, pady=(0, 8))

        buttons = ttk.Frame(win)
        buttons.pack(fill="x", padx=8, pady=8)

        def close() -> None:
            win.destroy()

        def do_execute() -> None:
            if is_prod:
                self._run_delivery(DeliveryMode.PRODUCTION, phrase_var.get(), True)
            else:
                self._run_delivery(DeliveryMode.TEST)
            win.destroy()

        ttk.Button(buttons, text="閉じる", command=close).pack(side="right")
        if execute:
            ttk.Button(buttons, text="この内容で実行する", command=do_execute).pack(side="right", padx=8)

    def _run_delivery(self, mode: DeliveryMode, phrase: str = "", approved: bool = False) -> None:
        assert self.campaign is not None
        try:
            if mode is DeliveryMode.PRODUCTION:
                campaign, result = self.service.confirm_and_send_production(self.campaign, phrase, approved)
            else:
                campaign, result = self.service.execute_delivery(self.campaign, DeliveryMode.TEST)
        except SafetyError as exc:
            messagebox.showerror("配信を中止しました", str(exc))
            return
        self.campaign = campaign
        self.refresh_list(campaign.id)
        status = "成功" if result.ok else "失敗"
        messagebox.showinfo("配信結果", f"{MODE_LABELS[mode]}: {status}\n{result.message or result.error}")

    def show_history(self) -> None:
        win = tk.Toplevel(self)
        win.title("配信履歴")
        win.geometry("900x420")
        columns = ("time", "id", "subject", "mode", "targets", "exclude", "url", "result", "operator")
        tree = ttk.Treeview(win, columns=columns, show="headings")
        headings = {
            "time": "実行日時",
            "id": "案件ID",
            "subject": "件名",
            "mode": "モード",
            "targets": "対象件数",
            "exclude": "除外件数",
            "url": "共有URL",
            "result": "結果",
            "operator": "実行者",
        }
        for key, label in headings.items():
            tree.heading(key, text=label)
            tree.column(key, width=90 if key != "url" else 180)
        for record in self.service.list_history():
            tree.insert(
                "",
                tk.END,
                values=(
                    record.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                    record.campaign_id,
                    record.subject,
                    MODE_LABELS[record.mode],
                    record.target_count,
                    record.exclude_count,
                    record.drive_share_url,
                    "成功" if record.success else f"失敗:{record.error}",
                    record.operator_name,
                ),
            )
        tree.pack(fill="both", expand=True)
        ttk.Label(win, text="履歴にメールアドレス一覧は保存・表示しません。").pack(anchor="w", padx=8, pady=4)


def main() -> int:
    service = build_service()
    app = App(service)
    app.mainloop()
    return 0
