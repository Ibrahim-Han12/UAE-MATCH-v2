import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, CheckCircle2, Loader2 } from 'lucide-react';

interface AIOnboardingChatProps {
  onComplete: (userData: any) => void;
}

interface Message {
  id: string;
  text: string;
  sender: 'ai' | 'user';
  timestamp: Date;
  isTyping?: boolean;
}

// 模拟AI问题序列
const AI_QUESTIONS = [
  { 
    key: 'greeting',
    text: '你好！我是你的专属AI红娘小缘 ✨\n\n很高兴认识你！为了帮你找到最合适的伴侣，我需要了解一些关于你的信息。这个过程会很轻松愉快，就像和朋友聊天一样。\n\n首先，我可以怎么称呼你呢？',
    field: 'name'
  },
  {
    key: 'age',
    text: '很高兴认识你，{name}！😊\n\n能告诉我你今年多大了吗？',
    field: 'age'
  },
  {
    key: 'gender',
    text: '了解了！那你是男生还是女生呢？（请回复"男"或"女"）',
    field: 'gender'
  },
  {
    key: 'city',
    text: '明白了！接下来想了解一下你在UAE的情况。\n\n你目前在哪个城市生活呢？（比如迪拜、阿布扎比等）',
    field: 'city'
  },
  {
    key: 'occupation',
    text: '好的！那你目前从事什么工作呢？',
    field: 'occupation'
  },
  {
    key: 'yearsInUAE',
    text: '很不错！你在UAE生活多久了？（比如"2年"、"半年"等）',
    field: 'yearsInUAE'
  },
  {
    key: 'marriageTimeline',
    text: '现在聊聊关于未来的想法吧 💭\n\n你期望多久内步入婚姻呢？\n1️⃣ 6个月内\n2️⃣ 1-2年内\n3️⃣ 2-3年内\n4️⃣ 3年以上\n\n（请回复数字或具体描述）',
    field: 'marriageTimeline'
  },
  {
    key: 'longTermPlan',
    text: '好的，那你对未来的长期规划是怎样的呢？\n1️⃣ 长期留在UAE\n2️⃣ 计划回国\n3️⃣ 去其他国家\n4️⃣ 灵活，可商量\n\n（请回复数字或具体描述）',
    field: 'longTermPlan'
  },
  {
    key: 'childrenPlan',
    text: '关于孩子，你的想法是？\n1️⃣ 想要孩子\n2️⃣ 可能要孩子\n3️⃣ 不想要孩子\n4️⃣ 已有孩子\n\n（请回复数字或具体描述）',
    field: 'childrenPlan'
  },
  {
    key: 'preferredAge',
    text: '现在聊聊你的理想伴侣吧 💕\n\n你希望对方的年龄大概在什么范围？（比如"25-30岁"）',
    field: 'preferredAge'
  },
  {
    key: 'preferences',
    text: '还有什么其他的期望或要求吗？比如学历、身高、兴趣爱好等，随便聊聊都可以～\n\n（如果没有特别要求，可以回复"没有了"或"差不多了"）',
    field: 'preferences'
  },
  {
    key: 'complete',
    text: '太好了！我已经了解了你的基本情况 ✨\n\n让我为你生成专属的个人画像...',
    field: 'complete'
  },
  {
    key: 'final',
    text: '画像生成完成！\n\n为了保障所有用户的安全和真实性，我们需要对你的信息进行审核。审核通过后，你就可以开始使用所有功能，包括查看每日推荐、与匹配对象聊天等。\n\n现在提交你的资料进行审核吧！',
    field: 'final'
  }
];

