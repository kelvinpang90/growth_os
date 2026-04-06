"""
i18n 工具 — YAML 语言包 + Babel 货币格式化 + Locale ContextVar
"""
from contextvars import ContextVar
from pathlib import Path

import yaml
from babel.numbers import format_currency as _babel_fmt

_locale: ContextVar[str] = ContextVar("locale", default="en")
_translations: dict[str, dict] = {}

_I18N_DIR = Path(__file__).parent.parent.parent / "i18n"


def _load_translations() -> None:
    for lang in ("zh", "en"):
        with open(_I18N_DIR / f"{lang}.yaml", encoding="utf-8") as f:
            _translations[lang] = yaml.safe_load(f)


_load_translations()


def set_locale(lang: str) -> None:
    _locale.set(lang if lang in _translations else "en")


def get_locale() -> str:
    return _locale.get()


def t(key: str, **kwargs) -> str:
    """翻译 dot-separated 键，例如 t('error.user_exists')"""
    data = _translations.get(_locale.get(), _translations["en"])
    for part in key.split("."):
        data = data.get(part, key) if isinstance(data, dict) else key
    return data.format(**kwargs) if (isinstance(data, str) and kwargs) else data


def fmt_currency(amount: float, currency: str) -> str:
    """使用 Babel 按当前 locale 格式化货币金额"""
    babel_locale = "zh_CN" if _locale.get() == "zh" else "en_US"
    return _babel_fmt(amount, currency, locale=babel_locale)
