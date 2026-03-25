# One stable public URL (Render)

This gives you a permanent internet URL like:

- `https://ite-live-quiz.onrender.com/` (presenter)
- `https://ite-live-quiz.onrender.com/vote` (audience phones)

## 1) Put this folder on GitHub

If this folder is not already in GitHub, do:

1. Create a new empty GitHub repo (for example `ite-live-quiz`).
2. Upload/push this folder's contents.

## 2) Deploy on Render

1. Go to [https://render.com](https://render.com) and sign in with GitHub.
2. Click **New +** -> **Blueprint**.
3. Select your repo.
4. Render reads `render.yaml` automatically.
5. Click **Apply** and wait for deploy.

## 3) Use your URL

Render will show a URL:

- Presenter: `https://<your-service>.onrender.com/`
- Voting: `https://<your-service>.onrender.com/vote`

Share these anywhere. No local terminal required.

## Notes

- Free tier may sleep when idle; first load can take a short wake-up delay.
- Vote state is in server memory, so restarting the service clears active counts.
