/**
 * API 服务层
 * 处理所有与后端的通信，包括参数转换、错误处理等
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export interface ApiError {
  status: number;
  message: string;
}

/**
 * 获取访问令牌
 */
function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

/**
 * 保存令牌
 */
export function saveTokens(tokens: { access_token: string; refresh_token: string }) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  // 触发自定义事件，通知其他组件登录状态变化
  window.dispatchEvent(new Event('auth-change'));
}

/**
 * 清除令牌
 */
export function clearTokens() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  // 触发自定义事件，通知其他组件登出状态变化
  window.dispatchEvent(new Event('auth-change'));
}

/**
 * 基础 API 请求函数
 */
async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  requireAuth: boolean = true
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  
  const headers: Record<string, string> = {};
  
  // 如果不是 FormData，设置 Content-Type
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  
  // 如果需要认证，添加 token
  if (requireAuth) {
    const token = getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  // 合并传入的 headers
  if (options.headers) {
    Object.assign(headers, options.headers);
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (!response.ok) {
      let message = response.statusText;
      try {
        const data = await response.json();
        if (data.detail) {
          message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
      } catch {
        // ignore JSON parse error
      }
      
      // 401 未授权，清除 token
      if (response.status === 401) {
        clearTokens();
      }
      
      throw { status: response.status, message } as ApiError;
    }
    
    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }
    
    return await response.json() as T;
  } catch (error: any) {
    if (error.status) {
      throw error;
    }
    // 网络错误
    throw {
      status: 0,
      message: `网络请求失败: ${error.message || '无法连接到服务器'}`
    } as ApiError;
  }
}

/**
 * 参数转换工具函数
 */

// 性别转换：中文 -> 英文
export function convertGenderToBackend(gender: string): string {
  if (gender === '男') return 'male';
  if (gender === '女') return 'female';
  return gender; // 其他情况直接返回
}

// 性别转换：英文 -> 中文
export function convertGenderFromBackend(gender: string): string {
  if (gender === 'male') return '男';
  if (gender === 'female') return '女';
  return gender;
}

// 年龄转出生年份
export function ageToBirthYear(age: string | number): number {
  const ageNum = typeof age === 'string' ? parseInt(age, 10) : age;
  if (isNaN(ageNum)) return new Date().getFullYear() - 25; // 默认25岁
  return new Date().getFullYear() - ageNum;
}

// 出生年份转年龄
export function birthYearToAge(birthYear: number | null | undefined): number | null {
  if (!birthYear) return null;
  return new Date().getFullYear() - birthYear;
}

/**
 * 用户认证 API
 */
export const authApi = {
  /**
   * 注册
   */
  async register(data: { email?: string; phone?: string; password: string }) {
    return apiFetch<{ id: number; email?: string; phone?: string; is_active: boolean }>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      false
    );
  },
  
  /**
   * 登录
   */
  async login(username: string, password: string) {
    const response = await apiFetch<{ access_token: string; refresh_token: string; token_type: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({
          username, // 可以是 email 或 phone
          password,
        }),
      },
      false
    );
    
    // 保存 token
    saveTokens({
      access_token: response.access_token,
      refresh_token: response.refresh_token,
    });
    
    return response;
  },
  
  /**
   * 登出
   */
  logout() {
    clearTokens();
  },
};

/**
 * 个人资料 API
 */
