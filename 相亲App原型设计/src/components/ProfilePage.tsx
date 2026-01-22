import {
  Settings,
  LogOut,
  Edit,
  Camera,
  Heart,
  MessageCircle,
  Shield,
  Crown,
  ChevronRight,
} from "lucide-react";

interface ProfilePageProps {
  user: any;
  onLogout: () => void;
}

export function ProfilePage({
  user,
  onLogout,
}: ProfilePageProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto">
        {/* 头部 */}
        <div className="bg-white p-6 border-b border-gray-200">
          <div className="flex justify-between items-start mb-6">
            <h1 className="text-2xl text-gray-900">我的资料</h1>
            <button className="text-gray-600 hover:text-gray-900 p-2 hover:bg-gray-100 rounded-lg transition-all">
              <Settings className="w-6 h-6" />
            </button>
          </div>

          {/* 用户信息卡片 */}
          <div className="bg-gray-50 rounded-2xl p-5 border border-gray-200">
            <div className="flex items-center gap-4 mb-4">
              <div className="relative">
                <img
                  src={
                    user.avatar ||
                    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&h=400&fit=crop"
                  }
                  alt={user.name}
                  className="w-16 h-16 rounded-full object-cover border-2 border-white shadow-sm"
                />
                <button className="absolute bottom-0 right-0 bg-[#E07A5F] text-white p-1.5 rounded-full hover:bg-[#D4674F] transition-all shadow-sm">
                  <Camera className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex-1">
                <h2 className="text-lg mb-1 text-gray-900">
                  {user.name || "用户"}, {user.age || "25"}
                </h2>
                <p className="text-gray-500 text-sm">
                  {user.bio || "完善你的个人简介"}
                </p>
              </div>
            </div>

            <button className="w-full bg-white border border-gray-300 text-gray-700 py-2.5 rounded-lg hover:bg-gray-50 transition-all flex items-center justify-center gap-2">
              <Edit className="w-4 h-4" />
              <span>编辑资料</span>
            </button>
          </div>
        </div>

        {/* VIP 会员卡 - 淡雅版本 */}
        <div className="p-4">
          <div className="bg-white rounded-2xl p-6 border-2 border-amber-200 relative overflow-hidden">
            {/* 淡雅的背景装饰 */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50 rounded-full -mr-16 -mt-16 opacity-50"></div>
            <div className="absolute bottom-0 left-0 w-24 h-24 bg-orange-50 rounded-full -ml-12 -mb-12 opacity-50"></div>

            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center">
                  <Crown className="w-5 h-5 text-amber-600" />
                </div>
                <h3 className="text-lg text-gray-900">
                  升级VIP会员
                </h3>
              </div>
              <p className="text-gray-600 text-sm mb-4 leading-relaxed">
                解锁更多推荐、查看谁喜欢我、获得优先匹配
              </p>
              <button className="bg-[#E07A5F] text-white px-5 py-2.5 rounded-lg hover:bg-[#D4674F] transition-all text-sm">
                立即升级 - 99 AED/月
              </button>
            </div>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="p-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl p-4 text-center border border-gray-200">
              <div className="w-10 h-10 bg-rose-50 rounded-lg flex items-center justify-center mx-auto mb-2">
                <Heart className="w-5 h-5 text-rose-500" />
              </div>
              <p className="text-2xl mb-1 text-gray-900">0</p>
              <p className="text-xs text-gray-500">获得喜欢</p>
            </div>
            <div className="bg-white rounded-xl p-4 text-center border border-gray-200">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mx-auto mb-2">
                <MessageCircle className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-2xl mb-1 text-gray-900">0</p>
              <p className="text-xs text-gray-500">匹配成功</p>
            </div>
            <div className="bg-white rounded-xl p-4 text-center border border-gray-200">
              <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center mx-auto mb-2">
                <Shield className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-2xl mb-1 text-gray-900">
                100%
              </p>
              <p className="text-xs text-gray-500">
                资料完整度
              </p>
            </div>
          </div>
        </div>

        {/* 菜单选项 */}
        <div className="p-4 space-y-3">
          <div className="bg-white rounded-xl overflow-hidden border border-gray-200">
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all border-b border-gray-100 flex items-center justify-between group">
              <span className="text-gray-900">我的认证</span>
              <div className="flex items-center gap-2">
                <span className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                  已认证
                </span>
                <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </div>
            </button>
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all border-b border-gray-100 flex items-center justify-between group">
              <span className="text-gray-900">谁喜欢我</span>
              <div className="flex items-center gap-2">
                <Crown className="w-4 h-4 text-amber-500" />
                <span className="text-xs text-gray-400">
                  VIP功能
                </span>
                <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
              </div>
            </button>
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all border-b border-gray-100 flex items-center justify-between group">
              <span className="text-gray-900">隐私设置</span>
              <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </button>
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all flex items-center justify-between group">
              <span className="text-gray-900">通知设置</span>
              <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </button>
          </div>

          <div className="bg-white rounded-xl overflow-hidden border border-gray-200">
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all border-b border-gray-100 flex items-center justify-between group">
              <span className="text-gray-900">安全中心</span>
              <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </button>
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all border-b border-gray-100 flex items-center justify-between group">
              <span className="text-gray-900">帮助与反馈</span>
              <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </button>
            <button className="w-full p-4 text-left hover:bg-gray-50 transition-all flex items-center justify-between group">
              <span className="text-gray-900">关于我们</span>
              <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </button>
          </div>

          <button
            onClick={onLogout}
            className="w-full bg-white rounded-xl p-4 text-left hover:bg-red-50 transition-all flex items-center gap-3 text-red-500 border border-gray-200 group"
          >
            <LogOut className="w-5 h-5" />
            <span>退出登录</span>
          </button>
        </div>

        <div className="p-4 text-center pb-8">
          <p className="text-sm text-gray-400 mb-1">
            缘分相遇 v1.0.0
          </p>
          <p className="text-xs text-gray-400">
            认真的人，值得被认真对待
          </p>
        </div>
      </div>
    </div>
  );
}