import { useState } from 'react';
import { Heart, MessageCircle, User, Compass } from 'lucide-react';
import { DailyRecommendationsPage } from './DailyRecommendationsPage';
import { MatchesPage } from './MatchesPage';
import { MessagesPage } from './MessagesPage';
import { ProfilePage } from './ProfilePage';
import { AICupidChatBubble } from './AICupidChatBubble';

interface MainAppProps {
  currentUser: any;
  onLogout: () => void;
}

export function MainApp({ currentUser, onLogout }: MainAppProps) {
  const [activeTab, setActiveTab] = useState<'recommendations' | 'matches' | 'messages' | 'profile'>('recommendations');
  const [matches, setMatches] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [dailyLikesUsed, setDailyLikesUsed] = useState(0);
  const dailyLikesLimit = 3; // 免费用户每天3个推荐
  const [isVIP, setIsVIP] = useState(false); // VIP状态，可以通过UI切换

  const handleLike = (user: any) => {
    setDailyLikesUsed(dailyLikesUsed + 1);
    
    // 模拟匹配（在真实应用中，需要检查对方是否也喜欢你）
    const isMatch = Math.random() > 0.5; // 50%概率匹配成功
    
    if (isMatch && !matches.find(m => m.id === user.id)) {
      setMatches([...matches, user]);
      // 创建新对话
      setConversations([
        ...conversations,
        {
          id: user.id,
          user: user,
          matchReason: user.matchReason || '你们的婚恋目标和生活规划高度契合',
          messages: [],
        },
      ]);
    }
  };

  const handleSendMessage = (userId: string, message: string) => {
    setConversations(
      conversations.map((conv) =>
        conv.id === userId
          ? {
              ...conv,
              messages: [
                ...conv.messages,
                {
                  id: Date.now().toString(),
                  text: message,
                  sender: currentUser.id,
                  timestamp: new Date(),
                },
              ],
            }
          : conv
      )
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-lg mx-auto flex justify-between items-center">
          <h1 className="text-xl text-gray-900">缘分相遇</h1>
          <div className="flex items-center gap-2 bg-orange-50 px-3 py-1.5 rounded-lg border border-orange-100">
            <div className="w-2 h-2 bg-[#E07A5F] rounded-full"></div>
            <span className="text-sm text-gray-700">今日: {dailyLikesUsed}/{dailyLikesLimit}</span>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <div className="flex-1 overflow-auto pb-20">
        {activeTab === 'recommendations' && (
          <DailyRecommendationsPage
            onLike={handleLike}
            dailyLikesUsed={dailyLikesUsed}
            dailyLikesLimit={dailyLikesLimit}
            isVIP={isVIP}
          />
        )}
        {activeTab === 'matches' && <MatchesPage matches={matches} />}
        {activeTab === 'messages' && (
          <MessagesPage
            conversations={conversations}
            currentUserId={currentUser.id}
            onSendMessage={handleSendMessage}
          />
        )}
        {activeTab === 'profile' && <ProfilePage user={currentUser} onLogout={onLogout} />}
      </div>

      {/* AI红娘聊天球 */}
      <AICupidChatBubble />

      {/* 底部导航栏 */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200">
        <div className="max-w-lg mx-auto flex justify-around items-center h-16">
          <button
            onClick={() => setActiveTab('recommendations')}
            className={`flex flex-col items-center justify-center w-20 h-16 transition-colors ${
              activeTab === 'recommendations' 
                ? 'text-[#E07A5F]' 
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <Compass className="w-6 h-6 mb-1" />
            <span className="text-xs">推荐</span>
          </button>
          <button
            onClick={() => setActiveTab('matches')}
            className={`flex flex-col items-center justify-center w-20 h-16 transition-colors relative ${
              activeTab === 'matches' 
                ? 'text-[#E07A5F]' 
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <Heart className="w-6 h-6 mb-1" />
            <span className="text-xs">匹配</span>
            {matches.length > 0 && (
              <span className="absolute top-2 right-3 bg-[#E07A5F] text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {matches.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('messages')}
            className={`flex flex-col items-center justify-center w-20 h-16 transition-colors relative ${
              activeTab === 'messages' 
                ? 'text-[#E07A5F]' 
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <MessageCircle className="w-6 h-6 mb-1" />
            <span className="text-xs">消息</span>
            {conversations.length > 0 && (
              <span className="absolute top-2 right-3 bg-[#E07A5F] text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {conversations.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex flex-col items-center justify-center w-20 h-16 transition-colors ${
              activeTab === 'profile' 
                ? 'text-[#E07A5F]' 
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <User className="w-6 h-6 mb-1" />
            <span className="text-xs">我的</span>
          </button>
        </div>
      </nav>
    </div>
  );
}