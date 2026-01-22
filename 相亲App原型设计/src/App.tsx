import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { AIOnboardingChat } from './components/AIOnboardingChat';
import { AuthPage } from './components/AuthPage';
import { MainApp } from './components/MainApp';

type AppState = 'landing' | 'auth' | 'onboarding' | 'pending-review' | 'main';

export default function App() {
  const [appState, setAppState] = useState<AppState>('landing');
  const [currentUser, setCurrentUser] = useState<any>(null);

  const handleStartRegistration = () => {
    setAppState('auth');
  };

  const handleShowLogin = () => {
    setAppState('auth');
  };

  const handleBackToLanding = () => {
    setAppState('landing');
  };

  const handleLogin = (email: string, password: string) => {
    // 实际应用中这里会调用后端登录API
    // 模拟登录成功，直接进入主应用
    console.log('登录:', email, password);
    setCurrentUser({ email, name: '用户' });
    setAppState('main');
  };

  const handleStartOnboarding = () => {
    setAppState('onboarding');
  };

  const handleCompleteOnboarding = (userData: any) => {
    setCurrentUser(userData);
    setAppState('pending-review');
    // 模拟审核过程 - 实际应用中这里会调用后端API
    // 为了演示，10秒后自动通过审核
    setTimeout(() => {
      setAppState('main');
    }, 10000);
  };

  const handleApprove = () => {
    // 手动批准审核（用于演示）
    setAppState('main');
  };

  const handleLogout = () => {
    setAppState('landing');
    setCurrentUser(null);
  };

  if (appState === 'landing') {
    return <LandingPage onGetStarted={handleStartRegistration} onLogin={handleShowLogin} />;
  }

  if (appState === 'auth') {
    return (
      <AuthPage
        onLogin={handleLogin}
        onRegister={handleStartOnboarding}
        onBack={handleBackToLanding}
      />
    );
  }

  if (appState === 'onboarding') {
    return <AIOnboardingChat onComplete={handleCompleteOnboarding} />;
  }

  if (appState === 'pending-review') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 text-center border border-rose-100">
          <div className="w-20 h-20 bg-gradient-to-br from-orange-100 to-amber-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg relative">
            <div className="absolute inset-0 bg-orange-300 rounded-full animate-ping opacity-20"></div>
            <svg className="w-10 h-10 text-[#E07A5F] relative z-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl mb-3">资料提交成功</h2>
          <p className="text-gray-600 mb-2 leading-relaxed">
            感谢你完成信息收集！我们正在审核你的身份信息。
          </p>
          <p className="text-sm text-gray-500 mb-6">
            审核通常会在24小时内完成。审核通过后，你将可以：
          </p>
          
          <div className="bg-orange-50 rounded-xl p-4 mb-6 text-left">
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#E07A5F] rounded-full"></div>
                查看每日AI精选推荐
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#E07A5F] rounded-full"></div>
                与匹配对象开始聊天
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#E07A5F] rounded-full"></div>
                随时咨询AI红娘助手
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-[#E07A5F] rounded-full"></div>
                管理你的个人资料
              </li>
            </ul>
          </div>

          <div className="flex items-center justify-center gap-2 text-sm text-[#E07A5F] mb-4">
            <div className="w-2 h-2 bg-[#E07A5F] rounded-full animate-pulse"></div>
            正在审核中...
          </div>

          {/* 开发环境下的快速通过按钮 */}
          <button
            onClick={handleApprove}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            [演示模式：点击立即通过审核]
          </button>
        </div>
      </div>
    );
  }

  return <MainApp currentUser={currentUser} onLogout={handleLogout} />;
}