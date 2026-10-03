import ReactDOM from "react-dom/client";
import { CometChatUIKit, UIKitSettingsBuilder } from "@cometchat/chat-uikit-react";
import "@cometchat/chat-uikit-react/styles";
import "./index.css";
import App, { Status } from "./App";
import { COMETCHAT, MY_UID } from "./config";

const settings = new UIKitSettingsBuilder()
  .setAppId(COMETCHAT.APP_ID)
  .setRegion(COMETCHAT.REGION)
  .setAuthKey(COMETCHAT.AUTH_KEY)
  .subscribePresenceForAllUsers()
  .build();

const root = ReactDOM.createRoot(document.getElementById("root")!);

CometChatUIKit.init(settings)
  .then(async () => {
    const existing = await CometChatUIKit.getLoggedInUser();
    if (!existing || existing.getUid() !== MY_UID) {
      if (existing) await CometChatUIKit.logout();
      await CometChatUIKit.login(MY_UID);
    }
    root.render(<App />);
  })
  .catch((err) => {
    console.error("CometChat init/login failed", err);
    const detail = `${String(err?.message ?? err)}\nCheck VITE_COMETCHAT_* in web/.env and that setup_cometchat.py created the users.`;
    root.render(<Status title="BlameChat couldn't sign in to CometChat" detail={detail} />);
  });