export function AIOnboardingChat({ onComplete }: AIOnboardingChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userData, setUserData] = useState<any>({});
  const [isAITyping, setIsAITyping] = useState(false);
  const [isGeneratingProfile, setIsGeneratingProfile] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // 初始化第一个AI问题
    if (messages.length === 0) {
      setTimeout(() => {
        addAIMessage(AI_QUESTIONS[0].text);
      }, 500);
    }
  }, []);

  const addAIMessage = (text: string) => {
    setIsAITyping(true);
    
    // 模拟打字效果
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          text: text.replace('{name}', userData.name || ''),
          sender: 'ai',
          timestamp: new Date()
        }
      ]);
      setIsAITyping(false);
    }, 800 + Math.random() * 400);
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);

    // 保存用户数据
    const currentQuestion = AI_QUESTIONS[currentQuestionIndex];
    const newUserData = {
      ...userData,
      [currentQuestion.field]: inputValue
    };
    setUserData(newUserData);

    setInputValue('');

    // 移动到下一个问题
    if (currentQuestionIndex < AI_QUESTIONS.length - 1) {
      setTimeout(() => {
        const nextIndex = currentQuestionIndex + 1;
        setCurrentQuestionIndex(nextIndex);
        
        if (AI_QUESTIONS[nextIndex].key === 'complete') {
          // 完成收集，生成画像
          setIsGeneratingProfile(true);
          addAIMessage(AI_QUESTIONS[nextIndex].text);
          
          setTimeout(() => {
            const profileSummary = generateProfileSummary(newUserData);
            addAIMessage(profileSummary);
            
            setTimeout(() => {
              // 继续到最后一步
              const finalIndex = nextIndex + 1;
              setCurrentQuestionIndex(finalIndex);
              addAIMessage(AI_QUESTIONS[finalIndex].text);
              
              setTimeout(() => {
                onComplete(newUserData);
              }, 3000);
            }, 2000);
          }, 2000);
        } else {
          addAIMessage(AI_QUESTIONS[nextIndex].text);
        }
      }, 600);
    }
  };

  const generateProfileSummary = (data: any) => {
    return `🎯 你的个人画像已生成！

📋 基本信息
• 姓名：${data.name}
• 年龄：${data.age}岁
• 性别：${data.gender}

🏙️ UAE情况
• 所在城市：${data.city}
• 职业：${data.occupation}
• 在UAE时长：${data.yearsInUAE}

💭 婚恋观
• 结婚时间：${data.marriageTimeline}
• 长期规划：${data.longTermPlan}
• 孩子计划：${data.childrenPlan}

💕 理想伴侣
• 年龄范围：${data.preferredAge}
• 其他期望：${data.preferences || '开放包容'}

系统将基于这些信息为你智能匹配！`;
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 flex flex-col">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-rose-100 px-4 py-4">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg text-gray-900">AI红娘小缘</h1>
            <p className="text-xs text-gray-500">帮你找到最合适的缘分</p>
          </div>
        </div>
      </header>

      {/* 进度指示器 */}
      <div className="bg-white/60 backdrop-blur-sm px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-600">信息收集进度</span>
            <span className="text-xs text-[#E07A5F]">
              {Math.min(Math.round((currentQuestionIndex / (AI_QUESTIONS.length - 1)) * 100), 100)}%
            </span>
          </div>
          <div className="h-1.5 bg-white rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-rose-400 to-orange-400 transition-all duration-500"
              style={{ width: `${Math.min((currentQuestionIndex / (AI_QUESTIONS.length - 1)) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* 聊天消息区 */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.sender === 'ai' && (
                <div className="w-8 h-8 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full flex items-center justify-center mr-2 flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}
              
              <div
                className={`max-w-[75%] px-4 py-3 rounded-2xl whitespace-pre-wrap ${
                  message.sender === 'user'
                    ? 'bg-gradient-to-r from-rose-500 to-orange-500 text-white'
                    : 'bg-white text-gray-800 shadow-sm'
                }`}
              >
                <p className="text-sm leading-relaxed">{message.text}</p>
                <p className={`text-xs mt-1 ${message.sender === 'user' ? 'text-rose-100' : 'text-gray-400'}`}>
                  {message.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}

          {isAITyping && (
            <div className="flex justify-start">
              <div className="w-8 h-8 bg-gradient-to-br from-rose-400 to-orange-400 rounded-full flex items-center justify-center mr-2">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-white px-4 py-3 rounded-2xl shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}

          {isGeneratingProfile && (
            <div className="flex justify-center py-4">
              <div className="bg-white px-6 py-3 rounded-full shadow-md flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-[#E07A5F] animate-spin" />
                <span className="text-sm text-gray-700">正在生成你的专属画像...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入框 */}
      {!isGeneratingProfile && (
        <div className="bg-white border-t border-rose-100 px-4 py-4">
          <div className="max-w-2xl mx-auto flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入你的回答..."
              className="flex-1 px-4 py-3 rounded-full border border-gray-200 focus:border-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-100 transition-all bg-gray-50"
              disabled={isAITyping}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isAITyping}
              className="w-12 h-12 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-full flex items-center justify-center hover:from-rose-600 hover:to-orange-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}