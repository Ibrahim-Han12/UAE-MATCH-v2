/**
 * 深访对话页（BR-201 / PRD 5.1）。取代旧 AIOnboardingChat（问题硬编码版）。
 * 流程：分层同意（PDPL）→ 与小缘对话（进度=“小缘已经了解你 X%”，禁表单语言）
 *     → 完成 → 画像报告 → 速写确认（进入候补池前置）。
 */
import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles, FileText, ShieldCheck } from 'lucide-react';
import { interviewApi, recommendationApi, ApiError } from '../lib/api';
import { t } from '../i18n';

interface Msg { role: 'user' | 'assistant'; content: string; }

interface InterviewPageProps {
  onCompleted: () => void;   // 深访完成且速写确认后：App 重新拉状态导航
}

export function InterviewPage({ onCompleted }: InterviewPageProps) {
  const [phase, setPhase] = useState<'consent' | 'chat' | 'report'>('consent');
  const [consents, setConsents] = useState<{ basic: boolean; sensitive: boolean; ai_processing: boolean }>({
    basic: true, sensitive: true, ai_processing: true,
  });
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [report, setReport] = useState<Record<string, string> | null>(null);
  const [sketchConfirmed, setSketchConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 已授权则直接进对话（恢复会话）
    interviewApi.getConsents().then((r) => {
      if (r.granted.includes('basic')) {
        setPhase('chat');
        void beginChat();
      }
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const beginChat = async () => {
    try {
      const hist = await interviewApi.getHistory();
      if (hist.length > 0) {
        setMessages(hist.map((h: any) => ({ role: h.role, content: h.content })));
      }
      const r = await interviewApi.start();
      if (r.message) setMessages((m) => [...m, { role: 'assistant', content: r.message! }]);
      setProgress(Math.round((r.progress?.completion || 0) * 100));
    } catch (e: any) {
      setError((e as ApiError).message);
    }
  };

  const handleConsent = async () => {
    setError(null);
    const types = Object.entries(consents).filter(([, v]) => v).map(([k]) => k);
    if (!types.includes('basic')) { setError(t('gates.interview')); return; }
    setBusy(true);
    try {
      await interviewApi.grantConsents(types);
      setPhase('chat');
      await beginChat();
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setBusy(true);
    try {
      const r = await interviewApi.sendMessage(text);
      setMessages((m) => [...m, { role: 'assistant', content: r.message }]);
      setProgress(Math.round((r.progress?.completion || 0) * 100));
      if (r.completed) {
        setCompleted(true);
      }
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const openReport = async () => {
    try {
      const r = await interviewApi.getReport();
      setReport(r.sections);
      setPhase('report');
    } catch (e: any) {
      setError((e as ApiError).message);
    }
  };

  const handleConfirmSketch = async () => {
    setBusy(true);
    try {
      await recommendationApi.confirmSketch();
      setSketchConfirmed(true);
      onCompleted();
    } catch (e: any) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  // ===== 同意门 =====
  if (phase === 'consent') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white/90 rounded-3xl shadow-xl p-8 border border-rose-100">
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="w-5 h-5 text-[#E07A5F]" />
            <h2 className="text-xl">{t('interview.consentTitle')}</h2>
          </div>
          <p className="text-sm text-gray-500 mb-5">{t('interview.consentIntro')}</p>
          {([
            ['basic', t('interview.consentBasic')],
            ['sensitive', t('interview.consentSensitive')],
            ['ai_processing', t('interview.consentAI')],
          ] as const).map(([key, label]) => (
            <label key={key} className="flex items-start gap-2.5 mb-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consents[key]}
                onChange={(e) => setConsents((c) => ({ ...c, [key]: e.target.checked }))}
                className="mt-1 accent-[#E07A5F]"
              />
              <span className="text-sm text-gray-700">{label}</span>
            </label>
          ))}
          <p className="text-xs text-gray-400 mb-5">{t('interview.consentNote')}</p>
          {error && <p className="text-sm text-red-500 mb-3">{error}</p>}
          <button
            onClick={handleConsent} disabled={busy || !consents.basic}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white disabled:opacity-40">
            {t('interview.consentStart')}
          </button>
        </div>
      </div>
    );
  }

  // ===== 报告页 =====
  if (phase === 'report' && report) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 p-4">
        <div className="max-w-2xl mx-auto bg-white/90 rounded-3xl shadow-xl p-8 border border-rose-100 my-8">
          <div className="flex items-center gap-2 mb-6">
            <FileText className="w-5 h-5 text-[#E07A5F]" />
            <h2 className="text-xl">{t('interview.reportTitle')}</h2>
          </div>
          {(['story', 'sketch', 'seeking', 'strategy'] as const).map((k) => (
            <div key={k} className="mb-6">
              <h3 className="text-sm text-[#E07A5F] mb-1.5">{t(`interview.reportSections.${k}`)}</h3>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{report[k]}</p>
            </div>
          ))}
          <div className="bg-orange-50 rounded-xl p-4 mt-8">
            <h3 className="text-sm mb-1">{t('interview.sketchConfirmTitle')}</h3>
            <p className="text-xs text-gray-500 mb-3">{t('interview.sketchConfirmBody')}</p>
            {error && <p className="text-sm text-red-500 mb-2">{error}</p>}
            <button
              onClick={handleConfirmSketch} disabled={busy || sketchConfirmed}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm disabled:opacity-40">
              {t('interview.sketchConfirmBtn')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ===== 对话页 =====
  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex flex-col">
      <div className="bg-white/80 backdrop-blur-sm border-b border-rose-100 px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#E07A5F]" />
              <span className="text-sm">{t('interview.title')}</span>
            </div>
            <span className="text-xs text-gray-500">{t('interview.progressLabel')} {progress}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-rose-400 to-orange-400 transition-all duration-500"
                 style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-2xl mx-auto space-y-3">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-br-md'
                  : 'bg-white shadow-sm text-gray-700 rounded-bl-md'
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex justify-start">
              <div className="bg-white shadow-sm px-4 py-2.5 rounded-2xl rounded-bl-md">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"
                         style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          {completed && (
            <div className="bg-white rounded-2xl shadow p-5 text-center">
              <h3 className="text-lg mb-1">{t('interview.completedTitle')}</h3>
              <p className="text-sm text-gray-500 mb-4">{t('interview.completedBody')}</p>
              <button
                onClick={openReport}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm">
                {t('interview.viewReport')}
              </button>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="bg-white/80 backdrop-blur-sm border-t border-rose-100 px-4 py-3">
        <div className="max-w-2xl mx-auto flex gap-2">
          <input
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={t('interview.inputPlaceholder')}
            disabled={busy || completed}
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:border-[#E07A5F] focus:outline-none text-sm disabled:bg-gray-50"
          />
          <button
            onClick={handleSend} disabled={busy || !input.trim() || completed}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white disabled:opacity-40">
            <Send className="w-4 h-4" />
          </button>
        </div>
        {error && <p className="max-w-2xl mx-auto text-xs text-red-500 mt-2">{error}</p>}
      </div>
    </div>
  );
}
