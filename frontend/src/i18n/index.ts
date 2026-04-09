import { createI18n } from 'vue-i18n'
import zh from '@/locales/zh'
import en from '@/locales/en'

const storedLang = localStorage.getItem('user_language')
const browserLang = navigator.language?.startsWith('zh') ? 'zh' : 'en'
const locale = (storedLang || browserLang) as 'zh' | 'en'

export const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: 'zh',
  messages: { zh, en },
})
