/**
 * 推荐信页（BR-301, BR-302, BR-303 / PRD 6.2-6.3）。取代滑动式推荐页。
 * 展示顺序为产品铁律（PRD 6.2）：①小缘推荐语 → ②对方画像速写 → ③照片(M2 后接) →
 * ④兼容性(亮点+诚实差异点) → ⑤基础信息(收入仅区间)。
 * 三动作：愿意认识(可附言) / 想再了解(延48h一次) / 这次不合适(强制结构化理由)。
 */
import { useEffect, useState } from 'react';
import { Mail, Clock, Sparkles, ChevronLeft, Heart, HelpCircle, X } from 'lucide-react';
import { recommendationApi, ApiError } from '../lib/api';
import { t } from '../i18n';

const REASONS = ['timeline_mismatch', 'lifestyle_difference', 'appearance_preference', 'other'] as const;

function Countdown({ expiresAt }: { expiresAt: string }) {
  const [left, setLeft] = useState('');
  useEffect(() => {
    const tick = () => {
      const ms = new Date(expiresAt).getTime() - Date.now();
      if (ms <= 0) { setLeft(t('letters.expired')); return; }
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      setLeft(`${h} 小时 ${m} 分`);
    };
    tick();
    const id = window.setInterval(tick, 60000);
    return () => window.clearInterval(id);
  }, [expiresAt]);
  return <span>{left}</span>;
}

