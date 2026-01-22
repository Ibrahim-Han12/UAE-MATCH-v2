import { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, ArrowLeft, Heart, Shield, Sparkles } from 'lucide-react';

interface AuthPageProps {
  onLogin: (email: string, password: string) => void;
  onRegister: () => void;
  onBack: () => void;
}

type AuthMode = 'login' | 'register';

export function AuthPage({ onLogin, onRegister, onBack }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; confirmPassword?: string }>({});

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateForm = () => {
    const newErrors: { email?: string; password?: string; confirmPassword?: string } = {};

    if (!email) {
      newErrors.email = '请输入邮箱地址';
    } else if (!validateEmail(email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    if (!password) {
      newErrors.password = '请输入密码';
    } else if (password.length < 6) {
      newErrors.password = '密码至少需要6个字符';
    }

    if (mode === 'register') {
      if (!confirmPassword) {
        newErrors.confirmPassword = '请确认密码';
      } else if (password !== confirmPassword) {
        newErrors.confirmPassword = '两次输入的密码不一致';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    if (mode === 'login') {
      // 调用登录逻辑
      onLogin(email, password);
    } else {
      // 注册模式：跳转到AI对话式注册
      onRegister();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex items-center justify-center p-4">
      {/* 返回按钮 */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        <span className="text-sm">返回首页</span>
      </button>

      <div className="w-full max-w-md">
        {/* Logo区域 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full mb-4 shadow-lg">
            <Heart className="w-8 h-8 text-white fill-white" />
          </div>
          <h1 className="text-2xl text-gray-900 mb-2">欢迎回来</h1>
          <p className="text-sm text-gray-600">
            {mode === 'login' ? '登录你的账号，继续寻找缘分' : '创建账号，开启真挚的婚恋之旅'}
          </p>
        </div>

        {/* 主卡片 */}
        <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 border border-rose-100">
          {/* 标签切换 */}
          <div className="flex gap-2 mb-6 bg-gray-100 rounded-full p-1">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 py-2.5 rounded-full text-sm transition-all ${
                mode === 'login'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => setMode('register')}
              className={`flex-1 py-2.5 rounded-full text-sm transition-all ${
                mode === 'register'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              注册
            </button>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 邮箱输入 */}
            <div>
              <label className="block text-sm text-gray-700 mb-2">邮箱地址</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setErrors({ ...errors, email: undefined });
                  }}
                  placeholder="your@email.com"
                  className={`w-full pl-12 pr-4 py-3 rounded-xl border ${
                    errors.email ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-gray-50'
                  } focus:border-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-100 transition-all`}
                />
              </div>
              {errors.email && (
                <p className="text-xs text-red-500 mt-1 ml-1">{errors.email}</p>
              )}
            </div>

            {/* 密码输入 */}
            <div>
              <label className="block text-sm text-gray-700 mb-2">密码</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setErrors({ ...errors, password: undefined });
                  }}
                  placeholder="输入密码"
                  className={`w-full pl-12 pr-12 py-3 rounded-xl border ${
                    errors.password ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-gray-50'
                  } focus:border-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-100 transition-all`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-red-500 mt-1 ml-1">{errors.password}</p>
              )}
            </div>

            {/* 确认密码（仅注册时显示） */}
            {mode === 'register' && (
              <div>
                <label className="block text-sm text-gray-700 mb-2">确认密码</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      setErrors({ ...errors, confirmPassword: undefined });
                    }}
                    placeholder="再次输入密码"
                    className={`w-full pl-12 pr-12 py-3 rounded-xl border ${
                      errors.confirmPassword ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-gray-50'
                    } focus:border-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-100 transition-all`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-xs text-red-500 mt-1 ml-1">{errors.confirmPassword}</p>
                )}
              </div>
            )}

            {/* 记住我 & 忘记密码（仅登录时显示） */}
            {mode === 'login' && (
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 text-rose-500 border-gray-300 rounded focus:ring-rose-200"
                  />
                  <span className="text-sm text-gray-600">记住我</span>
                </label>
                <button
                  type="button"
                  className="text-sm text-[#E07A5F] hover:text-rose-600 transition-colors"
                >
                  忘记密码？
                </button>
              </div>
            )}

            {/* 提交按钮 */}
            <button
              type="submit"
              className="w-full py-3.5 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-xl hover:from-rose-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
            >
              {mode === 'login' ? '登录' : '下一步：完善资料'}
              {mode === 'register' && <Sparkles className="w-4 h-4" />}
            </button>
          </form>

          {/* 注册提示（仅注册时显示） */}
          {mode === 'register' && (
            <div className="mt-6 p-4 bg-orange-50 rounded-xl border border-orange-100">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-[#E07A5F] flex-shrink-0 mt-0.5" />
                <div className="text-xs text-gray-700 leading-relaxed">
                  <p className="mb-1">注册后，你将通过AI对话完成：</p>
                  <ul className="space-y-1 ml-4">
                    <li className="flex items-center gap-1.5">
                      <div className="w-1 h-1 bg-[#E07A5F] rounded-full"></div>
                      个人信息收集
                    </li>
                    <li className="flex items-center gap-1.5">
                      <div className="w-1 h-1 bg-[#E07A5F] rounded-full"></div>
                      EID身份认证（确保真实性）
                    </li>
                    <li className="flex items-center gap-1.5">
                      <div className="w-1 h-1 bg-[#E07A5F] rounded-full"></div>
                      婚恋观念匹配
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* 分割线 */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-white text-gray-500">或者</span>
            </div>
          </div>

          {/* 第三方登录（预留） */}
          <div className="space-y-3">
            <button
              type="button"
              className="w-full py-3 border border-gray-200 rounded-xl hover:bg-gray-50 transition-all text-sm text-gray-700 flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              使用 Google 账号登录
            </button>
          </div>
        </div>

        {/* 底部说明 */}
        <p className="text-center text-xs text-gray-500 mt-6">
          {mode === 'login' ? '登录即表示你同意我们的' : '注册即表示你同意我们的'}
          <button className="text-[#E07A5F] hover:underline mx-1">服务条款</button>
          和
          <button className="text-[#E07A5F] hover:underline ml-1">隐私政策</button>
        </p>
      </div>
    </div>
  );
}
