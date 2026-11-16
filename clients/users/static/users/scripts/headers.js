import { postData } from "./main.js";

const accountID = document.getElementById("account-id");
const renameAccount = document.querySelectorAll(".rename-account");
const unreadContainer = document.querySelector(".unread-notifications > span");
const unreadNotifications = document.querySelector(".unread-notifications");
const notificationCount = document.querySelector(".notification-count");

renameAccount.forEach(input => {
  input.addEventListener("change", async () => {
    const form = new FormData();
    form.append("id", accountID?.textContent.trim() || "");
    form.append("name", input.value.trim());
    const result = await postData("/accounts/rename-account/", form);
    if (result?.status !== "success") {
      window.alert(result?.message || "The account name could not be updated.");
    }
  });
});

unreadContainer?.addEventListener("click", async event => {
  const item = event.target.closest(".unread-notification");
  if (!item) return;
  const id = item.querySelector(".unread_notification_id")?.textContent.trim();
  if (!id || item.dataset.marking === "true") return;
  item.dataset.marking = "true";
  const form = new FormData();
  form.append("id", id);
  const result = await postData("/notifications/read-notification/", form);
  if (result?.status === "success") {
    item.classList.add("is-read");
    item.remove();
    if (notificationCount) {
      const count = Math.max(0, Number(notificationCount.textContent) - 1);
      notificationCount.textContent = String(count);
      if (!count) {
        notificationCount.classList.add("d-none");
        unreadNotifications?.classList.add("d-none");
      }
    }
  } else {
    item.dataset.marking = "false";
    window.alert("Could not mark this notification as read. Please try again.");
  }
});
