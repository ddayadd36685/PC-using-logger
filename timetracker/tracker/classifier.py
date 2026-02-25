from dataclasses import dataclass
from typing import Optional

from timetracker.config.site_aliases import SITE_ALIASES
from timetracker.tracker.browser_bridge import TabInfo
from timetracker.tracker.win_api import WindowInfo


@dataclass(frozen=True)
class CategoryResult:
    category_type: str
    category_key: str
    category_name: str


class Classifier:
    def __init__(
        self,
        app_aliases: Optional[dict[str, str]] = None,
        site_aliases: Optional[dict[str, str]] = None,
    ) -> None:
        self._app_aliases = app_aliases or {
            "chrome.exe": "Chrome",
            "msedge.exe": "Edge",
            "code.exe": "VSCode",
            "pycharm64.exe": "PyCharm",
            "explorer.exe": "资源管理器",
        }
        self._site_aliases = site_aliases or SITE_ALIASES

    def classify(self, window: Optional[WindowInfo], tab: Optional[TabInfo]) -> CategoryResult:
        if tab is not None:
            domain = getattr(tab, "domain", "") or ""
            if domain:
                name = self._site_aliases.get(domain, domain)
                return CategoryResult("site", domain, name)
        if window is None:
            return CategoryResult("app", "system.desktop", "系统/桌面")
        process_key = (window.process_name or "").lower()
        name = self._app_aliases.get(process_key, window.app_display or process_key)
        if name.endswith(".exe"):
            name = name[:-4]
        return CategoryResult("app", process_key, name)
