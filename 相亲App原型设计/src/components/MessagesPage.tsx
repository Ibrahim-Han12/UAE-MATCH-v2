import { useState } from 'react';
import { MessageCircle, Send, ArrowLeft, CheckCircle, Shield } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: string;
  timestamp: Date;
}

interface Conversation {
  id: string;
  user: any;
  matchReason?: string;
  messages: Message[];
}

interface MessagesPageProps {
  conversations: Conversation[];
  currentUserId: string;
  onSendMessage: (userId: string, message: string) => void;
}

export function MessagesPage({ conversations, currentUserId, onSendMessage }: MessagesPageProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [messageText, setMessageText] = useState('');

  const handleSend = () => {
    if (messageText.trim() && selectedConversation) {
      onSendMessage(selectedConversation, messageText);
      setMessageText('');
    }
  };

  const currentConversation = conversations.find((c) => c.id === selectedConversation);

  if (selectedConversation && currentConversation) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-rose-50/30 via-orange-50/20 to-pink-50/30 flex flex-col">
        {/* 聊天头部 */}
        <div className="bg-white/90 backdrop-blur-md border-b border-rose-100 p-4 flex items-center gap-3 shadow-sm">
          <button
            onClick={() => setSelectedConversation(null)}
            className="text-gray-600 hover:text-gray-800 p-2 hover:bg-gray-100 rounded-xl transition-all"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div className="relative">
            <img
              src={currentConversation.user.avatar}
              alt={currentConversation.user.name}
              className="w-11 h-11 rounded-full object-cover shadow-md"
            />
            {currentConversation.user.verified && (
              <div className="absolute -bottom-1 -right-1 bg-white rounded-full p-0.5 shadow-sm">
                <CheckCircle className="w-4 h-4 text-rose-600" />
              </div>
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <h2 className="text-gray-800">{currentConversation.user.name}</h2>
            </div>
            <p className="text-sm text-gray-500">
              {currentConversation.user.occupation}
            </p>
          </div>
        </div>

        {/* 匹配提示 */}
        {currentConversation.matchReason && currentConversation.messages.length === 0 && (
          <div className="bg-gradient-to-r from-rose-50 to-orange-50 border-b border-rose-100 p-4">
            <div className="max-w-2xl mx-auto text-center">
              <p className="text-sm text-gray-700 leading-relaxed">
                🎉 恭喜匹配成功！{currentConversation.matchReason}
              </p>
            </div>
          </div>
        )}

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-2xl mx-auto space-y-4">
            {currentConversation.messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-20 h-20 bg-gradient-to-br from-rose-100 to-orange-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                  <MessageCircle className="w-10 h-10 text-rose-600" />
                </div>
                <h3 className="text-lg mb-3 text-gray-800">开始对话</h3>
                <p className="text-gray-500 text-sm mb-8 leading-relaxed">
                  你们已经互相喜欢，可以开始聊天了<br />
                  真诚、尊重地交流，了解彼此
                </p>
                <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-5 text-left max-w-md mx-auto shadow-lg border border-rose-100">
                  <p className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                    <span>💡</span>
                    <span>聊天小贴士</span>
                  </p>
                  <ul className="text-sm text-gray-700 space-y-2">
                    <li className="flex items-start gap-2">
                      <span className="text-rose-500 flex-shrink-0">•</span>
                      <span>从共同兴趣开始话题</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-rose-500 flex-shrink-0">•</span>
                      <span>分享在UAE的生活经历</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-rose-500 flex-shrink-0">•</span>
                      <span>诚实表达自己的想法</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-rose-500 flex-shrink-0">•</span>
                      <span>尊重对方的隐私边界</span>
                    </li>
                  </ul>
                </div>
              </div>
            ) : (
              currentConversation.messages.map((message) => {
                const isCurrentUser = message.sender === currentUserId;
                return (
                  <div
                    key={message.id}
                    className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xs px-5 py-3 rounded-3xl shadow-md ${
                        isCurrentUser
                          ? 'bg-gradient-to-r from-rose-500 to-orange-500 text-white'
                          : 'bg-white text-gray-800 border border-rose-100'
                      }`}
                    >
                      <p className="leading-relaxed">{message.text}</p>
                      <p
                        className={`text-xs mt-2 ${
                          isCurrentUser ? 'text-rose-100' : 'text-gray-400'
                        }`}
                      >
                        {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 输入框 */}
        <div className="bg-white/90 backdrop-blur-md border-t border-rose-100 p-4 shadow-lg">
          <div className="max-w-2xl mx-auto flex gap-3">
            <input
              type="text"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入消息..."
              className="flex-1 px-5 py-3 rounded-2xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 bg-white transition-all"
            />
            <button
              onClick={handleSend}
              disabled={!messageText.trim()}
              className="bg-gradient-to-r from-rose-500 to-orange-500 text-white p-3.5 rounded-2xl hover:from-rose-600 hover:to-orange-600 transition-all disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed shadow-md hover:shadow-lg disabled:shadow-none"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-2xl mx-auto pt-4">
        <h1 className="text-2xl mb-6 text-gray-800">消息</h1>

        {conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-24 h-24 bg-gradient-to-br from-rose-100 to-orange-100 rounded-full flex items-center justify-center mb-6 shadow-lg">
              <MessageCircle className="w-12 h-12 text-rose-500" />
            </div>
            <h2 className="text-xl mb-3 text-gray-800">还没有对话</h2>
            <p className="text-gray-500 text-center leading-relaxed">
              匹配成功后就可以开始聊天了
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {conversations.map((conversation) => {
              const lastMessage = conversation.messages[conversation.messages.length - 1];
              const hasUnread = conversation.messages.length > 0;

              return (
                <button
                  key={conversation.id}
                  onClick={() => setSelectedConversation(conversation.id)}
                  className="w-full bg-white/95 backdrop-blur-sm rounded-3xl p-5 flex items-center gap-4 hover:shadow-xl transition-all text-left border border-rose-100 hover:border-rose-200"
                >
                  <div className="relative flex-shrink-0">
                    <img
                      src={conversation.user.avatar}
                      alt={conversation.user.name}
                      className="w-16 h-16 rounded-full object-cover shadow-md"
                    />
                    {conversation.user.verified && (
                      <div className="absolute -bottom-1 -right-1 bg-white rounded-full p-0.5 shadow-sm">
                        <CheckCircle className="w-4 h-4 text-rose-600" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-gray-800">{conversation.user.name}</h3>
                      {conversation.messages.length === 0 && (
                        <span className="text-xs bg-gradient-to-r from-rose-500 to-orange-500 text-white px-2.5 py-1 rounded-full shadow-sm">
                          新匹配
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 truncate">
                      {lastMessage ? lastMessage.text : '开始聊天吧'}
                    </p>
                  </div>
                  {hasUnread && conversation.messages.length > 0 && (
                    <div className="bg-gradient-to-r from-rose-500 to-orange-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 shadow-md">
                      {conversation.messages.length}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* 安全提示 */}
        {conversations.length > 0 && (
          <div className="mt-6 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-5">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm mb-2 text-amber-900">安全提示</h3>
                <ul className="text-xs text-amber-800 space-y-1.5">
                  <li>• 不要透露过多个人隐私信息</li>
                  <li>• 首次见面选择公共场所</li>
                  <li>• 如遇不当行为，请及时举报</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
