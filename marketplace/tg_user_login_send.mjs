import fs from 'node:fs';
import path from 'node:path';
import input from 'input';
import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions/index.js';

const SESS_DIR = '/home/safeuser/.clawdbot/secrets';
const SESS_PATH = path.join(SESS_DIR, 'telegram-user.session');

const apiId = Number(process.env.TG_API_ID || '0');
const apiHash = process.env.TG_API_HASH || '';
const target = process.env.TG_TARGET || '';
const message = process.env.TG_MESSAGE || 'Привет, это проверка связи';

if (!apiId || !apiHash) {
  console.error('Set TG_API_ID and TG_API_HASH env vars.');
  process.exit(1);
}

if (!fs.existsSync(SESS_DIR)) fs.mkdirSync(SESS_DIR, { recursive: true, mode: 0o700 });
const existing = fs.existsSync(SESS_PATH) ? fs.readFileSync(SESS_PATH, 'utf8').trim() : '';
const stringSession = new StringSession(existing);

const client = new TelegramClient(stringSession, apiId, apiHash, {
  connectionRetries: 5,
});

await client.start({
  phoneNumber: async () => input.text('Phone (+7...): '),
  password: async () => input.text('2FA password (if enabled): '),
  phoneCode: async () => input.text('Code from Telegram: '),
  onError: (err) => console.log(err),
});

const newSession = client.session.save();
fs.writeFileSync(SESS_PATH, newSession, { mode: 0o600 });

console.log('User auth OK. Session saved:', SESS_PATH);

if (target) {
  await client.sendMessage(target, { message });
  console.log('Message sent to', target);
} else {
  console.log('No TG_TARGET provided. Auth only.');
}

await client.disconnect();
