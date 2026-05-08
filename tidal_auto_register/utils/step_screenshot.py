# -*- coding: utf-8 -*-
"""
步骤截图记录工具。

每次程序执行都会创建一个新的时间戳目录，并在每个子步骤结束后保存全屏截图，
便于排查具体是在哪一步出现了行为异常。
"""

import importlib
import io
import json
import os
import re
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime


class StepScreenshotRecorder:
    """为每次运行建立独立截图目录，并记录每个子步骤的全屏截图。"""

    def __init__(self, project_root):
        self.project_root = os.path.abspath(project_root)
        self.base_dir = os.path.join(self.project_root, "data", "logs", "screenshots")
        os.makedirs(self.base_dir, exist_ok=True)

        self.started_at = datetime.now()
        self.started_timestamp = int(self.started_at.timestamp() * 1000)
        self.run_dir = os.path.join(
            self.base_dir,
            f"{self.started_at:%Y%m%d_%H%M%S}_{self.started_timestamp}",
        )
        os.makedirs(self.run_dir, exist_ok=True)

        self.manifest_path = os.path.join(self.run_dir, "manifest.jsonl")
        self.capture_index = 0
        self._mss_module = None
        self._mss_tools = None
        self._pyautogui = None

        self._load_backends()
        print(f"[截图] 本次运行截图目录: {self.run_dir}")

    def _load_backends(self):
        """优先使用 mss 做全屏截图，其次回退到 PyAutoGUI。"""
        output_buffer = io.StringIO()

        try:
            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                self._mss_module = importlib.import_module("mss")
                self._mss_tools = importlib.import_module("mss.tools")
        except Exception:
            self._mss_module = None
            self._mss_tools = None

        try:
            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                self._pyautogui = importlib.import_module("pyautogui")
        except Exception:
            self._pyautogui = None

    def _sanitize_step_name(self, step_name):
        normalized = re.sub(r"[<>:\"/\\|?*]+", "_", step_name.strip())
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized)
        return normalized.strip("_") or "unnamed_step"

    def _append_manifest(self, file_name, step_name, note):
        record = {
            "index": self.capture_index,
            "step_name": step_name,
            "note": note,
            "file_name": file_name,
            "captured_at": datetime.now().isoformat(timespec="milliseconds"),
        }
        with open(self.manifest_path, "a", encoding="utf-8") as manifest_file:
            manifest_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _capture_with_mss(self, output_path):
        if not self._mss_module or not self._mss_tools:
            return False

        try:
            with self._mss_module.mss() as sct:
                monitor = sct.monitors[0] if len(sct.monitors) > 1 else sct.monitors[1]
                screenshot = sct.grab(monitor)
                self._mss_tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
            return True
        except Exception:
            return False

    def _capture_with_pyautogui(self, output_path):
        if not self._pyautogui:
            return False

        try:
            screenshot = self._pyautogui.screenshot()
            screenshot.save(output_path)
            return True
        except Exception:
            return False

    def capture(self, step_name, driver=None, note=""):
        """截取当前全屏画面，并记录到本次运行的截图目录。"""
        self.capture_index += 1
        now = datetime.now()
        timestamp_ms = int(time.time() * 1000)
        safe_name = self._sanitize_step_name(step_name)
        file_name = f"{self.capture_index:03d}_{safe_name}_{now:%Y%m%d}_{now:%H%M%S}_{timestamp_ms}.png"
        output_path = os.path.join(self.run_dir, file_name)

        saved = self._capture_with_mss(output_path)
        if not saved:
            saved = self._capture_with_pyautogui(output_path)

        if not saved and driver is not None:
            try:
                driver.save_screenshot(output_path)
                saved = True
            except Exception:
                saved = False

        if saved:
            self._append_manifest(file_name, step_name, note)
            print(f"[截图] 已保存: {output_path}")
            return output_path

        print(f"[警告] 截图保存失败: {step_name}")
        return None