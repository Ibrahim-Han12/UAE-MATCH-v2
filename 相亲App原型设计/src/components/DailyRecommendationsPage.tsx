import { useState } from 'react';
import { Heart, MapPin, Briefcase, GraduationCap, Clock, CheckCircle, Sparkles, Crown, ThumbsUp, ThumbsDown, Zap, Target, Brain } from 'lucide-react';

interface DailyRecommendationsPageProps {
  onLike: (user: any) => void;
  dailyLikesUsed: number;
  dailyLikesLimit: number;
  isVIP?: boolean;
}

const DAILY_RECOMMENDATIONS = [
  {
    id: '2',
    name: '陈雨',
    age: 28,
    verified: true,
    avatar: 'https://images.unsplash.com/photo-1649589244330-09ca58e4fa64?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjB3b21hbiUyMHBvcnRyYWl0fGVufDF8fHx8MTc2NTkxMDE0OHww&ixlib=rb-4.1.0&q=80&w=1080',
    bio: '在迪拜工作3年的产品经理，希望找到一个愿意长期在UAE发展的伴侣。喜欢旅行、美食和阅读。',
    location: 'Dubai',
    occupation: '产品经理',
    industry: '互联网',
    education: '硕士',
    marriageTimeline: '1-2年内',
    longTermPlan: '长期留在UAE',
    yearsInUAE: '3年',
    matchScore: 92,
    matchReason: '你们都计划长期在UAE发展，婚恋时间线一致（1-2年内），且都在科技行业工作，生活圈相近。',
    aiAnalysis: {
      compatibility: [
        { label: '婚恋目标', score: 95, reason: '你们都希望在1-2年内结婚，时间线高度一致' },
        { label: '生活规划', score: 92, reason: '都计划长期在UAE发展，对未来有明确共识' },
        { label: '职业匹配', score: 88, reason: '同在科技行业，工作时间和生活节奏相近' },
        { label: '价值观', score: 90, reason: '都重视家庭和事业的平衡' },
      ],
      highlights: [
        '你们的年龄差距适中（3岁），处于最佳婚配范围',
        '都在Dubai工作，见面约会非常方便',
        '教育背景相当，沟通不会有障碍',
        '对方的兴趣爱好（旅行、美食）与你高度重合',
      ],
      considerations: [
        '对方工作较忙，可能需要理解和支持',
        '建议初期见面多聊聊职业发展规划',
      ],
    },
    tags: ['旅行', '美食', '阅读'],
  },
  {
    id: '3',
    name: '李思琪',
    age: 26,
    verified: true,
    avatar: 'https://images.unsplash.com/photo-1581065178026-390bc4e78dad?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhc2lhbiUyMHdvbWFuJTIwcHJvZmVzc2lvbmFsfGVufDF8fHx8MTc2NTk4MzA1Nnww&ixlib=rb-4.1.0&q=80&w=1080',
    bio: '在阿布扎比的金融分析师，持有黄金签证。喜欢健身和摄影，期待遇到有责任感的另一半。',
    location: 'Abu Dhabi',
    occupation: '金融分析师',
    industry: '金融',
    education: '硕士',
    marriageTimeline: '1-2年内',
    longTermPlan: '长期留在UAE',
    yearsInUAE: '4年',
    matchScore: 88,
    matchReason: '你们的年龄差距在理想范围内，都希望在1-2年内结婚，且对未来规划都很明确。',
    aiAnalysis: {
      compatibility: [
        { label: '婚恋目标', score: 90, reason: '婚恋时间线一致，都认真考虑婚姻' },
        { label: '生活规划', score: 88, reason: '都有长期在UAE发展的计划' },
        { label: '经济基础', score: 85, reason: '对方持有黄金签证，经济稳定' },
        { label: '生活方式', score: 82, reason: '都注重健康生活，有共同话题' },
      ],
      highlights: [
        '对方持有黄金签证，说明在UAE有稳定的经济基础',
        '工作4年，比较成熟稳重',
        '注重健身，生活方式健康积极',
        '在金融行业，收入稳定可靠',
      ],
      considerations: [
        '在Abu Dhabi工作，距离Dubai约1.5小时车程',
        '工作性质可能压力较大，需要相互理解',
      ],
    },
    tags: ['健身', '摄影', '咖啡'],
  },
  {
    id: '4',
    name: '王欣怡',
    age: 27,
    verified: true,
    avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800&h=800&fit=crop',
    bio: '迪拜的建筑设计师，热爱艺术和设计。希望找到一个欣赏美好事物的伴侣，一起创造美好生活。',
    location: 'Dubai',
    occupation: '建筑设计师',
    industry: '设计',
    education: '硕士',
    marriageTimeline: '1-2年内',
    longTermPlan: '灵活，可商量',
    yearsInUAE: '2年',
    matchScore: 85,
    matchReason: '你们都在创意相关行业，对生活品质有共同追求，且都持开放态度面对未来。',
    aiAnalysis: {
      compatibility: [
        { label: '婚恋目标', score: 85, reason: '婚恋时间线基本一致' },
        { label: '生活规划', score: 80, reason: '对方态度灵活，愿意协商未来' },
        { label: '审美品味', score: 92, reason: '都追求生活品质，有共同的审美' },
        { label: '性格匹配', score: 83, reason: '创意型人格，思维活跃' },
      ],
      highlights: [
        '在设计行业，有独特的审美眼光',
        '对生活品质有追求，懂得享受生活',
        '性格开放包容，沟通起来会比较轻松',
        '年龄相近，共同话题多',
      ],
      considerations: [
        '对未来规划持开放态度，需要深入沟通达成共识',
        '创意行业工作时间可能不太规律',
      ],
    },
    tags: ['艺术', '设计', '旅行'],
  },
];

