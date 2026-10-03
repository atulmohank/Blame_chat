// Each repo file is a group member. Its UID is the file name with dots as underscores
// (auth.py -> auth_py, see brain/members.py). The hue slot gives every file its own gutter colour.
import { MY_UID } from "./config";

const KNOWN_SLOTS: Record<string, number> = { auth_py: 0, db_py: 1, utils_py: 2, cart_py: 3, api_py: 4 };
const SLOT_COUNT = 5;

export type FileIdentity = { name: string; stem: string; ext: string; monogram: string; slot: number };

export function fileIdentity(uid: string, name: string): FileIdentity | undefined {
  if (!uid || uid === MY_UID) return undefined;
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return undefined;
  const stem = name.slice(0, dot);
  const ext = name.slice(dot + 1);
  // Unknown files (other repos) still get a stable colour.
  const slot = KNOWN_SLOTS[uid] ?? [...uid].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7) % SLOT_COUNT;
  return { name, stem, ext, monogram: stem.slice(0, 2), slot };
}
