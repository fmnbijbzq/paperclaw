import type { NotificationFeedResponse } from "../../api-contracts.ts";
import { createHttpClient, type HttpDataSourceOptions } from "./shared.ts";
import type { NotificationsDataSource } from "../demo/notifications.ts";

export function createHttpNotificationsDataSource(options: HttpDataSourceOptions): NotificationsDataSource {
  const client = createHttpClient(options);

  return {
    async listNotifications() {
      const response = await client.get<NotificationFeedResponse>("notifications");

      return response.items.map((item) => item.notification);
    },
  };
}
