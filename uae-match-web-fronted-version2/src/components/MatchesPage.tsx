import { Heart, MessageCircle, CheckCircle, Crown, Sparkles } from 'lucide-react';

interface MatchesPageProps {
  matches: any[];
}

export function MatchesPage({ matches }: MatchesPageProps) {
  return (
    <div className="min-h-screen p-4">
      <div className="max-w-2xl mx-auto pt-4">
        <h1 className="text-2xl mb-6 text-gray-800">我的匹配</h1>

        {matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-24 h-24 bg-gradient-to-br from-rose-100 to-orange-100 rounded-full flex items-center justify-center mb-6 shadow-lg">
              <Heart className="w-12 h-12 text-rose-500" />
            </div>
            <h2 className="text-xl mb-3 text-gray-800">还没有匹配</h2>
            <p className="text-gray-500 text-center leading-relaxed">
              在每日推荐中表达喜欢，
              <br />
              对方也喜欢你时就会形成匹配
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {matches.map((match) => (
              <div
                key={match.id}
                className="bg-white/95 backdrop-blur-sm rounded-3xl overflow-hidden shadow-lg hover:shadow-xl transition-all border border-rose-100 hover:border-rose-200"
              >
                <div className="flex gap-4 p-5">
                  <div className="relative flex-shrink-0">
                    <img
                      src={match.avatar}
                      alt={match.name}
                      className="w-28 h-28 rounded-2xl object-cover shadow-md"
                    />
                    {match.verified && (
                      <div className="absolute -bottom-2 -right-2 bg-white rounded-full p-1 shadow-lg">
                        <CheckCircle className="w-5 h-5 text-rose-600" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg text-gray-800 truncate">
                        {match.name}, {match.age}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-500 mb-3">
                      {match.occupation} · {match.location}
                    </p>
                    {match.matchScore && (
                      <div className="mb-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs text-gray-600">匹配度</span>
                          <span className="text-sm bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                            {match.matchScore}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full"
                            style={{ width: `${match.matchScore}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                {match.matchReason && (
                  <div className="px-5 pb-4">
                    <div className="bg-gradient-to-r from-rose-50 to-orange-50 rounded-2xl p-4 border border-rose-100">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-4 h-4 text-rose-600" />
                        <p className="text-xs text-gray-600">匹配原因</p>
                      </div>
                      <p className="text-sm text-gray-800 leading-relaxed">{match.matchReason}</p>
                    </div>
                  </div>
                )}

                <div className="px-5 pb-5">
                  <button className="w-full bg-gradient-to-r from-rose-500 to-orange-500 text-white py-3 rounded-xl hover:from-rose-600 hover:to-orange-600 transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg">
                    <MessageCircle className="w-5 h-5" />
                    开始聊天
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* VIP 提示 */}
        {matches.length > 0 && (
          <div className="mt-6 bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 rounded-3xl p-6 border border-amber-200 shadow-lg">
            <div className="flex items-center gap-2 mb-3">
              <Crown className="w-6 h-6 text-amber-600" />
              <h3 className="text-gray-800">想知道谁喜欢你吗？</h3>
            </div>
            <p className="text-sm text-gray-600 mb-5 leading-relaxed">
              升级VIP会员，查看所有喜欢你的人，不错过任何缘分
            </p>
            <button className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 rounded-xl hover:from-amber-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg">
              升级VIP - 99 AED/月
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
