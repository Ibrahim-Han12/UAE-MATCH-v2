/**
 * 候补池 / 会员开通页（S3 → S4，第三道闸；BR-501 / A1 裁决）。
 * 展示真实目录：标准可买、高级"即将开放"、尊享席位余量真实。
 */
import { useEffect, useState } from 'react';
import { Crown, Clock, Scale, MailCheck } from 'lucide-react';
import { subscriptionApi, ApiError } from '../lib/api';
import { t } from '../i18n';

interface PaywallPageProps {
  onSubscribed: () => void;
}

export function PaywallPage({ onSubscribed }: PaywallPageProps) {
  const [items, setItems] = useState<any[]>([]);
  const [coupon, setCoupon] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devMode, setDevMode] = useState(false);

  useEffect(() => {
    subscriptionApi.products().then((r) => setItems(r.items)).catch(() => undefined);
  }, []);

  const handleBuy = async (sku: string) => {
    setBusy(sku); setError(null);
    try {
      const session = await subscriptionApi.checkout(sku, coupon.trim() || undefined);
      if (session.dev_note) {
        setDevMode(true);
        // mock 通道：直接模拟支付完成
        const r = await subscriptionApi.devMockPay(sku, coupon.trim() || undefined);
        if (r.state === 'S4' || r.state === 'S5') onSubscribed();
      } else {
        window.location.href = session.checkout_url;  // 真实 Stripe 托管页
      }
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };

  const intervalLabel = (m: number) => (m >= 3 ? t('paywall.perQuarter') : t('paywall.perMonth'));

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 p-4">
      <div className="max-w-2xl mx-auto my-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl mb-2">{t('paywall.title')}</h1>
          <p className="text-sm text-gray-500">{t('paywall.subtitle')}</p>
        </div>

        <div className="flex justify-center gap-6 mb-8 text-xs text-gray-500">
          <span className="flex items-center gap-1"><MailCheck className="w-3.5 h-3.5 text-[#E07A5F]" />{t('paywall.perWeek')}</span>
          <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-[#E07A5F]" />{t('paywall.ritual')}</span>
          <span className="flex items-center gap-1"><Scale className="w-3.5 h-3.5 text-[#E07A5F]" />{t('paywall.fair')}</span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3 mb-6">
          {items.map((item) => (
            <div key={item.sku}
                 className={`bg-white/90 rounded-2xl shadow p-5 border ${item.tier === 'elite' ? 'border-amber-200' : 'border-rose-100'} ${!item.purchasable ? 'opacity-60' : ''}`}>
              <div className="flex items-center gap-1.5 mb-2">
                {item.tier === 'elite' && <Crown className="w-4 h-4 text-amber-500" />}
                <h3 className="text-sm">{item.name}</h3>
              </div>
              <p className="text-2xl mb-1">
                {item.price} <span className="text-xs text-gray-400">{item.currency}{intervalLabel(item.interval_months)}</span>
              </p>
              {item.coming_soon ? (
                <p className="text-xs text-gray-400 mb-3">{t('paywall.comingSoon')}</p>
              ) : item.seats_left !== undefined ? (
                <p className="text-xs text-amber-600 mb-3">{t('paywall.seatsLeft', { n: item.seats_left })}</p>
              ) : (
                <p className="text-xs text-transparent mb-3">·</p>
              )}
              <button
                onClick={() => handleBuy(item.sku)}
                disabled={!item.purchasable || busy !== null || item.seats_left === 0}
                className="w-full py-2 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm disabled:opacity-30">
                {busy === item.sku ? t('common.loading') : (item.coming_soon ? t('paywall.comingSoon') : t('paywall.subscribe'))}
              </button>
            </div>
          ))}
        </div>

        <div className="max-w-sm mx-auto">
          <input
            value={coupon} onChange={(e) => setCoupon(e.target.value.toUpperCase())}
            placeholder={t('paywall.couponPlaceholder')}
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm mb-2"
          />
          <p className="text-xs text-gray-400 text-center">{t('paywall.earlyBird')}</p>
          {devMode && <p className="text-xs text-amber-600 text-center mt-2">{t('paywall.devMockPay')}</p>}
          {error && <p className="text-sm text-red-500 text-center mt-3">{error}</p>}
        </div>
      </div>
    </div>
  );
}
