from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import CampaignRequest
from moriyama_mail.services.campaign_service import CampaignService


class RequestFormWindow(tk.Toplevel):
    """Dedicated intake form. Does not execute delivery."""

    def __init__(self, master: tk.Tk, service: CampaignService, on_submitted) -> None:
        super().__init__(master)
        self.service = service
        self.on_submitted = on_submitted
        self.title("配信依頼フォーム")
        self.geometry("720x640")
        self.transient(master)
        self.grab_set()
        self.subject_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.plan_var = tk.StringVar(value="")
        self.material_path: Path | None = None
        self.additions_csv: Path | None = None
        self.exclusions_csv: Path | None = None
        self.material_var = tk.StringVar(value="未選択")
        self.add_var = tk.StringVar(value="未選択")
        self.exclude_var = tk.StringVar(value="未選択")
        self._build()

    def _build(self) -> None:
        pad = ttk.Frame(self, padding=12)
        pad.pack(fill="both", expand=True)
        ttk.Label(pad, text="顧客がブラウザから送れないときの、担当者用入力です。配信はここでは実行しません。").pack(anchor="w")

        ttk.Label(pad, text="MyASPプラン（依頼時に必ず選択）").pack(anchor="w", pady=(12, 4))
        for plan in self.service.settings.myasp_plans:
            ttk.Radiobutton(pad, text=plan.label(), value=plan.key, variable=self.plan_var).pack(anchor="w")

        ttk.Label(pad, text="メール件名").pack(anchor="w", pady=(12, 0))
        ttk.Entry(pad, textvariable=self.subject_var).pack(fill="x")

        ttk.Label(pad, text="メール本文").pack(anchor="w", pady=(8, 0))
        self.body = tk.Text(pad, height=10, wrap="word")
        self.body.pack(fill="both", expand=True)

        ttk.Label(pad, text="備考").pack(anchor="w", pady=(8, 0))
        ttk.Entry(pad, textvariable=self.notes_var).pack(fill="x")

        files = ttk.Frame(pad)
        files.pack(fill="x", pady=12)
        ttk.Button(files, text="資料を選択", command=self._pick_material).pack(side="left")
        ttk.Label(files, textvariable=self.material_var).pack(side="left", padx=8)
        ttk.Button(files, text="追加する宛先CSV", command=self._pick_add).pack(side="left")
        ttk.Label(files, textvariable=self.add_var).pack(side="left", padx=8)

        excl = ttk.Frame(pad)
        excl.pack(fill="x")
        ttk.Button(excl, text="今回だけ送らない宛先CSV", command=self._pick_exclude).pack(side="left")
        ttk.Label(excl, textvariable=self.exclude_var).pack(side="left", padx=8)

        ttk.Label(
            pad,
            text="除外は、MyASPでその配信のときだけ送らない処理です。リストから名前は消しません。",
        ).pack(anchor="w", pady=(8, 0))

        ttk.Button(pad, text="依頼を登録して通知する", command=self._submit).pack(anchor="e", pady=12)

    def _pick_material(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="配信用資料")
        if path:
            self.material_path = Path(path)
            self.material_var.set(self.material_path.name)

    def _pick_add(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="追加する宛先CSV", filetypes=[("CSV", "*.csv *.txt"), ("すべて", "*.*")])
        if path:
            self.additions_csv = Path(path)
            self.add_var.set(self.additions_csv.name)

    def _pick_exclude(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="今回だけ送らない宛先CSV",
            filetypes=[("CSV", "*.csv *.txt"), ("すべて", "*.*")],
        )
        if path:
            self.exclusions_csv = Path(path)
            self.exclude_var.set(self.exclusions_csv.name)

    def _submit(self) -> None:
        request = CampaignRequest(
            subject=self.subject_var.get().strip(),
            body=self.body.get("1.0", tk.END).rstrip("\n"),
            notes=self.notes_var.get().strip(),
            myasp_plan_key=self.plan_var.get(),
            material_path=self.material_path,
            additions_csv=self.additions_csv,
            exclusions_csv=self.exclusions_csv,
        )
        try:
            campaign, notify_message = self.service.submit_request(request)
        except SafetyError as exc:
            messagebox.showwarning("登録できません", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("登録失敗", str(exc), parent=self)
            return
        messagebox.showinfo("依頼を受け付けました", f"{campaign.id} を登録しました。\n{notify_message}", parent=self)
        self.on_submitted(campaign)
        self.destroy()
