/**
 * 身份核验页（BR-107，S2 阶段）。合规卖点前置展示："平台不存储证件图像"。
 * 真实 KYC SDK（B1 定型后）在 startKyc 返回的会话里唤起；当前 mock 通道提供开发按钮。
 */
import { useEffect, useState } from 'react';
import { ShieldCheck, CheckCircle2, Circle } from 'lucide-react';
import { verificationApi, ApiError } from '../lib/api';
import { t } from '../i18n';

interface VerificationPageProps {
  onVerified: () => void;
}

export function VerificationPage({ onVerified }: VerificationPageProps) {
  const [status, setStatus] = useState<{ kyc_passed: boolean; photo_approved: boolean; phone_verified: boolean; state: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const s = await verificationApi.status();
      setStatus(s);
      if (s.state === 'S3' || s.state === 'S4' || s.state === 'S5') onVerified();
    } catch (e: any) {
      setError((e as ApiError).message);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const handleStartKyc = async () => {
    setBusy(true); setError(null);
    try {
      const session = await verificationApi.startKyc();
      if (session.provider === 'mock') {
        // 开发通道：直接模拟服务商回传"通过"
        await verificationApi.devMockComplete(session.transaction_id, {
          result: 'passed', full_name: '测试用户',
          birth_date: '1993-01-01', gender: 'female',
          document_expiry: '2030-01-01', eid_number: `784-DEV-${Date.now()}`,
        });
        await refresh();
      } else {
        // 真实 SDK：跳转/内嵌服务商会话（B1 定型后实现）
        setError('KYC SDK 通道尚未接入');
      }
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const Item = ({ done, label }: { done: boolean; label: string }) => (
    <div className="flex items-center gap-2.5 py-2.5">
      {done ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <Circle className="w-5 h-5 text-gray-300" />}
      <span className="text-sm text-gray-700 flex-1">{label}</span>
      <span className={`text-xs ${done ? 'text-emerald-500' : 'text-gray-400'}`}>
        {done ? t('verification.statusDone') : t('verification.statusPending')}
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white/90 rounded-3xl shadow-xl p-8 border border-rose-100">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-5 h-5 text-[#E07A5F]" />
          <h2 className="text-xl">{t('verification.title')}</h2>
        </div>
        <p className="text-xs text-gray-500 mb-6">{t('verification.subtitle')}</p>

        {status && (
          <div className="divide-y divide-gray-100 mb-6">
            <Item done={status.phone_verified} label={t('verification.phoneItem')} />
            <Item done={status.kyc_passed} label={t('verification.kycItem')} />
            <Item done={status.photo_approved} label={t('verification.photoItem')} />
          </div>
        )}

        {status && !status.kyc_passed && (
          <button
            onClick={handleStartKyc} disabled={busy}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm disabled:opacity-40">
            {t('verification.startKyc')}
          </button>
        )}
        {status && status.kyc_passed && !status.photo_approved && (
          <p className="text-sm text-gray-500 text-center">{t('verification.waitingReview')}</p>
        )}
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>
    </div>
  );
}
