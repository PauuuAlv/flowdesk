export interface FlowdeskNotification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  route: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  unread_count: number;
  items: FlowdeskNotification[];
}
