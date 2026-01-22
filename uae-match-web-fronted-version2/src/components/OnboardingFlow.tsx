import { useState } from 'react';
import { ChevronRight, ChevronLeft, Upload, CheckCircle } from 'lucide-react';

interface OnboardingFlowProps {
  onComplete: (userData: any) => void;
}

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    // Step 1: 基本信息
    name: '',
    age: '',
    gender: '男',
    phone: '',
    email: '',
    
    // Step 2: UAE情况
    city: 'Dubai',
    occupation: '',
    industry: '',
    residencyStatus: 'work_visa',
    yearsInUAE: '',
    
    // Step 3: 婚恋观
    marriageTimeline: '1-2年内',
    longTermPlan: 'stay_uae',
    religiousView: 'not_religious',
    childrenPlan: 'want_children',
    
    // Step 4: 择偶条件
    preferredAgeMin: '',
    preferredAgeMax: '',
    preferredEducation: '',
    preferredCity: 'any',
    dealbreakers: [],
    
    // Step 5: 认证资料
    idVerification: null,
  });

  const totalSteps = 5;

  const handleNext = () => {
    if (step < totalSteps) {
      setStep(step + 1);
    } else {
      onComplete(formData);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const updateFormData = (field: string, value: any) => {
    setFormData({ ...formData, [field]: value });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-orange-50 to-pink-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-gray-600">步骤 {step} / {totalSteps}</span>
            <span className="text-sm text-rose-600">{Math.round((step / totalSteps) * 100)}% 完成</span>
          </div>
          <div className="h-2.5 bg-white/80 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-rose-500 to-orange-500 transition-all duration-300 rounded-full shadow-sm"
              style={{ width: `${(step / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 border border-rose-100/50">
          {step === 1 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-rose-100 to-orange-100 rounded-xl flex items-center justify-center">
                  <span className="text-lg">👤</span>
                </div>
                <h2 className="text-2xl">基本信息</h2>
              </div>
              <p className="text-gray-600 mb-8">请填写您的真实信息，这将帮助我们为您推荐合适的对象</p>
              
              <div className="space-y-5">
                <div>
                  <label className="block text-sm mb-2 text-gray-700">姓名 *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => updateFormData('name', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="请输入您的真实姓名"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm mb-2 text-gray-700">年龄 *</label>
                    <input
                      type="number"
                      value={formData.age}
                      onChange={(e) => updateFormData('age', e.target.value)}
                      className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                      placeholder="年龄"
                    />
                  </div>
                  <div>
                    <label className="block text-sm mb-2 text-gray-700">性别 *</label>
                    <select
                      value={formData.gender}
                      onChange={(e) => updateFormData('gender', e.target.value)}
                      className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    >
                      <option value="男">男</option>
                      <option value="女">女</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">手机号 *</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => updateFormData('phone', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="+971 ..."
                  />
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">邮箱 *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => updateFormData('email', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="your@email.com"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-orange-100 to-amber-100 rounded-xl flex items-center justify-center">
                  <span className="text-lg">🏙️</span>
                </div>
                <h2 className="text-2xl">在UAE的情况</h2>
              </div>
              <p className="text-gray-600 mb-8">了解您在阿联酋的生活和工作状态</p>
              
              <div className="space-y-5">
                <div>
                  <label className="block text-sm mb-2 text-gray-700">所在城市 *</label>
                  <select
                    value={formData.city}
                    onChange={(e) => updateFormData('city', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="Dubai">迪拜 (Dubai)</option>
                    <option value="Abu Dhabi">阿布扎比 (Abu Dhabi)</option>
                    <option value="Sharjah">沙迦 (Sharjah)</option>
                    <option value="Ajman">阿治曼 (Ajman)</option>
                    <option value="Other">其他</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">职业 *</label>
                  <input
                    type="text"
                    value={formData.occupation}
                    onChange={(e) => updateFormData('occupation', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="例如：软件工程师"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">行业 *</label>
                  <input
                    type="text"
                    value={formData.industry}
                    onChange={(e) => updateFormData('industry', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="例如：互联网、金融、教育"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">居留身份 *</label>
                  <select
                    value={formData.residencyStatus}
                    onChange={(e) => updateFormData('residencyStatus', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="work_visa">工作签证</option>
                    <option value="investor_visa">投资者签证</option>
                    <option value="golden_visa">黄金签证</option>
                    <option value="student_visa">学生签证</option>
                    <option value="family_visa">家属签证</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">在UAE多久了 *</label>
                  <input
                    type="text"
                    value={formData.yearsInUAE}
                    onChange={(e) => updateFormData('yearsInUAE', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                    placeholder="例如：2年"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-pink-100 to-rose-100 rounded-xl flex items-center justify-center">
                  <span className="text-lg">💕</span>
                </div>
                <h2 className="text-2xl">婚恋观与未来规划</h2>
              </div>
              <p className="text-gray-600 mb-8">这些信息将帮助我们匹配目标一致的对象</p>
              
              <div className="space-y-5">
                <div>
                  <label className="block text-sm mb-2 text-gray-700">期望多久内结婚 *</label>
                  <select
                    value={formData.marriageTimeline}
                    onChange={(e) => updateFormData('marriageTimeline', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="6个月内">6个月内</option>
                    <option value="1-2年内">1-2年内</option>
                    <option value="2-3年内">2-3年内</option>
                    <option value="3年以上">3年以上</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">长期规划 *</label>
                  <select
                    value={formData.longTermPlan}
                    onChange={(e) => updateFormData('longTermPlan', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="stay_uae">长期留在UAE</option>
                    <option value="back_china">计划回国</option>
                    <option value="other_country">去其他国家</option>
                    <option value="flexible">灵活，可商量</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">宗教信仰 *</label>
                  <select
                    value={formData.religiousView}
                    onChange={(e) => updateFormData('religiousView', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="not_religious">无宗教信仰</option>
                    <option value="buddhist">佛教</option>
                    <option value="christian">基督教</option>
                    <option value="muslim">伊斯兰教</option>
                    <option value="other">其他</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">对孩子的计划 *</label>
                  <select
                    value={formData.childrenPlan}
                    onChange={(e) => updateFormData('childrenPlan', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="want_children">想要孩子</option>
                    <option value="maybe_children">可能要孩子</option>
                    <option value="no_children">不想要孩子</option>
                    <option value="have_children">已有孩子</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-100 to-pink-100 rounded-xl flex items-center justify-center">
                  <span className="text-lg">🎯</span>
                </div>
                <h2 className="text-2xl">择偶条件</h2>
              </div>
              <p className="text-gray-600 mb-8">描述您理想伴侣的条件</p>
              
              <div className="space-y-5">
                <div>
                  <label className="block text-sm mb-2 text-gray-700">期望年龄范围 *</label>
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="number"
                      value={formData.preferredAgeMin}
                      onChange={(e) => updateFormData('preferredAgeMin', e.target.value)}
                      className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                      placeholder="最小年龄"
                    />
                    <input
                      type="number"
                      value={formData.preferredAgeMax}
                      onChange={(e) => updateFormData('preferredAgeMax', e.target.value)}
                      className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                      placeholder="最大年龄"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">期望学历</label>
                  <select
                    value={formData.preferredEducation}
                    onChange={(e) => updateFormData('preferredEducation', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="">不限</option>
                    <option value="bachelor">本科及以上</option>
                    <option value="master">硕士及以上</option>
                    <option value="phd">博士</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">期望所在城市</label>
                  <select
                    value={formData.preferredCity}
                    onChange={(e) => updateFormData('preferredCity', e.target.value)}
                    className="w-full px-4 py-3.5 rounded-xl border border-rose-200 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-200 transition-all bg-white"
                  >
                    <option value="any">不限</option>
                    <option value="Dubai">迪拜</option>
                    <option value="Abu Dhabi">阿布扎比</option>
                    <option value="Sharjah">沙迦</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm mb-2 text-gray-700">Deal breakers（绝对不接受的）</label>
                  <div className="space-y-3 bg-rose-50/50 rounded-xl p-4">
                    {['吸烟', '宗教信仰差异大', '不想要孩子', '短期内离开UAE'].map((item) => (
                      <label key={item} className="flex items-center gap-3 cursor-pointer group">
                        <input type="checkbox" className="rounded border-rose-300 text-rose-600 focus:ring-rose-500 w-5 h-5" />
                        <span className="text-sm text-gray-700 group-hover:text-gray-900">{item}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-green-100 to-emerald-100 rounded-xl flex items-center justify-center">
                  <span className="text-lg">✓</span>
                </div>
                <h2 className="text-2xl">身份认证</h2>
              </div>
              <p className="text-gray-600 mb-8">上传您的身份证件以完成认证，我们会严格保密您的信息</p>
              
              <div className="space-y-5">
                <div className="border-2 border-dashed border-rose-300 rounded-2xl p-10 text-center hover:border-rose-400 hover:bg-rose-50/30 transition-all cursor-pointer group">
                  <div className="w-16 h-16 bg-gradient-to-br from-rose-100 to-orange-100 rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                    <Upload className="w-8 h-8 text-rose-600" />
                  </div>
                  <p className="mb-2 text-gray-800">上传EID / 护照 / 居留卡</p>
                  <p className="text-sm text-gray-500 mb-4">
                    支持 JPG, PNG 格式，文件大小不超过5MB
                  </p>
                  <button className="px-6 py-2.5 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-xl hover:from-rose-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg">
                    选择文件
                  </button>
                </div>

                <div className="bg-gradient-to-r from-rose-50 to-orange-50 border border-rose-200 rounded-2xl p-5">
                  <div className="flex gap-3">
                    <CheckCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-gray-800 leading-relaxed">
                        <strong className="text-rose-700">隐私承诺：</strong>您的身份信息仅用于审核真实性，我们采用加密存储，绝不向第三方泄露。审核通过后，其他用户仅能看到您的昵称和基本资料。
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between mt-10 pt-8 border-t border-rose-100">
            {step > 1 ? (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 px-6 py-3 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-xl transition-all"
              >
                <ChevronLeft className="w-5 h-5" />
                上一步
              </button>
            ) : (
              <div />
            )}
            
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-xl hover:from-rose-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg hover:scale-105"
            >
              {step === totalSteps ? '提交审核' : '下一步'}
              {step < totalSteps && <ChevronRight className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
