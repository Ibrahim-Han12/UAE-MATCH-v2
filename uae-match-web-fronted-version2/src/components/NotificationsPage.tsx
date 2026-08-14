/**
 * 通知中心（站内信必达底座的用户端，HLD §8）。
 */
import { useEffect, useState } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import { notificationApi } from '../lib/api';
import { t } from '../i18n';

export function NotificationsPage({ onUnreadChange }: { onUnreadChange?: (n: number) => void }) {
  const [items, setItems] = useState<any[]>([]);
  const [unread, setUnread] = useState(0);

  const load = async () => {
    try {
      const r = await notificationApi.list();
      setItems(r.items);
      setUnread(r.unread_count);
      onUnreadChange?.(r.unread_count);
    } catch { /* 静默 */ }
  };
  useEffect(() => { void load(); }, []);

  const markAll = async () => {
    await notificationApi.markAllRead();
    await load();
  };

  const open = async (n: any) => {
    if (!n.is_read) {
      await notificationApi.markRead(n.id);
      await load();
    }
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg">{t('notifications.title')}</h2>
        {unread > 0 && (
          <button onClick={markAll} className="flex items-center gap-1 text-xs text-gray-400 hover:text-[#E07A5F]">
            <CheckCheck className="w-3.5 h-3.5" /> {t('notifications.markAll')}
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <div className="text-center py-16">
          <Bell className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">{t('notifications.empty')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <button key={n.id} onClick={() => open(n)}
                    className={`w-full text-left rounded-2xl p-4 transition-colors ${n.is_read ? 'bg-white' : 'bg-orange-50'}`}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-sm text-gray-800">{n.title}</span>
                {!n.is_read && <span className="w-2 h-2 bg-[#E07A5F] rounded-full shrink-0" />}
              </div>
              {n.body && <p className="text-xs text-gray-500">{n.body}</p>}
              <p className="text-xs text-gray-300 mt-1">{new Date(n.created_at).toLocaleString()}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
