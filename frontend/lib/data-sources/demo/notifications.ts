import { notifications } from "../../demo-data.ts";
import type { NotificationItem } from "../../types.ts";

export interface NotificationsDataSource {
  listNotifications(): Promise<NotificationItem[]>;
}

export const demoNotificationsDataSource: NotificationsDataSource = {
  async listNotifications() {
    return [...notifications];
  },
};
