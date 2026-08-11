/**
 * 应用入口：导航由后端用户状态机（S1-S7，PRD 2.2）驱动，前端不再自判流程。
 * v1.0 的演示态（注册 10 秒自动过审、手动过审按钮）已拆除。
 *   S1 → 深访；S2 → 身份核验；S3 → 候补/开通会员；S4/S5 → 主应用；S7 → 受限提示。
 */
import { useCallback, useEffect, useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { InterviewPage } from './components/InterviewPage';
import { VerificationPage } from './components/VerificationPage';
import { PaywallPage } from './components/PaywallPage';
import { MainApp } from './components/MainApp';
import { isAuthenticated } from './lib/auth';
import { meApi, authApi } from './lib/api';
import { t } from './i18n';

type Screen = 'landing' | 'login' | 'interview' | 'verification' | 'paywall' | 'main' | 'banned';

function screenForState(state: string): Screen {
  switch (state) {
    case 'S1': return 'interview';
    case 'S2': return 'verification';
    case 'S3': return 'paywall';
    case 'S4':
    case 'S5': return 'main';
    case 'S7': return 'banned';
    default: return 'interview';   // 兼容历史值（后端将 legacy 归一为 S1）
  }
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('landing');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  /** 从后端拉状态机状态并导航（登录后 / 关键动作完成后调用） */
  const syncState = useCallback(async () => {
    if (!isAuthenticated()) {
      setScreen('landing');
      setLoading(false);
      return;
    }
    try {
      const me = await meApi.get();
      setCurrentUser(me);
      setScreen(screenForState(me.status));
    } catch {
      authApi.logout();
      setScreen('landing');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void syncState(); }, [syncState]);

  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setScreen('landing');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E07A5F]" />
      </div>
    );
  }

  switch (screen) {
    case 'landing':
      return <LandingPage onGetStarted={() => (isAuthenticated() ? void syncState() : setScreen('login'))} />;
    case 'login':
      return <LoginPage onLogin={() => void syncState()} onBack={() => setScreen('landing')} />;
    case 'interview':
      return <InterviewPage onCompleted={() => void syncState()} />;
    case 'verification':
      return <VerificationPage onVerified={() => void syncState()} />;
    case 'paywall':
      return <PaywallPage onSubscribed={() => void syncState()} />;
    case 'banned':
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="text-center">
            <p className="text-gray-600 mb-4">{t('gates.banned')}</p>
            <button onClick={handleLogout} className="text-sm text-gray-400 underline">
              {t('common.logout')}
            </button>
          </div>
        </div>
      );
    case 'main':
    default:
      return <MainApp currentUser={currentUser} onLogout={handleLogout} />;
  }
}
