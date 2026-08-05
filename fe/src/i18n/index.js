/**
 * ================================================================================
 * File: i18n/index.js
 * Description:
 *       vue-i18n setup for the application. Locale message tables live in
 *       @/locales/{cs,en,sk}.js. Active locale is kept in sync with
 *       stores/useLanguageStore.js.
 * ================================================================================
 */

import { createI18n } from 'vue-i18n';
import cs from '@/locales/cs';
import en from '@/locales/en';
import sk from '@/locales/sk';

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: localStorage.getItem('lang') || 'sk',
  fallbackLocale: 'sk',
  messages: { cs, en, sk },
});
