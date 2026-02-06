# Discord CTF Bot

Bot Discord cho CTF: lay thong tin giai tu CTFtime, tao category/channel, va theo doi scoreboard realtime (CTFd/rCTF).

## Setup nhanh

1. Tao file `.env` tu `.env.example` va dien token.
2. Cai dependency:

```
pip install -r requirements.txt
playwright install
```

3. Chay bot:

```
python -m bot.main
```

## Lenh

- `/ctf upcoming [limit]` — danh sach CTF sap toi (embed + nut chuyen trang).
- `/ctf join <event_id>` — tao category + cac kenh theo ten giai.
- `/scoreboard <type> <url> [auth_token]` — cau hinh scoreboard.

## Luu y

- Bot chi dung embed cho moi phan hoi.
- Can quyen `manage_channels` de tao category/kenh.