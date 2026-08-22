/**
 * 照片管理（BR-101, BR-102 / DEC-002）。
 * 上传 → 人工审核 → 过审才会出现在推荐信里。每张照片显示真实审核状态与打回理由，
 * 不用假的"审核中"糊过去。
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, Clock, ImagePlus, Star, Trash2, XCircle } from 'lucide-react';

import { photosApi, resolveMediaUrl, type Photo } from '../lib/api';
import { t } from '../i18n';

const MAX_BYTES = 10 * 1024 * 1024;
const OK_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_PHOTOS = 9;

type Props = { onChange?: (photos: Photo[]) => void };

export function PhotoManager({ onChange }: Props) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const list = await photosApi.mine();
      setPhotos(list);
      onChange?.(list);
    } catch {
      setError(t('photos.uploadFailed'));
    }
  }, [onChange]);

  useEffect(() => { void load(); }, [load]);

  const pick = () => fileInput.current?.click();

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setError(null);
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (!OK_TYPES.includes(file.type)) { setError(t('photos.wrongType')); continue; }
        if (file.size > MAX_BYTES) { setError(t('photos.tooLarge')); continue; }
        await photosApi.upload(file);
      }
      await load();
    } catch {
      setError(t('photos.uploadFailed'));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const setPrimary = async (id: number) => {
    setBusy(true);
    try { await photosApi.setPrimary(id); await load(); }
    catch { setError(t('photos.uploadFailed')); }
    finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    if (!window.confirm(t('photos.removeConfirm'))) return;
    setBusy(true);
    try { await photosApi.remove(id); await load(); }
    catch { setError(t('photos.uploadFailed')); }
    finally { setBusy(false); }
  };

  const StatusChip = ({ p }: { p: Photo }) => {
    if (p.status === 'approved') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
          <CheckCircle2 className="w-3.5 h-3.5" /> {t('photos.statusApproved')}
        </span>
      );
    }
    if (p.status === 'rejected') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-rose-600">
          <XCircle className="w-3.5 h-3.5" /> {t('photos.statusRejected')}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs text-amber-600">
        <Clock className="w-3.5 h-3.5" /> {t('photos.statusPending')}
      </span>
    );
  };

  return (
    <div>
      <h3 className="text-sm mb-1">{t('photos.title')}</h3>
      <p className="text-xs text-gray-500 mb-4 leading-relaxed">{t('photos.subtitle')}</p>

      {photos.length === 0 && (
        <p className="text-sm text-gray-400 mb-4">{t('photos.empty')}</p>
      )}

      <div className="grid grid-cols-3 gap-3 mb-4">
        {photos.map((p) => (
          <div key={p.id} className="relative">
            <img
              src={resolveMediaUrl(p.file_url) || undefined}
              alt=""
              className={`w-full aspect-square object-cover rounded-xl border ${
                p.status === 'rejected' ? 'border-rose-200 opacity-60' : 'border-gray-200'
              }`}
            />
            {p.is_primary && (
              <span className="absolute top-1.5 left-1.5 bg-[#E07A5F] text-white text-xs px-1.5 py-0.5 rounded-md">
                {t('photos.isPrimary')}
              </span>
            )}
            <div className="mt-1.5">
              <StatusChip p={p} />
              {p.status === 'rejected' && p.rejection_reason && (
                <p className="text-xs text-rose-500 mt-0.5 leading-snug">
                  {t('photos.rejectedPrefix')}{p.rejection_reason}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {!p.is_primary && p.status === 'approved' && (
                <button onClick={() => setPrimary(p.id)} disabled={busy}
                        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-[#E07A5F]">
                  <Star className="w-3.5 h-3.5" /> {t('photos.setPrimary')}
                </button>
              )}
              <button onClick={() => remove(p.id)} disabled={busy}
                      className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-rose-500">
                <Trash2 className="w-3.5 h-3.5" /> {t('photos.remove')}
              </button>
            </div>
          </div>
        ))}

        {photos.length < MAX_PHOTOS && (
          <button
            onClick={pick} disabled={busy}
            className="w-full aspect-square rounded-xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 hover:border-[#E07A5F] hover:text-[#E07A5F] disabled:opacity-40">
            <ImagePlus className="w-6 h-6 mb-1" />
            <span className="text-xs">{busy ? t('photos.uploading') : t('photos.addBtn')}</span>
          </button>
        )}
      </div>

      <input
        ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" multiple
        onChange={(e) => void handleFiles(e.target.files)} className="hidden"
      />

      <p className="text-xs text-gray-400">{t('photos.limitHint')}</p>
      {error && (
        <p className="text-sm text-rose-500 mt-2">
          {error} <button onClick={pick} className="underline">{t('photos.retry')}</button>
        </p>
      )}
    </div>
  );
}
