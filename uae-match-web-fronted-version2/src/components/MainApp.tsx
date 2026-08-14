/**
 * 主应用容器（S4/S5）。信息架构对齐 PRD 2.1：推荐 / 消息 / 通知 / 我的 + 悬浮小缘。
 * v1.0 演示态已拆除：滑动推荐页、每日点赞计数、isVIP 前端开关均已移除。
 */
import { useEffect, useState } from 'react';
import { Mail, MessageCircle, Bell, User } from 'lucide-react';
import { RecommendationLettersPage } from './RecommendationLettersPage';
import { NotificationsPage } from './NotificationsPage';
import { MessagesPage } from './MessagesPage';
import { ProfilePage } from './ProfilePage';
import { AICupidChatBubble } from './AICupidChatBubble';
import { chatApi, notificationApi, birthYearToAge } from '../lib/api';
import { t } from '../i18n';

interface MainAppProps {
  currentUser: any;
  onLogout: () => void;
}

type Tab = 'letters' | 'messages' | 'notifications' | 'profile';

export function MainApp({ currentUser, onLogout }: MainAppProps) {
  const [activeTab, setActiveTab] = useState<Tab>('letters');
  const [conversations, setConversations] = useState<any[]>([]);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    notificationApi.unreadCount().then((r) => setUnread(r.unread_count)).catch(() => undefined);
  }, [activeTab]);

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await chatApi.getConversations();
        setConversations(data.map((conv: any) => ({
          id: conv.match_pair_id?.toString() || Date.now().toString(),
          matchPairId: conv.match_pair_id,
          user: {
            id: conv.other_user_id?.toString() || '',
            name: conv.other_nickname || conv.other_profile?.display_name || '用户',
            age: birthYearToAge(conv.other_profile?.birth_year) || null,
            avatar: conv.other_profile?.avatar_url || '',
            occupation: conv.other_profile?.occupation || '',
            verified: true,
          },
          matchReason: '',
          lastMessage: conv.last_message_preview || '',
          unreadCount: conv.unread_count || 0,
          messages: [],
        })));
      } catch { /* 静默 */ }
    };
    if (activeTab === 'messages') void loadConversations();
  }, [activeTab, currentUser]);

  const handleSendMessage = async (userId: string, message: string) => {
    const conversation = conversations.find((c) => c.id === userId);
    if (!conversation?.matchPairId) return;
    try {
      await chatApi.sendMessage(conversation.matchPairId, message);
      setConversations(conversations.map((conv) =>
        conv.id === userId
          ? { ...conv, messages: [...conv.messages, {
              id: Date.now().toString(), text: message,
              sender: currentUser.id.toString(), timestamp: new Date() }] }
          : conv
      ));
    } catch (e: any) {
      alert(e.message || t('common.networkError'));
    }
  };

  const TabButton = ({ tab, icon: Icon, label, badge }: { tab: Tab; icon: any; label: string; badge?: number }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`flex flex-col items-center justify-center w-20 h-16 transition-colors relative ${
        activeTab === tab ? 'text-[#E07A5F]' : 'text-gray-400 hover:text-gray-600'}`}>
      <Icon className="w-6 h-6 mb-1" />
      <span className="text-xs">{label}</span>
      {badge ? (
        <span className="absolute top-2 right-3 bg-[#E07A5F] text-white text-xs rounded-full min-w-5 h-5 px-1 flex items-center justify-center">
          {badge > 99 ? '99+' : badge}
        </span>
      ) : null}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-lg mx-auto">
          <h1 className="text-xl text-gray-900">{t('common.appName')}</h1>
        </div>
      </header>

      <div className="flex-1 overflow-auto pb-20">
        {activeTab === 'letters' && <RecommendationLettersPage />}
        {activeTab === 'messages' && (
          <MessagesPage
            conversations={conversations}
            currentUserId={currentUser.id}
            onSendMessage={handleSendMessage}
          />
        )}
        {activeTab === 'notifications' && <NotificationsPage onUnreadChange={setUnread} />}
        {activeTab === 'profile' && <ProfilePage user={currentUser} onLogout={onLogout} />}
      </div>

      <AICupidChatBubble />

      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200">
        <div className="max-w-lg mx-auto flex justify-around items-center h-16">
          <TabButton tab="letters" icon={Mail} label={t('letters.tabName')} />
          <TabButton tab="messages" icon={MessageCircle} label="消息" />
          <TabButton tab="notifications" icon={Bell} label={t('notifications.tabName')} badge={unread} />
          <TabButton tab="profile" icon={User} label="我的" />
        </div>
      </nav>
    </div>
  );
}