export function RecommendationLettersPage() {
  const [items, setItems] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [action, setAction] = useState<'accept' | 'decline' | null>(null);
  const [note, setNote] = useState('');
  const [reason, setReason] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const load = async () => {
    try {
      const r = await recommendationApi.list();
      if (!r.paywalled) setItems(r.items || []);
    } catch { /* 列表失败静默，空态兜底 */ }
  };
  useEffect(() => { void load(); }, []);

  const doRespond = async (act: 'accept' | 'more_info' | 'decline') => {
    if (!selected) return;
    setBusy(true); setError(null);
    try {
      const r = await recommendationApi.respond(selected.reco_pair_id, act, {
        note: note.trim() || undefined,
        decline_reason: act === 'decline' ? reason : undefined,
      });
      setFlash(r.message);
      setAction(null); setNote(''); setReason('');
      await load();
      const updated = (await recommendationApi.list());
      const fresh = (updated.items || []).find((i: any) => i.reco_pair_id === selected.reco_pair_id);
      setSelected(fresh || null);
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  // ===== 详情（信件本体）=====
  if (selected) {
    const letter = selected.letter || {};
    const compat = letter.compatibility || {};
    const info = letter.basic_info || {};
    const active = selected.status === 'delivered' && !selected.my_response;
    return (
      <div className="max-w-lg mx-auto px-4 py-5">
        <button onClick={() => { setSelected(null); setAction(null); setFlash(null); }}
                className="flex items-center gap-1 text-sm text-gray-500 mb-4">
          <ChevronLeft className="w-4 h-4" /> {t('common.back')}
        </button>

        {flash && <div className="bg-emerald-50 text-emerald-700 text-sm rounded-xl px-4 py-3 mb-4">{flash}</div>}
        {selected.status === 'matched' && (
          <div className="bg-rose-50 text-rose-600 text-sm rounded-xl px-4 py-3 mb-4">{t('letters.matchedBanner')}</div>
        )}

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#E07A5F]" />
            <h3 className="text-sm text-[#E07A5F]">{t('letters.from')}</h3>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{letter.reco_text}</p>
        </div>

        {letter.sketch && (
          <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
            <h3 className="text-sm text-[#E07A5F] mb-2">{t('letters.sketch')}</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{letter.sketch}</p>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <h3 className="text-sm text-[#E07A5F] mb-2">{t('letters.compatibility')}</h3>
          <div className="flex flex-wrap gap-2 mb-3">
            {(compat.highlights || []).map((h: string) => (
              <span key={h} className="text-xs bg-orange-50 text-[#E07A5F] rounded-full px-3 py-1">{h}</span>
            ))}
          </div>
          {compat.friction_point && (
            <p className="text-xs text-gray-500">
              <span className="text-gray-400">{t('letters.friction')}：</span>{compat.friction_point}
            </p>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <h3 className="text-sm text-[#E07A5F] mb-3">{t('letters.basicInfo')}</h3>
          <div className="grid grid-cols-2 gap-2 text-sm text-gray-700">
            {Object.entries(info).filter(([, v]) => v != null).map(([k, v]) => (
              <div key={k} className="flex justify-between bg-gray-50 rounded-lg px-3 py-2">
                <span className="text-gray-400 text-xs">{t(`letters.fields.${k}`)}</span>
                <span className="text-xs">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>

        {active && selected.expires_at && (
          <p className="flex items-center gap-1.5 text-xs text-gray-400 mb-4">
            <Clock className="w-3.5 h-3.5" /> {t('letters.expiresIn')}：<Countdown expiresAt={selected.expires_at} />
          </p>
        )}

        {active && !action && (
          <div className="grid grid-cols-3 gap-2">
            <button onClick={() => setAction('accept')}
                    className="flex flex-col items-center gap-1 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-xs">
              <Heart className="w-4 h-4" /> {t('letters.accept')}
            </button>
            <button onClick={() => doRespond('more_info')} disabled={busy}
                    className="flex flex-col items-center gap-1 py-3 rounded-xl bg-white shadow-sm text-gray-600 text-xs disabled:opacity-40">
              <HelpCircle className="w-4 h-4" /> {t('letters.moreInfo')}
            </button>
            <button onClick={() => setAction('decline')}
                    className="flex flex-col items-center gap-1 py-3 rounded-xl bg-white shadow-sm text-gray-400 text-xs">
              <X className="w-4 h-4" /> {t('letters.decline')}
            </button>
          </div>
        )}
        {selected.my_response === 'accept' && selected.status === 'delivered' && (
          <p className="text-sm text-gray-500 text-center">{t('letters.waitingOther')}</p>
        )}

        {action === 'accept' && (
          <div className="bg-white rounded-2xl shadow-sm p-4 mt-3">
            <p className="text-xs text-gray-500 mb-2">{t('letters.acceptNote')}</p>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
                      className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-[#E07A5F] focus:outline-none" />
            <button onClick={() => doRespond('accept')} disabled={busy}
                    className="w-full mt-2 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm disabled:opacity-40">
              {t('letters.submit')}
            </button>
          </div>
        )}
        {action === 'decline' && (
          <div className="bg-white rounded-2xl shadow-sm p-4 mt-3">
            <p className="text-xs text-gray-500 mb-2">{t('letters.declineTitle')}</p>
            <div className="grid grid-cols-2 gap-2 mb-2">
              {REASONS.map((r) => (
                <button key={r} onClick={() => setReason(r)}
                        className={`py-2 rounded-xl text-xs border ${reason === r ? 'border-[#E07A5F] text-[#E07A5F] bg-orange-50' : 'border-gray-200 text-gray-500'}`}>
                  {t(`letters.declineReasons.${r}`)}
                </button>
              ))}
            </div>
            <button onClick={() => doRespond('decline')} disabled={busy || !reason}
                    className="w-full py-2.5 rounded-xl bg-gray-700 text-white text-sm disabled:opacity-40">
              {t('letters.submit')}
            </button>
          </div>
        )}
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>
    );
  }

  // ===== 列表 =====
  return (
    <div className="max-w-lg mx-auto px-4 py-5">
      <h2 className="text-lg mb-4">{t('letters.title')}</h2>
      {items.length === 0 ? (
        <div className="text-center py-16">
          <Mail className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-1">{t('letters.empty')}</p>
          <p className="text-xs text-gray-400">{t('letters.emptyHint')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <button key={item.reco_pair_id} onClick={() => setSelected(item)}
                    className="w-full text-left bg-white rounded-2xl shadow-sm p-4 hover:shadow transition-shadow">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-[#E07A5F]" />
                  <span className="text-xs text-gray-400">{item.batch_id}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  item.status === 'matched' ? 'bg-rose-50 text-rose-500'
                  : item.status === 'delivered' ? 'bg-orange-50 text-[#E07A5F]'
                  : 'bg-gray-100 text-gray-400'}`}>
                  {item.status === 'matched' ? t('letters.matched')
                    : item.status === 'delivered' ? t('letters.title')
                    : item.status === 'expired' ? t('letters.expired') : t('letters.closed')}
                </span>
              </div>
              <p className="text-sm text-gray-700 line-clamp-2">{item.letter?.reco_text}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
