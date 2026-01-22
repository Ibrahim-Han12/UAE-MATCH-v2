import { useState, useEffect } from 'react';
import { Heart, MessageCircle, User, Compass } from 'lucide-react';
import { DailyRecommendationsPage } from './DailyRecommendationsPage';
import { MatchesPage } from './MatchesPage';
import { MessagesPage } from './MessagesPage';
import { ProfilePage } from './ProfilePage';
import { AICupidChatBubble } from './AICupidChatBubble';
import { matchesApi, chatApi, birthYearToAge } from '../lib/api';

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
  const [loadingMatches, setLoadingMatches] = useState(false);

  // 加载匹配列表
  useEffect(() => {
    const loadMatches = async () => {
      try {
        setLoadingMatches(true);
        const data = await matchesApi.getMyMatches();
        setMatches(data);
      } catch (error: any) {
        console.error('加载匹配失败:', error);
      } finally {
        setLoadingMatches(false);
      }
    };
    
    if (activeTab === 'matches') {
      loadMatches();
    }
  }, [activeTab]);

  // 加载对话列表
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await chatApi.getConversations();
        // 转换格式以匹配前端期望
        const formattedConversations = data.map((conv: any) => ({
          id: conv.match_pair_id?.toString() || Date.now().toString(),
          matchPairId: conv.match_pair_id,
          user: {
            id: conv.other_user_id?.toString() || '',
            name: conv.other_nickname || conv.other_profile?.display_name || '用户',
            age: conv.other_age || birthYearToAge(conv.other_profile?.birth_year) || 25,
            avatar: conv.other_profile?.avatar_url || `https://images.unsplash.com/photo-${1580000000000 + conv.other_user_id}?w=400&h=400&fit=crop`,
            occupation: conv.other_profile?.occupation || '',
            verified: true,
          },
          matchReason: '互相喜欢',
          lastMessage: conv.last_message_preview || '',
          unreadCount: conv.unread_count || 0,
          messages: [], // 消息在打开对话时加载
        }));
        setConversations(formattedConversations);
      } catch (error: any) {
        console.error('加载对话失败:', error);
      }
    };
    
    if (activeTab === 'messages') {
      loadConversations();
    }
  }, [activeTab, currentUser]);

  const handleLike = async (user: any) => {
    try {
      // 调用后端 API
      const response = await matchesApi.performAction(parseInt(user.id), 'like');
      
      setDailyLikesUsed(dailyLikesUsed + 1);
      
      // 如果形成互相匹配
      if (response.is_mutual_match) {
        // 添加到匹配列表
        const newMatch = {
          id: user.id,
          name: user.name,
          age: user.age,
          verified: user.verified,
          avatar: user.avatar,
          occupation: user.occupation,
          location: user.location,
          matchScore: user.matchScore,
          matchReason: user.matchReason || '你们的婚恋目标和生活规划高度契合',
        };
        
        if (!matches.find(m => m.id === user.id)) {
          setMatches([...matches, newMatch]);
        }
        
        // 创建新对话（需要从匹配列表中获取 matchPairId）
        // 这里简化处理：新匹配的对话会在下次加载对话列表时自动出现
        // 可以触发重新加载对话列表
        const loadConversations = async () => {
          try {
            const data = await matchesApi.getMyMatches();
            // 重新加载对话列表以获取新的匹配
            const convData = await chatApi.getConversations();
            const formattedConversations = convData.map((conv: any) => ({
              id: conv.match_pair_id?.toString() || Date.now().toString(),
              matchPairId: conv.match_pair_id,
              user: {
                id: conv.other_user_id?.toString() || '',
                name: conv.other_nickname || conv.other_profile?.display_name || '用户',
                age: conv.other_age || birthYearToAge(conv.other_profile?.birth_year) || 25,
                avatar: conv.other_profile?.avatar_url || `https://images.unsplash.com/photo-${1580000000000 + conv.other_user_id}?w=400&h=400&fit=crop`,
                occupation: conv.other_profile?.occupation || '',
                verified: true,
              },
              matchReason: '互相喜欢',
              lastMessage: conv.last_message_preview || '',
              unreadCount: conv.unread_count || 0,
              messages: [],
            }));
            setConversations(formattedConversations);
          } catch (error: any) {
            console.error('重新加载对话失败:', error);
          }
        };
        
        // 延迟一下再加载，确保后端已创建匹配
        setTimeout(loadConversations, 1000);
      }
    } catch (error: any) {
      console.error('表达好感失败:', error);
      alert(error.message || '操作失败，请重试');
    }
  };

  const handleSendMessage = async (userId: string, message: string) => {
    try {
      // 找到对应的对话
      const conversation = conversations.find(c => c.id === userId);
      if (!conversation || !conversation.matchPairId) {
        throw new Error('找不到对话');
      }
      
      // 调用后端 API 发送消息
      await chatApi.sendMessage(conversation.matchPairId, message);
      
      // 更新本地状态
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
                    sender: currentUser.id.toString(),
                    timestamp: new Date(),
                  },
                ],
              }
            : conv
        )
      );
    } catch (error: any) {
      console.error('发送消息失败:', error);
      alert(error.message || '发送失败，请重试');
    }
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