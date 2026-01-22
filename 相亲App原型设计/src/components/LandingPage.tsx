import { Heart, Shield, UserCheck, Sparkles, ArrowRight, Brain } from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
  onLogin: () => void;
}

export function LandingPage({ onGetStarted, onLogin }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-orange-50 to-white pt-20 pb-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-full mb-6 text-sm shadow-sm">
            <Shield className="w-4 h-4 text-[#E07A5F]" />
            面向UAE华人的严肃婚恋平台
          </div>
          <h1 className="text-5xl md:text-6xl mb-6 text-gray-900">
            在中东，遇见对的人
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed">
            真实身份认证 · AI智能推荐 · 以结婚为目的<br />
            帮助在阿联酋生活工作的华人找到适合步入婚姻的长期伴侣
          </p>
          <button
            onClick={onGetStarted}
            className="bg-[#E07A5F] text-white px-8 py-4 rounded-xl text-lg hover:bg-[#D4674F] transition-all shadow-md hover:shadow-lg inline-flex items-center gap-2"
          >
            开始认真相亲
            <ArrowRight className="w-5 h-5" />
          </button>
          <p className="text-sm text-gray-500 mt-4">
            已有超过1,000位认真的单身人士加入
          </p>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto py-20 px-4">
        <h2 className="text-3xl md:text-4xl text-center mb-12 text-gray-900">为什么选择我们</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-lg transition-all">
            <div className="w-14 h-14 bg-orange-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <UserCheck className="w-7 h-7 text-[#E07A5F]" />
            </div>
            <h3 className="text-xl mb-2 text-center text-gray-900">真实身份认证</h3>
            <p className="text-gray-600 text-sm text-center leading-relaxed">
              EID/护照验证，人工审核，杜绝虚假信息和骗婚风险
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-lg transition-all">
            <div className="w-14 h-14 bg-orange-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Heart className="w-7 h-7 text-[#E07A5F]" />
            </div>
            <h3 className="text-xl mb-2 text-center text-gray-900">严肃婚恋导向</h3>
            <p className="text-gray-600 text-sm text-center leading-relaxed">
              所有用户都以结婚为目的，匹配婚恋时间线一致的人
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-lg transition-all">
            <div className="w-14 h-14 bg-orange-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Brain className="w-7 h-7 text-[#E07A5F]" />
            </div>
            <h3 className="text-xl mb-2 text-center text-gray-900">AI深度分析</h3>
            <p className="text-gray-600 text-sm text-center leading-relaxed">
              AI深度分析匹配度，提供详细报告，而非简单刷卡
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-lg transition-all">
            <div className="w-14 h-14 bg-orange-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Shield className="w-7 h-7 text-[#E07A5F]" />
            </div>
            <h3 className="text-xl mb-2 text-center text-gray-900">隐私安全保护</h3>
            <p className="text-gray-600 text-sm text-center leading-relaxed">
              信息加密存���，严格隐私保护，只有匹配成功才能聊天
            </p>
          </div>
        </div>
      </div>

      {/* How it works */}
      <div className="bg-gray-50 py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl text-center mb-12 text-gray-900">简单三步，开始认真相亲</h2>
          <div className="space-y-6">
            <div className="flex gap-6 items-start bg-white rounded-2xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex-shrink-0 w-12 h-12 bg-[#E07A5F] text-white rounded-xl flex items-center justify-center text-xl">
                1
              </div>
              <div>
                <h3 className="text-xl mb-2 text-gray-900">完善真实资料</h3>
                <p className="text-gray-600 leading-relaxed">
                  填写详细问卷，包括个人情况、在UAE生活规划、婚恋观和择偶条件，上传身份认证资料
                </p>
              </div>
            </div>
            <div className="flex gap-6 items-start bg-white rounded-2xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex-shrink-0 w-12 h-12 bg-[#E07A5F] text-white rounded-xl flex items-center justify-center text-xl">
                2
              </div>
              <div>
                <h3 className="text-xl mb-2 text-gray-900">接收AI分析报告</h3>
                <p className="text-gray-600 leading-relaxed">
                  AI根据你的条件深度分析候选人，每天推送3-5位高匹配度对象，附带详细兼容性分析报告
                </p>
              </div>
            </div>
            <div className="flex gap-6 items-start bg-white rounded-2xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex-shrink-0 w-12 h-12 bg-[#E07A5F] text-white rounded-xl flex items-center justify-center text-xl">
                3
              </div>
              <div>
                <h3 className="text-xl mb-2 text-gray-900">双向匹配聊天</h3>
                <p className="text-gray-600 leading-relaxed">
                  互相表达好感后开启聊天，深入了解彼此，线下见面开始真实交往
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Differentiator */}
      <div className="max-w-5xl mx-auto py-20 px-4">
        <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl p-8 md:p-12 border border-orange-100">
          <div className="flex items-start gap-4 mb-6">
            <div className="w-12 h-12 bg-[#E07A5F] rounded-xl flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl md:text-3xl mb-3 text-gray-900">我们与传统约会app的区别</h2>
              <p className="text-gray-600 leading-relaxed">
                不是无休止的左滑右滑，而是AI红娘精心为你挑选的每日推荐。每个推荐都经过深度分析，附带详细的兼容性报告，帮助你做出明智的决定。
              </p>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <p className="text-sm text-gray-500 mb-1">传统约会app</p>
              <p className="text-gray-800">无限刷卡，浅层匹配</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-orange-200">
              <p className="text-sm text-[#E07A5F] mb-1">缘分相遇</p>
              <p className="text-gray-800">精选推荐，深度分析</p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="py-20 px-4 text-center bg-gray-50">
        <h2 className="text-3xl md:text-4xl mb-4 text-gray-900">认真的人，值得被认真对待</h2>
        <p className="text-gray-600 mb-8 text-lg">
          不贩卖焦虑，不过度催婚，我们只想帮你找到对的人
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={onGetStarted}
            className="bg-[#E07A5F] text-white px-8 py-4 rounded-xl text-lg hover:bg-[#D4674F] transition-all shadow-md hover:shadow-lg inline-flex items-center gap-2"
          >
            开始注册
            <ArrowRight className="w-5 h-5" />
          </button>
          <button
            onClick={onLogin}
            className="text-gray-600 hover:text-gray-900 transition-colors inline-flex items-center gap-1"
          >
            已有账号？<span className="text-[#E07A5F] hover:underline">立即登录</span>
          </button>
        </div>
      </div>
    </div>
  );
}