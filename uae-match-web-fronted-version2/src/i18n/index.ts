/**
 * i18n 入口（BR-011：框架自首行代码启用；v1 仅 zh-CN）。
 * 用法：t('login.title') 或 t('login.resendIn', { s: 60 })。
 * Phase 2 加语言 = 新增语言包 + 切换 current，组件零改动。
 */
import { zhCN, LanguagePack } from './zh-CN';

const packs: Record<string, LanguagePack> = { 'zh-CN': zhCN };
let current = 'zh-CN';

export function setLocale(locale: string) {
  if (packs[locale]) current = locale;
}

export function t(key: string, vars?: Record<string, string | number>): string {
  const parts = key.split('.');
  let node: any = packs[current];
  for (const p of parts) {
    node = node?.[p];
    if (node === undefined) return key;   // 缺键时回显 key，便于发现漏译
  }
  if (typeof node !== 'string') return key;
  if (vars) {
    return node.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? `{${name}}`));
  }
  return node;
}