export const profileApi = {
  /**
   * 获取我的资料
   */
  async getMyProfile() {
    const profile = await apiFetch<any>('/profile/me');
    
    // 转换格式以匹配前端期望
    return {
      id: profile.id,
      name: profile.display_name,
      age: birthYearToAge(profile.birth_year),
      gender: convertGenderFromBackend(profile.gender || ''),
      city: profile.current_city,
      occupation: profile.occupation,
      bio: profile.bio,
      avatar: profile.avatar_url || `https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&h=400&fit=crop`,
      extended_info: profile.extended_info || {},
    };
  },
  
  /**
   * 更新我的资料
   */
  async updateMyProfile(data: any) {
    // 转换前端格式到后端格式
    const backendData: any = {};
    
    if (data.name) backendData.display_name = data.name;
    if (data.age) backendData.birth_year = ageToBirthYear(data.age);
    if (data.gender) backendData.gender = convertGenderToBackend(data.gender);
    if (data.city) backendData.current_city = data.city;
    if (data.occupation) backendData.occupation = data.occupation;
    if (data.bio) backendData.bio = data.bio;
    
    // 扩展信息
    const extendedInfo: any = {};
    if (data.industry) extendedInfo.industry = data.industry;
    if (data.residencyStatus) extendedInfo.residency_status = data.residencyStatus;
    if (data.yearsInUAE) extendedInfo.years_in_uae = data.yearsInUAE;
    if (data.marriageTimeline) extendedInfo.marriage_timeline = data.marriageTimeline;
    if (data.longTermPlan) extendedInfo.long_term_plan = data.longTermPlan;
    if (data.religiousView) extendedInfo.religious_view = data.religiousView;
    if (data.childrenPlan) extendedInfo.children_plan = data.childrenPlan;
    if (data.preferredEducation) extendedInfo.preferred_education = data.preferredEducation;
    if (data.preferredCity) extendedInfo.preferred_city = data.preferredCity;
    if (data.dealbreakers) extendedInfo.dealbreakers = data.dealbreakers;
    
    if (Object.keys(extendedInfo).length > 0) {
      backendData.extended_info = extendedInfo;
    }
    
    return apiFetch<any>('/profile/me', {
      method: 'PUT',
      body: JSON.stringify(backendData),
    });
  },
};

/**
 * 匹配偏好 API
 */
export const preferencesApi = {
  /**
   * 获取我的匹配偏好
   */
  async getMyPreferences() {
    return apiFetch<any>('/preferences/me');
  },
  
  /**
   * 更新我的匹配偏好
   */
  async updateMyPreferences(data: {
    preferredAgeMin?: number;
    preferredAgeMax?: number;
    preferredGender?: string;
    preferredEducation?: string;
  }) {
    const backendData: any = {};
    
    if (data.preferredAgeMin !== undefined) backendData.min_age = data.preferredAgeMin;
    if (data.preferredAgeMax !== undefined) backendData.max_age = data.preferredAgeMax;
    if (data.preferredGender) {
      backendData.preferred_gender = convertGenderToBackend(data.preferredGender);
    }
    if (data.preferredEducation) {
      backendData.education_level = data.preferredEducation;
    }
    
    return apiFetch<any>('/preferences/me', {
      method: 'PUT',
      body: JSON.stringify(backendData),
    });
  },
};

/**
 * AI 聊天 API
 */
