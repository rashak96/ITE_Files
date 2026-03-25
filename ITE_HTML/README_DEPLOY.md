# Deploy so anyone can access (no local server)

## 1. Get Supabase credentials (free, 2 min)

1. Go to [supabase.com](https://supabase.com) - Start your project - sign in with GitHub
2. New Project - pick a name, password, region - Create
3. Settings (gear) - API - copy:
   - **Project URL** (e.g. `https://xxxx.supabase.co`)
   - **anon public** key (under Project API keys)

## 2. Generate presentations

```bash
cd "c:\Users\L\Downloads\ITE_Files"
python create_ite_html.py --supabase-url YOUR_URL --supabase-key YOUR_ANON_KEY
```

## 3. Deploy (choose one)

### Netlify Drop (simplest)
1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag the **ITE_HTML** folder onto the page
3. You get a URL like `https://random-name.netlify.app`
4. Share that URL — anyone can open it and vote from anywhere

### Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. `cd ITE_HTML` then `vercel`
3. Share the URL it gives you

### GitHub Pages
1. Create a repo, push the ITE_HTML folder contents to the root
2. Settings → Pages → Source: main branch
3. Your site: `https://yourusername.github.io/your-repo`

---

**Presenter:** Open the URL, present full-screen  
**Audience:** Same URL + `?audience` (e.g. `https://yoursite.netlify.app/Cardiology.html?audience`) — tap A–E to vote

Works from any device, any network, anywhere.
