import { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, X, Minus } from 'lucide-react';
import { aiChatApi } from '../lib/api';

interface Message {
  id: string;
  text: string;
  sender: 'ai' | 'user';
  timestamp: Date;
}

export function AICupidChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: window.innerHeight / 2 - 50 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [hasMoved, setHasMoved] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isAITyping, setIsAITyping] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);

  // 加载历史对话
  useEffect(() => {
    const loadHistory = async () => {
      if (isOpen && messages.length === 0) {
        try {
          setIsLoadingHistory(true);
          const history = await aiChatApi.getHistory('consultation', 50);
          
          if (history && history.length > 0) {
            const formattedMessages: Message[] = history.map((msg: any) => ({
              id: msg.id?.toString() || Date.now().toString(),
              text: msg.content || '',
              sender: msg.role === 'assistant' ? 'ai' : 'user',
              timestamp: new Date(msg.created_at || Date.now()),
            }));
            setMessages(formattedMessages);
          } else {
            // 没有历史对话，显示欢迎消息
            setMessages([{
              id: '1',
              text: '你好！我是你的专属AI红娘小缘 ✨\n\n有什么我可以帮你的吗？比如：\n• 分析匹配对象\n• 聊天建议\n• 约会技巧\n• 个人资料优化',
              sender: 'ai',
              timestamp: new Date()
            }]);
          }
        } catch (error: any) {
          console.error('加载历史对话失败:', error);
          // 失败时显示欢迎消息
          setMessages([{
            id: '1',
            text: '你好！我是你的专属AI红娘小缘 ✨\n\n有什么我可以帮你的吗？比如：\n• 分析匹配对象\n• 聊天建议\n• 约会技巧\n• 个人资料优化',
            sender: 'ai',
            timestamp: new Date()
          }]);
        } finally {
          setIsLoadingHistory(false);
        }
      }
    };
    
    loadHistory();
  }, [isOpen]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (isOpen) return; // 展开时不允许拖拽
    
    setIsDragging(true);
    setHasMoved(false);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    setHasMoved(true);
    const newX = e.clientX - dragOffset.x;
    const newY = e.clientY - dragOffset.y;

    // 限制在窗口范围内
    const maxX = window.innerWidth - 100;
    const maxY = window.innerHeight - 100;

    setPosition({
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY))
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    
    // 只有在没有移动的情况下才打开对话框
    if (!hasMoved) {
      setIsOpen(true);
    }
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);

      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isAITyping) return;

    const userInput = inputValue.trim();
    setInputValue('');

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      text: userInput,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsAITyping(true);

    try {
      // 调用后端 AI API
      const response = await aiChatApi.sendMessage(userInput, 'consultation');
      
      // 添加 AI 回复
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.content,
        sender: 'ai',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error: any) {
      console.error('发送消息失败:', error);
      // 显示错误消息
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        text: `抱歉，出现了错误：${error.message || '请稍后重试'}`,
        sender: 'ai',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAITyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <>
      {/* 聊天球 */}
      {!isOpen && (
        <div
          ref={bubbleRef}
          onMouseDown={handleMouseDown}
          className="fixed z-50 cursor-move"
          style={{
            left: `${position.x}px`,
            top: `${position.y}px`,
            transition: isDragging ? 'none' : 'all 0.3s'
          }}
        >
          <div className="relative group">
            {/* 呼吸光环效果 */}
            <div className="absolute inset-0 bg-gradient-to-r from-rose-400 to-orange-400 rounded-full opacity-20 group-hover:opacity-30 animate-pulse"></div>
            <div className="absolute inset-0 bg-gradient-to-r from-rose-400 to-orange-400 rounded-full blur-xl opacity-40 group-hover:opacity-60 animate-pulse"></div>
            
            {/* 主球体 */}
            <div className="relative w-16 h-16 bg-gradient-to-br from-rose-500 to-orange-500 rounded-full shadow-xl flex items-center justify-center hover:scale-110 transition-all">
              <Sparkles className="w-8 h-8 text-white animate-pulse" />
            </div>

            {/* 提示气泡 */}
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-white px-3 py-2 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              <p className="text-xs text-gray-700">点击咨询AI红娘</p>
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-2 h-2 bg-white rotate-45"></div>
            </div>
          </div>
        </div>
      )}

      {/* 展开的聊天窗口 */}
      {isOpen && (
        <div
          className="fixed z-50 bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          style={{
            left: `${Math.min(position.x, window.innerWidth - 400)}px`,
            top: `${Math.min(position.y, window.innerHeight - 600)}px`,
            width: '380px',
            height: '550px'
          }}
        >
          {/* 聊天窗口头部 */}
          <div className="bg-gradient-to-r from-rose-500 to-orange-500 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-white text-sm">AI红娘小缘</h3>
                <p className="text-white/80 text-xs">在线</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="w-7 h-7 rounded-full hover:bg-white/20 flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>

          {/* 消息区域 */}
          <div className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50">
            {isLoadingHistory ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#E07A5F] mx-auto mb-2"></div>
                  <p className="text-xs text-gray-500">加载历史对话...</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.sender === 'ai' && (
                    <div className="w-7 h-7 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full flex items-center justify-center mr-2 flex-shrink-0">
                      <Sparkles className="w-3.5 h-3.5 text-white" />
                    </div>
                  )}
                  
                  <div
                    className={`max-w-[70%] px-3 py-2 rounded-2xl whitespace-pre-wrap ${
                      message.sender === 'user'
                        ? 'bg-gradient-to-r from-rose-500 to-orange-500 text-white'
                        : 'bg-white text-gray-800'
                    }`}
                  >
                    <p className="text-xs leading-relaxed">{message.text}</p>
                  </div>
                </div>
              ))}

              {isAITyping && (
                <div className="flex justify-start">
                  <div className="w-7 h-7 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full flex items-center justify-center mr-2">
                    <Sparkles className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="bg-white px-3 py-2 rounded-2xl">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* 输入区域 */}
          <div className="border-t border-gray-200 px-3 py-3 bg-white">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入消息..."
                className="flex-1 px-3 py-2 text-sm rounded-full border border-gray-200 focus:border-rose-300 focus:outline-none focus:ring-1 focus:ring-rose-200 transition-all bg-gray-50"
                disabled={isAITyping}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isAITyping}
                className="w-9 h-9 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-full flex items-center justify-center hover:from-rose-600 hover:to-orange-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}