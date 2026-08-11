/**
 * 登录页（BR-001/002/108）。
 * 主路径：手机 OTP 验证即登录（无单独注册步骤）；辅路径：邮箱+密码。
 * 明确不做：微信 / Google / Apple 第三方登录（BR-001 决策，页面不出现任何第三方按钮）。
 */
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Phone, Mail, ShieldCheck } from 'lucide-react';
import { otpApi, authApi, ApiError } from '../lib/api';
import { t } from '../i18n';

interface LoginPageProps {
  onLogin: (userData: any) => void;
  onBack: () => void;
}

export function LoginPage({ onLogin, onBack }: LoginPageProps) {
  const [tab, setTab] = useState<'phone' | 'email'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => () => { if (timerRef.current) window.clearInterval(timerRef.current); }, []);

  const startCountdown = (seconds: number) => {
    setCountdown(seconds);
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      setCountdown((s) => {
        if (s <= 1) { if (timerRef.current) window.clearInterval(timerRef.current); return 0; }
        return s - 1;
      });
    }, 1000);
  };

  const handleSendCode = async () => {
    setError(null);
    if (!phone.trim()) return;
    setBusy(true);
    try {
      const resp = await otpApi.request(phone.trim());
      startCountdown(resp.resend_after || 60);
      if (resp.debug_code) setDebugCode(resp.debug_code);  // 仅 mock 短信通道返回
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async () => {
    setError(null);
    if (!phone.trim() || code.trim().length < 6) return;
    setBusy(true);
    try {
      const resp = await otpApi.verify(phone.trim(), code.trim());
      onLogin({ phone: phone.trim(), is_new_user: resp.is_new_user });
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const handleEmailLogin = async () => {
    setError(null);
    if (!email.trim() || !password) return;
    setBusy(true);
    try {
      await authApi.login(email.trim(), password);
      onLogin({ email: email.trim() });
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 border border-rose-100">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> {t('common.back')}
        </button>

        <h1 className="text-2xl mb-1">{t('login.title')}</h1>
        <p className="text-sm text-gray-500 mb-6">{t('login.subtitle')}</p>

        <div className="flex rounded-xl bg-gray-100 p-1 mb-6">
          <button
            onClick={() => { setTab('phone'); setError(null); }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm transition-colors ${tab === 'phone' ? 'bg-white shadow text-[#E07A5F]' : 'text-gray-500'}`}>
            <Phone className="w-4 h-4" /> {t('login.phoneTab')}
          </button>
          <button
            onClick={() => { setTab('email'); setError(null); }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm transition-colors ${tab === 'email' ? 'bg-white shadow text-[#E07A5F]' : 'text-gray-500'}`}>
            <Mail className="w-4 h-4" /> {t('login.emailTab')}
          </button>
        </div>

        {tab === 'phone' ? (
          <div className="space-y-4">
            <input
              type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder={t('login.phonePlaceholder')}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm"
            />
            <div className="flex gap-2">
              <input
                type="text" inputMode="numeric" maxLength={6}
                value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder={t('login.codePlaceholder')}
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm tracking-widest"
              />
              <button
                onClick={handleSendCode}
                disabled={busy || countdown > 0 || !phone.trim()}
                className="px-4 py-3 rounded-xl bg-orange-50 text-[#E07A5F] text-sm disabled:opacity-40 whitespace-nowrap">
                {countdown > 0 ? t('login.resendIn', { s: countdown }) : t('login.sendCode')}
              </button>
            </div>
            {debugCode && (
              <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
                [开发模式] 验证码：{debugCode}
              </p>
            )}
            <button
              onClick={handleVerify}
              disabled={busy || code.length < 6}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white disabled:opacity-40">
              {t('login.verifyAndLogin')}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder={t('login.emailPlaceholder')}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm"
            />
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder={t('login.passwordPlaceholder')}
              onKeyDown={(e) => e.key === 'Enter' && handleEmailLogin()}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm"
            />
            <button
              onClick={handleEmailLogin}
              disabled={busy || !email.trim() || !password}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white disabled:opacity-40">
              {t('login.emailLogin')}
            </button>
          </div>
        )}

        {error && <p className="text-sm text-red-500 mt-4">{error}</p>}

        <div className="mt-6 space-y-2">
          <p className="flex items-start gap-1.5 text-xs text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {t('login.singleDeviceHint')}
          </p>
          <p className="text-xs text-gray-400">{t('login.agreeHint')}</p>
        </div>
      </div>
    </div>
  );
}
