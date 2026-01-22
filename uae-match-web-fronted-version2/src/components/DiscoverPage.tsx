import { useState, useEffect } from 'react';
import { X, Heart, MapPin, Briefcase, GraduationCap } from 'lucide-react';

interface DiscoverPageProps {
  onMatch: (user: any) => void;
}

const MOCK_USERS = [
  {
    id: '2',
    name: '小雨',
    age: 26,
    gender: '女',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800&h=800&fit=crop',
    bio: '喜欢旅行和摄影，希望找到一个有趣的灵魂',
    location: '上海',
    occupation: '设计师',
    education: '本科',
    tags: ['旅行', '摄影', '美食'],
  },
  {
    id: '3',
    name: '思琪',
    age: 24,
    gender: '女',
    avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800&h=800&fit=crop',
    bio: '爱读书的文艺青年，喜欢一切美好的事物',
    location: '北京',
    occupation: '编辑',
    education: '硕士',
    tags: ['读书', '电影', '咖啡'],
  },
  {
    id: '4',
    name: '欣怡',
    age: 27,
    gender: '女',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&h=800&fit=crop',
    bio: '热爱运动和健康生活，寻找志同道合的伙伴',
    location: '深圳',
    occupation: '健身教练',
    education: '本科',
    tags: ['健身', '瑜伽', '烹饪'],
  },
  {
    id: '5',
    name: '梦瑶',
    age: 25,
    gender: '女',
    avatar: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&h=800&fit=crop',
    bio: '音乐是我的生活，希望遇到懂我的人',
    location: '杭州',
    occupation: '音乐老师',
    education: '本科',
    tags: ['音乐', '钢琴', '猫咪'],
  },
  {
    id: '6',
    name: '晓彤',
    age: 28,
    gender: '女',
    avatar: 'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800&h=800&fit=crop',
    bio: '工作之余喜欢画画，期待遇到温暖的你',
    location: '成都',
    occupation: '插画师',
    education: '本科',
    tags: ['绘画', '动漫', '甜品'],
  },
];

export function DiscoverPage({ onMatch }: DiscoverPageProps) {
  const [users, setUsers] = useState(MOCK_USERS);
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentUser = users[currentIndex];

  const handlePass = () => {
    if (currentIndex < users.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCurrentIndex(0);
    }
  };

  const handleLike = () => {
    onMatch(currentUser);
    if (currentIndex < users.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCurrentIndex(0);
    }
  };

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">暂无更多用户</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-lg mx-auto pt-4">
        <h1 className="text-2xl mb-6 text-center">发现</h1>

        {/* 用户卡片 */}
        <div className="bg-white rounded-3xl shadow-xl overflow-hidden mb-6">
          <div className="relative">
            <img
              src={currentUser.avatar}
              alt={currentUser.name}
              className="w-full h-96 object-cover"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-6 text-white">
              <h2 className="text-3xl mb-1">
                {currentUser.name}, {currentUser.age}
              </h2>
              <div className="flex items-center gap-2 text-sm mb-2">
                <MapPin className="w-4 h-4" />
                <span>{currentUser.location}</span>
              </div>
            </div>
          </div>

          <div className="p-6">
            <p className="text-gray-700 mb-4">{currentUser.bio}</p>

            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-3 text-gray-600">
                <Briefcase className="w-5 h-5" />
                <span>{currentUser.occupation}</span>
              </div>
              <div className="flex items-center gap-3 text-gray-600">
                <GraduationCap className="w-5 h-5" />
                <span>{currentUser.education}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {currentUser.tags.map((tag, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-pink-100 text-pink-600 rounded-full text-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex justify-center items-center gap-6">
          <button
            onClick={handlePass}
            className="w-16 h-16 rounded-full bg-white shadow-lg flex items-center justify-center border-2 border-gray-200 hover:border-gray-300 transition-all"
          >
            <X className="w-8 h-8 text-gray-400" />
          </button>
          <button
            onClick={handleLike}
            className="w-20 h-20 rounded-full bg-gradient-to-r from-pink-500 to-purple-500 shadow-lg flex items-center justify-center hover:from-pink-600 hover:to-purple-600 transition-all"
          >
            <Heart className="w-10 h-10 text-white" fill="white" />
          </button>
        </div>

        <p className="text-center text-gray-400 text-sm mt-6">
          {currentIndex + 1} / {users.length}
        </p>
      </div>
    </div>
  );
}