export const aiChatApi = {
  /**
   * 开始注册对话
   */
  async startRegistration() {
    return apiFetch<{ message: string; conversation_id: number }>(
      '/ai-chat/start-registration',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  },
  
  /**
   * 发送消息
   */
  async sendMessage(message: string, conversationType: 'registration' | 'consultation' = 'consultation') {
    return apiFetch<{ content: string; tokens_used: number; model: string; conversation_id: number }>(
      '/ai-chat/send-message',
      {
        method: 'POST',
        body: JSON.stringify({
          message,
          conversation_type: conversationType,
        }),
      }
    );
  },
  
  /**
   * 完成注册
   */
  async completeRegistration(confirm: boolean) {
    return apiFetch<{ message: string; profile_created: boolean }>(
      '/ai-chat/complete-registration',
      {
        method: 'POST',
        body: JSON.stringify({ confirm }),
      }
    );
  },
  
  /**
   * 获取对话历史
   */
  async getHistory(conversationType?: string, limit: number = 50) {
    const params = new URLSearchParams();
    if (conversationType) params.append('conversation_type', conversationType);
    params.append('limit', limit.toString());
    
    return apiFetch<any[]>(`/ai-chat/history?${params.toString()}`);
  },
};

/**
 * 匹配推荐 API
 */
export const matchesApi = {
  /**
   * 获取每日推荐
   */
  async getSuggestions() {
    const response = await apiFetch<{
      total_candidates: number;
      returned_count: number;
      items: any[];
    }>('/matches/suggestions');
    
    // 转换格式以匹配前端期望
    return response.items.map((item) => ({
      id: item.user_id.toString(),
      name: item.nickname || item.profile?.display_name || '用户',
      age: birthYearToAge(item.profile?.birth_year) || 25,
      verified: true, // TODO: 从后端获取认证状态
      avatar: item.profile?.avatar_url || `https://images.unsplash.com/photo-${1580000000000 + item.user_id}?w=400&h=400&fit=crop`,
      bio: item.bio || item.profile?.bio || '',
      location: item.city || item.profile?.current_city || 'Dubai',
      occupation: item.profile?.occupation || '',
      industry: item.profile?.extended_info?.industry || '',
      education: item.profile?.education_level || '',
      marriageTimeline: item.profile?.extended_info?.marriage_timeline || '',
      longTermPlan: item.profile?.extended_info?.long_term_plan || '',
      yearsInUAE: item.profile?.extended_info?.years_in_uae || '',
      matchScore: Math.round(item.compatibility_score * 100),
      matchReason: item.reasons?.[0] || '匹配度较高',
      reasons: item.reasons || [],
      profile: item.profile,
    }));
  },
  
  /**
   * 表达好感/跳过
   */
  async performAction(targetUserId: number, action: 'like' | 'pass' | 'super_like') {
    return apiFetch<{ is_mutual_match: boolean }>(
      '/matches/action',
      {
        method: 'POST',
        body: JSON.stringify({
          target_user_id: targetUserId,
          action_type: action,
        }),
      }
    );
  },
  
  /**
   * 获取我的匹配
   */
  async getMyMatches() {
    const matches = await apiFetch<any[]>('/matches/my-matches');
    
    return matches.map((match) => ({
      id: match.match_pair_id.toString(),
      name: match.other_nickname || match.other_user_profile?.display_name || '用户',
      age: birthYearToAge(match.other_user_profile?.birth_year) || 25,
      verified: true,
      avatar: match.other_user_profile?.avatar_url || `https://images.unsplash.com/photo-${1580000000000 + match.other_user_id}?w=400&h=400&fit=crop`,
      occupation: match.other_user_profile?.occupation || '',
      location: match.other_user_profile?.current_city || 'Dubai',
      matchScore: 85, // TODO: 从后端获取
      matchReason: '互相喜欢',
      other_user_id: match.other_user_id,
      other_user_profile: match.other_user_profile,
    }));
  },
  
  /**
   * 获取谁喜欢我
   */
  async getWhoLikedMe() {
    return apiFetch<any[]>('/matches/who-liked-me');
  },
};

/**
 * 匹配分析 API
 */
export const coachApi = {
  /**
   * 获取匹配分析报告
   */
  async getMatchInsights(targetUserId: number) {
    return apiFetch<{
      match_score: number;
      match_score_breakdown: any;
      analysis: string;
      highlights: string[];
      considerations: string[];
    }>(`/coach/match-insights?target_user_id=${targetUserId}`);
  },
};

/**
 * 消息 API
 */
export const chatApi = {
  /**
   * 获取对话列表
   */
  async getConversations() {
    return apiFetch<any[]>('/chats/my-conversations');
  },
  
  /**
   * 获取对话消息
   */
  async getMessages(matchPairId: number) {
    return apiFetch<any[]>(`/chats/${matchPairId}/messages`);
  },
  
  /**
   * 发送消息
   */
  async sendMessage(matchPairId: number, content: string) {
    return apiFetch<any>(`/chats/${matchPairId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },
};