export function DailyRecommendationsPage({ onLike, dailyLikesUsed, dailyLikesLimit, isVIP = false }: DailyRecommendationsPageProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [passedUsers, setPassedUsers] = useState<string[]>([]);
  const [likedUsers, setLikedUsers] = useState<string[]>([]);

  const availableRecommendations = DAILY_RECOMMENDATIONS.filter(
    (user) => !passedUsers.includes(user.id) && !likedUsers.includes(user.id)
  );

  const hasReachedLimit = dailyLikesUsed >= dailyLikesLimit;

  const handlePass = (userId: string) => {
    setPassedUsers([...passedUsers, userId]);
    setSelectedIndex(null);
  };

  const handleLike = (user: any) => {
    if (!hasReachedLimit) {
      setLikedUsers([...likedUsers, user.id]);
      onLike(user);
      setSelectedIndex(null);
    }
  };

  if (hasReachedLimit && !isVIP) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm p-8 text-center border border-gray-200">
          <div className="w-16 h-16 bg-orange-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Clock className="w-8 h-8 text-[#E07A5F]" />
          </div>
          <h2 className="text-2xl mb-2">今日推荐已用完</h2>
          <p className="text-gray-600 mb-6">
            免费用户每天可以查看3位推荐对象。明天会有新的推荐等着你！
          </p>
          <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl p-5 mb-6 border border-orange-100">
            <div className="flex items-center gap-2 mb-3">
              <Crown className="w-5 h-5 text-[#F4A261]" />
              <h3 className="text-sm">升级为VIP会员</h3>
            </div>
            <ul className="text-sm text-gray-700 space-y-2 text-left mb-4">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#E07A5F]" />
                每天10个推荐名额
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#E07A5F]" />
                查看"谁喜欢我"
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#E07A5F]" />
                更详细的匹配分析
              </li>
            </ul>
            <button className="w-full bg-[#E07A5F] text-white py-2.5 rounded-lg hover:bg-[#D4674F] transition-colors">
              升级VIP - 99 AED/月
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (availableRecommendations.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm p-8 text-center border border-gray-200">
          <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl mb-2">今日推荐已看完</h2>
          <p className="text-gray-600 mb-4">
            你已经看完了今天的所有推荐。明天会有新的推荐等着你！
          </p>
        </div>
      </div>
    );
  }

  const currentUser = selectedIndex !== null ? availableRecommendations[selectedIndex] : null;

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-4xl mx-auto pt-4">
        {/* 页面标题 */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-[#E07A5F] rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl">今日精选推荐</h1>
              <p className="text-sm text-gray-500">AI红娘为你精心挑选的{availableRecommendations.length}位候选</p>
            </div>
          </div>
        </div>

        {/* 提示卡片 */}
        <div className="bg-orange-50 border border-orange-100 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <Brain className="w-5 h-5 text-[#E07A5F] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-gray-800 mb-1">
                <strong>AI已为您分析</strong>
              </p>
              <p className="text-sm text-gray-600">
                基于你的个人资料、婚恋观和择偶条件，AI已对每位候选人进行了深度匹配分析。点击卡片查看详细分析报告。
              </p>
            </div>
          </div>
        </div>

        {/* 推荐列表 */}
        {selectedIndex === null ? (
          <div className="space-y-4">
            {availableRecommendations.map((user, index) => (
              <button
                key={user.id}
                onClick={() => setSelectedIndex(index)}
                className="w-full bg-white rounded-xl p-5 border border-gray-200 hover:border-[#E07A5F] hover:shadow-lg transition-all text-left group"
              >
                <div className="flex gap-4">
                  <div className="relative flex-shrink-0">
                    <img
                      src={user.avatar}
                      alt={user.name}
                      className="w-24 h-24 rounded-xl object-cover"
                    />
                    {user.verified && (
                      <div className="absolute -top-2 -right-2 bg-[#E07A5F] text-white p-1 rounded-full">
                        <CheckCircle className="w-4 h-4" />
                      </div>
                    )}
                    <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-white px-2 py-0.5 rounded-full text-xs border border-gray-200 whitespace-nowrap">
                      匹配 {user.matchScore}%
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg">{user.name}, {user.age}</h3>
                      <span className="text-xs bg-orange-50 text-[#E07A5F] px-2 py-0.5 rounded">
                        今日推荐 #{index + 1}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                      <MapPin className="w-4 h-4" />
                      <span>{user.location}</span>
                      <span>•</span>
                      <span>{user.occupation}</span>
                    </div>
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">{user.bio}</p>
                    <div className="flex items-center gap-2 text-sm text-[#E07A5F] group-hover:gap-3 transition-all">
                      <Zap className="w-4 h-4" />
                      <span>查看AI分析报告</span>
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          // 详细分析页面
          <div className="space-y-4">
            {/* 返回按钮 */}
            <button
              onClick={() => setSelectedIndex(null)}
              className="text-gray-600 hover:text-gray-900 flex items-center gap-2 mb-2"
            >
              ← 返回推荐列表
            </button>

            {/* 用户基本信息卡片 */}
            <div className="bg-white rounded-xl overflow-hidden border border-gray-200">
              <div className="relative h-80">
                <img
                  src={currentUser!.avatar}
                  alt={currentUser!.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                {currentUser!.verified && (
                  <div className="absolute top-4 right-4 bg-white text-[#E07A5F] px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 shadow-lg">
                    <CheckCircle className="w-4 h-4" />
                    已认证
                  </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                  <h2 className="text-3xl mb-2">{currentUser!.name}, {currentUser!.age}</h2>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {currentUser!.location}
                    </div>
                    <div className="flex items-center gap-1">
                      <Briefcase className="w-4 h-4" />
                      {currentUser!.occupation}
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6">
                <p className="text-gray-700 mb-4 leading-relaxed">{currentUser!.bio}</p>
                <div className="flex flex-wrap gap-2">
                  {currentUser!.tags.map((tag, i) => (
                    <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-lg text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* AI分析报告 */}
            <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl p-6 border border-orange-100">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 bg-[#E07A5F] rounded-xl flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg">AI匹配分析报告</h3>
                  <p className="text-sm text-gray-600">综合匹配度：{currentUser!.matchScore}%</p>
                </div>
                {isVIP && (
                  <span className="ml-auto bg-[#F4A261] text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                    <Crown className="w-3 h-3" />
                    VIP
                  </span>
                )}
              </div>

              {/* 简化版分析（普通用户） */}
              {!isVIP && (
                <>
                  {/* 基础匹配原因 */}
                  <div className="bg-white rounded-lg p-4 mb-4">
                    <h4 className="text-sm mb-2">匹配原因</h4>
                    <p className="text-sm text-gray-700">{currentUser!.matchReason}</p>
                  </div>

                  {/* 显示前2个兼容性维度 */}
                  <div className="mb-4">
                    <h4 className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      兼容性分析（前2项）
                    </h4>
                    <div className="space-y-3">
                      {currentUser!.aiAnalysis.compatibility.slice(0, 2).map((item, i) => (
                        <div key={i} className="bg-white rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm">{item.label}</span>
                            <span className="text-sm text-[#E07A5F]">{item.score}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-[#E07A5F] h-2 rounded-full transition-all"
                              style={{ width: `${item.score}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 升级VIP提示 */}
                  <div className="bg-white rounded-lg p-5 border-2 border-dashed border-orange-300">
                    <div className="flex items-start gap-3 mb-3">
                      <Crown className="w-5 h-5 text-[#F4A261] flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-sm mb-1">升级VIP查看完整分析</h4>
                        <p className="text-xs text-gray-600 mb-3">
                          解锁全部4项兼容性分析、匹配亮点、注意事项和详细匹配报告
                        </p>
                        <button className="w-full bg-[#E07A5F] text-white py-2 rounded-lg text-sm hover:bg-[#D4674F] transition-colors">
                          升级VIP - 99 AED/月
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* 完整版分析（VIP用户） */}
              {isVIP && (
                <>
                  {/* 兼容性分析 */}
                  <div className="mb-6">
                    <h4 className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      多维度兼容性分析
                    </h4>
                    <div className="space-y-3">
                      {currentUser!.aiAnalysis.compatibility.map((item, i) => (
                        <div key={i} className="bg-white rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm">{item.label}</span>
                            <span className="text-sm text-[#E07A5F]">{item.score}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                            <div
                              className="bg-[#E07A5F] h-2 rounded-full transition-all"
                              style={{ width: `${item.score}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-600">{item.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 匹配亮点 */}
                  <div className="mb-6">
                    <h4 className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      匹配亮点
                    </h4>
                    <div className="space-y-2">
                      {currentUser!.aiAnalysis.highlights.map((item, i) => (
                        <div key={i} className="flex items-start gap-2 bg-white rounded-lg p-3">
                          <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-gray-700">{item}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 需要考虑的方面 */}
                  <div>
                    <h4 className="text-sm text-gray-600 mb-3">需要考虑的方面</h4>
                    <div className="space-y-2">
                      {currentUser!.aiAnalysis.considerations.map((item, i) => (
                        <div key={i} className="flex items-start gap-2 bg-white rounded-lg p-3">
                          <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <div className="w-1.5 h-1.5 bg-amber-500 rounded-full"></div>
                          </div>
                          <p className="text-sm text-gray-700">{item}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* 详细资料 */}
            <div className="bg-white rounded-xl p-6 border border-gray-200">
              <h3 className="text-lg mb-4">详细资料</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">职业</p>
                  <p className="text-gray-800">{currentUser!.occupation}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">行业</p>
                  <p className="text-gray-800">{currentUser!.industry}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">学历</p>
                  <p className="text-gray-800">{currentUser!.education}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">在UAE时长</p>
                  <p className="text-gray-800">{currentUser!.yearsInUAE}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">期望结婚时间</p>
                  <p className="text-gray-800">{currentUser!.marriageTimeline}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">长期规划</p>
                  <p className="text-gray-800">{currentUser!.longTermPlan}</p>
                </div>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-4 sticky bottom-20 bg-white/95 backdrop-blur-sm p-4 -mx-4 border-t border-gray-200">
              <button
                onClick={() => handlePass(currentUser!.id)}
                className="flex-1 py-4 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
              >
                <ThumbsDown className="w-5 h-5" />
                <span>不太合适</span>
              </button>
              <button
                onClick={() => handleLike(currentUser!)}
                className="flex-1 py-4 bg-[#E07A5F] text-white rounded-xl hover:bg-[#D4674F] transition-all flex items-center justify-center gap-2 shadow-lg"
              >
                <ThumbsUp className="w-5 h-5" />
                <span>表达好感</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}