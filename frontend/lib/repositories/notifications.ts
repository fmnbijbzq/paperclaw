import { demoNotificationsDataSource, type NotificationsDataSource } from "../data-sources/demo/notifications.ts";
import type { NotificationItem } from "../types.ts";

export interface NotificationsRepository {
  listFeed(): Promise<NotificationItem[]>;
  listByPaperId(paperId: number): Promise<NotificationItem[]>;
}

function compareDesc(left: string, right: string): number {
  return new Date(right).getTime() - new Date(left).getTime();
}

export function createNotificationsRepository(dataSource: NotificationsDataSource): NotificationsRepository {
  async function listSortedNotifications(): Promise<NotificationItem[]> {
    return [...(await dataSource.listNotifications())].sort((left, right) => compareDesc(left.sentAt, right.sentAt));
  }

  return {
    async listFeed() {
      return listSortedNotifications();
    },
    async listByPaperId(paperId: number) {
      return (await listSortedNotifications()).filter((notification) => notification.paperId === paperId);
    },
  };
}

export const notificationsRepository = createNotificationsRepository(demoNotificationsDataSource);
