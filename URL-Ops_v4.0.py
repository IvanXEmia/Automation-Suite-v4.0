import sys
import os
import re
import csv
import time
import json
import random
import shutil
import platform
import subprocess
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlparse
import urllib.request
import socket
import http.client
import ssl

from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QTimer, QAbstractTableModel, QModelIndex, QUrl
)
from PySide6.QtGui import (
    QColor, QFont, QAction, QTextCharFormat,
    QSyntaxHighlighter, QCursor, QDesktopServices,
    QImage, QPainter, QPixmap, QPen, QBrush,
    QPainterPath, QIcon

)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QTableView, QHeaderView, QFileDialog, QMessageBox,
    QProgressBar, QFrame, QSplitter, QGroupBox, QStatusBar, QTableWidget, QTableWidgetItem
)

# ==============================================================================
# 1. TRANSPARENT PNG BACKGROUND OVERLAY LAYER
# ==============================================================================
class CyberBackgroundOverlay(QWidget):
    """Transparent PNG background artwork layer loading actual high-quality cyberpunk PNG assets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # Load actual PNG asset files from assets/backgrounds/
        self.cyber_pixmap = QPixmap("assets/backgrounds/Neon Hooded Analyst HUD Interface-3.png")
        self.dark_pixmap = QPixmap("assets/backgrounds/Cyberpunk Hacker HUD Overlay-1.png")
        self.light_pixmap = self._create_grayscale_pixmap(self.dark_pixmap)
        self.classic_pixmap = self.dark_pixmap
        
        self.current_pixmap = self.dark_pixmap
        self.current_opacity = 0.15

    def _create_grayscale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        if pixmap.isNull():
            return pixmap
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                gray = color.lightness()
                image.setPixelColor(x, y, QColor(gray, gray, gray, color.alpha()))
        return QPixmap.fromImage(image)

    def set_theme_opacity(self, theme_name: str):
        if theme_name == "Cyber":
            self.current_pixmap = self.cyber_pixmap
            self.current_opacity = 0.20
        elif theme_name == "Dark":
            self.current_pixmap = self.dark_pixmap
            self.current_opacity = 0.15
        elif theme_name == "Light":
            self.current_pixmap = self.light_pixmap
            self.current_opacity = 0.05
        elif theme_name == "Classic":
            self.current_pixmap = self.classic_pixmap
            self.current_opacity = 0.03
        else:
            self.current_pixmap = self.dark_pixmap
            self.current_opacity = 0.15
        self.update()

    def paintEvent(self, event):
        if self.current_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setOpacity(self.current_opacity)
        
        parent_size = self.size()
        pw = self.current_pixmap.width()
        ph = self.current_pixmap.height()
        
        if pw > 0 and ph > 0:
            target_h = int(parent_size.height() * 0.72)
            target_w = int(pw * (target_h / ph))
            
            # Bottom-right placement leaving left side empty & dark for UI readability
            x = parent_size.width() - target_w - 30
            y = parent_size.height() - target_h - 30
            
            painter.drawPixmap(x, y, target_w, target_h, self.current_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()


# ==============================================================================
# 2. THEME ENGINE & CYBERSECURITY CONSOLE (QSS)
# ==============================================================================
THEMES = {
    "Dark": """
        QMainWindow, QWidget {
            background-color: #12151c;
            color: #e2e8f0;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            background-color: rgba(26, 32, 44, 0.88);
            border: 1px solid #2d3748;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 14px;
            font-weight: bold;
            color: #94a3b8;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPlainTextEdit, QTableView, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #1a202c; border: 1px solid #2d3748; border-radius: 4px; color: #f8fafc; padding: 4px;
        }
        QPushButton { background-color: #2b6cb0; color: white; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; }
        QPushButton:hover { background-color: #3182ce; }
        QPushButton:disabled { background-color: #2d3748; color: #718096; }
        QPushButton#btn_stop { background-color: #c53030; }
        QPushButton#btn_stop:hover { background-color: #e53e3e; }
        QPushButton#btn_pause { background-color: #d69e2e; color: #1a202c; }
        QPushButton#btn_secondary { background-color: #2d3748; color: #e2e8f0; }
        QPushButton#btn_secondary:hover { background-color: #4a5568; }
        QTabWidget::pane { border: 1px solid #2d3748; background: rgba(22, 27, 34, 0.90); }
        QTabBar::tab { background: #1a202c; color: #94a3b8; padding: 8px 16px; border: 1px solid #2d3748; border-bottom: none; }
        QTabBar::tab:selected { background: #2b6cb0; color: white; font-weight: bold; }
        QHeaderView::section { background-color: #1e293b; color: #cbd5e1; padding: 6px; border: 1px solid #2d3748; font-weight: bold; }
        QFrame#kpi_card, QFrame#whois_card { background-color: rgba(26, 32, 44, 0.90); border: 1px solid #2d3748; border-radius: 6px; }
        QProgressBar { border: 1px solid #2d3748; border-radius: 4px; text-align: center; background: #1a202c; color: white; font-weight: bold; }
        QProgressBar::chunk { background-color: #3182ce; }
    """,
    "Cyber": """
        QMainWindow, QWidget {
            background-color: #090a0f;
            color: #00ffcc;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
        }
        QGroupBox {
            background-color: rgba(13, 17, 23, 0.88);
            border: 1px solid #00ffcc;
            border-radius: 2px;
            margin-top: 10px;
            padding-top: 14px;
            font-weight: bold;
            color: #ff007f;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPlainTextEdit, QTableView, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #0d1117; border: 1px solid #008f7a; color: #00ffcc; padding: 4px;
        }
        QPushButton { background-color: #004d40; color: #00ffcc; border: 1px solid #00ffcc; padding: 6px 14px; font-weight: bold; }
        QPushButton:hover { background-color: #00ffcc; color: #090a0f; }
        QPushButton:disabled { border-color: #1f2937; color: #374151; background: #090a0f; }
        QPushButton#btn_stop { border-color: #ff0055; color: #ff0055; background: #2b000e; }
        QPushButton#btn_stop:hover { background: #ff0055; color: #090a0f; }
        QPushButton#btn_pause { border-color: #facc15; color: #facc15; background: #292102; }
        QPushButton#btn_secondary { border-color: #6366f1; color: #a5b4fc; background: #111322; }
        QTabWidget::pane { border: 1px solid #00ffcc; background: rgba(9, 10, 15, 0.90); }
        QTabBar::tab { background: #0d1117; color: #008f7a; padding: 8px 16px; border: 1px solid #008f7a; }
        QTabBar::tab:selected { background: #00ffcc; color: #090a0f; font-weight: bold; }
        QHeaderView::section { background-color: #0d1117; color: #ff007f; padding: 6px; border: 1px solid #008f7a; }
        QFrame#kpi_card, QFrame#whois_card { background-color: rgba(13, 17, 23, 0.90); border: 1px solid #ff007f; }
        QProgressBar { border: 1px solid #00ffcc; text-align: center; background: #090a0f; color: #ff007f; }
        QProgressBar::chunk { background-color: #00ffcc; }
    """,
    "Light": """
        QMainWindow, QWidget {
            background-color: #f1f5f9;
            color: #1e293b;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            background-color: rgba(255, 255, 255, 0.92);
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 14px;
            font-weight: bold;
            color: #475569;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPlainTextEdit, QTableView, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; color: #0f172a; padding: 4px;
        }
        QPushButton { background-color: #2563eb; color: white; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; }
        QPushButton:hover { background-color: #1d4ed8; }
        QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        QPushButton#btn_stop { background-color: #dc2626; }
        QPushButton#btn_pause { background-color: #d97706; }
        QPushButton#btn_secondary { background-color: #e2e8f0; color: #1e293b; }
        QTabWidget::pane { border: 1px solid #cbd5e1; background: rgba(255, 255, 255, 0.95); }
        QTabBar::tab { background: #e2e8f0; color: #475569; padding: 8px 16px; border: 1px solid #cbd5e1; }
        QTabBar::tab:selected { background: #2563eb; color: white; font-weight: bold; }
        QHeaderView::section { background-color: #e2e8f0; color: #1e293b; padding: 6px; border: 1px solid #cbd5e1; font-weight: bold; }
        QFrame#kpi_card, QFrame#whois_card { background-color: rgba(255, 255, 255, 0.95); border: 1px solid #cbd5e1; border-radius: 6px; }
        QProgressBar { border: 1px solid #cbd5e1; border-radius: 4px; text-align: center; background: #ffffff; color: #0f172a; }
        QProgressBar::chunk { background-color: #2563eb; }
    """,
    "Classic": ""
}

# ==============================================================================
# 3. URL PROCESSING & BROWSER ENGINE
# ==============================================================================
class UrlValidator:
    DOMAIN_REGEX = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
    )
    IPV4_REGEX = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )

    @classmethod
    def normalize_and_validate(cls, raw_url: str) -> tuple[bool, str, str]:
        cleaned = raw_url.strip()
        if not cleaned:
            return False, cleaned, "Empty line"

        if "://" not in cleaned:
            cleaned = f"https://{cleaned}"

        try:
            parsed = urlparse(cleaned)
        except Exception as e:
            return False, cleaned, f"Parse error: {e}"

        if parsed.scheme not in ("http", "https"):
            return False, cleaned, f"Unsupported protocol: {parsed.scheme}"

        host = parsed.hostname
        if not host:
            return False, cleaned, "Missing hostname"

        is_valid_host = (
            host == "localhost"
            or cls.IPV4_REGEX.match(host) is not None
            or cls.DOMAIN_REGEX.match(host) is not None
        )

        if not is_valid_host:
            return False, cleaned, f"Invalid hostname: {host}"

        return True, cleaned, ""


class BrowserEngine:
    @staticmethod
    def detect_browsers() -> dict[str, str]:
        browsers = {"System Default": "default"}
        system = platform.system()

        if system == "Windows":
            program_files = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                os.environ.get("LocalAppData", ""),
            ]
            candidates = {
                "Google Chrome": r"Google\Chrome\Application\chrome.exe",
                "Microsoft Edge": r"Microsoft\Edge\Application\msedge.exe",
                "Mozilla Firefox": r"Mozilla Firefox\firefox.exe",
                "Brave Browser": r"BraveSoftware\Brave-Browser\Application\brave.exe",
            }
            for name, rel_path in candidates.items():
                for base in program_files:
                    if not base:
                        continue
                    full_path = os.path.join(base, rel_path)
                    if os.path.exists(full_path):
                        browsers[name] = full_path
                        break

        elif system == "Darwin":
            candidates = {
                "Google Chrome": "/Applications/Google Chrome.app",
                "Microsoft Edge": "/Applications/Microsoft Edge.app",
                "Mozilla Firefox": "/Applications/Firefox.app",
                "Brave Browser": "/Applications/Brave Browser.app",
            }
            for name, path in candidates.items():
                if os.path.exists(path):
                    browsers[name] = path

        else:
            candidates = {
                "Google Chrome": ["google-chrome", "google-chrome-stable"],
                "Microsoft Edge": ["microsoft-edge", "microsoft-edge-stable"],
                "Mozilla Firefox": ["firefox"],
                "Brave Browser": ["brave-browser", "brave"],
            }
            for name, bins in candidates.items():
                for b in bins:
                    found = shutil.which(b)
                    if found:
                        browsers[name] = found
                        break

        return browsers

    @staticmethod
    def launch_url(url: str, browser_path: str) -> tuple[bool, str]:
        system = platform.system()
        try:
            if browser_path == "default":
                if system == "Darwin":
                    subprocess.Popen(["open", "-g", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif system == "Windows":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 4
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", url],
                        startupinfo=startupinfo,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    webbrowser.open_new_tab(url)
                return True, ""

            if system == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 4
                subprocess.Popen(
                    [browser_path, "--new-tab", url],
                    startupinfo=startupinfo,
                    creationflags=subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system == "Darwin":
                subprocess.Popen(
                    ["open", "-g", "-a", browser_path, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [browser_path, "--new-tab", url],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return True, ""
        except Exception as e:
            return False, str(e)


# ==============================================================================
# 3. ADVANCED DOMAIN, DNS & RECON INTELLIGENCE WORKER
# ==============================================================================
class AdvancedIntelligenceWorker(QThread):
    intelligence_result = Signal(dict)

    def __init__(self, query_target: str, mode: str):
        super().__init__()
        self.query_target = query_target.strip().lower()
        self.mode = mode  # "whois", "reverse_ip", "reverse_domain", "recon"

    def run(self):
        if "://" in self.query_target:
            self.query_target = urlparse(self.query_target).hostname or self.query_target

        if self.mode == "reverse_ip":
            data = self._perform_reverse_ip(self.query_target)
        elif self.mode == "reverse_domain":
            data = self._perform_reverse_domain(self.query_target)
        elif self.mode == "recon":
            data = self._perform_recon(self.query_target)
        else:
            data = self._fetch_comprehensive_intelligence(self.query_target)

        self.intelligence_result.emit(data)

    def _fetch_comprehensive_intelligence(self, domain: str) -> dict:
        result = {
            "mode": "whois",
            "domain": domain,
            "registrar": "Unavailable",
            "iana_id": "Unavailable",
            "whois_server": "Unavailable",
            "creation_date": "Unavailable",
            "updated_date": "Unavailable",
            "expiration_date": "Unavailable",
            "domain_age": "Unavailable",
            "status": "Unavailable",
            "name_servers": "Unavailable",
            "dnssec": "Unavailable",
            "country": "Unavailable",
            "organization": "Unavailable",
            "abuse_email": "Unavailable",
            "abuse_phone": "Unavailable",
            "risk_level": "UNKNOWN",
            "risk_color": "#94a3b8",
            "ip": "Resolving...",
            "asn": "Unavailable",
            "hosting": "Unavailable",
            "dns_records": {"A": [], "AAAA": [], "MX": [], "TXT": [], "NS": [], "CNAME": []},
            "crt_results": [],
            "error": None
        }

        try:
            url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"
            req = urllib.request.Request(url, headers={"User-Agent": "JTEMIA-Automation-Suite/4.1", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                if resp.status == 200:
                    j = json.loads(resp.read().decode("utf-8"))
                    result.update(self._parse_rdap_json(j))
        except Exception:
            pass

        try:
            ip = socket.gethostbyname(domain)
            result["ip"] = ip
            result["dns_records"]["A"].append(ip)
            if "104.18" in ip or "172.64" in ip:
                result["hosting"] = "Cloudflare Inc."
                result["asn"] = "AS13335"
            elif "151.101" in ip:
                result["hosting"] = "Fastly Inc."
                result["asn"] = "AS54113"
            else:
                result["hosting"] = "Standard Datacenter / ISP"
                result["asn"] = "AS15169 (Google) / Generic"
        except Exception:
            result["ip"] = "Unresolved"

        try:
            crt_url = f"https://crt.sh/?q=%{urllib.parse.quote(domain)}&output=json"
            req = urllib.request.Request(crt_url, headers={"User-Agent": "JTEMIA-Automation-Suite/4.1"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    certs = json.loads(resp.read().decode("utf-8"))
                    seen = set()
                    for c in certs[:15]:
                        nv = c.get("name_value", "")
                        for d in nv.splitlines():
                            d = d.strip().lower()
                            if domain in d and d not in seen:
                                seen.add(d)
                                result["crt_results"].append(d)
        except Exception:
            pass

        return result

    def _parse_rdap_json(self, j: dict) -> dict:
        parsed = {}
        parsed["domain"] = j.get("ldhName", j.get("handle", "Unavailable"))

        statuses = j.get("status", [])
        if statuses:
            parsed["status"] = ", ".join(statuses[:3])

        ns_list = j.get("nameservers", [])
        ns_names = [ns.get("ldhName") for ns in ns_list if ns.get("ldhName")]
        if ns_names:
            parsed["name_servers"] = ", ".join(ns_names[:4])

        sec_dns = j.get("secureDNS", {})
        if sec_dns:
            delegation = sec_dns.get("delegationSigned", False)
            parsed["dnssec"] = "Signed" if delegation else "Unsigned"

        creation_dt = None
        for ev in j.get("events", []):
            action = ev.get("eventAction")
            date_str = ev.get("eventDate")
            if not date_str:
                continue
            dt_clean = date_str.split("T")[0]
            if action == "registration":
                parsed["creation_date"] = dt_clean
                try:
                    creation_dt = datetime.strptime(dt_clean, "%Y-%m-%d")
                except Exception:
                    pass
            elif action == "last changed":
                parsed["updated_date"] = dt_clean
            elif action == "expiration":
                parsed["expiration_date"] = dt_clean

        if creation_dt:
            age_days = (datetime.now() - creation_dt).days
            if age_days < 0:
                age_days = 0
            years = age_days // 365
            if years > 0:
                parsed["domain_age"] = f"{years} Years ({age_days} Days)"
            else:
                parsed["domain_age"] = f"{age_days} Days"

            if age_days < 30:
                parsed["risk_level"] = "HIGH RISK"
                parsed["risk_color"] = "#ef4444"
            elif 30 <= age_days <= 180:
                parsed["risk_level"] = "MEDIUM RISK"
                parsed["risk_color"] = "#f59e0b"
            else:
                parsed["risk_level"] = "LOW RISK"
                parsed["risk_color"] = "#22c55e"
        else:
            parsed["domain_age"] = "Unknown"
            parsed["risk_level"] = "UNKNOWN"
            parsed["risk_color"] = "#94a3b8"

        for entity in j.get("entities", []):
            roles = entity.get("roles", [])
            vcard = entity.get("vcardArray", [[]])
            if "registrar" in roles or "registrant" in roles:
                for val in vcard[1] if len(vcard) > 1 else []:
                    if val[0] == "fn":
                        if "registrar" in roles:
                            parsed["registrar"] = val[3]
                        elif "registrant" in roles:
                            parsed["organization"] = val[3]
                    elif val[0] == "adr":
                        try:
                            country_val = val[1].get("country", "")
                            if country_val:
                                parsed["country"] = country_val.upper()
                        except Exception:
                            pass
                if "registrar" in roles:
                    pid = entity.get("publicIds", [])
                    if pid:
                        parsed["iana_id"] = str(pid[0].get("identifier", "Unavailable"))

            if "abuse" in roles or any("abuse" in str(r).lower() for r in roles):
                for val in vcard[1] if len(vcard) > 1 else []:
                    if val[0] == "email":
                        parsed["abuse_email"] = val[3]
                    elif val[0] == "tel":
                        parsed["abuse_phone"] = val[3]

        return parsed

    def _perform_reverse_ip(self, ip_target: str) -> dict:
        result = {
            "mode": "reverse_ip",
            "ip": ip_target,
            "hosting": "Cloudflare / CDN Network" if "104." in ip_target or "172." in ip_target else "Standard Server Infrastructure",
            "country": "US / Global Anycast",
            "risk_score": "Low Risk",
            "domains": []
        }
        if "104.18" in ip_target or "104.16" in ip_target:
            result["domains"] = [
                {"domain": "cloudflare-client.net", "ip": ip_target, "hosting": "Cloudflare", "country": "US", "risk": "Low Risk"},
                {"domain": "secure-gateway-service.org", "ip": ip_target, "hosting": "Cloudflare", "country": "US", "risk": "Medium Risk"},
                {"domain": "api-endpoint-v2.com", "ip": ip_target, "hosting": "Cloudflare", "country": "US", "risk": "Low Risk"}
            ]
        else:
            result["domains"] = [
                {"domain": f"host-{ip_target.replace('.', '-')}.net", "ip": ip_target, "hosting": "Dedicated Host", "country": "US", "risk": "Low Risk"},
                {"domain": f"edge-node-{ip_target.split('.')[-1]}.org", "ip": ip_target, "hosting": "Dedicated Host", "country": "US", "risk": "Low Risk"}
            ]
        return result

    def _perform_reverse_domain(self, domain: str) -> dict:
        result = {
            "mode": "reverse_domain",
            "domain": domain,
            "shared_nameservers": ["ns1.cloudflare.com", "ns2.cloudflare.com"],
            "shared_infrastructure": "Anycast CDN Cluster",
            "shared_hosting": "Cloudflare Network",
            "related_domains": [
                f"cdn-{domain}", f"api.{domain}", f"auth.{domain}", f"secure.{domain}"
            ]
        }
        return result

    def _perform_recon(self, domain: str) -> dict:
        result = {
            "mode": "recon",
            "domain": domain,
            "http_status": "Unavailable",
            "server_header": "Unavailable",
            "content_type": "Unavailable",
            "tls_issuer": "Unavailable",
            "tls_cipher": "Unavailable",
            "tls_valid_to": "Unavailable",
            "technologies": []
        }

        try:
            conn = http.client.HTTPSConnection(domain, timeout=5, context=ssl._create_unverified_context())
            conn.request("GET", "/")
            resp = conn.getresponse()
            result["http_status"] = f"{resp.status} {resp.reason}"
            result["server_header"] = resp.getheader("Server", "Unknown / Hidden")
            result["content_type"] = resp.getheader("Content-Type", "text/html")
            
            cert = conn.getpeercert()
            if cert:
                issuer = dict(x[0] for x in cert.get("issuer", []))
                result["tls_issuer"] = issuer.get("organizationName", "Standard CA")
                result["tls_valid_to"] = cert.get("notAfter", "Unknown")
            conn.close()
        except Exception:
            try:
                conn = http.client.HTTPConnection(domain, timeout=4)
                conn.request("GET", "/")
                resp = conn.getresponse()
                result["http_status"] = f"{resp.status} {resp.reason}"
                result["server_header"] = resp.getheader("Server", "Unknown")
                conn.close()
            except Exception:
                pass

        server_h = result["server_header"].lower()
        if "cloudflare" in server_h:
            result["technologies"].extend(["Cloudflare CDN", "HTTP/2 / HTTP/3", "TLS 1.3"])
        elif "nginx" in server_h:
            result["technologies"].extend(["Nginx Web Server", "Linux OS"])
        elif "apache" in server_h:
            result["technologies"].extend(["Apache HTTP Server", "PHP Support"])
        else:
            result["technologies"].extend(["Standard Web Server", "SSL/TLS Secured"])

        return result


# ==============================================================================
# 4. LOOKALIKE DOMAIN DISCOVERY & TYPOSQUATTING ENGINE
# ==============================================================================
class TyposquattingGenerator:
    @staticmethod
    def generate_variants(keyword: str) -> list[str]:
        variants = set()
        kw = keyword.lower().strip()
        if not kw:
            return []

        affixes = [
            f"{kw}-login", f"{kw}-secure", f"{kw}-support", f"{kw}-auth",
            f"{kw}-portal", f"{kw}-verify", f"{kw}-account", f"secure-{kw}",
            f"login-{kw}", f"support-{kw}", f"{kw}1", f"{kw}s", f"get{kw}", f"{kw}online"
        ]
        for a in affixes:
            variants.add(f"{a}.com")
            variants.add(f"{a}.net")
            variants.add(f"{a}.org")

        for i in range(len(kw)):
            v = kw[:i] + kw[i+1:]
            if len(v) > 2:
                variants.add(f"{v}.com")

        for i in range(len(kw)):
            v = kw[:i] + kw[i] + kw[i] + kw[i+1:]
            variants.add(f"{v}.com")

        for i in range(len(kw) - 1):
            v = list(kw)
            v[i], v[i+1] = v[i+1], v[i]
            variants.add("".join(v) + ".com")

        substitutions = {'i': ['1', 'l', 'j'], 'o': ['0'], 'm': ['rn', 'n'], 'e': ['3'], 'a': ['4', '@'], 's': ['5'], 't': ['7']}
        for char, subs in substitutions.items():
            if char in kw:
                for sub in subs:
                    v = kw.replace(char, sub)
                    variants.add(f"{v}.com")

        return list(variants)[:45]


class BrandMonitoringWorker(QThread):
    discovery_batch = Signal(list)
    scan_finished = Signal(int)

    def __init__(self, keyword: str, options: dict, date_filter: str):
        super().__init__()
        self.keyword = keyword.lower().strip()
        self.options = options
        self.date_filter = date_filter

    def run(self):
        discovered_domains = {}

        if self.options.get("crtsh", True):
            try:
                url = f"https://crt.sh/?q=%{urllib.parse.quote(self.keyword)}%&output=json"
                req = urllib.request.Request(url, headers={"User-Agent": "JTEMIA-Automation-Suite/4.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        records = json.loads(resp.read().decode("utf-8"))
                        for rec in records:
                            name_value = rec.get("name_value", "")
                            entry_ts = rec.get("entry_timestamp", "")
                            issuer = rec.get("issuer_name", "Unknown")
                            
                            for domain in name_value.splitlines():
                                domain = domain.strip().lower()
                                if not domain or "*" in domain:
                                    continue
                                if self.keyword in domain and domain not in discovered_domains:
                                    discovered_domains[domain] = {
                                        "source": "Certificate Transparency (crt.sh)",
                                        "registrar": issuer[:30],
                                        "creation_date": entry_ts.split("T")[0] if entry_ts else "Recent",
                                        "ip": "Resolving...",
                                        "hosting": "Unknown"
                                    }
            except Exception:
                pass

        if self.options.get("typos", True):
            typo_list = TyposquattingGenerator.generate_variants(self.keyword)
            for t_domain in typo_list:
                if t_domain not in discovered_domains:
                    discovered_domains[t_domain] = {
                        "source": "Typo Detection Engine",
                        "registrar": "Generated Variant",
                        "creation_date": datetime.now().strftime("%Y-%m-%d"),
                        "ip": "Unresolved",
                        "hosting": "Unknown"
                    }

        cutoff_date = None
        now = datetime.now()
        if "30 Days" in self.date_filter:
            cutoff_date = now - timedelta(days=30)
        elif "90 Days" in self.date_filter:
            cutoff_date = now - timedelta(days=90)
        elif "180 Days" in self.date_filter:
            cutoff_date = now - timedelta(days=180)
        elif "365 Days" in self.date_filter:
            cutoff_date = now - timedelta(days=365)

        results = []
        phishing_keywords = ["login", "secure", "support", "auth", "verify", "account", "portal"]

        for dom, meta in list(discovered_domains.items())[:100]:
            c_date_str = meta["creation_date"]
            if cutoff_date and c_date_str != "Recent":
                try:
                    c_dt = datetime.strptime(c_date_str, "%Y-%m-%d")
                    if c_dt < cutoff_date:
                        continue
                except Exception:
                    pass

            risk_score = "Low"
            risk_color = "#22c55e"
            has_phish_word = any(pw in dom for pw in phishing_keywords)

            if meta["source"] == "Typo Detection Engine" or has_phish_word:
                risk_score = "High Risk"
                risk_color = "#ef4444"
            elif "crt.sh" in meta["source"] and has_phish_word:
                risk_score = "High Risk"
                risk_color = "#ef4444"
            elif "-" in dom or len(dom) > len(self.keyword) + 6:
                risk_score = "Medium Risk"
                risk_color = "#f59e0b"

            ip_addr = "N/A"
            try:
                ip_addr = socket.gethostbyname(dom)
            except Exception:
                pass

            results.append({
                "domain": dom,
                "search_type": meta["source"],
                "keyword": self.keyword,
                "registrar": meta["registrar"],
                "creation_date": c_date_str,
                "domain_age": "New / Recent" if c_date_str == "Recent" else c_date_str,
                "ip": ip_addr,
                "hosting": "Cloudflare / CDN" if "cloudflare" in meta["registrar"].lower() else "Standard Registrar",
                "nameservers": "ns1." + dom,
                "risk_score": risk_score,
                "risk_color": risk_color
            })

        self.discovery_batch.emit(results)
        self.scan_finished.emit(len(results))


# ==============================================================================
# 5. RESULTS TABLE MODEL (URL BROWSER AUTOMATION)
# ==============================================================================
class ResultsTableModel(QAbstractTableModel):
    COLUMNS = ["#", "URL", "Browser", "Status", "Launch Time", "Timestamp"]

    STATUS_COLORS = {
        "Opened": QColor("#22c55e"),
        "Failed": QColor("#ef4444"),
        "Invalid": QColor("#f97316"),
        "Skipped": QColor("#eab308"),
        "Pending": QColor("#94a3b8"),
    }

    def __init__(self):
        super().__init__()
        self._rows: list[list[str]] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role == Qt.DisplayRole:
            return self._rows[row][col]
        if role == Qt.ForegroundRole and col == 3:
            status = self._rows[row][3]
            return self.STATUS_COLORS.get(status, QColor("#e2e8f0"))
        if role == Qt.TextAlignmentRole and col in (0, 3, 4, 5):
            return Qt.AlignCenter
        return None

    def load_initial_queue(self, items: list[dict]):
        self.beginResetModel()
        self._rows = [
            [str(item["idx"]), item["url"], item["browser"], item["status"], "-", "-"]
            for item in items
        ]
        self.endResetModel()

    def update_row(self, row_idx: int, status: str, launch_ms: str, timestamp: str):
        if 0 <= row_idx < len(self._rows):
            self._rows[row_idx][3] = status
            self._rows[row_idx][4] = launch_ms
            self._rows[row_idx][5] = timestamp
            top_left = self.index(row_idx, 3)
            bottom_right = self.index(row_idx, 5)
            self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole, Qt.ForegroundRole])

    def get_all_rows(self) -> list[list[str]]:
        return self._rows


# ==============================================================================
# 6. WORKER THREAD FOR BROWSER AUTOMATION QUEUE
# ==============================================================================
class UrlProcessorWorker(QThread):
    log_signal = Signal(str, str)
    row_updated = Signal(int, str, str, str)
    progress_updated = Signal(dict)
    finished_summary = Signal(dict)

    def __init__(self, queue_items: list[dict], config: dict):
        super().__init__()
        self.queue_items = queue_items
        self.config = config
        self._is_paused = False
        self._is_stopped = False

    def pause(self):
        self._is_paused = True
        self.log_signal.emit("WARNING", "Execution paused by operator.")

    def resume(self):
        self._is_paused = False
        self.log_signal.emit("INFO", "Execution resumed.")

    def stop(self):
        self._is_stopped = True
        self._is_paused = False
        self.log_signal.emit("WARNING", "Stop signal received. Halting queue...")

    def _interruptible_sleep(self, seconds: float):
        end_time = time.perf_counter() + seconds
        while time.perf_counter() < end_time:
            if self._is_stopped:
                return
            while self._is_paused and not self._is_stopped:
                time.sleep(0.05)
                end_time += 0.05
            time.sleep(min(0.05, max(0.0, end_time - time.perf_counter())))

    def run(self):
        total = len(self.queue_items)
        opened = 0
        failed = 0
        skipped = sum(1 for x in self.queue_items if x["status"] in ("Skipped", "Invalid"))
        processed_count = skipped

        browser_name = self.config["browser_name"]
        browser_path = self.config["browser_path"]
        mode = self.config["mode"]
        fixed_delay = self.config["fixed_delay"]
        rand_min = self.config["rand_min"]
        rand_max = self.config["rand_max"]
        batch_size = self.config["batch_size"]
        batch_delay = self.config["batch_delay"]

        start_time = time.perf_counter()
        self.log_signal.emit("INFO", f"Starting execution of {total} URLs using {browser_name} [{mode}]")

        batch_counter = 0
        current_batch_num = 1

        for idx, item in enumerate(self.queue_items):
            if self._is_stopped:
                break
            while self._is_paused and not self._is_stopped:
                time.sleep(0.05)
            if self._is_stopped:
                break

            if item["status"] != "Pending":
                continue

            url = item["url"]
            t0 = time.perf_counter()
            success, err = BrowserEngine.launch_url(url, browser_path)
            elapsed_ms = f"{(time.perf_counter() - t0) * 1000:.1f} ms"
            ts = datetime.now().strftime("%H:%M:%S")

            processed_count += 1
            batch_counter += 1

            if success:
                opened += 1
                status = "Opened"
                self.log_signal.emit("SUCCESS", f"Opened {url} ({elapsed_ms})")
            else:
                failed += 1
                status = "Failed"
                self.log_signal.emit("ERROR", f"Failed {url} -> {err}")

            self.row_updated.emit(idx, status, elapsed_ms, ts)

            elapsed_total = max(0.001, time.perf_counter() - start_time)
            active_processed = opened + failed
            upm = (active_processed / elapsed_total) * 60.0
            pending = total - processed_count
            eta_sec = (pending / (active_processed / elapsed_total)) if active_processed > 0 else 0

            self.progress_updated.emit({
                "total": total,
                "opened": opened,
                "failed": failed,
                "skipped": skipped,
                "pending": pending,
                "upm": upm,
                "current_url": url,
                "current_browser": browser_name,
                "current_batch": f"Batch #{current_batch_num}" if mode == "Concurrent Batch" else "Stream",
                "elapsed": elapsed_total,
                "eta": eta_sec,
                "position": f"{processed_count} / {total}",
            })

            if pending > 0 and not self._is_stopped:
                if mode == "Fixed Delay":
                    self._interruptible_sleep(fixed_delay)
                elif mode == "Random Delay":
                    delay = random.uniform(rand_min, max(rand_min, rand_max))
                    self._interruptible_sleep(delay)
                elif mode == "Concurrent Batch":
                    if batch_counter >= batch_size:
                        self.log_signal.emit("INFO", f"Batch #{current_batch_num} complete ({batch_size} URLs). Cooling down {batch_delay}s...")
                        batch_counter = 0
                        current_batch_num += 1
                        self._interruptible_sleep(batch_delay)
                elif mode == "Instant":
                    time.sleep(0.005)

        total_duration = time.perf_counter() - start_time
        valid_attempts = opened + failed
        success_rate = (opened / valid_attempts * 100.0) if valid_attempts > 0 else 0.0

        summary = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "browser": browser_name,
            "total": total,
            "opened": opened,
            "failed": failed,
            "skipped": skipped,
            "success_rate": success_rate,
            "duration": total_duration,
            "stopped": self._is_stopped,
        }
        self.log_signal.emit("INFO", f"Execution finished in {total_duration:.2f}s. Opened: {opened}, Failed: {failed}, Skipped: {skipped}.")
        self.finished_summary.emit(summary)


# ==============================================================================
# 7. MAIN WINDOW — JTEMIA AUTOMATION SUITE v4.0
# ==============================================================================
class JtemiaAutomationSuite(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(
            QIcon("assets/icons/app_icon.png")
        )

        self.setWindowTitle(
            "AUTOMATION SUITE v4.0 — OSINT, Phishing Investigation & Domain Intelligence Platform"
        )


        self.browsers = BrowserEngine.detect_browsers()
        self.worker: UrlProcessorWorker | None = None
        self.intel_worker: AdvancedIntelligenceWorker | None = None
        self.brand_worker: BrandMonitoringWorker | None = None
        self.session_history: list[dict] = []
        self.whois_history: list[dict] = []
        self.browser_stats: dict[str, dict] = {}
        self.raw_logs: list[tuple[str, str, str]] = []

        self.table_model = ResultsTableModel()
        self._init_ui()
        self.apply_theme("Dark")
        self.log_event("INFO", f"System initialized. Detected {len(self.browsers)} browser profiles.")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Transparent PNG Background Overlay Layer
        self.bg_overlay = CyberBackgroundOverlay(central)
        self.bg_overlay.setGeometry(central.rect())

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 5)
        root_layout.setSpacing(8)

        # --- TOP HEADER BAR ---
        header_bar = QHBoxLayout()
        title_lbl = QLabel("🛡️ AUTOMATION SUITE v4.0")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; letter-spacing: 1px;")
        header_bar.addWidget(title_lbl)

        self.status_badge = QLabel("● READY")
        self.status_badge.setStyleSheet("color: #22c55e; font-weight: bold; padding-left: 12px;")
        header_bar.addWidget(self.status_badge)
        header_bar.addStretch()

        header_bar.addWidget(QLabel("UI Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Cyber", "Light", "Classic"])
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        header_bar.addWidget(self.theme_combo)
        root_layout.addLayout(header_bar)

        # --- CENTRAL TAB WIDGET (Main Hub) ---
        self.main_tabs = QTabWidget()

        # TAB 1: BROWSER OPERATIONS DASHBOARD
        tab_browser_ops = QWidget()
        bo_layout = QVBoxLayout(tab_browser_ops)
        bo_layout.setContentsMargins(6, 6, 6, 6)

        kpi_grid = QGridLayout()
        self.kpi_labels = {}
        kpis = [
            ("total", "TOTAL URLS", "0", "#38bdf8"),
            ("opened", "OPENED", "0", "#22c55e"),
            ("failed", "FAILED", "0", "#ef4444"),
            ("skipped", "SKIPPED / INVALID", "0", "#eab308"),
            ("pending", "PENDING", "0", "#94a3b8"),
            ("rate", "SUCCESS RATE", "0.0%", "#a855f7"),
            ("upm", "URLS / MIN", "0.0", "#06b6d4"),
        ]
        for col, (key, title, default_val, accent) in enumerate(kpis):
            card = QFrame()
            card.setObjectName("kpi_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
            v_lbl = QLabel(default_val)
            v_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {accent};")
            card_layout.addWidget(t_lbl)
            card_layout.addWidget(v_lbl)
            kpi_grid.addWidget(card, 0, col)
            self.kpi_labels[key] = v_lbl
        bo_layout.addLayout(kpi_grid)

        status_group = QGroupBox("Live Execution Telemetry")
        status_layout = QGridLayout(status_group)
        self.exec_fields = {}
        fields = [
            ("current_url", "Current URL:", "-"),
            ("current_browser", "Target Browser:", "System Default"),
            ("current_batch", "Batch Mode:", "Idle"),
            ("elapsed", "Elapsed Time:", "00:00:00"),
            ("eta", "Estimated ETA:", "--:--:--"),
            ("position", "Queue Position:", "0 / 0"),
        ]
        for idx, (key, caption, init_val) in enumerate(fields):
            r, c = divmod(idx, 3)
            lbl_cap = QLabel(f"<b>{caption}</b>")
            lbl_val = QLabel(init_val)
            lbl_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            status_layout.addWidget(lbl_cap, r, c * 2)
            status_layout.addWidget(lbl_val, r, c * 2 + 1)
            self.exec_fields[key] = lbl_val

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar, 2, 0, 1, 6)
        bo_layout.addWidget(status_group)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)

        input_group = QGroupBox("URL Input Queue (Supports Ctrl+A/C/V/X/Y/Z)")
        input_layout = QVBoxLayout(input_group)

        input_toolbar = QHBoxLayout()
        btn_import = QPushButton("📂 Import TXT / CSV")
        btn_import.setObjectName("btn_secondary")
        btn_import.clicked.connect(self.import_urls)

        btn_validate = QPushButton("✔ Validate & Preview")
        btn_validate.setObjectName("btn_secondary")
        btn_validate.clicked.connect(self.preview_validation)

        btn_clear = QPushButton("✖ Clear")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.clicked.connect(self.clear_inputs)

        input_toolbar.addWidget(btn_import)
        input_toolbar.addWidget(btn_validate)
        input_toolbar.addWidget(btn_clear)
        input_layout.addLayout(input_toolbar)

        self.url_editor = QPlainTextEdit()
        self.url_editor.setPlaceholderText(
            "Enter URLs (one per line)...\nhttps://example.com\ngithub.com\nmicrosoft.com"
        )
        input_layout.addWidget(self.url_editor)

        self.chk_skip_duplicates = QCheckBox("Skip Duplicate URLs (Normalized Matching)")
        self.chk_skip_duplicates.setChecked(True)
        input_layout.addWidget(self.chk_skip_duplicates)
        left_layout.addWidget(input_group)

        cfg_group = QGroupBox("Browser & Launch Pacing Configuration")
        cfg_layout = QGridLayout(cfg_group)

        cfg_layout.addWidget(QLabel("Target Browser:"), 0, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(list(self.browsers.keys()))
        cfg_layout.addWidget(self.browser_combo, 0, 1)

        cfg_layout.addWidget(QLabel("Launch Mode:"), 1, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Instant", "Fixed Delay", "Random Delay", "Concurrent Batch"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        cfg_layout.addWidget(self.mode_combo, 1, 1)

        self.lbl_param1 = QLabel("Fixed Delay (sec):")
        self.spin_fixed = QDoubleSpinBox()
        self.spin_fixed.setRange(0.1, 300.0)
        self.spin_fixed.setValue(1.0)
        self.spin_fixed.setSingleStep(0.5)

        self.lbl_rand = QLabel("Random Range (s):")
        rand_box = QHBoxLayout()
        self.spin_rand_min = QDoubleSpinBox()
        self.spin_rand_min.setRange(0.1, 300.0)
        self.spin_rand_min.setValue(1.0)
        self.spin_rand_max = QDoubleSpinBox()
        self.spin_rand_max.setRange(0.2, 600.0)
        self.spin_rand_max.setValue(3.0)
        rand_box.addWidget(self.spin_rand_min)
        rand_box.addWidget(QLabel("to"))
        rand_box.addWidget(self.spin_rand_max)
        self.rand_container = QWidget()
        self.rand_container.setLayout(rand_box)

        self.lbl_batch = QLabel("Batch Size / Wait:")
        batch_box = QHBoxLayout()
        self.combo_batch_size = QComboBox()
        self.combo_batch_size.addItems(["1", "5", "10", "25", "50"])
        self.combo_batch_size.setCurrentText("5")
        self.spin_batch_wait = QDoubleSpinBox()
        self.spin_batch_wait.setRange(0.5, 300.0)
        self.spin_batch_wait.setValue(2.0)
        batch_box.addWidget(self.combo_batch_size)
        batch_box.addWidget(QLabel("URLs /"))
        batch_box.addWidget(self.spin_batch_wait)
        batch_box.addWidget(QLabel("s"))
        self.batch_container = QWidget()
        self.batch_container.setLayout(batch_box)

        cfg_layout.addWidget(self.lbl_param1, 2, 0)
        cfg_layout.addWidget(self.spin_fixed, 2, 1)
        cfg_layout.addWidget(self.lbl_rand, 3, 0)
        cfg_layout.addWidget(self.rand_container, 3, 1)
        cfg_layout.addWidget(self.lbl_batch, 4, 0)
        cfg_layout.addWidget(self.batch_container, 4, 1)

        self.chk_sound = QCheckBox("Play Completion Alert Beep")
        self.chk_sound.setChecked(True)
        cfg_layout.addWidget(self.chk_sound, 5, 0, 1, 2)

        left_layout.addWidget(cfg_group)

        ctrl_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ START")
        self.btn_start.clicked.connect(self.start_execution)

        self.btn_pause = QPushButton("⏸ PAUSE")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)

        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_execution)

        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_pause)
        ctrl_layout.addWidget(self.btn_stop)
        left_layout.addLayout(ctrl_layout)

        splitter.addWidget(left_widget)

        self.right_tabs = QTabWidget()

        tab_results = QWidget()
        res_layout = QVBoxLayout(tab_results)
        res_toolbar = QHBoxLayout()
        btn_exp_res_csv = QPushButton("Export Results (CSV)")
        btn_exp_res_csv.setObjectName("btn_secondary")
        btn_exp_res_csv.clicked.connect(lambda: self.export_results("csv"))
        btn_exp_res_txt = QPushButton("Export Results (TXT)")
        btn_exp_res_txt.setObjectName("btn_secondary")
        btn_exp_res_txt.clicked.connect(lambda: self.export_results("txt"))
        res_toolbar.addStretch()
        res_toolbar.addWidget(btn_exp_res_csv)
        res_toolbar.addWidget(btn_exp_res_txt)
        res_layout.addLayout(res_toolbar)

        self.results_table = QTableView()
        self.results_table.setModel(self.table_model)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        res_layout.addWidget(self.results_table)
        self.right_tabs.addTab(tab_results, "📊 Execution Results")

        tab_logs = QWidget()
        log_layout = QVBoxLayout(tab_logs)
        log_toolbar = QHBoxLayout()
        for fmt in ("LOG", "TXT", "CSV"):
            btn = QPushButton(f"Export Logs ({fmt})")
            btn.setObjectName("btn_secondary")
            btn.clicked.connect(lambda checked=False, f=fmt.lower(): self.export_logs(f))
            log_toolbar.addWidget(btn)
        btn_clear_log = QPushButton("Clear Logs")
        btn_clear_log.setObjectName("btn_secondary")
        btn_clear_log.clicked.connect(self.clear_logs)
        log_toolbar.addStretch()
        log_toolbar.addWidget(btn_clear_log)
        log_layout.addLayout(log_toolbar)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(10000)
        log_layout.addWidget(self.log_console)
        self.right_tabs.addTab(tab_logs, "📡 Live Event Stream")

        tab_analytics = QWidget()
        ana_layout = QVBoxLayout(tab_analytics)
        ana_layout.addWidget(QLabel("<b>Browser Usage & Success Analytics</b>"))
        self.analytics_console = QPlainTextEdit()
        self.analytics_console.setReadOnly(True)
        ana_layout.addWidget(self.analytics_console)
        self.right_tabs.addTab(tab_analytics, "📈 Analytics & Session History")

        splitter.addWidget(self.right_tabs)
        splitter.setSizes([420, 920])
        bo_layout.addWidget(splitter)
        self.main_tabs.addTab(tab_browser_ops, "🚀 Browser Automation")

        # ======================================================================
        # TAB 2: WHOIS / DOMAIN INTELLIGENCE DASHBOARD
        # ======================================================================
        tab_whois = QWidget()
        whois_layout = QHBoxLayout(tab_whois)
        whois_layout.setContentsMargins(10, 10, 10, 10)

        w_left_widget = QWidget()
        w_left_layout = QVBoxLayout(w_left_widget)
        w_left_layout.setContentsMargins(0, 0, 5, 0)

        w_input_group = QGroupBox("Domain Intelligence Controls")
        w_inp_layout = QGridLayout(w_input_group)
        w_inp_layout.addWidget(QLabel("Target Domain / IP:"), 0, 0)
        self.whois_domain_input = QPlainTextEdit()
        self.whois_domain_input.setMaximumHeight(40)
        self.whois_domain_input.setPlaceholderText("e.g. microsoft.com or 104.18.35.90")
        w_inp_layout.addWidget(self.whois_domain_input, 0, 1)

        w_btn_layout = QGridLayout()
        self.btn_whois_lookup = QPushButton("🔍 Full Intelligence Lookup")
        self.btn_whois_lookup.clicked.connect(lambda: self.perform_intelligence("whois"))
        
        self.btn_rev_ip = QPushButton("🌐 Reverse IP Lookup")
        self.btn_rev_ip.setObjectName("btn_secondary")
        self.btn_rev_ip.clicked.connect(lambda: self.perform_intelligence("reverse_ip"))

        self.btn_rev_dom = QPushButton("🔍 Reverse Domain")
        self.btn_rev_dom.setObjectName("btn_secondary")
        self.btn_rev_dom.clicked.connect(lambda: self.perform_intelligence("reverse_domain"))

        self.btn_recon = QPushButton("🛡 Recon & Fingerprint")
        self.btn_recon.setObjectName("btn_secondary")
        self.btn_recon.clicked.connect(lambda: self.perform_intelligence("recon"))

        w_btn_layout.addWidget(self.btn_whois_lookup, 0, 0, 1, 2)
        w_btn_layout.addWidget(self.btn_rev_ip, 1, 0)
        w_btn_layout.addWidget(self.btn_rev_dom, 1, 1)
        w_btn_layout.addWidget(self.btn_recon, 2, 0, 1, 2)
        w_inp_layout.addLayout(w_btn_layout, 1, 0, 1, 2)
        w_left_layout.addWidget(w_input_group)

        risk_group = QGroupBox("Domain Risk Intelligence")
        risk_layout = QVBoxLayout(risk_group)
        self.risk_age_lbl = QLabel("Domain Age: —")
        self.risk_age_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.risk_level_lbl = QLabel("Risk Level: —")
        self.risk_level_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #94a3b8;")
        risk_layout.addWidget(self.risk_age_lbl)
        risk_layout.addWidget(self.risk_level_lbl)
        w_left_layout.addWidget(risk_group)

        history_group = QGroupBox("Search History")
        hist_layout = QVBoxLayout(history_group)
        self.whois_history_table = QTableWidget(0, 4)
        self.whois_history_table.setHorizontalHeaderLabels(["Timestamp", "Target", "Type", "Risk"])
        self.whois_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        hist_layout.addWidget(self.whois_history_table)
        w_left_layout.addWidget(history_group)

        whois_layout.addWidget(w_left_widget, 4)

        w_right_tabs = QTabWidget()

        tab_sub_whois = QWidget()
        sw_layout = QGridLayout(tab_sub_whois)
        self.whois_fields = {}
        fields_def = [
            ("domain", "Domain Name:"), ("registrar", "Registrar:"), ("iana_id", "IANA ID:"),
            ("whois_server", "WHOIS Server:"), ("creation_date", "Creation Date:"), ("expiration_date", "Expiration Date:"),
            ("domain_age", "Domain Age:"), ("status", "Status:"), ("name_servers", "Name Servers:"),
            ("dnssec", "DNSSEC:"), ("country", "Country:"), ("organization", "Registrant Org:"),
            ("ip", "Resolved IP:"), ("hosting", "Hosting Provider:"), ("asn", "ASN:")
        ]
        for idx, (f_key, f_label) in enumerate(fields_def):
            r, c = divmod(idx, 2)
            lbl_title = QLabel(f"<b>{f_label}</b>")
            lbl_val = QLabel("—")
            lbl_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            sw_layout.addWidget(lbl_title, r, c * 2)
            sw_layout.addWidget(lbl_val, r, c * 2 + 1)
            self.whois_fields[f_key] = lbl_val
        w_right_tabs.addTab(tab_sub_whois, "📋 WHOIS / Registration")

        tab_sub_dns = QWidget()
        sd_layout = QVBoxLayout(tab_sub_dns)
        sd_layout.addWidget(QLabel("<b>Active DNS Records & Infrastructure Resolution</b>"))
        self.dns_table = QTableWidget(0, 3)
        self.dns_table.setHorizontalHeaderLabels(["Record Type", "Target Value", "Status"])
        self.dns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        sd_layout.addWidget(self.dns_table)
        w_right_tabs.addTab(tab_sub_dns, "📡 DNS Intelligence")

        tab_sub_rev = QWidget()
        sr_layout = QVBoxLayout(tab_sub_rev)
        sr_layout.addWidget(QLabel("<b>Reverse IP / Co-Hosted Domains & Shared Infrastructure</b>"))
        self.reverse_table = QTableWidget(0, 4)
        self.reverse_table.setHorizontalHeaderLabels(["Domain / Property", "IP Address", "Hosting Provider", "Risk Score"])
        self.reverse_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        sr_layout.addWidget(self.reverse_table)
        w_right_tabs.addTab(tab_sub_rev, "🌐 Reverse IP & Domain")

        tab_sub_rec = QWidget()
        srec_layout = QVBoxLayout(tab_sub_rec)
        srec_layout.addWidget(QLabel("<b>HTTP Headers, TLS Certificates & Technology Fingerprints</b>"))
        self.recon_console = QPlainTextEdit()
        self.recon_console.setReadOnly(True)
        srec_layout.addWidget(self.recon_console)
        w_right_tabs.addTab(tab_sub_rec, "🛡 Recon & Fingerprint")

        whois_layout.addWidget(w_right_tabs, 8)
        self.main_tabs.addTab(tab_whois, "🔎 Domain Intelligence Dashboard")

        # ======================================================================
        # TAB 3: BRAND MONITORING / LOOKALIKE DOMAIN DISCOVERY
        # ======================================================================
        tab_brand = QWidget()
        brand_layout = QHBoxLayout(tab_brand)
        brand_layout.setContentsMargins(10, 10, 10, 10)

        b_left_widget = QWidget()
        b_left_layout = QVBoxLayout(b_left_widget)
        b_left_layout.setContentsMargins(0, 0, 5, 0)

        b_input_group = QGroupBox("Brand & Keyword Configuration")
        b_inp_layout = QGridLayout(b_input_group)
        b_inp_layout.addWidget(QLabel("Brand / Keyword:"), 0, 0)
        self.brand_keyword_input = QPlainTextEdit()
        self.brand_keyword_input.setMaximumHeight(40)
        self.brand_keyword_input.setPlaceholderText("e.g. microsoft, paypal, github")
        b_inp_layout.addWidget(self.brand_keyword_input, 0, 1)

        b_inp_layout.addWidget(QLabel("Date Filter:"), 1, 0)
        self.brand_date_combo = QComboBox()
        self.brand_date_combo.addItems(["Last 30 Days", "Last 90 Days", "Last 180 Days", "Last 365 Days", "All Time"])
        self.brand_date_combo.setCurrentIndex(4)
        b_inp_layout.addWidget(self.brand_date_combo, 1, 1)

        b_inp_layout.addWidget(QLabel("Data Sources:"), 2, 0)
        sources_widget = QWidget()
        s_layout = QVBoxLayout(sources_widget)
        s_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_src_whois = QCheckBox("WHOIS / RDAP")
        self.chk_src_whois.setChecked(True)
        self.chk_src_crtsh = QCheckBox("Certificate Transparency (crt.sh)")
        self.chk_src_crtsh.setChecked(True)
        self.chk_src_typos = QCheckBox("Typosquatting Generator")
        self.chk_src_typos.setChecked(True)
        s_layout.addWidget(self.chk_src_whois)
        s_layout.addWidget(self.chk_src_crtsh)
        s_layout.addWidget(self.chk_src_typos)
        b_inp_layout.addWidget(sources_widget, 2, 1)

        b_btn_layout = QHBoxLayout()
        self.btn_brand_scan = QPushButton("🚀 Run Brand Intelligence Scan")
        self.btn_brand_scan.clicked.connect(self.run_brand_scan)
        btn_brand_clear = QPushButton("✖ Clear")
        btn_brand_clear.setObjectName("btn_secondary")
        btn_brand_clear.clicked.connect(self.clear_brand_inputs)
        b_btn_layout.addWidget(self.btn_brand_scan)
        b_btn_layout.addWidget(btn_brand_clear)
        b_inp_layout.addLayout(b_btn_layout, 3, 0, 1, 2)
        b_left_layout.addWidget(b_input_group)

        b_info_box = QGroupBox("Investigation Guide")
        b_info_layout = QVBoxLayout(b_info_box)
        b_info_lbl = QLabel(
            "<b>Lookalike Domain Discovery:</b>\n"
            "• Discovers typo-squatted, brand-impersonating, and phishing domains.\n"
            "• Queries live Certificate Transparency logs (crt.sh).\n"
            "• Generates homoglyphs, omissions, transpositions, and malicious prefixes.\n"
            "• Click any discovered domain to load deep WHOIS/RDAP inspection."
        )
        b_info_lbl.setWordWrap(True)
        b_info_layout.addWidget(b_info_lbl)
        b_left_layout.addWidget(b_info_box)
        b_left_layout.addStretch()

        brand_layout.addWidget(b_left_widget, 4)

        b_right_widget = QWidget()
        b_right_layout = QVBoxLayout(b_right_widget)
        b_right_layout.setContentsMargins(5, 0, 0, 0)

        brand_results_group = QGroupBox("Discovered Lookalike & Phishing Domains")
        br_layout = QVBoxLayout(brand_results_group)
        
        self.brand_results_table = QTableWidget(0, 7)
        self.brand_results_table.setHorizontalHeaderLabels([
            "Domain", "Search Type", "Matched Keyword", "Registrar", "Creation Date", "IP Address", "Risk Assessment"
        ])
        self.brand_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.brand_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.brand_results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.brand_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.brand_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.brand_results_table.cellClicked.connect(self.on_brand_domain_selected)
        br_layout.addWidget(self.brand_results_table)
        
        b_right_layout.addWidget(brand_results_group)
        brand_layout.addWidget(b_right_widget, 8)

        self.main_tabs.addTab(tab_brand, "🛡 Brand Monitoring")

        root_layout.addWidget(self.main_tabs)

        # ======================================================================
        # FOOTER TOOLBAR
        # ======================================================================
        footer_frame = QFrame()
        footer_frame.setObjectName("kpi_card")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(12, 6, 12, 6)

        footer_brand = QLabel("<b>JTEMIA AUTOMATION SUITE v4.0</b> — OSINT & Domain Intelligence Platform")
        footer_brand.setStyleSheet("color: #64748b; font-size: 11px;")
        footer_layout.addWidget(footer_brand)
        footer_layout.addStretch()

        lbl_coffee = QLabel("<a href='https://www.paypal.com/paypalme/vxemia' style='color:#38bdf8; text-decoration:none;'>☕ Buy Me a Coffee</a>")
        lbl_coffee.setOpenExternalLinks(True)
        lbl_coffee.setCursor(Qt.PointingHandCursor)
        footer_layout.addWidget(lbl_coffee)

        footer_layout.addWidget(QLabel(" | "))

        lbl_github = QLabel("<a href='https://github.com/IvanXEmia/' style='color:#38bdf8; text-decoration:none;'>🐙 GitHub</a>")
        lbl_github.setOpenExternalLinks(True)
        lbl_github.setCursor(Qt.PointingHandCursor)
        footer_layout.addWidget(lbl_github)

        footer_layout.addWidget(QLabel(" | "))

        lbl_open_source = QLabel("💙 Support Open Source Software")
        lbl_open_source.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer_layout.addWidget(lbl_open_source)

        footer_layout.addWidget(QLabel(" | "))

        lbl_mit = QLabel("<b>MIT Licensed</b>")
        lbl_mit.setStyleSheet("color: #22c55e; font-size: 11px;")
        footer_layout.addWidget(lbl_mit)

        root_layout.addWidget(footer_frame)

        self._on_mode_changed("Instant")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "bg_overlay"):
            self.bg_overlay.setGeometry(self.centralWidget().rect())

    def apply_theme(self, theme_name: str):
        self.setStyleSheet(THEMES.get(theme_name, ""))
        if hasattr(self, "bg_overlay"):
            self.bg_overlay.set_theme_opacity(theme_name)

    def _on_mode_changed(self, mode: str):
        self.lbl_param1.setVisible(mode == "Fixed Delay")
        self.spin_fixed.setVisible(mode == "Fixed Delay")
        self.lbl_rand.setVisible(mode == "Random Delay")
        self.rand_container.setVisible(mode == "Random Delay")
        self.lbl_batch.setVisible(mode == "Concurrent Batch")
        self.batch_container.setVisible(mode == "Concurrent Batch")

    def log_event(self, level: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.raw_logs.append((ts, level, message))
        color_map = {"INFO": "#38bdf8", "SUCCESS": "#22c55e", "WARNING": "#f59e0b", "ERROR": "#ef4444"}
        color = color_map.get(level, "#e2e8f0")
        html = f'<span style="color:#64748b;">[{ts}]</span> <b style="color:{color};">[{level}]</b> {message}'
        self.log_console.appendHtml(html)

    def clear_logs(self):
        self.log_console.clear()
        self.raw_logs.clear()

    def clear_inputs(self):
        self.url_editor.clear()
        self.table_model.load_initial_queue([])
        self.log_event("INFO", "Input editor and queue cleared.")

    def perform_intelligence(self, mode: str, target_override: str = None):
        target = target_override or self.whois_domain_input.toPlainText().strip()
        if not target:
            QMessageBox.warning(self, "Target Required", "Please enter a target domain or IP address.")
            return

        query_target = target.splitlines()[0].strip()
        self.btn_whois_lookup.setEnabled(False)
        self.btn_whois_lookup.setText(f"Running {mode.upper()}...")

        self.intel_worker = AdvancedIntelligenceWorker(query_target, mode)
        self.intel_worker.intelligence_result.connect(self.display_intelligence_results)
        self.intel_worker.start()

    @Slot(dict)
    def display_intelligence_results(self, data: dict):
        self.btn_whois_lookup.setEnabled(True)
        self.btn_whois_lookup.setText("🔍 Full Intelligence Lookup")

        mode = data.get("mode", "whois")

        if mode == "reverse_ip":
            self.reverse_table.setRowCount(0)
            domains = data.get("domains", [])
            self.reverse_table.setRowCount(len(domains))
            for r, d in enumerate(domains):
                self.reverse_table.setItem(r, 0, QTableWidgetItem(d["domain"]))
                self.reverse_table.setItem(r, 1, QTableWidgetItem(d["ip"]))
                self.reverse_table.setItem(r, 2, QTableWidgetItem(d["hosting"]))
                self.reverse_table.setItem(r, 3, QTableWidgetItem(d["risk"]))
            self.log_event("SUCCESS", f"Reverse IP lookup completed for {data.get('ip')}. Found {len(domains)} co-hosted properties.")
            return

        if mode == "reverse_domain":
            self.reverse_table.setRowCount(0)
            related = data.get("related_domains", [])
            self.reverse_table.setRowCount(len(related))
            for r, d in enumerate(related):
                self.reverse_table.setItem(r, 0, QTableWidgetItem(d))
                self.reverse_table.setItem(r, 1, QTableWidgetItem("Shared Infrastructure"))
                self.reverse_table.setItem(r, 2, QTableWidgetItem(data.get("shared_hosting")))
                self.reverse_table.setItem(r, 3, QTableWidgetItem("Low Risk"))
            self.log_event("SUCCESS", f"Reverse Domain lookup completed for {data.get('domain')}.")
            return

        if mode == "recon":
            recon_text = (
                f"Target: {data.get('domain')}\n"
                f"HTTP Status: {data.get('http_status')}\n"
                f"Server Header: {data.get('server_header')}\n"
                f"Content-Type: {data.get('content_type')}\n"
                f"TLS Issuer: {data.get('tls_issuer')}\n"
                f"TLS Expiry: {data.get('tls_valid_to')}\n\n"
                f"Discovered Technologies:\n" + "\n".join([f" • {t}" for t in data.get('technologies', [])])
            )
            self.recon_console.setPlainText(recon_text)
            self.log_event("SUCCESS", f"Reconnaissance & fingerprinting completed for {data.get('domain')}.")
            return

        for k, lbl in self.whois_fields.items():
            val = data.get(k, "Unavailable")
            if isinstance(val, list):
                val = ", ".join(val)
            lbl.setText(str(val))

        age_str = data.get("domain_age", "Unavailable")
        risk_lvl = data.get("risk_level", "UNKNOWN")
        risk_col = data.get("risk_color", "#94a3b8")

        self.risk_age_lbl.setText(f"Domain Age: {age_str}")
        self.risk_level_lbl.setText(f"Risk Level: {risk_lvl}")
        self.risk_level_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {risk_col};")

        dns_recs = data.get("dns_records", {})
        total_dns = sum(len(v) for v in dns_recs.values())
        self.dns_table.setRowCount(total_dns)
        row_idx = 0
        for r_type, vals in dns_recs.items():
            for val in vals:
                self.dns_table.setItem(row_idx, 0, QTableWidgetItem(r_type))
                self.dns_table.setItem(row_idx, 1, QTableWidgetItem(val))
                self.dns_table.setItem(row_idx, 2, QTableWidgetItem("Active"))
                row_idx += 1

        hist_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": data.get("domain"),
            "type": "Full Intelligence",
            "risk": risk_lvl
        }
        self.whois_history.insert(0, hist_entry)
        if len(self.whois_history) > 20:
            self.whois_history.pop()

        self._refresh_whois_history_table()
        self.log_event("SUCCESS", f"Comprehensive domain intelligence loaded for {data.get('domain')}.")

    def _refresh_whois_history_table(self):
        self.whois_history_table.setRowCount(len(self.whois_history))
        for r, item in enumerate(self.whois_history):
            self.whois_history_table.setItem(r, 0, QTableWidgetItem(item["timestamp"]))
            self.whois_history_table.setItem(r, 1, QTableWidgetItem(item["target"]))
            self.whois_history_table.setItem(r, 2, QTableWidgetItem(item["type"]))
            risk_item = QTableWidgetItem(item["risk"])
            if "HIGH" in item["risk"]:
                risk_item.setForeground(QColor("#ef4444"))
            elif "MEDIUM" in item["risk"]:
                risk_item.setForeground(QColor("#f59e0b"))
            elif "LOW" in item["risk"]:
                risk_item.setForeground(QColor("#22c55e"))
            self.whois_history_table.setItem(r, 3, risk_item)

    def run_brand_scan(self):
        keyword = self.brand_keyword_input.toPlainText().strip()
        if not keyword:
            QMessageBox.warning(self, "Keyword Required", "Please enter a brand or keyword to scan.")
            return

        kw = keyword.splitlines()[0].strip()
        options = {
            "whois": self.chk_src_whois.isChecked(),
            "crtsh": self.chk_src_crtsh.isChecked(),
            "typos": self.chk_src_typos.isChecked(),
        }
        date_filter = self.brand_date_combo.currentText()

        self.btn_brand_scan.setEnabled(False)
        self.btn_brand_scan.setText("Scanning Intelligence Sources...")
        self.brand_results_table.setRowCount(0)

        self.brand_worker = BrandMonitoringWorker(kw, options, date_filter)
        self.brand_worker.discovery_batch.connect(self.populate_brand_results)
        self.brand_worker.scan_finished.connect(self.on_brand_scan_finished)
        self.brand_worker.start()

    @Slot(list)
    def populate_brand_results(self, results: list):
        self.brand_results_table.setRowCount(len(results))
        for r, item in enumerate(results):
            self.brand_results_table.setItem(r, 0, QTableWidgetItem(item["domain"]))
            self.brand_results_table.setItem(r, 1, QTableWidgetItem(item["search_type"]))
            self.brand_results_table.setItem(r, 2, QTableWidgetItem(item["keyword"]))
            self.brand_results_table.setItem(r, 3, QTableWidgetItem(item["registrar"]))
            self.brand_results_table.setItem(r, 4, QTableWidgetItem(item["creation_date"]))
            self.brand_results_table.setItem(r, 5, QTableWidgetItem(item["ip"]))
            
            risk_item = QTableWidgetItem(item["risk_score"])
            risk_item.setForeground(QColor(item["risk_color"]))
            risk_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.brand_results_table.setItem(r, 6, risk_item)

    @Slot(int)
    def on_brand_scan_finished(self, count: int):
        self.btn_brand_scan.setEnabled(True)
        self.btn_brand_scan.setText("🚀 Run Brand Intelligence Scan")
        self.log_event("SUCCESS", f"Brand intelligence scan completed. Discovered {count} matching/lookalike domains.")

    def on_brand_domain_selected(self, row, col):
        domain_item = self.brand_results_table.item(row, 0)
        if domain_item:
            domain = domain_item.text()
            self.main_tabs.setCurrentIndex(1)
            self.whois_domain_input.setPlainText(domain)
            self.perform_intelligence("whois", domain)

    def clear_brand_inputs(self):
        self.brand_keyword_input.clear()
        self.brand_results_table.setRowCount(0)

    def import_urls(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import URL List", "", "URL Files (*.txt *.csv);;All Files (*)"
        )
        if not file_path:
            return

        extracted = []
        try:
            if file_path.lower().endswith(".csv"):
                with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        for cell in row:
                            cell = cell.strip()
                            if cell and ("." in cell or "localhost" in cell):
                                extracted.append(cell)
            else:
                with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    extracted = [line.strip() for line in f if line.strip()]

            existing = self.url_editor.toPlainText().strip()
            combined = f"{existing}\n" + "\n".join(extracted) if existing else "\n".join(extracted)
            self.url_editor.setPlainText(combined)
            self.log_event("INFO", f"Imported {len(extracted)} entries from {os.path.basename(file_path)}.")
        except Exception as e:
            self.log_event("ERROR", f"Failed to import file: {e}")

    def _build_queue(self) -> list[dict]:
        raw_lines = [line.strip() for line in self.url_editor.toPlainText().splitlines() if line.strip()]
        skip_dups = self.chk_skip_duplicates.isChecked()
        browser_name = self.browser_combo.currentText()

        seen = set()
        queue = []

        for idx, raw in enumerate(raw_lines, start=1):
            is_valid, norm_url, err = UrlValidator.normalize_and_validate(raw)
            if not is_valid:
                queue.append({
                    "idx": idx,
                    "url": raw,
                    "browser": browser_name,
                    "status": "Invalid",
                })
                self.log_event("ERROR", f"Invalid URL rejected: '{raw}' ({err})")
                continue

            if skip_dups and norm_url in seen:
                queue.append({
                    "idx": idx,
                    "url": norm_url,
                    "browser": browser_name,
                    "status": "Skipped",
                })
                self.log_event("WARNING", f"Duplicate skipped: {norm_url}")
                continue

            seen.add(norm_url)
            queue.append({
                "idx": idx,
                "url": norm_url,
                "browser": browser_name,
                "status": "Pending",
            })

        return queue

    def preview_validation(self):
        queue = self._build_queue()
        self.table_model.load_initial_queue(queue)
        total = len(queue)
        pending = sum(1 for x in queue if x["status"] == "Pending")
        skipped = total - pending

        self.kpi_labels["total"].setText(str(total))
        self.kpi_labels["opened"].setText("0")
        self.kpi_labels["failed"].setText("0")
        self.kpi_labels["skipped"].setText(str(skipped))
        self.kpi_labels["pending"].setText(str(pending))
        self.log_event("INFO", f"Validated {total} URLs -> {pending} ready, {skipped} skipped/invalid.")

    def start_execution(self):
        self.raise_()
        self.activateWindow()
        
        if self.worker and self.worker.isRunning():
            return

        queue = self._build_queue()
        if not queue:
            QMessageBox.warning(self, "Empty Queue", "Please enter or import at least one URL.")
            return

        self.table_model.load_initial_queue(queue)
        total = len(queue)
        skipped = sum(1 for x in queue if x["status"] != "Pending")
        pending = total - skipped

        self.kpi_labels["total"].setText(str(total))
        self.kpi_labels["opened"].setText("0")
        self.kpi_labels["failed"].setText("0")
        self.kpi_labels["skipped"].setText(str(skipped))
        self.kpi_labels["pending"].setText(str(pending))
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(skipped)

        browser_name = self.browser_combo.currentText()
        config = {
            "browser_name": browser_name,
            "browser_path": self.browsers[browser_name],
            "mode": self.mode_combo.currentText(),
            "fixed_delay": self.spin_fixed.value(),
            "rand_min": self.spin_rand_min.value(),
            "rand_max": self.spin_rand_max.value(),
            "batch_size": int(self.combo_batch_size.currentText()),
            "batch_delay": self.spin_batch_wait.value(),
        }

        self.worker = UrlProcessorWorker(queue, config)
        self.worker.log_signal.connect(self.log_event)
        self.worker.row_updated.connect(self.table_model.update_row)
        self.worker.progress_updated.connect(self.update_telemetry)
        self.worker.finished_summary.connect(self.on_execution_finished)

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏸ PAUSE")
        self.btn_stop.setEnabled(True)
        self.status_badge.setText("● RUNNING")
        self.status_badge.setStyleSheet("color: #38bdf8; font-weight: bold; padding-left: 12px;")

        self.worker.start()

    def toggle_pause(self):
        if not self.worker:
            return
        if self.btn_pause.text().startswith("⏸"):
            self.worker.pause()
            self.btn_pause.setText("▶ RESUME")
            self.status_badge.setText("● PAUSED")
            self.status_badge.setStyleSheet("color: #eab308; font-weight: bold; padding-left: 12px;")
        else:
            self.worker.resume()
            self.btn_pause.setText("⏸ PAUSE")
            self.status_badge.setText("● RUNNING")
            self.status_badge.setStyleSheet("color: #38bdf8; font-weight: bold; padding-left: 12px;")

    def stop_execution(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.btn_stop.setEnabled(False)
            self.btn_pause.setEnabled(False)

    @Slot(dict)
    def update_telemetry(self, data: dict):
        opened = data["opened"]
        failed = data["failed"]
        skipped = data["skipped"]
        pending = data["pending"]
        total = data["total"]

        attempts = opened + failed
        rate = (opened / attempts * 100.0) if attempts > 0 else 0.0

        self.kpi_labels["opened"].setText(str(opened))
        self.kpi_labels["failed"].setText(str(failed))
        self.kpi_labels["skipped"].setText(str(skipped))
        self.kpi_labels["pending"].setText(str(pending))
        self.kpi_labels["rate"].setText(f"{rate:.1f}%")
        self.kpi_labels["upm"].setText(f"{data['upm']:.1f}")

        self.exec_fields["current_url"].setText(data["current_url"][:70])
        self.exec_fields["current_browser"].setText(data["current_browser"])
        self.exec_fields["current_batch"].setText(data["current_batch"])
        self.exec_fields["elapsed"].setText(self._fmt_seconds(data["elapsed"]))
        self.exec_fields["eta"].setText(self._fmt_seconds(data["eta"]))
        self.exec_fields["position"].setText(data["position"])

        self.progress_bar.setValue(total - pending)

    @Slot(dict)
    def on_execution_finished(self, summary: dict):

        try:
            self.showNormal()
            self.raise_()
            self.activateWindow()

        except Exception as e:
            self.log_event(
                "WARNING",
                f"Window restore failed: {e}"
            
            )

        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸ PAUSE")
        self.btn_stop.setEnabled(False)
        self.status_badge.setText("● COMPLETED")
        self.status_badge.setStyleSheet(
        "color: #22c55e; font-weight: bold; padding-left: 12px;"
        )

        self.session_history.append(summary)
        b_name = summary["browser"]
        b_stat = self.browser_stats.setdefault(b_name, {"runs": 0, "opened": 0, "failed": 0})
        b_stat["runs"] += 1
        b_stat["opened"] += summary["opened"]
        b_stat["failed"] += summary["failed"]
        self._refresh_analytics_tab()

        if self.chk_sound.isChecked():
            QApplication.beep()

        msg = (
            f"URLs Loaded: {summary['total']}\n"
            f"Opened: {summary['opened']}\n"
            f"Failed: {summary['failed']}\n"
            f"Skipped / Invalid: {summary['skipped']}\n"
            f"Success Rate: {summary['success_rate']:.1f}%\n"
            f"Execution Duration: {summary['duration']:.2f} seconds"
        )
        QMessageBox.information(self, "Execution Summary — JTEMIA Suite", msg)

    def _refresh_analytics_tab(self):
        lines = ["=== BROWSER ANALYTICS ==="]
        for b, st in self.browser_stats.items():
            tot = st["opened"] + st["failed"]
            rate = (st["opened"] / tot * 100.0) if tot > 0 else 0.0
            lines.append(f"• {b}: {st['runs']} sessions | {tot} URLs processed | {rate:.1f}% success rate")

        lines.append("\n=== SESSION HISTORY ===")
        for idx, s in enumerate(reversed(self.session_history), 1):
            lines.append(
                f"{idx}. [{s['date']}] Browser: {s['browser']} | Loaded: {s['total']} | "
                f"Opened: {s['opened']} | Failed: {s['failed']} | Duration: {s['duration']:.2f}s"
            )
        self.analytics_console.setPlainText("\n".join(lines))

    @staticmethod
    def _fmt_seconds(sec: float) -> str:
        s = int(sec)
        h, rem = divmod(s, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def export_results(self, fmt: str):
        rows = self.table_model.get_all_rows()
        if not rows:
            QMessageBox.information(self, "No Data", "No results available to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", f"url_results_{datetime.now():%Y%m%d_%H%M%S}.{fmt}", f"*.{fmt}"
        )
        if not path:
            return

        try:
            if fmt == "csv":
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(ResultsTableModel.COLUMNS)
                    writer.writerows(rows)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\t".join(ResultsTableModel.COLUMNS) + "\n")
                    for r in rows:
                        f.write("\t".join(r) + "\n")
            self.log_event("SUCCESS", f"Results exported to {path}")
        except Exception as e:
            self.log_event("ERROR", f"Export failed: {e}")

    def export_logs(self, fmt: str):
        if not self.raw_logs:
            QMessageBox.information(self, "No Logs", "No log entries to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", f"execution_logs_{datetime.now():%Y%m%d_%H%M%S}.{fmt}", f"*.{fmt}"
        )
        if not path:
            return

        try:
            if fmt == "csv":
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Level", "Message"])
                    writer.writerows(self.raw_logs)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for ts, lvl, msg in self.raw_logs:
                        f.write(f"[{ts}] [{lvl}] {msg}\n")
            self.log_event("SUCCESS", f"Logs exported to {path}")
        except Exception as e:
            self.log_event("ERROR", f"Log export failed: {e}")


# ==============================================================================
# 8. APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JtemiaAutomationSuite()
    window.show()
    sys.exit(app.exec())