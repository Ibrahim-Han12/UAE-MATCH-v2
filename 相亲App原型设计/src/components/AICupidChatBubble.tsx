import { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, X, Minus } from 'lucide-react';

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
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: '你好！我是你的专属AI红娘小缘 ✨\n\n有什么我可以帮你的吗？比如：\n• 分析匹配对象\n• 聊天建议\n• 约会技巧\n• 个人资料优化',
      sender: 'ai',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isAITyping, setIsAITyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);

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

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsAITyping(true);

    // 模拟AI回复
    setTimeout(() => {
      const aiResponses = [
        '这是一个很好的问题！根据你的个人画像，我建议...',
        '我理解你的想法。让我为你分析一下...',
        '基于匹配算法，我认为...',
        '这位匹配对象和你的契合度很高，主要体现在...',
        '关于这个话题，你可以尝试从以下几个角度切入...'
      ];

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: aiResponses[Math.floor(Math.random() * aiResponses.length)],
        sender: 'ai',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);
      setIsAITyping(false);
    }, 1000 + Math.random() * 1000);
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