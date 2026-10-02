export const COMETCHAT = {
  APP_ID: import.meta.env.VITE_COMETCHAT_APP_ID as string,
  REGION: import.meta.env.VITE_COMETCHAT_REGION as string,
  AUTH_KEY: import.meta.env.VITE_COMETCHAT_AUTH_KEY as string,
};
export const BRAIN_URL = (import.meta.env.VITE_BRAIN_URL as string) || "http://localhost:8787";
export const MY_UID = "atul";
