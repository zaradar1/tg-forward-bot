# Telegram Forward & Download Bot

A Telegram bot that downloads links (Terabox, Mega, Google Drive, any direct file
URL) and moves media between channels using a Telethon userbot.

Two engines do the work:

| Engine | Talks | Upload cap | Used for |
| --- | --- | --- | --- |
| **Bot** (`BOT_TOKEN`) | Bot API | 50 MB | Chat UI, small files, relaying from the dump channel |
| **Userbot** (API ID + hash + session) | MTProto | 2 GB | Big uploads, `/forward`, `/scraper`, `/download` |

The 50 MB ceiling is Telegram's, not this project's: a bot token cannot upload
more. Everything above it goes through an account instead.

---

## 1. Quick start

1. Create a Railway project from this repository.
2. Set the **required** variables below.
3. Deploy — Railway runs `python main.py`.
4. Message the bot `/start`, then `/claim_admin` to make yourself super-admin.
5. Optional but recommended: set up the **worker account** (section 4) so every
   user gets 2 GB downloads without logging in.

### Required variables

| Variable | What it is |
| --- | --- |
| `BOT_TOKEN` | Bot API token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | Comma-separated user IDs, e.g. `123456789,987654321` |
| `FERNET_KEY` | Stable key encrypting stored credentials — see below |

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep `FERNET_KEY` stable. Change it and every stored session becomes unreadable.

### Optional variables

| Variable | Effect |
| --- | --- |
| `WORKER_API_ID`, `WORKER_API_HASH`, `WORKER_SESSION`, `DUMP_CHANNEL_ID` | Shared worker account — 2 GB downloads for everyone (section 4) |
| `API_ID`, `API_HASH` | Default app credentials offered during `/login` |
| `RAPIDAPI_KEY` | Enables one extra Terabox backend |
| `PROXY_URL`, `PREMIUM_PROXY` | Proxy for API-1 and `/apihealth` only — see note |
| `SURL_EP`, `SHARE_EP`, `DL_EP` | Override Terabox worker endpoints |

**Proxy note:** the rotating public-proxy pool is currently disabled —
`_start_proxy_manager()` is commented out in `main()`. Setting `PROXY_URL` or
`PREMIUM_PROXY` still routes API-1 and `/apihealth` through that proxy, but the
other extraction backends go out directly.

---

## 2. How a link download works

Send a link — no command needed.

```
https://terabox.com/s/1AbCd…              Terabox (≈30 domains)
https://mega.nz/file/xxxx#key             Mega file or folder
https://drive.google.com/file/d/ID/view   Google Drive
https://site.com/video.mp4                any direct file URL
```

The bot probes the URL, then routes by size:

| File size | Path |
| --- | --- |
| ≤ 50 MB | Bot uploads it straight into the chat |
| 50 MB – 2 GB | Worker uploads to the dump channel → bot copies it to the chat |
| 50 MB – 2 GB, no worker | The user's own `/login` account → their Saved Messages |
| > 2 GB | Download button only |

Copying from the dump channel has no size limit, because the file already lives
on Telegram's servers — only fresh uploads are capped at 50 MB.

During the transfer the bot edits one message every few seconds:

```
📥 Downloading…
movie.mkv
[██████░░░░░░░░░░] 38.5%
📦 268.00 MB / 696.00 MB
⚡ 14.49 MB/s  ·  ⏱ 18s  ·  ⏳ 29s left
```

Notes:

- A link that returns a **web page** is rejected — send the direct file link.
- Hosts that omit `Content-Length` still work: the download runs with a hard cap
  and falls back to the button if it exceeds the limit.
- Files served without an extension get one from `Content-Type`, so a video
  arrives as a playable video rather than a nameless document.
- Every URL is screened before it is fetched: `http`/`https` only, and the host
  must resolve to public addresses. Loopback, private ranges and the cloud
  metadata endpoint are blocked, and the check is repeated after redirects.

You can also send a `.txt` file of Terabox links for bulk processing.

---

## 3. How `/forward` works

`/forward` copies posts from one chat to another using **the user's own
account**. The bot is not involved and does not need to be in either chat.

The wizard asks five things:

1. **Source** — `@username`, invite link, chat ID, or a row number from `/channels`
2. **Destination** — same formats
3. **How many messages to scan** — a number, or `0` / `all`
4. **Resume point** — the last forwarded Msg ID, e.g. `27078`, or `0`
5. **Media types** — Photos / Videos / Audio / Documents / ALL

### Resume point

The database is wiped on every redeploy, so the saved checkpoint disappears.
The status and completion messages show a **🔖 Last msg ID** — save it, and type
it at step 4 next time to continue from exactly there.

An explicit ID also overrides the dedup history, so those messages are re-sent
even if an earlier run already forwarded them. Send `0` to use the saved
checkpoint instead, or to start from the first message when there is none.

To wipe a source's history completely: `/reset_forward @channel`, then `0`.

### Albums

Posts sharing a `grouped_id` are forwarded as one grouped album, not as separate
messages. In **ALL** mode text-only posts are carried over too, so the
destination mirrors the source post for post.

### Auto-join

If the account is not in the chat yet, it joins automatically:

| Input | Result |
| --- | --- |
| `https://t.me/joinchat/<hash>` | joins via invite |
| `https://t.me/+<hash>` | joins via invite |
| `https://t.me/name` or `@name` | joins the public chat |
| `-1002391576207` | **cannot join** — a numeric ID carries no access hash |

### Permissions

