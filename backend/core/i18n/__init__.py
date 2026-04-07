"""
i18n utilities — YAML language packs + Babel currency formatting + Locale ContextVar
"""
from contextvars import ContextVar
from pathlib import Path

import yaml
from babel.numbers import format_currency as _babel_fmt

_locale: ContextVar[str] = ContextVar("locale", default="en")
_translations: dict[str, dict] = {}

_I18N_DIR = Path(__file__).parent.parent.parent / "i18n"


def _load_translations() -> None:
    # 加载 zh.yaml 和 en.yaml 翻译文件到内存字典。
    for lang in ("zh", "en"):
        with open(_I18N_DIR / f"{lang}.yaml", encoding="utf-8") as f:
            _translations[lang] = yaml.safe_load(f)


_load_translations()


def set_locale(lang: str) -> None:
    # 设置当前请求的语言环境，不支持的语言回退到英文。
    _locale.set(lang if lang in _translations else "en")


def get_locale() -> str:
    # 获取当前请求的语言环境标识。
    return _locale.get()


def t(key: str, **kwargs) -> str:
    # 按当前 locale 翻译 dot-separated 键（如 t('error.user_exists')），支持格式化参数。
    data = _translations.get(_locale.get(), _translations["en"])
    for part in key.split("."):
        data = data.get(part, key) if isinstance(data, dict) else key
    return data.format(**kwargs) if (isinstance(data, str) and kwargs) else data


def fmt_currency(amount: float, currency: str) -> str:
    # 使用 Babel 按当前 locale 将货币金额格式化为本地化字符串。
    babel_locale = "zh_CN" if _locale.get() == "zh" else "en_US"
    return _babel_fmt(amount, currency, locale=babel_locale)
