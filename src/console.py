"""控制台输出工具"""
import sys
from datetime import datetime

class Console:
    HEADER = '\033[95m'; BLUE = '\033[94m'; CYAN = '\033[96m'
    GREEN = '\033[92m'; YELLOW = '\033[93m'; RED = '\033[91m'
    BOLD = '\033[1m'; DIM = '\033[2m'; RESET = '\033[0m'

    @staticmethod
    def ts(): return datetime.now().strftime('%H:%M:%S')

    @classmethod
    def _print(cls, color, icon, msg, end='\n'):
        print(f"[{cls.ts()}] {color}{icon}{cls.RESET} {msg}", end=end, flush=True)

    @classmethod
    def info(cls, msg): cls._print(cls.CYAN, '•', msg)
    @classmethod
    def ok(cls, msg): cls._print(cls.GREEN, '✓', msg)
    @classmethod
    def warn(cls, msg): cls._print(cls.YELLOW, '!', msg)
    @classmethod
    def err(cls, msg): cls._print(cls.RED, '✗', msg)
    @classmethod
    def title(cls, msg):
        print(f"\n{cls.BOLD}{cls.HEADER}{'='*60}{cls.RESET}")
        print(f"{cls.BOLD}{cls.HEADER}  {msg}{cls.RESET}")
        print(f"{cls.BOLD}{cls.HEADER}{'='*60}{cls.RESET}\n")

    @classmethod
    def progress(cls, current, total, label="", width=40):
        if total > 0:
            pct = current / total * 100
            filled = int(width * current / total)
            bar = '█' * filled + '░' * (width - filled)
        else:
            pct = 0; bar = '░' * width
        print(f"\r[{cls.ts()}] {cls.BLUE}⏳{cls.RESET} [{bar}] {pct:5.1f}%  {current}/{total}  {label}", end='', flush=True)

    @classmethod
    def clear_line(cls):
        print('\r' + ' ' * 120 + '\r', end='', flush=True)

    @classmethod
    def menu(cls, title, options):
        print(f"\n{cls.BOLD}{title}{cls.RESET}")
        for i, (key, desc) in enumerate(options, 1):
            print(f"  {cls.CYAN}{i}.{cls.RESET} {desc}")

    @classmethod
    def section(cls, msg):
        print(f"\n[{cls.ts()}] {cls.BOLD}{cls.BLUE}▸ {msg}{cls.RESET}")