- **Source** — joining is enough, it is only read.
- **Destination group** — joining is enough.
- **Destination channel** — the **account** must be an admin there, because
  Telegram only lets admins post in a channel. This is not something the bot
  can grant; add it yourself in the channel settings. The **bot** needs nothing.

---

## 4. Worker account (2 GB for everyone)

Without it, files over 50 MB require each user to `/login`. With it, nobody
logs in and files land directly in chat.

A worker is a normal Telegram account, so it cannot post *as the bot*. It
uploads into a private dump channel and the bot copies the message out.

```
user sends link → worker downloads → worker uploads to DUMP CHANNEL
                                   → bot copies into the user's chat
```

**Setup**

1. Use a **separate number**, never your personal account — if it gets banned
   you lose that account.
2. Get its `api_id` / `api_hash` from [my.telegram.org](https://my.telegram.org).
3. Generate a string session:

   ```python
   from telethon.sync import TelegramClient
   from telethon.sessions import StringSession
   print(TelegramClient(StringSession(), api_id, api_hash).start().session.save())
   ```

4. Create a **private channel**. Add the worker account as a member and the
   **bot as an admin** — the bot must be admin *here* to copy messages out.
5. Set the four variables:

   ```
   WORKER_API_ID    = 12345678
   WORKER_API_HASH  = abc123…
   WORKER_SESSION   = 1BVtsOK…
   DUMP_CHANNEL_ID  = -1002xxxxxxxxx
   ```

6. Redeploy and run `/worker` — it reports the account and whether the dump
   channel is reachable.

**Trade-offs**

- One account is one rate-limit bucket: concurrent jobs queue behind each other.
- If it is banned, all users lose large downloads at once.
- Every downloaded file keeps a copy in the dump channel.
- It is deliberately **not** used for `/forward` / `/scraper`: those need access
  to each user's own channels, and one account joining everyone's chats would
  hit Telegram's ~500-chat limit and risk a flood ban.

---

## 5. Commands

### Everyone

| Command | Does |
| --- | --- |
| *(send a link)* | Download it — no command needed |
| `/start`, `/menu` | Dashboard with buttons |
| `/help` | Full guide with usage hints |
| `/id` | Your Telegram user ID |
| `/stats`, `/history` | Your usage and last 5 downloads |
| `/premium`, `/redeem <code>` | Plans, and activate a code |
| `/mega <link>` | Mega file or folder |

### Userbot (needs `/login`)

| Command | Does |
| --- | --- |
| `/login` | Connect an account — phone OTP, string session, or custom API |
| `/login string` / `/login force` | Session-string login / force re-login |
| `/logout` | Log out; the session stays encrypted in the vault |
| `/channels` | List your channels and groups with IDs |
| `/forward` | Copy posts between two chats |
| `/download` | Save channel media to disk |
| `/scraper` | Pull Terabox links from a chat and forward them |
| `/gdrive_leech` | Leech files to Google Drive |

**OTP warning:** send the code with a space between every digit — `1 2 3 4 5`.
Telegram expires any code that appears as plain text in a message, so `12345`
will always fail. The bot retries and requests a fresh code automatically.

### Job control

`/status` (live progress + last msg ID) · `/pause` (`ps`) · `/resume` (`rm`) ·
`/stop` (`so`) · `/cancel` (abort a wizard)

### Admin

Run `/panel` for the full list. Highlights:

| Command | Does |
| --- | --- |
| `/claim_admin` | Make yourself super-admin |
| `/pending`, `/approve <id>`, `/reject <id>` | Access requests |
| `/ban <id>`, `/unban <id>`, `/users` | User management |
| `/broadcast <text>` | Message every approved user |
| `/gencode <plan>`, `/addpremium <id> <plan>` | Premium codes (`1day`/`7day`/`15day`/`30day`) |
| `/worker` | Worker + dump-channel status |
| `/joinchat <link>` | Worker joins a chat (link or @username only) |
| `/reset_forward <channel>` | Clear a source's forward history |
| `/skipfwd <channel> <n>` | Mark the latest N posts as already sent |
| `/checkpoint` | View or set resume checkpoints |
| `/apihealth`, `/proxystatus` | Diagnostics |
| `/backup` | Back up DB and sessions to Google Drive (Colab only) |
| `/all_sessions`, `/show_account <id>`, `/user_channels <id>` | Session vault (super-admin) |
| `/db_unlock`, `/kill` | Maintenance |

---

## 6. Access and limits

New users land in a pending queue and an admin must `/approve` them.

| Tier | Extractions |
| --- | --- |
| Free | 5 per 10 minutes |
| Premium | unlimited |
| Admin | unlimited |

---

## 7. Storage and safety

State lives in `terabox_v5.db` (SQLite) plus JSON checkpoint files. **Railway
wipes these on redeploy** — attach a volume to keep them, or rely on the
`/forward` resume point to carry on manually.

Security notes:

- `/login` stores each user's API hash and session string encrypted with
  `FERNET_KEY`. That is full access to their account, so keep admin commands
  restricted and never leak the key. A worker account avoids this for plain
  downloads, since users then never hand over credentials.
- Never commit `.env`, `*.session`, the database, logs, or downloaded media.
- `MASTER_KEY` and the fallback API credentials are currently hardcoded in
  `main.py`. Move them to environment variables before making the repo public.

---

## 8. Running locally

```bash
pip install -r requirements.txt
export BOT_TOKEN=... ADMIN_IDS=... FERNET_KEY=...
python main.py
```

Python 3.10+ (the code uses `X | Y` type syntax and `list[str]` generics).
