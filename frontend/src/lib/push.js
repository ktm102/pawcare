import api from "@/lib/api";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}

export function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js");
  } catch (e) {
    console.error("SW registration failed", e);
    return null;
  }
}

export async function getSubscriptionStatus() {
  if (!pushSupported()) return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  return !!sub;
}

export async function subscribeToPush() {
  if (!pushSupported()) throw new Error("Notifiche non supportate su questo dispositivo/browser.");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Permesso notifiche negato.");

  const reg = await navigator.serviceWorker.ready;
  const { data } = await api.get("/push/vapid-public-key");
  const applicationServerKey = urlBase64ToUint8Array(data.public_key);

  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey });
  }
  await api.post("/push/subscribe", { subscription: sub.toJSON() });
  return true;
}

export async function unsubscribeFromPush() {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (sub) {
    await api.post("/push/unsubscribe", { subscription: sub.toJSON() });
    await sub.unsubscribe();
  }
  return true;
}

export async function checkReminders() {
  try {
    await api.post("/push/check-reminders");
  } catch (e) {}
}
