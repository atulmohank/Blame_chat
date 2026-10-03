import { CometChatTextPlugin, type CometChatMessagePlugin } from "@cometchat/chat-uikit-react";
import { fileIdentity, type FileIdentity } from "./files";
import { confessionOf } from "./confession";
import { FileBadge, MessageTime, Receipt } from "./BubbleParts";

// The stock text plugin still renders every bubble (markdown, mentions, links). This one only
// swaps the robot avatar for a file badge, sets the sender name in mono, shows a quiet hh:mm:ss
// timestamp instead of time + receipts, and frames the confession with its evidence.

function senderFile(message: CometChat.BaseMessage): FileIdentity | undefined {
  const sender = message.getSender();
  return sender ? fileIdentity(sender.getUid(), sender.getName()) : undefined;
}

export const BlameTextPlugin: CometChatMessagePlugin = {
  ...CometChatTextPlugin,
  id: "blamechat-text",

  renderBubble(message, context) {
    const confession = senderFile(message) ? confessionOf(message as CometChat.TextMessage) : undefined;
    if (!confession) return CometChatTextPlugin.renderBubble(message, context);
    // Never fold the confession behind "Read more": it carries the commit.
    const bubble = CometChatTextPlugin.renderBubble(message, { ...context, disableTruncation: true });
    return <Receipt confession={confession}>{bubble}</Receipt>;
  },

  renderLeadingView(message, context) {
    const file = senderFile(message);
    if (!file) return CometChatTextPlugin.renderLeadingView?.(message, context);
    return <FileBadge file={file} />;
  },

  renderHeaderView(message, context) {
    const file = senderFile(message);
    if (!file) return CometChatTextPlugin.renderHeaderView?.(message, context);
    return <span className="bc-sender" data-hue={file.slot}>{file.name}</span>;
  },

  // Seconds, same clock and format as the brain log ([HH:MM:SS]), so the video can line them up.
  renderStatusInfoView(message) {
    return <MessageTime sentAt={message.getSentAt()} />;
  },
};
