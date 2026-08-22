/**
 * 照片审核台（DEC-002：种子期人工核验，仅 is_admin 可见）。
 * 这是每天的运营动作，不是一次性开发动作——所以做成界面而不是脚本：
 * "是不是真人、是不是本人"必须看图才能判断。
 */
import { useCallback, useEffect, useState } from 'react';
import { Check, ShieldCheck, X } from 'lucide-react';

import { adminPhotosApi, resolveMediaUrl, type PhotoReviewItem } from '../lib/api';
import { t } from '../i18n';

export function AdminPhotosPage({ onBack }: { onBack?: () => void }) {
  const [items, setItems] = useState<PhotoReviewItem[]>([]);
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await adminPhotosApi.queue();
      setItems(r.items);
    } catch {
      setError(t('adminPhotos.failed'));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const act = async (id: number, action: 'approve' | 'reject') => {
    setError(null);
    const reason = (reasons[id] || '').trim();
    if (action === 'reject' && !reason) {
      setError(t('adminPhotos.reasonRequired'));
      return;
    }
    setBusyId(id);
    try {
      const r = await adminPhotosApi.review(id, action, reason || undefined);
      setFlash(r.promoted
        ? t('adminPhotos.promoted')
        : action === 'approve' ? t('adminPhotos.approved') : t('adminPhotos.rejected'));
      await load();
    } catch {
      setError(t('adminPhotos.failed'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-5 h-5 text-[#E07A5F]" />
          <h2 className="text-xl">{t('adminPhotos.title')}</h2>
          <span className="ml-auto text-sm text-gray-500">
            {t('adminPhotos.queueCount')} {items.length}
          </span>
        </div>
        <p className="text-xs text-gray-500 mb-4">{t('adminPhotos.subtitle')}</p>

        {onBack && (
          <button onClick={onBack} className="text-sm text-gray-500 mb-4">
            {t('common.back')}
          </button>
        )}

        {flash && (
          <div className="bg-emerald-50 text-emerald-700 text-sm rounded-xl px-4 py-3 mb-4">{flash}</div>
        )}
        {error && (
          <div className="bg-rose-50 text-rose-600 text-sm rounded-xl px-4 py-3 mb-4">{error}</div>
        )}

        {items.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-10">{t('adminPhotos.empty')}</p>
        )}

        {items.map((it) => (
          <div key={it.id} className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <img src={resolveMediaUrl(it.file_url) || undefined} alt="" className="w-full rounded-xl mb-3 object-contain max-h-96" />
            <p className="text-xs text-gray-500 mb-1">
              {t('adminPhotos.userLabel')} #{it.user_id}
              {it.is_primary && ` · ${t('photos.isPrimary')}`}
            </p>
            {(it.declared_gender || it.declared_age) && (
              <p className="text-xs text-gray-500 mb-3">
                {t('adminPhotos.declared')}：
                {it.declared_gender === 'male' ? '男' : it.declared_gender === 'female' ? '女' : '—'}
                {it.declared_age ? ` · ${it.declared_age}` : ''}
              </p>
            )}
            <input
              value={reasons[it.id] || ''}
              onChange={(e) => setReasons({ ...reasons, [it.id]: e.target.value })}
              placeholder={t('adminPhotos.reasonPlaceholder')}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm mb-3"
            />
            <div className="flex gap-2">
              <button
                onClick={() => void act(it.id, 'approve')} disabled={busyId === it.id}
                className="flex-1 py-2.5 rounded-xl bg-emerald-500 text-white text-sm inline-flex items-center justify-center gap-1 disabled:opacity-40">
                <Check className="w-4 h-4" /> {t('adminPhotos.approve')}
              </button>
              <button
                onClick={() => void act(it.id, 'reject')} disabled={busyId === it.id}
                className="flex-1 py-2.5 rounded-xl bg-white border border-rose-200 text-rose-600 text-sm inline-flex items-center justify-center gap-1 disabled:opacity-40">
                <X className="w-4 h-4" /> {t('adminPhotos.reject')}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
