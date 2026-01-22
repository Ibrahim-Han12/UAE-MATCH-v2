import { useState, useEffect } from 'react';
import { LandingPage } from './components/LandingPage';
import { AIOnboardingChat } from './components/AIOnboardingChat';
import { MainApp } from './components/MainApp';
import { LoginPage } from './components/LoginPage';
import { isAuthenticated } from './lib/auth';
import { profileApi, authApi } from './lib/api';

type AppState = 'landing' | 'login' | 'onboarding' | 'pending-review' | 'approved' | 'main';

export default function App() {
  const [appState, setAppState] = useState<AppState>('landing');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // 检查登录状态
  useEffect(() => {
    const checkAuth = async () => {
      if (isAuthenticated()) {
        try {
          // 尝试获取用户资料
          const profile = await profileApi.getMyProfile();
          setCurrentUser({
            id: profile.id,
            ...profile,
          });
          setAppState('main');
        } catch (error: any) {
          // 如果获取资料失败，可能是资料未完成，进入引导流程
          if (error.status === 404) {
            setAppState('onboarding');
          } else {
            // 其他错误，清除 token 并返回登录页
            authApi.logout();
            setAppState('landing');
          }
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  const handleStartRegistration = () => {
    // 检查是否已登录
    if (!isAuthenticated()) {
      // 未登录，显示登录页面
      setAppState('login');
    } else {
      // 已登录，直接进入引导流程
      setAppState('onboarding');
    }
  };

  const handleLogin = async (userData: any) => {
    try {
      // 登录成功后，检查是否有完整资料
      const profile = await profileApi.getMyProfile();
      if (profile && profile.name) {
        // 有完整资料，进入主应用
        setCurrentUser({
          id: profile.id,
          ...profile,
        });
        setAppState('main');
      } else {
        // 资料不完整，进入引导流程
        setCurrentUser(userData);
        setAppState('onboarding');
      }
    } catch (error: any) {
      if (error.status === 404) {
        // 没有资料，进入引导流程
        setCurrentUser(userData);
        setAppState('onboarding');
      } else {
        console.error('检查资料失败:', error);
        setCurrentUser(userData);
        setAppState('onboarding');
      }
    }
  };

  const handleCompleteOnboarding = async (userData: any) => {
    try {
      // 调用后端完成注册
      await authApi.completeRegistration(true);
      setCurrentUser(userData);
      setAppState('pending-review');
      
      // 模拟审核过程 - 实际应用中这里会调用后端API检查审核状态
      // 为了演示，10秒后自动通过审核
      setTimeout(() => {
        setAppState('main');
      }, 10000);
    } catch (error: any) {
      console.error('完成注册失败:', error);
      alert(error.message || '注册失败，请重试');
    }
  };

  const handleApprove = () => {
    // 手动批准审核（用于演示）
    setAppState('main');
  };

  const handleLogout = () => {
    authApi.logout();
    setAppState('landing');
    setCurrentUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#E07A5F]" />
      </div>
    );
  }

  if (appState === 'landing') {
    return <LandingPage onGetStarted={handleStartRegistration} />;
  }

  if (appState === 'login') {
    return <LoginPage onLogin={handleLogin} onBack={() => setAppState('landing')} />;
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