
Claude finished the response
You said: creaed an app read my code to see what it does changing it currently from stream lit to railway
1778864277778_image.png

import streamlit as st import os import html as html_lib for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]: if key in st.secrets: os.environ[key] = st.secrets[key] import json, io, csv, logging from datetime import datetime, date

pasted


""" auth.py — Authentication using Supabase Auth Handles: signup, login, logout, password reset, session persistence in Streamlit """ import streamlit as st from supabase import create_client, Client import os from database import get_profile, update_profile SUPABASE_URL = os.getenv

pasted


""" billing.py — Stripe integration for DrawingIQ Handles: checkout sessions, customer portal, webhook processing, plan upgrades """ import os import stripe import streamlit as st def _get_secret(key: str, default: str = "") -> str: """Get secret from Streamlit secrets or environment

pasted


""" database.py — All Supabase DB operations for DrawingIQ Tables managed here: - profiles (user metadata, plan, usage) - analyses (every drawing analysis result) - team_members (workspace membership) - workspaces (team accounts) - materials (shop material pri

pasted

creaed an app read my code to see what it does changing it currently from stream lit to railway

9:59 AM
Claude responded: Looking at your code, I can see DrawingIQ is a machine shop intelligence platform — engineering drawing analysis, quoting, FAI reports, production queue, etc.
Looking at your code, I can see DrawingIQ is a machine shop intelligence platform — engineering drawing analysis, quoting, FAI reports, production queue, etc. Currently built with Streamlit, and you're migrating to Railway.

What specifically are you working on with the Railway migration? A few common paths:

Keeping Streamlit but deploying on Railway (simplest — Railway runs Streamlit fine)
Rewriting the frontend in FastAPI + React/HTML to get away from Streamlit's limitations
Adding a proper backend API while keeping some Streamlit pages
What's your goal with the switch? That'll help me give you the most useful guidance.

You said: make more proffesional now lookk where im at rn
1778864402678_image.png
make more proffesional now lookk where im at rn

10:00 AM
Claude responded: So you're still running Streamlit on Railway (not rewriting the framework) — just need it deployed and looking more polished.
So you're still running Streamlit on Railway (not rewriting the framework) — just need it deployed and looking more polished.

The crash is likely just the missing start command. Let's fix that first, then I can help you level up the UI.

Step 1 — Fix the crash right now:

In Railway → your service → Settings → scroll to "Start Command" → enter exactly:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0
Save → Deployments tab → Restart.

Step 2 — What "more professional" do you want?

What would you like to focus on?

You said: i think it crashing cuase of stripe
i think it crashing cuase of stripe

10:01 AM
Claude responded: Good catch.
Good catch. Looking at your billing.py, the Stripe keys are being called at module import time — before Streamlit secrets are loaded. That'll crash Railway on startup.

The problem is this line at the top of billing.py:

python
PLANS = {
    "pro": {
        "stripe_price_id": _get_secret("STRIPE_PRICE_PRO", "price_REPLACE_ME_PRO"),
_get_secret is called when the module is first imported, but on Railway your secrets are env vars — if any are missing or Stripe tries to initialize before env vars are ready, it crashes.

Quick fixes:

1. Check your Railway environment variables — go to your service → Variables tab and make sure ALL of these are set:

OPENAI_API_KEY
SUPABASE_URL  
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY
STRIPE_SECRET_KEY
STRIPE_PRICE_PRO
STRIPE_PRICE_SHOP
STRIPE_WEBHOOK_SECRET
APP_URL
2. The crash is likely STRIPE_SECRET_KEY being empty — in billing.py line ~12, _get_secret runs at import time and if Stripe does anything with a bad key it'll throw.

Can you check two things for me:

Go to Railway → your service → Variables — are those env vars actually set there?
Go to Railway → Deployments → click the crashed deploy → view the logs — what's the last error message before it crashes?
The logs will tell us the exact line. What do you see?

1778864519022_image.png
10:02 AM
Claude responded: All 9 variables are set, so that's not the issue.
All 9 variables are set, so that's not the issue. The problem is your app uses st.secrets but Railway uses environment variables — and your app.py does this at the very top:

python
for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
On Railway there are no Streamlit secrets — only env vars. So st.secrets is empty, st.secrets access might throw, and Stripe/Supabase keys never get loaded properly.

You're also missing STRIPE_SECRET_KEY, STRIPE_PRICE_PRO, STRIPE_PRICE_SHOP, and STRIPE_WEBHOOK_SECRET from that sync loop.

The fix — replace that block at the top of app.py:

python
# Load secrets — works on both Streamlit Cloud (st.secrets) and Railway (env vars)
_KEYS = [
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "APP_URL", "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_PRO", "STRIPE_PRICE_SHOP", "STRIPE_WEBHOOK_SECRET"
]
for key in _KEYS:
    # If already in env (Railway), keep it. Otherwise pull from st.secrets.
    if not os.environ.get(key):
        try:
            if key in st.secrets:
                os.environ[key] = st.secrets[key]
        except Exception:
            pass  # st.secrets not available — Railway env vars already set above
This way Railway's env vars are used directly without touching st.secrets at all, and Streamlit Cloud still works via st.secrets.

Make that change, push/redeploy, and it should come up. Want me to also check if there are any other import-time crashes in your code?

You said: ok so give me new code to update dont break anything it works fine on stream lit
ok so give me new code to update dont break anything it works fine on stream lit

10:03 AM
Claude responded: Looking at your code carefully, here's the minimal safe fix — only touching the secrets loading block at the top of app.
Looking at your code carefully, here's the minimal safe fix — only touching the secrets loading block at the top of app.py, nothing else:

Find this at the very top of app.py (lines 1-10):

python
for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
Replace it with this:

python
# Works on both Streamlit Cloud (st.secrets) and Railway (os.environ)
_KEYS = [
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "APP_URL", "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_PRO", "STRIPE_PRICE_SHOP", "STRIPE_WEBHOOK_SECRET"
]
for key in _KEYS:
    if not os.environ.get(key):          # Railway already has it — skip
        try:
            if key in st.secrets:        # Streamlit Cloud — pull from secrets
                os.environ[key] = st.secrets[key]
        except Exception:
            pass                         # Neither — will fail gracefully later
That's the only change needed. Everything else stays exactly as-is.

Then in Railway → your service → Settings → Start Command, make sure this is set:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0
Push the change and redeploy. Railway will use its env vars directly, Streamlit Cloud will keep working via st.secrets exactly as before. Nothing else in your app changes.

You said: give me full code
give me full code

10:03 AM
Claude responded: Here's the complete app.
Here's the complete app.py with only that one change at the top:


Created 2 files, viewed a file, ran a command
Created 2 files, viewed a file, ran a command
Claude's response could not be fully generated
You said: why do you keep on failing u gave ,e code before
why do you keep on failing u gave ,e code before

1:04 PM
Claude responded: You're right, I'm sorry.
You're right, I'm sorry. The file is too large to create in one shot and keeps getting cut off. Let me do it differently — I'll patch just the specific lines that need changing.

Your original app.py works perfectly. You only need to replace one block at the top. Open your app.py file and find this (around lines 4-7):

python
for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
Replace it with this:

python
_KEYS = [
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "APP_URL", "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_PRO", "STRIPE_PRICE_SHOP", "STRIPE_WEBHOOK_SECRET"
]
for key in _KEYS:
    if not os.environ.get(key):
        try:
            if key in st.secrets:
                os.environ[key] = st.secrets[key]
        except Exception:
            pass
That is literally the only change. Everything else in your file stays exactly the same.

Then in Railway → your service → Settings → Start Command make sure you have:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0
Save → redeploy. That's it.

You said: what do i put for this do leave it .
what do i put for this do leave it .0.0.0

1:06 PM
Claude responded: Yes, leave it exactly as 0.
Yes, leave it exactly as 0.0.0.0. That's correct for Railway — it tells Streamlit to listen on all network interfaces so Railway can route traffic to it.

Your start command should be exactly:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0
Don't change anything. Hit save and redeploy.

1778875617368_image.png
1:06 PM
Claude responded: It's live!
It's live! 🎉

"Deployment successful" and "Online" — your app is running on Railway.

Now go to Settings → Networking → click Generate Domain to get your public URL if you haven't already, then update your APP_URL variable in Railway Variables to match that URL.

You said: i want see it first before i change domin what do i go
i want see it first before i change domin what do i go

1:07 PM
Claude responded: Go to Settings tab → scroll down to Networking → click Generate Domain — that gives you a free *.
Go to Settings tab → scroll down to Networking → click Generate Domain — that gives you a free *.up.railway.app URL to view it right now without any custom domain changes.

1778875702975_image.png
1:08 PM
Claude responded: You're in Project Settings — that's the wrong settings.
You're in Project Settings — that's the wrong settings. You need the service settings, not the project settings.

Go back and click directly on the DrawingIQ service box (the card that says "Online") → then click the Settings tab at the top of that panel → scroll down to Networking → Generate Domain.

1778875753884_image.png
1:09 PM
Claude responded: You're in your account/workspace settings — too far out.
You're in your account/workspace settings — too far out. Here's exactly how to get back:

Click the Railway logo (top left) to go to your dashboard
Click on the DrawingIQ project
Click the DrawingIQ service card (the box that says Online)
In the panel that slides open, click Settings tab
Scroll down to Networking → Generate Domain
You said: says enter port
says enter port

1:12 PM
Claude responded: Type 8501 — that's the default Streamlit port.
Type 8501 — that's the default Streamlit port.

You said: can i change url
can i change url

1:12 PM
Claude responded: Yes!
Yes! You can customize the subdomain part. It'll be:

your-custom-name.up.railway.app

Just type whatever you want in the subdomain field — like drawingiq and it'll become drawingiq.up.railway.app (if it's not already taken).

1778876020549_image.png
1:13 PM
Claude responded: Your URL is drawingiq.
Your URL is drawingiq.up.railway.app — visit it now to see your app!

Then go to Railway → Variables → update APP_URL to:

https://drawingiq.up.railway.app
That's it, you're live!

You said: can i switch it ti .
can i switch it ti .com

1:14 PM
Claude responded: Not directly through Railway — drawingiq.
Not directly through Railway — drawingiq.up.railway.app is their free subdomain. To get drawingiq.com you need to:

Buy the domain — from Namecheap, GoDaddy, Google Domains, etc. (~$10-15/year)
Add it in Railway — click + Custom Domain and type drawingiq.com
Point your DNS — Railway will show you a CNAME record to add in your domain registrar's DNS settings
But first go visit drawingiq.up.railway.app and make sure everything is working before buying a domain!

1778876071981_image.png
1:14 PM
Claude responded: The app is crashing.
The app is crashing. Go to Railway → click your DrawingIQ service → Deployments tab → View logs on the active deployment.

Copy and paste what the last few lines say and I'll fix it immediately.

You said: where
where

1:15 PM
Claude responded: Click Go to Railway button on that error page → then click the DrawingIQ service card → in the panel that opens click View logs (the button on the right side o…
Click Go to Railway button on that error page → then click the DrawingIQ service card → in the panel that opens click View logs (the button on the right side of the active green deployment).

1778876172407_image.png
1:16 PM
Claude responded: The app is running on port 8080 but you told Railway to use port 8501.
The app is running on port 8080 but you told Railway to use port 8501. That's the mismatch.

Go to Railway → your service → Settings → Networking → click the edit (pencil) icon on your domain → change the port from 8501 to 8080.

Save it and try the URL again.

1778876248747_image.png
1:17 PM
Claude responded: The fix I gave you didn't make it into your deployed code yet.
The fix I gave you didn't make it into your deployed code yet. The error is on line 6 — it's still the old code doing if key in st.secrets which crashes when there's no secrets.toml file.

Your GitHub repo still has the old app.py. You need to push the fix.

In your app.py on GitHub, find this (lines 4-7):

python
for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
Replace with:

python
_KEYS = [
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "APP_URL", "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_PRO", "STRIPE_PRICE_SHOP", "STRIPE_WEBHOOK_SECRET"
]
for key in _KEYS:
    if not os.environ.get(key):
        try:
            if key in st.secrets:
                os.environ[key] = st.secrets[key]
        except Exception:
            pass
You can do this directly on GitHub — go to your repo → click app.py → click the pencil edit icon → make the change → commit. Railway will auto-redeploy.

You said: i didnt push maybe thats why give me a puch code
i didnt push maybe thats why give me a puch code

1:18 PM
Claude responded: Run these commands in your terminal in your project folder:
Run these commands in your terminal in your project folder:

bash
git add app.py
git commit -m "Fix secrets loading for Railway"
git push
Railway will automatically redeploy once it sees the push.

You said: same error
1778876329965_image.png
same error

1:18 PM
Claude responded: Still line 6 with the old code — the fix didn't get pushed.
Still line 6 with the old code — the fix didn't get pushed. Let's check what's actually in your file right now. Run this in your terminal:

bash
head -10 app.py
Paste what it shows me — I need to see if your local file actually has the fix or not.

1778876359795_image.png
1:19 PM
Claude responded: You're on Windows PowerShell.
You're on Windows PowerShell. Run this instead:

powershell
Get-Content app.py -TotalCount 10
Paste what it shows.

1778876385486_image.png
1:19 PM
Claude responded: Your local file has the fix — but the push didn't include the full loop.
Your local file has the fix — but the push didn't include the full loop. The file got cut off at for key in _KEYS: without the rest of the block. That's why it's still crashing.

Run this in PowerShell to see more:

powershell
Get-Content app.py -TotalCount 20
1778876416107_image.png
1:20 PM
Claude responded: Your local file is perfect — the fix is correctly in there.
Your local file is perfect — the fix is correctly in there. The push already went to GitHub. Railway just needs to redeploy with the new code.

Go to Railway → your DrawingIQ service → Deployments tab → click the three dots menu on the latest deployment → click Redeploy.

You said: i have this problem tab
1778876430600_image.png
i have this problem tab

1:20 PM
Claude responded: Those are just VS Code Pylance warnings — not real errors.
Those are just VS Code Pylance warnings — not real errors. It means fitz (PyMuPDF) isn't installed in your local Python environment, but it's fine as long as it's in your requirements.txt for Railway.

Check your requirements.txt has this line:

PyMuPDF
If it does, ignore those warnings — Railway will install it fine. Now go redeploy on Railway.

You said: how do i redelpoy
how do i redelpoy

1:21 PM
Claude responded: Railway → click your DrawingIQ service → Deployments tab → find the latest deployment → click the three dots (⋮) on the right → click Redeploy.
Railway → click your DrawingIQ service → Deployments tab → find the latest deployment → click the three dots (⋮) on the right → click Redeploy.

You said: i cant log in now
1778876602830_image.png
i cant log in now

1:23 PM
Claude responded: The app is loading!
The app is loading! Great progress. The error "Name or service not known" means it can't reach Supabase — your SUPABASE_URL variable is probably missing or wrong in Railway.

Go to Railway → your service → Variables → click on SUPABASE_URL → make sure it looks exactly like:

https://xxxxxxxxxxxx.supabase.co
No trailing slash, no extra spaces. What does yours show?

You said: i put the wring thing
1778876758888_image.png
i put the wring thing

1:26 PM
Claude responded: I can see APPURL is set correctly.
I can see APP_URL is set correctly. Scroll down in the variables list — click on SUPABASE_URL to reveal and check its value. It needs to be exactly:

https://xxxxxxxxxxxx.supabase.co
Go to your Supabase dashboard → Settings → API → copy the Project URL and paste it into the SUPABASE_URL variable in Railway.

1778876800029_image.png
1:26 PM
Claude responded: That URL looks correct — https://xhjtzuhcmhhauunggfzq.
That URL looks correct — https://xhjtzuhcmhhauunggfzq.supabase.co.

The issue is it's wrapping across two lines in the display which sometimes means there's a hidden space or line break in the value. Click on it, clear it completely, and retype it as one clean line:

https://xhjtzuhcmhhauunggfzq.supabase.co
Save → Railway will redeploy automatically → try logging in again.

You said: i dont thhink thats the issue
i dont thhink thats the issue

1:27 PM
Claude responded: You're right, the URL looks fine.
You're right, the URL looks fine. The error "Name or service not known" is a DNS issue — Railway can't resolve the Supabase hostname at runtime.

Try this — go to Railway → your service → Deployments → click three dots → Redeploy to force a fresh restart. Sometimes it's just a cold start network issue that resolves itself on redeploy.

You said: nope
1778876939666_image.png
nope

1:29 PM
Claude responded: This is a Supabase network issue on Railway's side.
This is a Supabase network issue on Railway's side. Check your Supabase project isn't paused.

Go to supabase.com/dashboard → click your project → if it says "Project Paused" click Restore and wait 2 minutes, then try logging in again.

1778876974603_image.png
1:29 PM
Claude responded: I can see the problem — your Supabase URL here is:
I can see the problem — your Supabase URL here is:

https://dsrfamuyunatvjxocfei.supabase.co

But your Railway variable has:

https://xhjtzuhcmhhauunggfzq.supabase.co

They don't match — you have two different Supabase projects. Go to Railway → Variables → click SUPABASE_URL → change it to:

https://dsrfamuyunatvjxocfei.supabase.co
Then also update SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY to match this project's keys. Get them from Supabase → Settings → API.

You said: ok u changed them why is tho is stream lit it worked just fine
ok u changed them why is tho is stream lit it worked just fine

1:35 PM
Claude responded: Because on Streamlit Cloud you had a secrets.
Because on Streamlit Cloud you had a secrets.toml file with the correct keys. When you moved to Railway you copied the wrong Supabase URL into the variables — probably from an old project.

Now that you've updated all three Supabase variables to match the correct project, try logging in again at drawingiq.up.railway.app.

You said: how do i upload or do i jusr redeploy
1778877375861_image.png
how do i upload or do i jusr redeploy

1:36 PM
Claude responded: Click the purple Deploy button at the top left — it says "2 Changes" so it'll redeploy with your updated Supabase variables.
Click the purple Deploy button at the top left — it says "2 Changes" so it'll redeploy with your updated Supabase variables.

1778877417168_image.png
1:37 PM
Claude responded: Still the same error.
Still the same error. Go to Supabase → Settings → API and copy the exact values for all three and paste them here (you can blur the keys partially) so I can verify they're correct:

Project URL
anon public key
service_role key
The wrong Supabase project keys are definitely the issue.

1778877456224_image.png
1778877530123_image.png
1:38 PM
Claude responded: I can see the problem — your SUPABASEANONKEY in Railway is cut off at the beginning, it starts with pXVCJ9.
I can see the problem — your SUPABASE_ANON_KEY in Railway is cut off at the beginning, it starts with pXVCJ9... but it should start with eyJhbGci.... The full key is being split across lines and only part of it got saved.

Click on SUPABASE_ANON_KEY → clear it completely → paste the full key from Supabase in one go. Make sure it's one continuous string with no line breaks.

Do the same check for SUPABASE_SERVICE_KEY — it looks like it might also be truncated.

You said: no i was just scrolled
1778877558333_image.png
no i was just scrolled

1:39 PM
Claude responded: OK the keys look fine then — they're just wrapping for display.
OK the keys look fine then — they're just wrapping for display. The issue must be something else.

Click on SUPABASE_URL and show me what value is actually saved there now — let's confirm it matches https://dsrfamuyunatvjxocfei.supabase.co.

1778877583662_image.png
1:39 PM
Claude responded: That URL is correct.
That URL is correct. The display is just wrapping — the actual value is https://dsrfamuyunatvjxocfei.supabase.co which is right.

Did you click Deploy after making the changes? The error might still be from the old deployment. Go to Railway → Deployments tab → make sure the latest deployment shows Active and finished building, then try logging in again.

You said: yes i deployed
yes i deployed

1:40 PM
Claude responded: Check if the new deployment actually finished.
Check if the new deployment actually finished. Go to Railway → Deployments tab → what does the latest deployment show — is it Active or still Building?

You said: yes
yes

1:40 PM
Claude responded: Try logging in again at drawingiq.
Try logging in again at drawingiq.up.railway.app — hard refresh first with Ctrl+Shift+R to clear any cached version, then try signing in.

You said: im in but cant analaze
im in but cant analaze

1:41 PM
Claude responded: What error do you see when you try to analyze?
What error do you see when you try to analyze? Does it say something specific or just fail silently?

You said: a error pop up for second then dispaapres and nothing loads
a error pop up for second then dispaapres and nothing loads

1:41 PM
Claude responded: That's the OpenAI API key issue most likely.
That's the OpenAI API key issue most likely. Go to Railway → Variables → click on OPENAI_API_KEY → make sure it starts with sk- and is the full key with no spaces or line breaks.

You said: says api aunthication
says api aunthication

1:41 PM
Claude responded: That confirms it — your OPENAIAPIKEY in Railway is wrong.
That confirms it — your OPENAI_API_KEY in Railway is wrong.

Go to platform.openai.com → API Keys → copy your key → go to Railway → Variables → click the three dots on OPENAI_API_KEY → Edit → paste the full key → Deploy.

You said: do i make new one or whag
1778877775201_image.png
do i make new one or whag

1:43 PM
Claude responded: You can't see the full key once it's created — that's normal.
You can't see the full key once it's created — that's normal. You have two options:

Create a new key — click + Create new secret key, copy the full key immediately, paste it into Railway
Use the existing one — but you can never see the full key again so you'd need to create new anyway
Click + Create new secret key, name it DRAWINIQ, copy the full sk-... key, then update it in Railway Variables.

You said: i can anyazie now my plan is hardcoded set to be pro but look
1778877983943_image.png
i can anyazie now my plan is hardcoded set to be pro but look

1:46 PM
Claude responded: The issue is your email check.
The issue is your email check. In app.py the owner email is hardcoded as:

python
_owner_email = "isaiah.williams2002@outlook.com"
But you're probably logged in with a different email on this Supabase project. Check what email you signed up with on the new Supabase project and update that line in your code to match, then push and redeploy.

You said: never mind that was just a prompt
1778878009992_image.png
never mind that was just a prompt

1:46 PM
Claude responded: It's working!
It's working! 🎉 The app is fully live and analyzing drawings. You're good to go!

You said: now that im on railway what can i do that couldnt before fix everthing male it professional and smooth.
now that im on railway what can i do that couldnt before fix everthing male it professional and smooth. I need my app to be worth the price thry pay

1:47 PM
Claude responded: Let me look at your full codebase to give you a proper answer on what to prioritize.
Let me look at your full codebase to give you a proper answer on what to prioritize.

What should we tackle first?

You said: Q: What's the biggest pain point right now?
Q: What's the biggest pain point right now?
A: All of the above

Q: What do you want to focus on first?
A: [No preference]

1:48 PM
Claude responded: Here's your full priority list of everything we can improve now that you're on Railway:
Here's your full priority list of everything we can improve now that you're on Railway:

🎨 UI & Professional Polish

Replace Streamlit's default widgets with fully custom HTML/CSS components — no more "this looks like a Streamlit app"
Better landing page with real screenshots, testimonials, pricing table
Smoother loading states and animations
Mobile responsive layout
Professional email templates for quote sending
⚡ Performance

Add caching so repeat analyses don't re-call OpenAI
Faster PDF processing
Background job processing so the UI doesn't freeze during analysis
💰 Features Worth Paying For

Email quotes directly to customers from the app
Customer-facing quote approval portal (already built but needs polish)
PDF export for quotes and FAI reports (not just .txt)
Drawing history search that actually works well
Webhook to notify you when a customer approves a quote
🔧 Reliability

Error handling that doesn't crash the whole page
Better session management
What I'd do in order:

Landing page — first impression = conversions
Analysis results UI — this is what they're paying for
PDF exports — txt files feel cheap
Email quotes
Which one do you want me to build first?

You said: start doig your magic claude lets become rich
start doig your magic claude lets become rich

1:48 PM
Claude responded: Let's start with the landing page since that's what converts visitors to paying customers.
Let's start with the landing page since that's what converts visitors to paying customers. Then we'll roll through everything.

First — share your auth.py file content so I can see the current landing page code and build something that blows it out of the water.

Actually I already have it from earlier in our conversation. Let me build it.


Check skills for frontend design
Check skills for frontend design
Now let me build the new professional auth.py with a stunning landing page and a completely redesigned login experience.


Created a file, read a file
Created a file, read a file
Replace your auth.py with this. Here's what changed:

Landing page — full professional marketing page with hero, feature grid, testimonials, pricing table, and footer. Dark industrial theme using Syne + DM Sans fonts.

Login/signup — two-column layout with the pitch on the left and the form on the right. Clean inputs, smooth hover effects, trial badge.

After you replace it, push and deploy:

bash
git add auth.py
git commit -m "Professional landing page redesign"
git push
Next up I'll tackle the main app header, navigation, and analysis results to match this quality level. Want me to go ahead?


Auth
PY 
You said: next
next

1:51 PM
Claude responded: Now let me rebuild the main app's CSS and header to match the professional landing page quality.
Now let me rebuild the main app's CSS and header to match the professional landing page quality.


Check frontend design skill
Check frontend design skill
The main app CSS is the biggest visual upgrade we can make. Here's the new professional CSS block — replace the entire st.markdown("""<style>...</style>""") block at the top of your app.py with this:


New professional CSS for app.py main stylesheet
New professional CSS for app.py main stylesheet
Now here's the new header block — replace your existing st.markdown(f"""<div class="app-header">...</div>""") with this in app.py:


Created a file, read a file
Created a file, read a file
Here's exactly what to do:

1. In app.py, add this near the top (after imports, before init_session()):

python
APP_CSS = """..."""  # paste full content of app_css.py
2. Replace the old st.markdown("""<style>...""") block with:

python
st.markdown(APP_CSS, unsafe_allow_html=True)
3. Replace the old header div with the new diq-app-header version from the snippets file.

What this gives you:

Dark professional header with Syne font
Clean white content area (not that flat blue)
JetBrains Mono for all numbers/code
Smooth hover effects on every card
Custom scrollbar
Much better metric displays and tables
Buttons with hover lift effect
Want me to now tackle the PDF export for quotes (instead of .txt files) and email quotes directly to customers? Those are the two biggest "worth paying for" features.


App css
PY 

App header snippets
PY 
You said: why u telling me steps then gave me code
why u telling me steps then gave me code

1:53 PM
Claude responded: You're right, my bad.
You're right, my bad. Let me just give you the complete ready-to-use files. No steps, no instructions — just drop them in and push.

What do you want me to output next as a complete file — the full new app.py with everything updated, or tackle the PDF export and email quotes first?

You said: fix everthing in app i eplaced auth do proffesional version of app
fix everthing in app i eplaced auth do proffesional version of app

1:54 PM
Claude responded: The file is too large to output in one shot — that's been the problem.
The file is too large to output in one shot — that's been the problem. Let me do it in smart chunks. I'll output app.py in 3 parts that you paste together.

Part 1 of 3 — top of app.py (imports through navigation):


Created 3 files, read a file
Created 3 files, read a file

app.py part 1 - imports through navigation
app_part1.py

app.py part 2 - checklist, render_result, analyze page
app_part2.py

app.py part 3 - all remaining pages
app_part3.py

Presented 3 files
Done
Three files — concatenate them in order to make your new app.py:

powershell
Get-Content app_part1.py, app_part2.py, app_part3.py | Set-Content app.py
Or just open all three and paste them one after another into a single app.py file.

What's new:

Dark professional header with Syne font + JetBrains Mono for numbers
Clean white content area instead of flat blue
Every card has hover effects
All page titles use the bold Syne font
Cleaner metric strips, flag items, dimension tables
Consistent spacing throughout
Slicker quote display with dark gradient card
Then push:

powershell
git add app.py
git commit -m "Professional UI redesign"
git push

App part1
PY 

App part2
PY 

App part3
PY 

You're out of extra usage ∙ Your limit resets at 5:50 PM
Buy more



Claude is AI and can make mistakes. Please double-check responses.
App part1 · PY
Copy

import streamlit as st
import os
import html as html_lib
 
# Works on both Streamlit Cloud (st.secrets) and Railway (os.environ)
_KEYS = [
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY", "APP_URL", "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_PRO", "STRIPE_PRICE_SHOP", "STRIPE_WEBHOOK_SECRET"
]
for key in _KEYS:
    if not os.environ.get(key):
        try:
            if key in st.secrets:
                os.environ[key] = st.secrets[key]
        except Exception:
            pass
 
import json, io, csv, logging
from datetime import datetime, date, timedelta
 
_api_key = os.getenv("OPENAI_API_KEY", "")
if not _api_key:
    st.error("OpenAI API key not configured.")
    st.stop()
 
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
 
st.set_page_config(page_title="DrawingIQ", page_icon="⚙", layout="wide",
                   initial_sidebar_state="collapsed")
 
from auth import (init_session, is_logged_in, get_current_user,
                  get_current_profile, logout, render_landing_page, refresh_profile)
from database import (
    get_profile, save_analysis, get_analyses, get_analysis_by_id, increment_usage,
    delete_analysis, get_plan_limits, can_analyze,
    create_workspace, get_user_workspaces, get_workspace_members,
    invite_member, remove_member, get_usage_stats, PLAN_LIMITS, update_profile,
    save_material, get_materials, delete_material,
    get_effective_limits, is_in_trial,
    save_machine, get_machines, delete_machine,
    save_quote, get_quotes, get_quote_by_token, update_quote_status,
    save_job_actual, get_job_actuals, find_similar_parts,
    save_fai, get_fai_reports,
    save_job_to_queue, get_job_queue, update_job_status, delete_job_from_queue,
)
from billing import render_pricing_page, PLANS, enforce_free_limits
from analyzer import analyze_image, analyze_pdf_pages, estimate_quote
from pdf_utils import pdf_to_images, image_file_to_b64, get_pdf_page_count
 
init_session()
 
# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&family=JetBrains+Mono:wght@400;500&display=swap');
 
*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif;}
#MainMenu,footer,[data-testid="stToolbar"],.stDeployButton,button[title="View app in Streamlit Community Cloud"]{display:none!important;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stSidebar"]{display:none!important;}
.block-container{padding-top:0!important;max-width:100%!important;}
.main,.stApp,[data-testid="stAppViewContainer"]{background:#f8fafc!important;}
 
/* HEADER */
.diq-header{background:#080c14;padding:0 2rem;height:60px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.06);margin:-1rem -1rem 0 -1rem;}
.diq-header-left{display:flex;align-items:center;gap:12px;}
.diq-logo-box{width:34px;height:34px;background:linear-gradient(135deg,#1d4ed8,#4f46e5);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;}
.diq-app-title{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:white;letter-spacing:-0.02em;}
.diq-app-title span{color:#3b82f6;}
.diq-app-sub{font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.1em;margin-top:1px;}
.diq-plan-chip{font-size:0.62rem;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:0.06em;}
.chip-free{background:rgba(37,99,235,0.15);color:#60a5fa;border:1px solid rgba(37,99,235,0.25);}
.chip-starter{background:#bfdbfe;color:#1e40af;}
.chip-pro{background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.25);}
.chip-shop{background:rgba(139,92,246,0.15);color:#a78bfa;border:1px solid rgba(139,92,246,0.25);}
.chip-enterprise{background:rgba(139,92,246,0.15);color:#a78bfa;border:1px solid rgba(139,92,246,0.25);}
.diq-header-right{display:flex;align-items:center;gap:1rem;}
.diq-avatar{width:30px;height:30px;background:linear-gradient(135deg,#1d4ed8,#4f46e5);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.7rem;color:white;}
.diq-username{color:#64748b;font-size:0.82rem;}
 
/* USAGE */
.diq-usage-wrap{display:flex;align-items:center;gap:8px;font-size:0.78rem;color:#94a3b8;}
.diq-usage-track{width:80px;height:4px;background:#e2e8f0;border-radius:2px;overflow:hidden;}
.diq-usage-fill{height:100%;border-radius:2px;}
 
/* METRICS */
.diq-metric-strip{display:flex;gap:0.6rem;margin:1rem 0;flex-wrap:wrap;}
.diq-metric-box{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:0.75rem 1rem;flex:1;min-width:90px;transition:border-color 0.2s,box-shadow 0.2s;}
.diq-metric-box:hover{border-color:#bfdbfe;box-shadow:0 2px 8px rgba(37,99,235,0.06);}
.diq-metric-label{font-size:0.62rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.07em;font-weight:600;margin-bottom:4px;}
.diq-metric-value{font-family:'JetBrains Mono',monospace;font-size:0.9rem;font-weight:500;color:#0f172a;}
 
/* FLAGS */
.diq-flag{border-left:3px solid #2563eb;padding:0.65rem 1rem;margin:0.35rem 0;border-radius:0 8px 8px 0;font-size:0.86rem;line-height:1.5;}
.diq-flag-critical{border-left-color:#ef4444;background:#fef2f2;color:#1a0a0a;}
.diq-flag-warning{border-left-color:#f59e0b;background:#fffbeb;color:#1a1200;}
.diq-flag-info{border-left-color:#3b82f6;background:#eff6ff;color:#0c1e3d;}
.diq-flag-evidence{font-size:0.72rem;color:#9ca3af;margin-top:4px;font-family:'JetBrains Mono',monospace;background:#f9fafb;padding:2px 6px;border-radius:3px;display:inline-block;}
 
/* TABLES */
.diq-dim-table{width:100%;border-collapse:collapse;font-size:0.82rem;}
.diq-dim-table th{background:#f8fafc;text-align:left;padding:8px 12px;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.07em;color:#94a3b8;font-weight:600;border-bottom:1px solid #e2e8f0;}
.diq-dim-table td{padding:7px 12px;border-bottom:1px solid #f1f5f9;color:#374151;font-family:'JetBrains Mono',monospace;font-size:0.78rem;}
.diq-dim-table tr:hover td{background:#f8fafc;}
.diq-dim-table .critical-row td{background:#fef2f2;}
 
/* CARDS */
.diq-result-card{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;margin:0.75rem 0;}
.diq-dash-card{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;margin-bottom:1rem;}
.diq-dash-card-title{font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#94a3b8;margin-bottom:1rem;}
.diq-history-card{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:0.9rem 1.1rem;margin-bottom:0.4rem;transition:border-color 0.2s,box-shadow 0.2s;}
.diq-history-card:hover{border-color:#bfdbfe;box-shadow:0 2px 12px rgba(37,99,235,0.06);}
 
/* QUOTE */
.diq-quote-total{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid rgba(255,255,255,0.08);color:white;border-radius:12px;padding:1.5rem;text-align:center;margin:1rem 0;}
.diq-quote-price{font-family:'JetBrains Mono',monospace;font-size:3rem;font-weight:500;color:#f1f5f9;letter-spacing:-0.02em;line-height:1;}
.diq-quote-label{font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;}
.diq-quote-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:0.86rem;}
.diq-quote-row:last-child{border-bottom:none;}
.diq-quote-row-label{color:#64748b;}
.diq-quote-row-value{font-family:'JetBrains Mono',monospace;font-weight:500;color:#0f172a;}
 
/* MISC */
.diq-type-tag{display:inline-block;background:linear-gradient(135deg,#1d4ed8,#4f46e5);color:white;font-size:0.68rem;font-weight:700;padding:3px 10px;border-radius:4px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.75rem;}
.diq-checklist-item{display:flex;align-items:flex-start;gap:10px;padding:0.55rem 0;border-bottom:1px solid #f8fafc;font-size:0.86rem;color:#374151;}
.diq-checklist-item:last-child{border-bottom:none;}
.diq-drop-zone{border:2px dashed #cbd5e1;border-radius:14px;background:white;padding:2.5rem 2rem 2rem;text-align:center;margin-bottom:0.75rem;transition:border-color 0.2s,background 0.2s;}
.diq-drop-zone:hover{border-color:#93c5fd;background:#f0f9ff;}
.diq-drop-zone h3{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:0.35rem;}
.diq-drop-zone p{color:#94a3b8;font-size:0.82rem;}
.diq-empty{text-align:center;padding:3.5rem 2rem;color:#94a3b8;}
.diq-empty h3{font-family:'Syne',sans-serif;font-size:1rem;font-weight:600;color:#475569;margin-bottom:0.35rem;}
.diq-confirm-delete{background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:0.65rem 1rem;margin:0.2rem 0;font-size:0.84rem;color:#7f1d1d;}
.diq-member-row{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:0.75rem 1rem;margin:0.3rem 0;display:flex;align-items:center;gap:1rem;}
.diq-member-avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#1d4ed8,#4f46e5);color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.75rem;flex-shrink:0;}
.diq-role-badge{font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:10px;text-transform:uppercase;letter-spacing:0.06em;}
.role-owner{background:#fef3c7;color:#78350f;}.role-admin{background:#dbeafe;color:#1e40af;}.role-member{background:#eff6ff;color:#1d4ed8;}.role-viewer{background:#f3e8ff;color:#6b21a8;}
.diq-upgrade-banner{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid rgba(255,255,255,0.08);color:white;border-radius:12px;padding:1.25rem 1.5rem;margin:0.5rem 0;text-align:center;}
.diq-queue-card{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:0.9rem 1.1rem;margin-bottom:0.4rem;border-left-width:4px;}
 
/* STREAMLIT OVERRIDES */
[data-testid="stTextInput"] input{background:white!important;border:1px solid #e2e8f0!important;border-radius:8px!important;color:#0f172a!important;font-family:'DM Sans',sans-serif!important;font-size:0.88rem!important;transition:border-color 0.2s,box-shadow 0.2s!important;}
[data-testid="stTextInput"] input:focus{border-color:#93c5fd!important;box-shadow:0 0 0 3px rgba(59,130,246,0.1)!important;}
[data-testid="stTextInput"] label,[data-testid="stSelectbox"] label,[data-testid="stNumberInput"] label,[data-testid="stTextArea"] label{color:#64748b!important;font-size:0.78rem!important;font-weight:500!important;font-family:'DM Sans',sans-serif!important;}
[data-testid="stButton"] button{font-family:'DM Sans',sans-serif!important;font-weight:500!important;border-radius:8px!important;font-size:0.88rem!important;transition:all 0.2s!important;}
[data-testid="stButton"] button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8,#4f46e5)!important;border:none!important;}
[data-testid="stButton"] button[kind="primary"]:hover{transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(29,78,216,0.3)!important;}
[data-testid="stMetricValue"]{font-family:'JetBrains Mono',monospace!important;font-size:1.6rem!important;font-weight:500!important;color:#0f172a!important;}
[data-testid="stMetricLabel"]{font-size:0.72rem!important;color:#94a3b8!important;text-transform:uppercase!important;letter-spacing:0.06em!important;}
[data-testid="stExpander"]{border:1px solid #e2e8f0!important;border-radius:10px!important;background:white!important;}
[data-testid="stAlert"]{border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:0.85rem!important;}
button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8,#4f46e5)!important;border:none!important;}
::-webkit-scrollbar{width:6px;height:6px;}::-webkit-scrollbar-track{background:transparent;}::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px;}::-webkit-scrollbar-thumb:hover{background:#94a3b8;}
</style>
""", unsafe_allow_html=True)
 
if not is_logged_in():
    render_landing_page()
    st.stop()
 
user    = get_current_user()
profile = get_current_profile() or {}
if not profile:
    refresh_profile()
    profile = get_current_profile() or {}
 
plan = profile.get("plan", "free")
 
_owner_email = "isaiah.williams2002@outlook.com"
if profile.get("email", "") == _owner_email:
    plan = "pro"
    profile["plan"] = "pro"
else:
    if not st.session_state.get("_stripe_synced"):
        st.session_state["_stripe_synced"] = True
        try:
            import stripe as _stripe
            from billing import _get_secret
            _stripe.api_key = _get_secret("STRIPE_SECRET_KEY")
            if _stripe.api_key and "REPLACE" not in _stripe.api_key:
                _email = profile.get("email", "")
                _custs = _stripe.Customer.list(email=_email, limit=1)
                if _custs.data:
                    _cid  = _custs.data[0].id
                    _subs = _stripe.Subscription.list(customer=_cid, status="active", limit=1)
                    if _subs.data:
                        _sub      = _subs.data[0]
                        _price_id = _sub["items"]["data"][0]["price"]["id"]
                        _pro_p    = _get_secret("STRIPE_PRICE_PRO")
                        _shop_p   = _get_secret("STRIPE_PRICE_SHOP")
                        _new_plan = "shop" if _price_id == _shop_p else "pro" if _price_id == _pro_p else plan
                        if _new_plan != plan:
                            update_profile(user["id"], {"plan": _new_plan, "stripe_customer_id": _cid, "stripe_subscription_id": _sub.id})
                            profile["plan"] = _new_plan
                            plan = _new_plan
                            st.session_state["profile"] = profile
                    elif plan not in ("free", "trial"):
                        update_profile(user["id"], {"plan": "free"})
                        profile["plan"] = "free"
                        plan = "free"
                        st.session_state["profile"] = profile
        except Exception:
            pass
 
limits    = get_effective_limits(profile)
user_name = (user.get("full_name") or profile.get("full_name") or
             profile.get("email", "") or user.get("email", "")).strip() or "User"
user_initials = "".join([p[0].upper() for p in user_name.split()[:2]])
 
# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="diq-header">
  <div class="diq-header-left">
    <div class="diq-logo-box">⚙</div>
    <div>
      <div class="diq-app-title">Drawing<span>IQ</span></div>
      <div class="diq-app-sub">Machine Shop Intelligence</div>
    </div>
    <span class="diq-plan-chip chip-{plan}">{html_lib.escape(plan.upper())}</span>
  </div>
  <div class="diq-header-right">
    <div class="diq-avatar">{html_lib.escape(user_initials)}</div>
    <span class="diq-username">{html_lib.escape(user_name)}</span>
  </div>
</div>
""", unsafe_allow_html=True)
 
# ── ONBOARDING ────────────────────────────────────────────────────────────────
_analyses_total  = profile.get("analyses_total", 0)
_onboarding_done = st.session_state.get("onboarding_dismissed", False)
_show_onboarding = not _onboarding_done and _analyses_total == 0
 
if _show_onboarding:
    with st.expander("👋 Welcome to DrawingIQ — Get started in 4 steps", expanded=True):
        oc1, oc2, oc3, oc4 = st.columns(4)
        steps = [
            ("⚙", "Add your machines", "Go to Shop Setup → Machine Profiles.", False),
            ("🧱", "Add your materials", "Go to Shop Setup → Material Library.", False),
            ("📐", "Analyze a drawing", "Upload any engineering drawing.", _analyses_total > 0),
            ("💰", "Generate a quote", "After analyzing, go to the Quote tab.", False),
        ]
        for col, (icon, title, desc, done) in zip([oc1, oc2, oc3, oc4], steps):
            with col:
                st.markdown(f"""
                <div style='background:{"#f0fdf4" if done else "white"};border:1px solid {"#86efac" if done else "#e2e8f0"};
                            border-radius:12px;padding:1.25rem;text-align:center;'>
                    <div style='font-size:1.5rem;margin-bottom:0.5rem;'>{icon}</div>
                    <div style='font-size:0.85rem;font-weight:600;color:#0f172a;margin-bottom:4px;'>{title}</div>
                    <div style='font-size:0.76rem;color:#64748b;line-height:1.4;'>{desc}</div>
                    <div style='margin-top:8px;font-size:0.9rem;'>{"✅" if done else "○"}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("✕ Dismiss", use_container_width=True):
            st.session_state["onboarding_dismissed"] = True
            st.rerun()
 
# ── NAVIGATION ────────────────────────────────────────────────────────────────
_forced    = st.session_state.pop("force_page", None)
NAV = ["📤 Analyze", "📊 Dashboard", "📋 History", "🔍 Compare", "✅ Review Checklist",
       "💰 Quotes", "🔬 FAI Reports", "📈 Job Tracker", "🔧 Shop Setup",
       "👥 Team", "💳 Billing", "⚙ Account", "📜 Terms & Privacy"]
_nav_index = NAV.index(_forced) if _forced in NAV else st.session_state.get("_nav_index", 0)
 
used  = st.session_state.get("profile", {}).get("analyses_this_month", profile.get("analyses_this_month", 0))
cap   = limits["analyses_per_month"]
pct   = int(used / max(cap, 1) * 100)
bar_c = "#ef4444" if pct >= 90 else "#f59e0b" if pct >= 70 else "#3b82f6"
 
workspace_id = None
 
nav_c1, nav_c2, nav_c3 = st.columns([5, 2, 1])
with nav_c1:
    page = st.selectbox("Navigation", NAV, index=_nav_index, key="main_nav",
                        label_visibility="collapsed")
    if NAV.index(page) != _nav_index:
        st.session_state["_nav_index"] = NAV.index(page)
with nav_c2:
    _trial_html = ""
    _created = profile.get("created_at", "")
    if _created and plan in ("free", "trial"):
        try:
            from datetime import timezone as _tz
            _cdt   = datetime.fromisoformat(_created.replace("Z", "+00:00"))
            _dleft = max(0, 30 - (datetime.now(_tz.utc) - _cdt).days)
            _tcol  = "#ef4444" if _dleft <= 5 else "#f59e0b" if _dleft <= 10 else "#3b82f6"
            _trial_html = f"<span style='font-size:0.7rem;color:{_tcol};font-weight:600;margin-left:4px;'>{_dleft}d left</span>"
        except Exception:
            pass
    st.markdown(
        f"""<div class="diq-usage-wrap">
        <div class="diq-usage-track">
            <div class="diq-usage-fill" style="width:{min(pct,100)}%;background:{bar_c};"></div>
        </div>
        <span><strong style="color:#1d4ed8;">{used}</strong><span style="color:#94a3b8;"> / {cap}</span></span>
        {_trial_html}</div>""",
        unsafe_allow_html=True
    )
with nav_c3:
    if st.button("Sign Out", use_container_width=True, key="signout_main"):
        logout()
 
st.markdown("<hr style='margin:0.5rem 0 1rem 0;border-color:#e2e8f0;border-width:1px 0 0 0;'>", unsafe_allow_html=True)
 
# ── CONSTANTS ─────────────────────────────────────────────────────────────────
DISCIPLINES   = ["Auto-Detect", "Mechanical / Machining", "Structural / Civil",
                 "Electrical / Schematic", "Architectural", "PCB / Electronics",
                 "Welding / Fabrication"]
DETAIL_LEVELS = ["Quick Scan", "Standard", "Deep Review"]
MAX_FILE_MB   = 20
 
if "pref_discipline" not in st.session_state: st.session_state["pref_discipline"] = "Mechanical / Machining"
if "pref_detail"     not in st.session_state: st.session_state["pref_detail"]     = "Standard"
if "pending_delete"  not in st.session_state: st.session_state["pending_delete"]  = None
 
# ── HELPERS ───────────────────────────────────────────────────────────────────
def friendly_error(exc):
    msg = str(exc).lower()
    if "rate_limit" in msg or "429" in msg: return "AI service is busy. Wait 30 seconds and retry."
    if "timeout"    in msg: return "Request timed out. Check connection and retry."
    if "json"       in msg or "decode" in msg: return "AI returned unexpected output. Try Deep Review."
    if "api_key"    in msg or "auth"   in msg: return "API authentication failed. Contact administrator."
    logger.error("Analysis error: %s", exc, exc_info=True)
    return "Analysis failed. Please retry or contact support."
 
def esc(v):
    return html_lib.escape(str(v) if v is not None else "—")
 
def upgrade_prompt(feature: str, min_plan: str = "Pro", price: str = "$50/month") -> None:
    plan_colors = {"Pro": "#f59e0b", "Shop": "#a78bfa"}
    color = plan_colors.get(min_plan, "#3b82f6")
    st.markdown(f"""
    <div style='background:white;border:2px solid {color};border-radius:12px;
                padding:2rem;text-align:center;margin:1rem 0;'>
        <div style='font-size:2rem;margin-bottom:0.5rem;'>🔒</div>
        <div style='font-family:"Syne",sans-serif;font-size:1.1rem;font-weight:700;color:#0f172a;margin-bottom:0.5rem;'>
            {feature} — {min_plan} Plan Required
        </div>
        <div style='color:#64748b;font-size:0.88rem;margin-bottom:1.25rem;'>
            Upgrade to {min_plan} ({price}) to unlock this feature.
        </div>
        <div style='font-size:0.82rem;color:{color};font-weight:600;'>
            Your 30-day free trial includes full access.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(f"🚀 Upgrade to {min_plan} — {price}", type="primary",
                 use_container_width=True, key=f"upg_{feature.replace(' ','_')}"):
        st.session_state["force_page"] = "💳 Billing"
        st.rerun()
 def build_checklist(result):
    checks = []
    dims  = result.get("dimensions", [])
    flags = result.get("flags", [])
    def add(status, label, note=""):
        checks.append({"status": status, "label": label, "note": note})
    tb = result.get("title_block_found", False)
    add("pass" if tb else "fail", "Title block found", "No title block detected." if not tb else "")
    pn = result.get("part_number")
    add("pass" if pn else "warn", "Part number present", "No part number — assign before quoting." if not pn else str(pn))
    rev = result.get("revision")
    add("pass" if rev else "warn", "Revision level present", "No revision found." if not rev else str(rev))
    mat = result.get("material")
    add("pass" if mat else "fail", "Material specified", "Must be called out before machining." if not mat else str(mat))
    spec = result.get("material_spec")
    add("pass" if spec else "warn", "Material spec/grade", "e.g. ASTM A36, 6061-T6 for traceability." if not spec else str(spec))
    sf = result.get("surface_finish")
    add("pass" if sf else "warn", "Surface finish specified", "No surface finish callout." if not sf else str(sf))
    add("pass" if dims else "fail", "Dimensions extracted", f"{len(dims)} found." if dims else "None readable.")
    crits = [d for d in dims if d.get("is_critical")]
    add("warn" if crits else "pass", f"{len(crits)} critical dimension(s)", "Review carefully before setup." if crits else "")
    tsr = result.get("tolerance_stack_risk", "Unknown")
    add("fail" if tsr == "High" else "warn" if tsr == "Medium" else "pass", f"Tolerance stack risk: {tsr}", "High risk — verify assembly clearances." if tsr == "High" else "")
    crit_flags = [f for f in flags if f.get("severity") == "critical"]
    add("fail" if crit_flags else "pass", f"{len(crit_flags)} critical flag(s)", "; ".join(f.get("category", "") for f in crit_flags) if crit_flags else "None.")
    gdt = result.get("gdt_callouts", [])
    add("pass" if gdt else "warn", "GD&T callouts", f"{len(gdt)} found." if gdt else "None — may be OK for simple parts.")
    stds = result.get("standards_referenced", [])
    add("pass" if stds else "warn", "Standards referenced", ", ".join(stds) if stds else "None called out.")
    conf = result.get("confidence_score", 0)
    add("fail" if conf < 50 else "warn" if conf < 75 else "pass", f"Drawing readability: {conf}%", "Upload higher-res scan." if conf < 75 else "")
    return checks

def check_machine_capability(dims, machines):
    if not machines or not dims:
        return []
    best_tol = min(m["tolerance_mm"] for m in machines)
    risks = []
    for d in dims:
        tol_str = d.get("tolerance", "")
        if not tol_str or tol_str in ("N/A", "—", "Unknown", "null", "None"):
            continue
        try:
            tol_val = float(str(tol_str).replace("±", "").replace("+/-", "").strip().split("/")[0])
            unit    = d.get("unit", "mm")
            tol_mm  = tol_val if "mm" in unit.lower() else tol_val * 25.4
            if tol_mm < best_tol:
                risks.append({
                    "feature": d.get("feature", ""),
                    "tolerance": tol_str,
                    "unit": unit,
                    "tightest_machine": min(machines, key=lambda m: m["tolerance_mm"])["name"],
                    "machine_capability": best_tol,
                })
        except Exception:
            continue
    return risks

def render_result(result, filename, analysis_id=None):
    flags    = result.get("flags", [])
    critical = [f for f in flags if f.get("severity") == "critical"]
    warnings = [f for f in flags if f.get("severity") == "warning"]
    info_f   = [f for f in flags if f.get("severity") == "info"]
    dims     = result.get("dimensions", [])
    conf     = result.get("confidence_score", 0)
    clarity  = result.get("drawing_clarity", "Unknown")
    clarity_color = {"Clear": "#16a34a", "Partially Legible": "#f59e0b", "Difficult to Read": "#ef4444", "Unclear": "#ef4444"}.get(clarity, "#64748b")
    crit_color = "#ef4444" if critical else "#16a34a"

    st.markdown(f'<span class="diq-type-tag">{esc(result.get("drawing_type","Unknown"))}</span>', unsafe_allow_html=True)

    if conf < 60:
        st.warning(f"⚠️ Low confidence ({conf}%) — upload a cleaner scan for full accuracy.")
    if critical:
        st.error(f"🔴 {len(critical)} critical issue(s) require attention before machining.")

    st.markdown(f"""
    <div class="diq-metric-strip">
      <div class="diq-metric-box"><div class="diq-metric-label">Part</div><div class="diq-metric-value">{esc(result.get("part_name"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">P/N</div><div class="diq-metric-value">{esc(result.get("part_number"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Rev</div><div class="diq-metric-value">{esc(result.get("revision"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Material</div><div class="diq-metric-value">{esc(result.get("material"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Units</div><div class="diq-metric-value">{esc(result.get("units"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Scale</div><div class="diq-metric-value">{esc(result.get("scale"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Complexity</div><div class="diq-metric-value">{esc(result.get("estimated_complexity"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Setups</div><div class="diq-metric-value">{esc(result.get("setup_count_estimate"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Confidence</div><div class="diq-metric-value">{conf}%</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Clarity</div><div class="diq-metric-value" style="color:{clarity_color}">{esc(clarity)}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Tol.Risk</div><div class="diq-metric-value">{esc(result.get("tolerance_stack_risk"))}</div></div>
      <div class="diq-metric-box"><div class="diq-metric-label">Flags</div><div class="diq-metric-value" style="color:{crit_color}">{len(critical)}🔴 {len(warnings)}⚠️ {len(info_f)}ℹ️</div></div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["🚩 Flags", "📐 Dimensions", "🔧 Notes", "📋 Specs", "✅ Checklist", "💰 Quote", "📝 Raw Notes", "✏️ Verify", "🖨 Print", "⬇ Export"])
    t_flags, t_dims, t_notes, t_specs, t_checklist, t_quote, t_rawnotes, t_verify, t_print, t_export = tabs

    with t_flags:
        if not flags:
            st.success("✓ No flags raised — drawing looks clean.")
        for severity, label, cls in [("critical", "🔴 Critical", "diq-flag-critical"), ("warning", "⚠️ Warnings", "diq-flag-warning"), ("info", "ℹ️ Info", "diq-flag-info")]:
            subset = [f for f in flags if f.get("severity") == severity]
            if not subset: continue
            st.markdown(f"**{label}**")
            for f in subset:
                ev = f.get("evidence", "")
                ev_html = f'<div class="diq-flag-evidence">Evidence: {esc(ev)}</div>' if ev else ""
                st.markdown(f'<div class="diq-flag {cls}"><strong>{esc(f.get("category",""))}</strong>: {esc(f.get("description",""))}<br><span style="color:#64748b;font-size:0.82rem;">→ {esc(f.get("recommendation",""))}</span>{ev_html}</div>', unsafe_allow_html=True)
        concerns = result.get("manufacturing_concerns", [])
        if concerns:
            st.markdown("---\n**Manufacturing Concerns**")
            for c in concerns: st.markdown(f"• {c}")

    with t_dims:
        if dims:
            rows = ""
            for d in dims:
                row_cls = "critical-row" if d.get("is_critical") else ""
                tol = esc(d.get("tolerance")) if d.get("tolerance") else "—"
                est = ' <span style="font-size:0.7rem;color:#9ca3af;">~est</span>' if d.get("is_estimated") else ""
                rows += f'<tr class="{row_cls}"><td>{esc(d.get("feature",""))}</td><td>{esc(d.get("value",""))}{est}</td><td>{tol}</td><td>{esc(d.get("unit",""))}</td><td>{esc(d.get("location_hint",""))}</td><td>{"🔴" if d.get("is_critical") else ""}</td></tr>'
            st.markdown(f'<table class="diq-dim-table"><thead><tr><th>Feature</th><th>Value</th><th>Tolerance</th><th>Unit</th><th>Location</th><th></th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        else:
            st.info("No dimensions extracted — try Deep Review or a cleaner scan.")
        gdt = result.get("gdt_callouts", [])
        if gdt:
            st.markdown("---\n**GD&T Callouts**")
            for g in gdt:
                dat = f' — Datum **{g.get("datum")}**' if g.get("datum") else ""
                st.markdown(f'`{esc(g.get("symbol",""))}` **{esc(g.get("feature",""))}**: {esc(g.get("value",""))}{dat}')

    with t_notes:
        note = result.get("machinist_notes", "")
        if note:
            st.markdown(f'<div class="diq-result-card"><p style="line-height:1.8;color:#1e293b;font-size:0.95rem;">{esc(note)}</p></div>', unsafe_allow_html=True)
        procs = result.get("recommended_processes", [])
        if procs:
            st.markdown("**Recommended Processes**")
            cols = st.columns(min(len(procs), 4))
            for i, p in enumerate(procs):
                cols[i % len(cols)].markdown(f'<div style="background:#eff6ff;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.82rem;text-align:center;font-weight:500;color:#1d4ed8;">{esc(p)}</div>', unsafe_allow_html=True)
        stds = result.get("standards_referenced", [])
        if stds: st.markdown("**Standards:** " + " · ".join(f"`{s}`" for s in stds))

    with t_specs:
        fields = [("Part Name","part_name"),("Part Number","part_number"),("Revision","revision"),("Scale","scale"),("Sheet","sheet_info"),("Units","units"),("Material","material"),("Material Spec","material_spec"),("Surface Finish","surface_finish"),("Heat Treatment","heat_treatment"),("Weight Est.","weight_estimate"),("Setups Est.","setup_count_estimate"),("Tol. Stack Risk","tolerance_stack_risk"),("Drawing Clarity","drawing_clarity"),("Title Block","title_block_found")]
        rows = "".join(f'<tr><td style="color:#64748b;font-size:0.82rem;padding:6px 12px;">{label}</td><td style="font-family:JetBrains Mono,monospace;font-size:0.82rem;padding:6px 12px;color:#0f172a;">{esc(result.get(key))}</td></tr>' for label, key in fields)
        st.markdown(f'<table class="diq-dim-table"><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        with st.expander("Raw JSON"): st.json(result)

    with t_checklist:
        st.markdown("### ✅ Pre-Machining Readiness Checklist")
        checks = build_checklist(result)
        passed = sum(1 for c in checks if c["status"] == "pass")
        failed = sum(1 for c in checks if c["status"] == "fail")
        warned = sum(1 for c in checks if c["status"] == "warn")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Passed", passed); sc2.metric("Warnings", warned); sc3.metric("Failed", failed)
        if failed == 0 and warned == 0: st.success("🟢 Ready to machine.")
        elif failed == 0: st.warning(f"🟡 {warned} item(s) to review.")
        else: st.error(f"🔴 {failed} item(s) must be resolved.")
        st.markdown("---")
        icons = {"pass": "✅", "fail": "❌", "warn": "⚠️"}
        for c in checks:
            note = f' <span style="color:#94a3b8;font-size:0.8rem;">— {esc(c["note"])}</span>' if c["note"] else ""
            st.markdown(f'<div class="diq-checklist-item"><span>{icons[c["status"]]}</span><span><strong>{esc(c["label"])}</strong>{note}</span></div>', unsafe_allow_html=True)
        cl_txt = "\n".join(f'[{"PASS" if c["status"]=="pass" else "FAIL" if c["status"]=="fail" else "WARN"}] {c["label"]}' + (f' — {c["note"]}' if c["note"] else "") for c in checks)
        st.download_button("⬇ Download Checklist", f'DRAWINGIQ PRE-MACHINING CHECKLIST\nPart: {result.get("part_name","Unknown")} | File: {filename} | {datetime.now().strftime("%Y-%m-%d %H:%M")}\n{"="*60}\n{cl_txt}', file_name=f'{filename.rsplit(".",1)[0]}_checklist.txt', mime="text/plain", use_container_width=True)

    with t_quote:
        if not limits.get("quote", False):
            st.markdown('<div class="diq-upgrade-banner"><div style="font-size:1.5rem;margin-bottom:0.5rem;">💰</div><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Quote Engine — Starter Plan & Above</div><div style="opacity:0.7;font-size:0.88rem;">Generate instant job cost estimates starting at $50/month.</div></div>', unsafe_allow_html=True)
            if st.button("🚀 Upgrade to Starter — $50/month", type="primary", use_container_width=True, key=f"upg_q_{analysis_id}"):
                st.session_state["force_page"] = "💳 Billing"; st.rerun()
        else:
            st.markdown("### 💰 Job Cost Estimator")
            qr1, qr2, qr3 = st.columns(3)
            with qr1:
                machine_rate = st.number_input("Machine Rate ($/hr)", 0.0, value=85.0, step=5.0, key=f"qmr_{analysis_id}")
                labor_rate   = st.number_input("Labor Rate ($/hr)", 0.0, value=65.0, step=5.0, key=f"qlr_{analysis_id}")
                setup_cost   = st.number_input("Fixed Setup Cost ($)", 0.0, value=50.0, step=10.0, key=f"qsc_{analysis_id}")
            with qr2:
                mat_cost_kg = st.number_input("Material Cost ($/kg)", 0.0, value=5.0, step=0.5, key=f"qmc_{analysis_id}")
                mat_density = st.number_input("Material Density (kg/m³)", 100.0, value=2700.0, step=100.0, key=f"qmd_{analysis_id}", help="Al=2700 · Steel=7850 · SS=8000 · Ti=4500")
                quantity    = st.number_input("Quantity", 1, value=1, step=1, key=f"qqty_{analysis_id}")
            with qr3:
                overhead_pct = st.number_input("Overhead (%)", 0.0, value=15.0, step=1.0, key=f"qoh_{analysis_id}")
                profit_pct   = st.number_input("Profit Margin (%)", 0.0, value=20.0, step=1.0, key=f"qpm_{analysis_id}")
                rush_mult    = st.number_input("Rush Multiplier", 1.0, value=1.0, step=0.1, key=f"qrm_{analysis_id}", help="1.0=standard · 1.5=rush · 2.0=emergency")
            qi1, qi2 = st.columns(2)
            with qi1:
                cust_name  = st.text_input("Customer Name", placeholder="Acme Corp", key=f"qcn_{analysis_id}")
                cust_email = st.text_input("Customer Email", placeholder="buyer@acme.com", key=f"qce_{analysis_id}")
            with qi2:
                quote_num = st.text_input("Quote Number", placeholder="Q-2026-001", key=f"qqn_{analysis_id}")
                due_date  = st.text_input("Delivery Date", placeholder="2026-06-15", key=f"qdd_{analysis_id}")
            if st.button("⚙ Calculate Estimate", type="primary", key=f"qcalc_{analysis_id}", use_container_width=True):
                shop_rates = {"machine_rate_per_hr": machine_rate, "labor_rate_per_hr": labor_rate, "material_cost_per_kg": mat_cost_kg, "material_density_kg_m3": mat_density, "overhead_pct": overhead_pct, "profit_margin_pct": profit_pct, "setup_cost": setup_cost, "quantity": int(quantity)}
                q = estimate_quote(result, shop_rates)
                if rush_mult > 1.0:
                    q["total_job_cost"] = round(q["total_job_cost"] * rush_mult, 2)
                    q["price_per_part"] = round(q["price_per_part"] * rush_mult, 2)
                st.session_state[f"quote_{analysis_id}"]      = q
                st.session_state[f"quote_meta_{analysis_id}"] = {"customer_name": cust_name, "customer_email": cust_email, "quote_number": quote_num, "due_date": due_date}
            if f"quote_{analysis_id}" in st.session_state:
                q    = st.session_state[f"quote_{analysis_id}"]
                meta = st.session_state.get(f"quote_meta_{analysis_id}", {})
                st.markdown(f'<div class="diq-quote-total"><div class="diq-quote-label">Price Per Part</div><div class="diq-quote-price">${q["price_per_part"]:,.2f}</div><div style="margin-top:0.5rem;opacity:0.6;font-size:0.85rem;">Total Job ({q["quantity"]} pcs): <strong>${q["total_job_cost"]:,.2f}</strong></div></div>', unsafe_allow_html=True)
                st.markdown('<div class="diq-result-card">', unsafe_allow_html=True)
                for lbl, val, note in [("Machine Cost", f'${q["machine_cost"]:,.2f}', f'{q["machine_hours_per_part"]} hr/part'), ("Labor Cost", f'${q["labor_cost"]:,.2f}', f'{q["labor_hours_per_part"]} hr/part'), ("Material Cost", f'${q["material_cost"]:,.2f}', q["material_note"]), ("Setup Cost", f'${q["setup_cost"]:,.2f}', ""), ("Overhead", f'${q["overhead_amount"]:,.2f}', ""), ("Profit", f'${q["profit_amount"]:,.2f}', "")]:
                    note_html = f' <span style="color:#94a3b8;font-size:0.78rem;">{esc(note)}</span>' if note else ""
                    st.markdown(f'<div class="diq-quote-row"><span class="diq-quote-row-label">{lbl}</span><span class="diq-quote-row-value">{val}{note_html}</span></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.caption(f"⚠️ {q['disclaimer']}")
                now_q  = datetime.now().strftime("%Y-%m-%d")
                qlines = ["="*62, "              SHOP QUOTE — DrawingIQ", "="*62, f'Quote #:        {meta.get("quote_number") or "N/A"}', f'Date:           {now_q}', f'Delivery:       {meta.get("due_date") or "TBD"}', "-"*62, f'Customer:       {meta.get("customer_name") or "N/A"}', f'Email:          {meta.get("customer_email") or "N/A"}', "-"*62, f'Part:           {result.get("part_name") or "Unknown"}', f'Material:       {result.get("material") or "Unknown"}', f'Drawing File:   {filename}', "-"*62, f'Quantity:       {q["quantity"]} pcs', f'Complexity:     {q["complexity"]}', "-"*62, f'Machine Cost:   ${q["machine_cost"]:,.2f}', f'Labor Cost:     ${q["labor_cost"]:,.2f}', f'Material Cost:  ${q["material_cost"]:,.2f}', f'Setup Cost:     ${q["setup_cost"]:,.2f}', f'Overhead:       ${q["overhead_amount"]:,.2f}', f'Profit:         ${q["profit_amount"]:,.2f}', "="*62, f'PRICE PER PART: ${q["price_per_part"]:,.2f}', f'TOTAL JOB:      ${q["total_job_cost"]:,.2f}', "="*62, "", q["disclaimer"]]
                st.download_button("⬇ Download Quote (.txt)", "\n".join(qlines), file_name=f'quote_{meta.get("quote_number") or "estimate"}.txt', mime="text/plain", use_container_width=True)

    with t_rawnotes:
        st.markdown("### 📝 Raw Drawing Content")
        raw_notes = result.get("raw_notes", [])
        if raw_notes:
            for i, n in enumerate(raw_notes, 1):
                st.markdown(f'<div class="diq-flag diq-flag-info"><strong>Note {i}:</strong> {esc(n)}</div>', unsafe_allow_html=True)
        else:
            st.info("No notes extracted.")
        rev_hist = result.get("revision_history", [])
        if rev_hist:
            st.markdown("---\n**Revision History**")
            for r in rev_hist: st.markdown(f"• {esc(r)}")

    with t_verify:
        if not limits.get("verify"):
            upgrade_prompt("Verify & Schedule", "Pro", "$50/month")
        else:
            st.markdown("### ✏️ Verify & Schedule")
        st.caption("Review AI-extracted values, correct anything wrong, assign to a machine, and schedule the job.")
        st.markdown("---")
        _aid = str(analysis_id or filename or "draft").replace(" ", "_")
        vkey = f"vs_{_aid}"
        if vkey not in st.session_state:
            st.session_state[vkey] = {"dims": {i: {"value": d.get("value", ""), "tolerance": d.get("tolerance", "") or "", "confirmed": False} for i, d in enumerate(dims)}, "part_name": result.get("part_name") or "", "part_number": result.get("part_number") or "", "revision": result.get("revision") or "", "material": result.get("material") or "", "surface_finish": result.get("surface_finish") or "", "machine": "", "operator": "", "due_date": "", "job_number": "", "priority": "Normal", "status": "Pending", "notes": "", "verified": False}
        vs = st.session_state[vkey]
        st.markdown("#### Step 1 — Verify Drawing Info")
        vf1, vf2, vf3 = st.columns(3)
        with vf1:
            vs["part_name"] = st.text_input("Part Name", value=vs["part_name"], key=f"vf_pn_{vkey}", placeholder="Enter part name")
            vs["material"]  = st.text_input("Material", value=vs["material"], key=f"vf_mat_{vkey}", placeholder="e.g. 6061-T6 Aluminum")
        with vf2:
            vs["part_number"]    = st.text_input("Part Number", value=vs["part_number"], key=f"vf_pno_{vkey}", placeholder="e.g. PN-001")
            vs["surface_finish"] = st.text_input("Surface Finish", value=vs["surface_finish"], key=f"vf_sf_{vkey}", placeholder="e.g. 125 Ra")
        with vf3:
            vs["revision"] = st.text_input("Revision", value=vs["revision"], key=f"vf_rev_{vkey}", placeholder="e.g. Rev A")
        st.markdown("---")
        st.markdown("#### Step 2 — Verify Dimensions")
        if dims:
            hc1, hc2, hc3, hc4, hc5 = st.columns([3, 2, 2, 1, 1])
            for h, t in zip([hc1, hc2, hc3, hc4, hc5], ["Feature", "Value", "Tolerance", "Unit", "✓"]):
                h.markdown(f"<span style='font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:600;'>{t}</span>", unsafe_allow_html=True)
            for i, d in enumerate(dims):
                dc1, dc2, dc3, dc4, dc5 = st.columns([3, 2, 2, 1, 1])
                is_crit = d.get("is_critical", False)
                with dc1:
                    st.markdown(f"<div style='padding:8px 0;font-size:0.85rem;color:{'#ef4444' if is_crit else '#374151'};font-weight:{'600' if is_crit else '400'};'>{'🔴 ' if is_crit else ''}{esc(d.get('feature',''))}</div>", unsafe_allow_html=True)
                with dc2:
                    vs["dims"][i]["value"] = st.text_input("v", value=vs["dims"][i]["value"], key=f"vd_v_{vkey}_{i}", label_visibility="collapsed")
                with dc3:
                    vs["dims"][i]["tolerance"] = st.text_input("t", value=vs["dims"][i]["tolerance"], key=f"vd_t_{vkey}_{i}", label_visibility="collapsed", placeholder="N/A")
                with dc4:
                    st.markdown(f"<div style='padding:8px 0;font-size:0.82rem;color:#94a3b8;'>{esc(d.get('unit',''))}</div>", unsafe_allow_html=True)
                with dc5:
                    vs["dims"][i]["confirmed"] = st.checkbox("", value=vs["dims"][i]["confirmed"], key=f"vd_c_{vkey}_{i}", label_visibility="collapsed")
            confirmed_n = sum(1 for d in vs["dims"].values() if d["confirmed"])
            total_n = len(dims)
            pct_n = int(confirmed_n / max(total_n, 1) * 100)
            bar_color = "#16a34a" if pct_n == 100 else "#3b82f6"
            st.markdown(f"""<div style='background:#f8fafc;border-radius:8px;padding:0.75rem 1rem;margin-top:0.5rem;display:flex;align-items:center;gap:1rem;'><div style='flex:1;background:#e2e8f0;border-radius:4px;height:6px;'><div style='background:{bar_color};border-radius:4px;height:6px;width:{pct_n}%;'></div></div><span style='font-size:0.82rem;color:#374151;font-weight:500;white-space:nowrap;'>{confirmed_n}/{total_n} confirmed</span></div>""", unsafe_allow_html=True)
            if st.button("✓ Confirm All", key=f"conf_all_{vkey}"):
                for i in vs["dims"]: vs["dims"][i]["confirmed"] = True
                st.rerun()
        else:
            st.info("No dimensions extracted. You can still assign this job below.")
        st.markdown("---")
        st.markdown("#### Step 3 — Assign & Schedule")
        try:
            machines_vs = get_machines(user["id"])
        except Exception:
            machines_vs = []
        sa1, sa2, sa3 = st.columns(3)
        with sa1:
            if machines_vs:
                mach_opts = ["-- Select Machine --"] + [m["name"] for m in machines_vs]
                sel_m = st.selectbox("Machine / Cell", mach_opts, key=f"vs_mach_{vkey}")
                vs["machine"] = "" if sel_m == "-- Select Machine --" else sel_m
            else:
                vs["machine"] = st.text_input("Machine / Cell", value=vs["machine"], key=f"vs_mach_t_{vkey}", placeholder="Add machines in Shop Setup")
            vs["operator"] = st.text_input("Operator", value=vs["operator"], key=f"vs_op_{vkey}", placeholder="Machinist name")
        with sa2:
            vs["job_number"] = st.text_input("Job / WO #", value=vs["job_number"], key=f"vs_job_{vkey}", placeholder="WO-2026-001")
            vs["due_date"]   = str(st.date_input("Due Date", key=f"vs_due_{vkey}"))
        with sa3:
            vs["priority"] = st.selectbox("Priority", ["Normal", "Rush", "Emergency", "Low"], key=f"vs_pri_{vkey}")
            vs["status"]   = st.selectbox("Status", ["Pending", "In Progress", "On Hold", "Complete"], key=f"vs_stat_{vkey}")
        vs["notes"] = st.text_area("Setup Notes", value=vs["notes"], key=f"vs_notes_{vkey}", placeholder="Special fixturing, customer requirements...", height=80)
        st.markdown("---")
        st.markdown("#### Step 4 — Sign Off")
        confirmed_c = sum(1 for d in vs["dims"].values() if d["confirmed"]) if dims else 0
        total_c = len(dims)
        r_score = 0; r_items = []
        if total_c > 0 and confirmed_c == total_c: r_score += 40; r_items.append(("✅", f"All {total_c} dimensions confirmed"))
        elif total_c > 0: r_items.append(("⚠️", f"{confirmed_c}/{total_c} dimensions confirmed"))
        if vs.get("material"):  r_score += 20; r_items.append(("✅", f"Material: {vs['material']}"))
        else: r_items.append(("❌", "Material not specified"))
        if vs.get("machine"):   r_score += 20; r_items.append(("✅", f"Assigned to: {vs['machine']}"))
        else: r_items.append(("⚠️", "No machine assigned"))
        if vs.get("operator"):  r_score += 10; r_items.append(("✅", f"Operator: {vs['operator']}"))
        else: r_items.append(("⚠️", "No operator assigned"))
        if vs.get("job_number"): r_score += 10; r_items.append(("✅", f"Job #: {vs['job_number']}"))
        else: r_items.append(("⚠️", "No job number"))
        sc_color = "#16a34a" if r_score >= 80 else "#f59e0b" if r_score >= 50 else "#ef4444"
        items_html = "".join(f'<div style="font-size:0.83rem;padding:2px 0;">{icon} {esc(item)}</div>' for icon, item in r_items)
        st.markdown(f"""<div style='background:white;border:1px solid #e2e8f0;border-radius:10px;padding:1rem 1.25rem;'><div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;'><span style='font-weight:600;color:#0f172a;'>Job Readiness</span><span style='font-size:1.5rem;font-weight:800;font-family:JetBrains Mono,monospace;color:{sc_color};'>{r_score}%</span></div><div style='background:#f1f5f9;border-radius:4px;height:8px;margin-bottom:0.75rem;'><div style='background:{sc_color};border-radius:4px;height:8px;width:{r_score}%;'></div></div>{items_html}</div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        btn1, btn2 = st.columns([2, 1])
        with btn1:
            if st.button("✅ Mark as Verified & Ready to Machine", type="primary", use_container_width=True, key=f"vs_verify_{vkey}"):
                vs["verified"] = True; vs["verified_by"] = user_name; vs["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state[vkey] = vs
                st.success(f"✅ Verified by {user_name} at {vs['verified_at']}.")
                st.balloons()
        with btn2:
            if vs.get("verified"):
                st.markdown(f"""<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:0.6rem 0.9rem;text-align:center;'><div style='color:#16a34a;font-weight:700;font-size:0.85rem;'>✅ VERIFIED</div><div style='color:#64748b;font-size:0.72rem;margin-top:2px;'>{esc(vs.get("verified_at",""))}</div><div style='color:#64748b;font-size:0.72rem;'>{esc(vs.get("verified_by",""))}</div></div>""", unsafe_allow_html=True)
        if vs.get("verified"):
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("💾 Save to Production Queue", key=f"vs_save_{vkey}", use_container_width=True):
                job_entry = {"id": vkey, "filename": filename, "part_name": vs["part_name"] or result.get("part_name", "Unknown"), "part_number": vs["part_number"], "material": vs["material"], "machine": vs["machine"], "operator": vs["operator"], "job_number": vs["job_number"], "due_date": vs["due_date"], "priority": vs["priority"], "status": vs["status"], "notes": vs["notes"], "verified_by": vs.get("verified_by", ""), "verified_at": vs.get("verified_at", ""), "complexity": result.get("estimated_complexity", "Unknown"), "analysis_id": str(analysis_id or "")}
                try:
                    save_job_to_queue(user["id"], job_entry)
                    st.success("✅ Job saved to production queue!")
                except Exception as _save_err:
                    logger.error("Queue save error: %s", _save_err)
                    if "job_queue" not in st.session_state: st.session_state["job_queue"] = []
                    existing = [j for j in st.session_state["job_queue"] if j["id"] != vkey]
                    existing.append(job_entry)
                    st.session_state["job_queue"] = existing

    with t_print:
        st.markdown("**🖨 Job Traveler / Setup Sheet**")
        pt1, pt2 = st.columns(2)
        with pt1:
            op_name    = st.text_input("Operator Name", key=f"pt_op_{analysis_id}")
            machine_id = st.text_input("Machine / Cell", placeholder="VMC-3", key=f"pt_mc_{analysis_id}")
        with pt2:
            job_number = st.text_input("Job / Work Order #", key=f"pt_job_{analysis_id}")
            due_date_p = st.text_input("Due Date", key=f"pt_due_{analysis_id}")
        verify_key_p = f"vs_{str(analysis_id or filename or 'draft').replace(' ','_')}"
        vs_p = st.session_state.get(verify_key_p, {})
        verified_stamp = ""
        if vs_p.get("verified"):
            verified_stamp = f"AI ANALYZED — HUMAN VERIFIED by {vs_p.get('verified_by','')} at {vs_p.get('verified_at','')}"
            if not op_name and vs_p.get("operator"):      op_name    = vs_p["operator"]
            if not machine_id and vs_p.get("machine"):    machine_id = vs_p["machine"]
            if not job_number and vs_p.get("job_number"): job_number = vs_p["job_number"]
            if not due_date_p and vs_p.get("due_date"):   due_date_p = vs_p["due_date"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = ["="*62, "       DRAWINGIQ — JOB TRAVELER / SETUP SHEET", "="*62, (verified_stamp if verified_stamp else "AI ANALYZED — AWAITING HUMAN VERIFICATION"), "="*62, f"File:           {filename}", f"Generated:      {now_str}", f"Job / WO #:     {job_number or 'N/A'}", f"Operator:       {op_name or 'N/A'}", f"Machine / Cell: {machine_id or 'N/A'}", f"Due Date:       {due_date_p or 'N/A'}", "-"*62, f"Part:           {result.get('part_name') or 'Unknown'}", f"Part Number:    {result.get('part_number') or 'Unknown'}", f"Revision:       {result.get('revision') or 'Unknown'}", f"Material:       {result.get('material') or 'Unknown'} ({result.get('material_spec') or 'No spec'})", f"Surface Finish: {result.get('surface_finish') or 'Unknown'}", f"Units:          {result.get('units') or 'Unknown'}", f"Complexity:     {result.get('estimated_complexity') or 'Unknown'}", f"Confidence:     {conf}%  |  Clarity: {clarity}", "-"*62, f"FLAGS — {len(critical)} critical  {len(warnings)} warnings", "-"*62]
        for f in flags:
            lines.append(f"  [{f.get('severity','').upper()}] {f.get('category','')}: {f.get('description','')}")
            if f.get("recommendation"): lines.append(f"         → {f.get('recommendation')}")
        lines += ["-"*62, "MACHINIST NOTES:", "-"*62, result.get("machinist_notes") or "—"]
        if dims:
            lines += ["", "KEY DIMENSIONS:", "-"*62]
            for d in dims:
                crit_m = "  *** CRITICAL ***" if d.get("is_critical") else ""
                lines.append(f"  {str(d.get('feature','')):<28} {d.get('value','')} {d.get('unit','')}  ±{d.get('tolerance','N/A')}{crit_m}")
        lines += ["", "SIGN-OFF:", "-"*62, "Setup verified by: ___________________  Date: __________", "First article OK:  ___________________  Date: __________", "QC approved:       ___________________  Date: __________"]
        traveler_text = "\n".join(lines)
        st.text_area("Preview", traveler_text, height=300, key=f"pt_prev_{analysis_id}")
        st.download_button("⬇ Download Job Traveler (.txt)", traveler_text, file_name=f'{filename.rsplit(".",1)[0]}_traveler.txt', mime="text/plain", use_container_width=True)

    with t_export:
        if not limits.get("export"):
            st.markdown('<div class="diq-upgrade-banner">Export requires Starter plan or higher.</div>', unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇ Full JSON", json.dumps(result, indent=2), file_name=f'{filename.rsplit(".",1)[0]}.json', mime="application/json", use_container_width=True)
            with c2:
                buf = io.StringIO(); w = csv.writer(buf)
                w.writerow(["Field", "Value"])
                for k, v in result.items():
                    if isinstance(v, (str, int, float, bool)): w.writerow([k, v])
                for d in result.get("dimensions", []):
                    w.writerow([f'DIM:{d.get("feature")}', f'{d.get("value")} {d.get("unit")} ±{d.get("tolerance","N/A")}'])
                for f in flags:
                    w.writerow([f'FLAG[{f.get("severity","").upper()}]', f'{f.get("category")}: {f.get("description")}'])
                st.download_button("⬇ CSV", buf.getvalue(), file_name=f'{filename.rsplit(".",1)[0]}.csv', mime="text/csv", use_container_width=True)


# ── PAGE: ANALYZE ─────────────────────────────────────────────────────────────
if page == "📤 Analyze":
    allowed, reason = can_analyze(profile)
    if allowed and profile.get("plan", "free") == "free":
        try:
            allowed2, reason2 = enforce_free_limits(profile, user.get("email", ""))
            if not allowed2: allowed, reason = allowed2, reason2
        except Exception:
            pass
    if not allowed:
        today = date.today()
        reset = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
        st.markdown(f"""
        <div style='background:white;border:2px solid #ef4444;border-radius:12px;padding:2rem;text-align:center;margin:1rem 0;'>
            <div style='font-size:2rem;margin-bottom:0.5rem;'>⛔</div>
            <div style='font-family:Syne,sans-serif;font-size:1.2rem;font-weight:700;color:#0f172a;margin-bottom:0.5rem;'>Monthly Limit Reached</div>
            <div style='color:#64748b;font-size:0.9rem;margin-bottom:0.5rem;'>{reason}</div>
            <div style='color:#94a3b8;font-size:0.82rem;margin-bottom:1.5rem;'>Resets on <strong>{reset.strftime("%B 1st")}</strong></div>
        </div>""", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Upgrade to Pro — $50/month", type="primary", use_container_width=True, key="upgrade_from_limit"):
                st.session_state["force_page"] = "💳 Billing"; st.rerun()
        with col2:
            st.info("✨ Free trial includes 30 days of full Pro access.")
        st.stop()

    qc1, qc2 = st.columns([3, 2])
    with qc1:
        disc_idx   = DISCIPLINES.index(st.session_state["pref_discipline"]) if st.session_state["pref_discipline"] in DISCIPLINES else 0
        discipline = st.selectbox("Discipline", DISCIPLINES, index=disc_idx, key="qs_disc")
        st.session_state["pref_discipline"] = discipline
    with qc2:
        detail_level = st.select_slider("Detail Level", DETAIL_LEVELS, value=st.session_state["pref_detail"], key="qs_detail")
        st.session_state["pref_detail"] = detail_level

    accepted  = ["png", "jpg", "jpeg", "webp"] + (["pdf"] if limits.get("pdf") else [])
    max_batch = limits["batch_size"]
    fmt_str   = " · ".join(t.upper() for t in accepted)

    st.markdown(f'<div class="diq-drop-zone"><div style="font-size:2.5rem;margin-bottom:0.75rem;">📐</div><h3>Drop your engineering drawing here</h3><p>{fmt_str} &nbsp;|&nbsp; Max {MAX_FILE_MB} MB &nbsp;|&nbsp; Up to {max_batch} file(s) on {plan.title()} plan</p></div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload", type=accepted, accept_multiple_files=(max_batch > 1), label_visibility="collapsed")
    if not uploaded: uploaded = []
    elif not isinstance(uploaded, list): uploaded = [uploaded]
    if len(uploaded) > max_batch: st.warning(f"Only first {max_batch} files analyzed."); uploaded = uploaded[:max_batch]

    if uploaded:
        if len(uploaded) == 1:
            f = uploaded[0]; pc1, pc2 = st.columns([1, 2])
            with pc1:
                if not f.name.lower().endswith(".pdf"): prev = f.read(); f.seek(0); st.image(prev, use_container_width=True)
                else: st.info(f"📄 PDF: `{f.name}`")
            with pc2:
                st.markdown(f"**`{f.name}`**")
                st.caption(f"{f.size/1024:.1f} KB · {discipline} · {detail_level}")
        else:
            cols = st.columns(min(len(uploaded), 5))
            for i, f in enumerate(uploaded):
                with cols[i % 5]:
                    if not f.name.lower().endswith(".pdf"): prev = f.read(); f.seek(0); st.image(prev, use_container_width=True, caption=f.name[:15])
                    else: st.markdown(f"📄 `{f.name[:15]}`")

        for uf_check in uploaded:
            _rk = f"cached_result_{uf_check.name}"
            if _rk in st.session_state:
                _cr, _cf, _ci = st.session_state[_rk]
                with st.expander(f"📄 {_cf}", expanded=True):
                    render_result(_cr, _cf, _ci)

        st.markdown("---")
        _analyzing = st.session_state.pop("_analyzing", False)
        if st.button(f"⚙ Analyze {len(uploaded)} Drawing(s)", type="primary", use_container_width=True) and not _analyzing:
            st.session_state["_analyzing"] = True
            for uf_c in uploaded: st.session_state.pop(f"cached_result_{uf_c.name}", None)
            for uf in uploaded:
                fname = uf.name; file_bytes = uf.read(); size_kb = len(file_bytes) / 1024
                if size_kb > MAX_FILE_MB * 1024: st.error(f"{fname} too large ({size_kb/1024:.1f} MB). Max {MAX_FILE_MB} MB."); continue
                with st.expander(f"📄 {fname}", expanded=True):
                    try:
                        if fname.lower().endswith(".pdf"):
                            with st.spinner("Converting PDF pages…"): pages = pdf_to_images(file_bytes, dpi=200, max_pages=10)
                            if not pages: st.error("Could not extract pages from PDF."); continue
                            st.caption(f"Extracted {len(pages)} page(s)")
                            with st.spinner(f"Analyzing {fname}…"): result = analyze_pdf_pages(pages, discipline, detail_level, _api_key)
                        else:
                            with st.spinner(f"Analyzing {fname}…"): b64, mime = image_file_to_b64(file_bytes, fname); result = analyze_image(b64, mime, discipline, detail_level, _api_key)
                        saved = save_analysis(user_id=user["id"], filename=fname, result=result, file_size_kb=size_kb, analysis_mode=discipline, detail_level=detail_level, workspace_id=workspace_id)
                        try:
                            _sp = st.session_state.get("profile", {})
                            _sp["analyses_this_month"] = _sp.get("analyses_this_month", 0) + 1
                            st.session_state["profile"] = _sp
                        except Exception:
                            pass
                        st.session_state[f"cached_result_{fname}"] = (result, fname, saved.get("id"))
                        render_result(result, fname, saved.get("id"))
                        try:
                            pname = result.get("part_name", ""); pnum = result.get("part_number", "")
                            if pname or pnum:
                                similar = find_similar_parts(user["id"], pname, pnum)
                                similar = [s for s in similar if s.get("id") != saved.get("id")]
                                if similar:
                                    st.info(f"🔁 **Repeat Part** — Found {len(similar)} previous analysis(es) matching this part.")
                                    for sim in similar[:3]:
                                        st.markdown(f"• **{esc(sim.get('filename',''))}** — {str(sim.get('created_at',''))[:10]} · {esc(sim.get('material','?'))} · {esc(sim.get('estimated_complexity','?'))} complexity")
                        except Exception:
                            pass
                        try:
                            machines = get_machines(user["id"])
                            if machines:
                                cap_risks = check_machine_capability(result.get("dimensions", []), machines)
                                if cap_risks:
                                    st.warning(f"⚠️ **{len(cap_risks)} dimension(s)** may exceed your machines' capability:")
                                    for r in cap_risks:
                                        st.markdown(f"• `{esc(r['feature'])}` ±{esc(r['tolerance'])} — tighter than **{esc(r['tightest_machine'])}** (±{r['machine_capability']} mm)")
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(friendly_error(e))
                        if st.button("↩ Retry", key=f"retry_{fname}"): st.rerun()
            try:
                _fresh_p = get_profile(user["id"])
                if _fresh_p: st.session_state["profile"] = _fresh_p
            except Exception:
                pass
            st.rerun()
    else:
        st.markdown('<div class="diq-empty"><div style="font-size:2.5rem;margin-bottom:0.75rem;">⚙</div><h3>Upload a drawing to get started</h3><p>Supports mechanical, structural, electrical, architectural, welding drawings.</p></div>', unsafe_allow_html=True)
        # ── PAGE: DASHBOARD ───────────────────────────────────────────────────────────
elif page == "📊 Dashboard":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;letter-spacing:-0.02em;margin-bottom:0.25rem;">📊 Shop Dashboard</div>', unsafe_allow_html=True)
    stats    = get_usage_stats(user["id"])
    analyses = get_analyses(user["id"], limit=300, workspace_id=workspace_id)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("This Month",    stats.get("analyses_this_month", 0))
    mc2.metric("All Time",      stats.get("analyses_total", 0))
    mc3.metric("Remaining",     max(0, cap - stats.get("analyses_this_month", 0)))
    mc4.metric("Critical Flags",sum(a.get("flag_critical_count", 0) for a in analyses))
    avg_conf = round(sum(a.get("confidence_score", 0) for a in analyses) / len(analyses)) if analyses else 0
    mc5.metric("Avg Confidence", f"{avg_conf}%")
    st.markdown("---")
    dc1, dc2 = st.columns(2)
    with dc1:
        type_counts = {}
        for a in analyses:
            t = a.get("drawing_type") or "Unknown"; type_counts[t] = type_counts.get(t, 0) + 1
        st.markdown('<div class="diq-dash-card"><div class="diq-dash-card-title">Drawing Types</div>', unsafe_allow_html=True)
        for dtype, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = int(cnt / max(len(analyses), 1) * 100)
            st.markdown(f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:0.83rem;margin-bottom:3px;"><span style="color:#374151;">{esc(dtype)}</span><span style="color:#94a3b8;">{cnt} ({pct}%)</span></div><div style="background:#f1f5f9;border-radius:3px;height:5px;"><div style="background:#3b82f6;border-radius:3px;height:5px;width:{pct}%;"></div></div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        cmp_counts  = {}
        for a in analyses:
            c = a.get("estimated_complexity") or "Unknown"; cmp_counts[c] = cmp_counts.get(c, 0) + 1
        cmp_colors = {"Low": "#16a34a", "Medium": "#f59e0b", "High": "#ef4444", "Very High": "#7c3aed", "Unknown": "#94a3b8"}
        st.markdown('<div class="diq-dash-card"><div class="diq-dash-card-title">Complexity Distribution</div>', unsafe_allow_html=True)
        for cmp, cnt in sorted(cmp_counts.items(), key=lambda x: ["Low","Medium","High","Very High","Unknown"].index(x[0]) if x[0] in ["Low","Medium","High","Very High","Unknown"] else 99):
            pct = int(cnt / max(len(analyses), 1) * 100); color = cmp_colors.get(cmp, "#94a3b8")
            st.markdown(f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:0.83rem;margin-bottom:3px;"><span style="color:{color};font-weight:500;">{esc(cmp)}</span><span style="color:#94a3b8;">{cnt} ({pct}%)</span></div><div style="background:#f1f5f9;border-radius:3px;height:5px;"><div style="background:{color};border-radius:3px;height:5px;width:{pct}%;"></div></div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with dc2:
        recent_crits = [a for a in analyses[:20] if a.get("flag_critical_count", 0) > 0]
        st.markdown('<div class="diq-dash-card"><div class="diq-dash-card-title">Recent Critical Flags</div>', unsafe_allow_html=True)
        if recent_crits:
            for a in recent_crits[:8]:
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f8fafc;font-size:0.83rem;"><span style="color:#374151;">{esc(a.get("filename",""))}</span><span style="background:#fef2f2;color:#991b1b;font-size:0.7rem;font-weight:600;padding:1px 7px;border-radius:4px;">🔴 {a.get("flag_critical_count",0)}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#94a3b8;font-size:0.85rem;">No critical flags recently.</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        mat_counts = {}
        for a in analyses:
            m = a.get("material") or "Unknown"; mat_counts[m] = mat_counts.get(m, 0) + 1
        st.markdown('<div class="diq-dash-card"><div class="diq-dash-card-title">Top Materials</div>', unsafe_allow_html=True)
        for mat, cnt in sorted(mat_counts.items(), key=lambda x: -x[1])[:6]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.83rem;border-bottom:1px solid #f8fafc;"><span style="color:#374151;">{esc(mat)}</span><span style="color:#94a3b8;font-family:JetBrains Mono,monospace;">{cnt}</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Production Queue
    st.markdown("---")
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">🏭 Production Queue</div>', unsafe_allow_html=True)
    try:
        queue    = get_job_queue(user["id"])
        ss_queue = st.session_state.get("job_queue", [])
        db_ids   = {j.get("id") for j in queue}
        for ssj in ss_queue:
            if ssj.get("id") not in db_ids: queue.append(ssj)
    except Exception:
        queue = st.session_state.get("job_queue", [])
    if not queue:
        st.markdown('<div class="diq-empty"><div style="font-size:2rem;">🏭</div><h3>No jobs in queue yet</h3><p>Verify and schedule a job from the Analyze page.</p></div>', unsafe_allow_html=True)
    else:
        priority_colors = {"Emergency": "#ef4444", "Rush": "#f59e0b", "Normal": "#3b82f6", "Low": "#94a3b8"}
        status_colors   = {"Pending": "#94a3b8", "In Progress": "#3b82f6", "On Hold": "#f59e0b", "Complete": "#16a34a"}
        qm1, qm2, qm3, qm4 = st.columns(4)
        qm1.metric("Total Jobs",  len(queue))
        qm2.metric("In Progress", sum(1 for j in queue if j.get("status") == "In Progress"))
        qm3.metric("Pending",     sum(1 for j in queue if j.get("status") == "Pending"))
        qm4.metric("Complete",    sum(1 for j in queue if j.get("status") == "Complete"))
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        priority_order = {"Emergency": 0, "Rush": 1, "Normal": 2, "Low": 3}
        sorted_queue   = sorted(queue, key=lambda x: (priority_order.get(x.get("priority", "Normal"), 2), x.get("due_date", "")))
        for job in sorted_queue:
            pc  = priority_colors.get(job.get("priority", "Normal"), "#3b82f6")
            sc  = status_colors.get(job.get("status", "Pending"), "#94a3b8")
            jc1, jc2 = st.columns([5, 1])
            with jc1:
                st.markdown(f"""<div class="diq-queue-card" style="border-left-color:{pc};">
                    <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:5px;">
                        <span style="font-weight:700;color:#0f172a;font-size:0.92rem;">{esc(job.get("part_name","Unknown"))}</span>
                        <span style="background:{sc}20;color:{sc};font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:4px;">{esc(job.get("status","Pending").upper())}</span>
                        <span style="background:{pc}15;color:{pc};font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:4px;">{esc(job.get("priority","Normal").upper())}</span>
                        <span style="margin-left:auto;font-size:0.75rem;color:#94a3b8;">Due: {esc(job.get("due_date","TBD"))}</span>
                    </div>
                    <div style="font-size:0.78rem;color:#94a3b8;display:flex;gap:1rem;flex-wrap:wrap;">
                        <span>📄 {esc(job.get("filename",""))}</span>
                        <span>⚙ {esc(job.get("machine","No machine"))}</span>
                        <span>👷 {esc(job.get("operator","Unassigned"))}</span>
                        <span>🔢 {esc(job.get("job_number","No WO#"))}</span>
                        <span>🧱 {esc(job.get("material","Unknown"))}</span>
                    </div>
                </div>""", unsafe_allow_html=True)
            with jc2:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                new_status = st.selectbox("Status", ["Pending", "In Progress", "On Hold", "Complete"],
                    index=["Pending", "In Progress", "On Hold", "Complete"].index(job.get("status", "Pending")),
                    key=f"qs_stat_{job['id']}", label_visibility="collapsed")
                if new_status != job.get("status"):
                    try: update_job_status(job["id"], user["id"], new_status)
                    except Exception:
                        for j in st.session_state.get("job_queue", []):
                            if j["id"] == job["id"]: j["status"] = new_status
                    st.rerun()
                if st.button("🗑", key=f"qs_del_{job['id']}"):
                    try: delete_job_from_queue(job["id"], user["id"])
                    except Exception: st.session_state["job_queue"] = [j for j in st.session_state.get("job_queue", []) if j["id"] != job["id"]]
                    st.rerun()

# ── PAGE: HISTORY ─────────────────────────────────────────────────────────────
elif page == "📋 History":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;letter-spacing:-0.02em;margin-bottom:1rem;">📋 Analysis History</div>', unsafe_allow_html=True)
    with st.spinner("Loading…"): analyses = get_analyses(user["id"], limit=200, workspace_id=workspace_id)
    if not analyses:
        st.markdown('<div class="diq-empty"><h3>No analyses yet</h3><p>Upload a drawing to get started.</p></div>', unsafe_allow_html=True)
    else:
        fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
        with fc1: search = st.text_input("Search", placeholder="Part name, filename…", label_visibility="collapsed")
        with fc2: type_filter = st.selectbox("Type", ["All Types", "Mechanical", "Structural", "Electrical", "Architectural", "PCB", "Welding"], label_visibility="collapsed")
        with fc3: date_filter = st.selectbox("Date", ["All Time", "Today", "This Week", "This Month"], label_visibility="collapsed")
        with fc4:
            if limits.get("export"):
                buf = io.StringIO(); w = csv.writer(buf)
                w.writerow(["ID", "Filename", "Date", "Type", "Part", "Material", "Complexity", "Confidence", "Critical", "Warnings"])
                for a in analyses: w.writerow([a["id"], a["filename"], a["created_at"], a.get("drawing_type"), a.get("part_name"), a.get("material"), a.get("estimated_complexity"), a.get("confidence_score"), a.get("flag_critical_count", 0), a.get("flag_warning_count", 0)])
                st.download_button("⬇ Export CSV", buf.getvalue(), file_name=f'drawingiq_{datetime.now().strftime("%Y%m%d")}.csv', mime="text/csv", use_container_width=True)
            else:
                if st.button("⬇ Export (Starter+)", use_container_width=True): st.info("Upgrade to export.")
        filtered = analyses
        if search:
            s = search.lower(); filtered = [a for a in filtered if s in (a.get("filename", "")).lower() or s in (a.get("part_name", "") or "").lower()]
        if type_filter != "All Types": filtered = [a for a in filtered if a.get("drawing_type") == type_filter]
        if date_filter != "All Time":
            today = date.today()
            if date_filter == "Today": filtered = [a for a in filtered if str(a.get("created_at", ""))[:10] == str(today)]
            elif date_filter == "This Week": cutoff = str(today - timedelta(days=7)); filtered = [a for a in filtered if str(a.get("created_at", ""))[:10] >= cutoff]
            elif date_filter == "This Month": prefix = today.strftime("%Y-%m"); filtered = [a for a in filtered if str(a.get("created_at", "")).startswith(prefix)]
        st.caption(f"Showing {len(filtered)} of {len(analyses)} analyses")
        st.markdown("---")
        for a in filtered:
            crit = a.get("flag_critical_count", 0); warn = a.get("flag_warning_count", 0)
            dt   = str(a.get("created_at", ""))[:10]; aid = a["id"]
            if st.session_state["pending_delete"] == aid:
                st.markdown(f'<div class="diq-confirm-delete">⚠️ Delete <strong>{esc(a.get("filename",""))}</strong>?</div>', unsafe_allow_html=True)
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✓ Yes", key=f"conf_{aid}", type="primary", use_container_width=True):
                        delete_analysis(aid, user["id"]); st.session_state["pending_delete"] = None; st.rerun()
                with cc2:
                    if st.button("✗ Cancel", key=f"cancel_{aid}", use_container_width=True):
                        st.session_state["pending_delete"] = None; st.rerun()
                continue
            flag_badges = ""
            if crit: flag_badges += f'<span style="background:#fef2f2;color:#991b1b;font-size:0.68rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:5px;">🔴 {crit}</span>'
            if warn: flag_badges += f'<span style="background:#fffbeb;color:#92400e;font-size:0.68rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:5px;">⚠ {warn}</span>'
            card_col, btn_col = st.columns([6, 1])
            with card_col:
                st.markdown(f'<div class="diq-history-card"><div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;"><span style="font-weight:600;color:#0f172a;font-size:0.92rem;">{esc(a.get("filename",""))}</span>{flag_badges}<span style="margin-left:auto;font-size:0.75rem;color:#94a3b8;">📅 {esc(dt)}</span></div><div style="font-size:0.77rem;color:#94a3b8;margin-top:4px;display:flex;gap:1rem;flex-wrap:wrap;"><span>📐 {esc(a.get("drawing_type","Unknown"))}</span><span>🔩 {esc(a.get("part_name","Unknown"))}</span><span>🧱 {esc(a.get("material","Unknown"))}</span><span>⚙ {esc(a.get("estimated_complexity","Unknown"))}</span><span>🎯 {esc(a.get("confidence_score","?"))}%</span></div></div>', unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.button("👁 View", key=f"view_{aid}", use_container_width=True): st.session_state["viewing_analysis"] = aid; st.rerun()
                if st.button("🗑 Del",  key=f"del_{aid}",  use_container_width=True): st.session_state["pending_delete"]   = aid; st.rerun()
        if "viewing_analysis" in st.session_state:
            aid    = st.session_state["viewing_analysis"]; record = get_analysis_by_id(aid)
            if record:
                st.markdown("---"); st.markdown(f"### {esc(record['filename'])}")
                if st.button("✕ Close", key="close_view"): del st.session_state["viewing_analysis"]; st.rerun()
                render_result(record["result_json"], record["filename"], aid)
            else:
                st.warning("Analysis not found."); del st.session_state["viewing_analysis"]

# ── PAGE: COMPARE ─────────────────────────────────────────────────────────────
elif page == "🔍 Compare":
    if not limits.get("quote"):
        upgrade_prompt("Compare Drawings", "Pro", "$50/month"); st.stop()
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">🔍 Side-by-Side Comparison</div>', unsafe_allow_html=True)
    with st.spinner("Loading…"): analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)
    if len(analyses) < 2: st.info("Need at least 2 analyses to compare.")
    else:
        options = {f'{a.get("filename","")!s} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}
        keys = list(options.keys())
        cmp1, cmp2 = st.columns(2)
        with cmp1: sel1 = st.selectbox("Drawing A", keys, index=0, key="cmp_a")
        with cmp2: sel2 = st.selectbox("Drawing B", keys, index=min(1, len(keys)-1), key="cmp_b")
        if st.button("Compare →", type="primary", use_container_width=True):
            r1 = get_analysis_by_id(options[sel1]); r2 = get_analysis_by_id(options[sel2])
            if r1 and r2:
                d1 = r1["result_json"]; d2 = r2["result_json"]; st.markdown("---")
                compare_fields = [("Drawing Type","drawing_type"),("Part Name","part_name"),("Part Number","part_number"),("Revision","revision"),("Material","material"),("Material Spec","material_spec"),("Surface Finish","surface_finish"),("Scale","scale"),("Units","units"),("Complexity","estimated_complexity"),("Tol. Stack Risk","tolerance_stack_risk"),("Confidence","confidence_score")]
                h1, h2 = st.columns(2); h1.markdown(f"**A: {esc(r1['filename'])}**"); h2.markdown(f"**B: {esc(r2['filename'])}**")
                for label, key in compare_fields:
                    v1 = str(d1.get(key) or "—"); v2 = str(d2.get(key) or "—")
                    changed = v1.lower() != v2.lower()
                    bg = "background:#fffbeb;" if changed else ""
                    badge = " 🔄" if changed else ""
                    fc1, fc2 = st.columns(2)
                    with fc1: st.markdown(f'<div style="padding:5px 8px;border-radius:6px;{bg}font-size:0.85rem;margin-bottom:3px;"><span style="color:#94a3b8;font-size:0.72rem;">{label}{badge}</span><br><strong style="color:#0f172a;">{esc(v1)}</strong></div>', unsafe_allow_html=True)
                    with fc2: st.markdown(f'<div style="padding:5px 8px;border-radius:6px;{bg}font-size:0.85rem;margin-bottom:3px;"><span style="color:#94a3b8;font-size:0.72rem;">{label}{badge}</span><br><strong style="color:#0f172a;">{esc(v2)}</strong></div>', unsafe_allow_html=True)

# ── PAGE: REVIEW CHECKLIST ────────────────────────────────────────────────────
elif page == "✅ Review Checklist":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem;">✅ Pre-Machining Checklist</div>', unsafe_allow_html=True)
    with st.spinner("Loading…"): analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)
    if not analyses: st.info("No analyses yet.")
    else:
        options = {f'{a.get("filename","")!s} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}
        sel = st.selectbox("Select Drawing", list(options.keys()))
        if st.button("Generate Checklist", type="primary"):
            record = get_analysis_by_id(options[sel])
            if record:
                result = record["result_json"]; checks = build_checklist(result)
                passed = sum(1 for c in checks if c["status"] == "pass"); failed = sum(1 for c in checks if c["status"] == "fail"); warned = sum(1 for c in checks if c["status"] == "warn")
                sc1, sc2, sc3 = st.columns(3); sc1.metric("Passed", passed); sc2.metric("Warnings", warned); sc3.metric("Failed", failed)
                if failed == 0 and warned == 0: st.success("🟢 Ready to machine.")
                elif failed == 0: st.warning(f"🟡 {warned} item(s) to review.")
                else: st.error(f"🔴 {failed} item(s) must be resolved.")
                st.markdown("---")
                icons = {"pass": "✅", "fail": "❌", "warn": "⚠️"}
                for c in checks:
                    note = f' <span style="color:#94a3b8;font-size:0.8rem;">— {esc(c["note"])}</span>' if c["note"] else ""
                    st.markdown(f'<div class="diq-checklist-item"><span>{icons[c["status"]]}</span><span><strong>{esc(c["label"])}</strong>{note}</span></div>', unsafe_allow_html=True)

# ── PAGE: QUOTES ──────────────────────────────────────────────────────────────
elif page == "💰 Quotes":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">💰 Quote Portal</div>', unsafe_allow_html=True)
    qt1, qt2 = st.columns([3, 1])
    with qt2:
        if st.button("↩ Back to Analyze", use_container_width=True):
            st.session_state["force_page"] = "📤 Analyze"; st.rerun()
    try: quotes = get_quotes(user["id"])
    except Exception: quotes = []; st.warning("Quote table not set up yet.")
    if not quotes:
        st.markdown('<div class="diq-empty"><div style="font-size:2rem;">💰</div><h3>No quotes sent yet</h3><p>Generate a quote from any analysis.</p></div>', unsafe_allow_html=True)
    else:
        status_colors = {"pending": "#f59e0b", "approved": "#16a34a", "declined": "#ef4444", "revised": "#3b82f6"}
        for q in quotes:
            sc = status_colors.get(q.get("status", "pending"), "#94a3b8"); qd = q.get("quote_data") or {}
            qc1, qc2, qc3 = st.columns([4, 1, 1])
            with qc1:
                st.markdown(f'<div class="diq-history-card"><div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;"><strong style="color:#0f172a;">{esc(q.get("quote_number","N/A"))}</strong><span style="background:{sc}20;color:{sc};font-size:0.68rem;font-weight:600;padding:2px 8px;border-radius:4px;">{esc(q.get("status","pending").upper())}</span><span style="margin-left:auto;font-size:0.75rem;color:#94a3b8;">{esc(str(q.get("created_at",""))[:10])}</span></div><div style="font-size:0.78rem;color:#94a3b8;margin-top:4px;display:flex;gap:1rem;flex-wrap:wrap;"><span>👤 {esc(q.get("customer_name","Unknown"))}</span><span>✉️ {esc(q.get("customer_email",""))}</span><span>💵 ${qd.get("price_per_part",0):,.2f}/part · ${qd.get("total_job_cost",0):,.2f} total</span></div></div>', unsafe_allow_html=True)
            with qc2:
                app_url = os.getenv("APP_URL", "https://drawingiq.up.railway.app")
                st.markdown(f"[🔗 Share]({app_url}?quote_token={q.get('token','')})")
        st.markdown("---")
        st.markdown("### Quote Analytics")
        total_val = sum((q.get("quote_data") or {}).get("total_job_cost", 0) for q in quotes)
        approved  = [q for q in quotes if q.get("status") == "approved"]
        win_rate  = round(len(approved) / len(quotes) * 100) if quotes else 0
        qa1, qa2, qa3, qa4 = st.columns(4)
        qa1.metric("Total Quoted", f"${total_val:,.0f}"); qa2.metric("Quotes Sent", len(quotes)); qa3.metric("Approved", len(approved)); qa4.metric("Win Rate", f"{win_rate}%")

# ── PAGE: FAI REPORTS ─────────────────────────────────────────────────────────
elif page == "🔬 FAI Reports":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">🔬 First Article Inspection</div>', unsafe_allow_html=True)
    with st.spinner("Loading…"): analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)
    if not analyses: st.info("No analyses yet.")
    else:
        fa1, fa2 = st.columns([3, 1])
        with fa1: options = {f'{a.get("filename","")!s} — P/N: {a.get("part_number","?") or "?"} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}; sel_fai = st.selectbox("Select Drawing", list(options.keys()), key="fai_sel")
        with fa2: inspector = st.text_input("Inspector Name", key="fai_inspector")
        job_num_fai = st.text_input("Job / Work Order #", key="fai_job")
        record = get_analysis_by_id(options[sel_fai])
        if record:
            result = record["result_json"]; dims = result.get("dimensions", [])
            if not dims: st.warning("No dimensions extracted. Run a Deep Review analysis.")
            else:
                st.markdown("---"); st.markdown("### Enter Actual Measurements")
                measurements = []
                for i, d in enumerate(dims):
                    nominal = d.get("value", ""); tol = d.get("tolerance", ""); unit = d.get("unit", ""); feature = d.get("feature", ""); is_crit = d.get("is_critical", False)
                    mc1, mc2, mc3, mc4 = st.columns([3, 2, 2, 1])
                    with mc1: st.markdown(f"{'🔴 ' if is_crit else ''}`{esc(feature)}` — Nominal: **{esc(nominal)} {esc(unit)}** ±{esc(tol) if tol else 'N/A'}")
                    with mc2: actual_val = st.text_input("Actual", key=f"fai_act_{i}", placeholder=nominal, label_visibility="collapsed")
                    with mc3: fai_note  = st.text_input("Note",   key=f"fai_note_{i}", placeholder="Tool wear...", label_visibility="collapsed")
                    with mc4:
                        status = "pending"
                        if actual_val:
                            try:
                                act_f  = float(actual_val); nom_f = float(str(nominal).replace("Ø","").replace("R","").strip()); tol_f = float(str(tol).replace("±","").replace("+/-","").strip()) if tol else 0.1
                                status = "pass" if abs(act_f - nom_f) <= tol_f else "fail"
                                st.markdown(f"<div style='padding-top:1.8rem;font-size:1.2rem;'>{'✅' if status=='pass' else '❌'}</div>", unsafe_allow_html=True)
                            except Exception: status = "pending"
                    measurements.append({"feature": feature, "nominal": nominal, "tolerance": tol, "unit": unit, "actual": actual_val, "status": status, "note": fai_note, "critical": is_crit})
                st.markdown("---")
                if st.button("📋 Generate FAI Report", type="primary", use_container_width=True):
                    filled = [m for m in measurements if m.get("actual", "").strip()]
                    if not filled: st.error("Enter at least one actual measurement.")
                    else:
                        try: save_fai(options[sel_fai], user["id"], measurements, inspector, job_num_fai)
                        except Exception: pass
                        passed_m = [m for m in measurements if m.get("status") == "pass"]; failed_m = [m for m in measurements if m.get("status") == "fail"]
                        if failed_m: st.error(f"🔴 FAI FAILED — {len(failed_m)} dimension(s) out of tolerance.")
                        else: st.success(f"🟢 FAI PASSED — All {len(passed_m)} measured dimensions within tolerance.")
                        rc1, rc2, rc3 = st.columns(3); rc1.metric("Passed", len(passed_m)); rc2.metric("Failed", len(failed_m)); rc3.metric("Skipped", len([m for m in measurements if m.get("status")=="pending"]))

# ── PAGE: JOB TRACKER ─────────────────────────────────────────────────────────
elif page == "📈 Job Tracker":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">📈 Job Tracker — Actual vs Estimated</div>', unsafe_allow_html=True)
    jt_tab1, jt_tab2 = st.tabs(["📝 Log Actual Job", "📊 Performance Report"])
    with jt_tab1:
        with st.spinner("Loading…"): analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)
        if not analyses: st.info("No analyses yet.")
        else:
            jt_options = {f'{a.get("filename","")!s} — {a.get("part_name","?") or "?"} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}
            sel_jt = st.selectbox("Select Completed Job", list(jt_options.keys()))
            jc1, jc2, jc3 = st.columns(3)
            with jc1: act_machine = st.number_input("Actual Machine Hrs", 0.0, step=0.25, key="jt_mach"); act_labor = st.number_input("Actual Labor Hrs", 0.0, step=0.25, key="jt_lab")
            with jc2: act_material = st.number_input("Actual Material Cost ($)", 0.0, step=1.0, key="jt_mat"); act_total = st.number_input("Actual Total Cost ($)", 0.0, step=1.0, key="jt_tot")
            with jc3: jt_notes = st.text_area("Notes", placeholder="Setup issues, tool changes...", key="jt_notes", height=100)
            if st.button("💾 Save Job Actuals", type="primary", use_container_width=True):
                try: save_job_actual(jt_options[sel_jt], user["id"], act_machine, act_labor, act_material, act_total, jt_notes); st.success("Job actuals saved!")
                except Exception as e: st.error(f"Could not save: {e}")
    with jt_tab2:
        try: actuals = get_job_actuals(user["id"], limit=100)
        except Exception: actuals = []; st.warning("Job actuals table not set up yet.")
        if not actuals: st.info("No job actuals logged yet.")
        else:
            total_act = sum(a.get("actual_total", 0) for a in actuals)
            pa1, pa2, pa3 = st.columns(3)
            pa1.metric("Jobs Tracked", len(actuals)); pa2.metric("Total Actual $", f"${total_act:,.0f}"); pa3.metric("Avg Actual Hrs", f"{sum(a.get('actual_machine_hrs',0)+a.get('actual_labor_hrs',0) for a in actuals)/max(len(actuals),1):.1f} hr")
            st.markdown("---")
            for a in actuals:
                analysis = a.get("analyses") or {}
                st.markdown(f'<div class="diq-history-card"><div style="font-weight:600;color:#0f172a;">{esc(analysis.get("filename","Unknown"))}</div><div style="font-size:0.8rem;color:#94a3b8;margin-top:4px;display:flex;gap:1.5rem;flex-wrap:wrap;"><span>⚙ {a.get("actual_machine_hrs",0):.2f} hr</span><span>👷 {a.get("actual_labor_hrs",0):.2f} hr</span><span>🧱 ${a.get("actual_material_cost",0):,.2f}</span><span>💵 <strong>${a.get("actual_total",0):,.2f}</strong></span></div></div>', unsafe_allow_html=True)

# ── PAGE: SHOP SETUP ──────────────────────────────────────────────────────────
elif page == "🔧 Shop Setup":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;">🔧 Shop Setup</div>', unsafe_allow_html=True)
    ss_tab1, ss_tab2 = st.tabs(["🧱 Material Library", "⚙ Machine Profiles"])
    with ss_tab1:
        st.markdown("### 🧱 Material Price Library")
        with st.expander("➕ Add New Material", expanded=False):
            mc1, mc2, mc3 = st.columns(3)
            with mc1: mat_name = st.text_input("Material Name", placeholder="6061 Aluminum", key="mat_name"); mat_spec = st.text_input("Spec / Grade", placeholder="ASTM B221 T6511", key="mat_spec")
            with mc2: mat_form = st.text_input("Form", placeholder="Round Bar, Sheet", key="mat_form"); mat_price = st.number_input("Price ($/kg)", 0.0, value=5.0, step=0.1, key="mat_price")
            with mc3: mat_density = st.number_input("Density (kg/m³)", 100.0, value=2700.0, step=10.0, key="mat_density", help="Al=2700 · Steel=7850 · SS=8000 · Ti=4500"); mat_supplier = st.text_input("Supplier", placeholder="McMaster, Online Metals", key="mat_sup")
            mat_notes_inp = st.text_input("Notes", placeholder="Lead time, min order qty...", key="mat_notes")
            if st.button("💾 Save Material", type="primary", key="save_mat"):
                if mat_name:
                    try: save_material(user["id"], mat_name, mat_spec, mat_form, mat_price, mat_density, mat_supplier, mat_notes_inp); st.success(f"Saved {mat_name}!"); st.rerun()
                    except Exception as e: st.error(f"Could not save: {e}")
                else: st.error("Material name is required.")
        try: materials = get_materials(user["id"])
        except Exception: materials = []; st.warning("Materials table not set up. Run the SQL migration.")
        if materials:
            st.markdown(f"**{len(materials)} material(s) in your library**")
            for m in materials:
                mc1, mc2, mc3, mc4, mc5, mc6 = st.columns([3, 2, 2, 2, 2, 1])
                mc1.markdown(f"**{esc(m.get('name',''))}**"); mc2.markdown(f'<span style="font-size:0.82rem;color:#64748b;">{esc(m.get("spec","—"))}</span>', unsafe_allow_html=True); mc3.markdown(f'<span style="font-size:0.82rem;">{esc(m.get("form","—"))}</span>', unsafe_allow_html=True); mc4.markdown(f'<span style="font-family:JetBrains Mono,monospace;">${m.get("price_per_kg",0):.2f}</span>', unsafe_allow_html=True); mc5.markdown(f'<span style="font-family:JetBrains Mono,monospace;">{m.get("density_kg_m3",0):.0f} kg/m³</span>', unsafe_allow_html=True)
                with mc6:
                    if st.button("🗑", key=f"delmat_{m['id']}"):
                        try: delete_material(m["id"], user["id"]); st.rerun()
                        except Exception: st.error("Could not delete.")
        else: st.markdown('<div class="diq-empty"><h3>No materials yet</h3><p>Add your commonly used materials to speed up quoting.</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        with st.expander("⚡ Quick-Add Common Materials"):
            defaults = [("6061-T6 Aluminum","ASTM B221","Round Bar",4.50,2700,"Online Metals"),("304 Stainless Steel","ASTM A276","Round Bar",9.20,8000,"McMaster"),("4140 Steel","ASTM A108","Round Bar",3.80,7850,"Metals Depot"),("1018 Mild Steel","ASTM A108","Round Bar",2.40,7850,"Local supplier"),("Grade 5 Titanium","ASTM B265","Sheet",52.00,4430,"TMS Titanium"),("C360 Brass","ASTM B16","Round Bar",11.50,8500,"Online Metals"),("Delrin (POM)","—","Round Bar",8.00,1410,"McMaster"),("HDPE","—","Sheet",3.20,950,"McMaster")]
            for d in defaults:
                dname, dspec, dform, dprice, ddens, dsup = d
                if st.button(f"+ {dname}", key=f"qadd_{dname}"):
                    try: save_material(user["id"], dname, dspec, dform, dprice, ddens, dsup, ""); st.success(f"Added {dname}!"); st.rerun()
                    except Exception as e: st.error(str(e))
    with ss_tab2:
        st.markdown("### ⚙ Machine Capability Profiles")
        with st.expander("➕ Add New Machine", expanded=False):
            mach1, mach2, mach3 = st.columns(3)
            with mach1: mach_name = st.text_input("Machine Name", placeholder="Haas VF-2", key="mach_name"); mach_type = st.selectbox("Type", ["CNC Mill","CNC Lathe","Manual Mill","Manual Lathe","Surface Grinder","EDM","5-Axis","Swiss Screw","Other"], key="mach_type")
            with mach2: mach_tol = st.number_input("Best Tolerance (mm)", 0.001, value=0.05, step=0.001, format="%.4f", key="mach_tol"); mach_rate = st.number_input("Rate ($/hr)", 0.0, value=85.0, step=5.0, key="mach_rate")
            with mach3: mach_notes = st.text_area("Notes", placeholder="Year, controller...", key="mach_notes", height=80)
            if st.button("💾 Save Machine", type="primary", key="save_mach"):
                if mach_name:
                    try: save_machine(user["id"], mach_name, mach_type, mach_tol, mach_rate, mach_notes); st.success(f"Saved {mach_name}!"); st.rerun()
                    except Exception as e: st.error(f"Could not save: {e}")
                else: st.error("Machine name is required.")
        try: machines = get_machines(user["id"])
        except Exception: machines = []; st.warning("Machines table not set up.")
        if machines:
            st.markdown(f"**{len(machines)} machine(s) configured**")
            for m in machines:
                mm1, mm2, mm3, mm4, mm5 = st.columns([3, 2, 2, 2, 1])
                mm1.markdown(f"**{esc(m.get('name',''))}** <span style='font-size:0.78rem;color:#64748b;'>{esc(m.get('machine_type',''))}</span>", unsafe_allow_html=True); mm2.markdown(f'<span style="font-size:0.82rem;">±{m.get("tolerance_mm",0):.4f} mm</span>', unsafe_allow_html=True); mm3.markdown(f'<span style="font-family:JetBrains Mono,monospace;">${m.get("rate_per_hr",0):.0f}/hr</span>', unsafe_allow_html=True); mm4.markdown(f'<span style="font-size:0.78rem;color:#64748b;">{esc(m.get("notes",""))}</span>', unsafe_allow_html=True)
                with mm5:
                    if st.button("🗑", key=f"delmach_{m['id']}"):
                        try: delete_machine(m["id"], user["id"]); st.rerun()
                        except Exception: st.error("Could not delete.")
        else: st.markdown('<div class="diq-empty"><h3>No machines yet</h3><p>Add your machines to enable tolerance checks.</p></div>', unsafe_allow_html=True)

# ── PAGE: TEAM ────────────────────────────────────────────────────────────────
elif page == "👥 Team":
    if not limits.get("team"): upgrade_prompt("Team Workspaces", "Pro", "$50/month"); st.stop()
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem;">👥 Team Workspaces</div>', unsafe_allow_html=True)
    workspaces = get_user_workspaces(user["id"]); col1, col2 = st.columns([2, 1])
    with col2:
        with st.expander("+ Create Workspace"):
            ws_name = st.text_input("Workspace Name", placeholder="Acme Mfg – QA Team")
            if st.button("Create", type="primary"):
                if ws_name: create_workspace(user["id"], ws_name); st.success(f"Workspace '{ws_name}' created!"); st.rerun()
    if not workspaces: st.markdown('<div class="diq-empty"><h3>No workspaces yet</h3></div>', unsafe_allow_html=True)
    else:
        for ws_entry in workspaces:
            wsd = ws_entry.get("workspaces") or {}; ws_id = wsd.get("id"); ws_name = wsd.get("name", "Unnamed"); my_role = ws_entry.get("role", "member")
            with st.expander(f"🏢 {ws_name}  ({my_role})", expanded=True):
                members = get_workspace_members(ws_id)
                for m in members:
                    p = m.get("profiles") or {}; name = p.get("full_name") or p.get("email", "Unknown"); email = p.get("email", ""); role = m.get("role", "member"); initials = "".join([x[0].upper() for x in name.split()[:2]])
                    ca, cb = st.columns([4, 1])
                    with ca: st.markdown(f'<div class="diq-member-row"><div class="diq-member-avatar">{esc(initials)}</div><div style="flex:1"><div style="font-weight:500;color:#0f172a;font-size:0.88rem;">{esc(name)}</div><div style="font-size:0.76rem;color:#64748b;">{esc(email)}</div></div><span class="diq-role-badge role-{esc(role)}">{esc(role)}</span></div>', unsafe_allow_html=True)
                    with cb:
                        uid = p.get("id")
                        if my_role in ("owner", "admin") and uid and uid != user["id"]:
                            if st.button("Remove", key=f"rm_{ws_id}_{uid}"): remove_member(ws_id, uid); st.rerun()
                if my_role in ("owner", "admin"):
                    st.markdown("---"); i1, i2, i3 = st.columns([3, 1, 1])
                    with i1: inv_email = st.text_input("Invite by email", key=f"inv_{ws_id}", placeholder="engineer@company.com", label_visibility="collapsed")
                    with i2: inv_role  = st.selectbox("Role", ["member","admin","viewer"], key=f"invr_{ws_id}", label_visibility="collapsed")
                    with i3:
                        if st.button("Invite", key=f"invbtn_{ws_id}", type="primary"):
                            try: invite_member(ws_id, user["id"], inv_email, inv_role); st.success(f"Invited {inv_email}!"); st.rerun()
                            except ValueError as e: st.error(str(e))

# ── PAGE: BILLING ─────────────────────────────────────────────────────────────
elif page == "💳 Billing":
    render_pricing_page(user["id"], profile.get("email", ""), plan)
    st.markdown("---"); st.markdown("### Your Usage"); stats = get_usage_stats(user["id"])
    bc1, bc2, bc3 = st.columns(3); bc1.metric("This Month", stats.get("analyses_this_month", 0)); bc2.metric("All Time", stats.get("analyses_total", 0))
    lim = stats.get("limit_this_month", 5); bc3.metric("Monthly Limit", lim if lim < 99999 else "∞")

# ── PAGE: ACCOUNT ─────────────────────────────────────────────────────────────
elif page == "⚙ Account":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem;">⚙ Account Settings</div>', unsafe_allow_html=True)
    ac1, ac2 = st.columns(2)
    with ac1:
        st.markdown("### Profile")
        new_name    = st.text_input("Full Name",          value=profile.get("full_name") or "")
        new_company = st.text_input("Company",            value=profile.get("company") or "")
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        if st.button("Save Profile", type="primary"): update_profile(user["id"], {"full_name": new_name, "company": new_company}); refresh_profile(); st.success("Profile updated!")
        st.markdown("### Analysis Defaults")
        pref_disc   = st.selectbox("Default Discipline",   DISCIPLINES,    index=DISCIPLINES.index(st.session_state["pref_discipline"]) if st.session_state["pref_discipline"] in DISCIPLINES else 1)
        pref_detail = st.select_slider("Default Detail Level", DETAIL_LEVELS, value=st.session_state["pref_detail"])
        if st.button("Save Defaults"): st.session_state["pref_discipline"] = pref_disc; st.session_state["pref_detail"] = pref_detail; st.success("Saved!")
    with ac2:
        st.markdown("### Current Plan"); lim = get_plan_limits(plan)
        st.markdown(f"**Plan:** {plan.title()}"); st.markdown(f"**Analyses:** {profile.get('analyses_this_month',0)} / {lim['analyses_per_month']} this month"); st.markdown(f"**Batch size:** {lim['batch_size']} drawings"); st.markdown(f"**PDF:** {'✓' if lim['pdf'] else '✗'}"); st.markdown(f"**Team:** {'✓' if lim['team'] else '✗'}"); st.markdown(f"**Export:** {'✓' if lim['export'] else '✗'}")
        st.markdown("### API Keys"); st.info("🔒 Managed via environment variables.")
    st.markdown("---"); st.markdown("### Danger Zone")
    with st.expander("Delete Account"):
        st.error("Permanently deletes account and all analyses.")
        if st.text_input("Type DELETE to confirm") == "DELETE":
            if st.button("Delete My Account", type="primary"): st.warning("Contact support@drawingiq.com to complete deletion.")

# ── PAGE: TERMS ───────────────────────────────────────────────────────────────
elif page == "📜 Terms & Privacy":
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:1rem;">📜 Terms of Service & Privacy Policy</div>', unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("### Terms of Service")
        st.markdown("""
**1. Service** — DrawingIQ provides AI-powered engineering drawing analysis. Results are reference tools only.

**2. Accuracy** — Always verify AI results before machining. DrawingIQ is not liable for manufacturing errors or scrapped parts.

**3. Payment** — Subscriptions billed monthly. Cancel anytime. No refunds for partial months.

**4. Your Data** — Your drawings are stored securely. We never share your data with third parties.

**5. Copyright** — Your drawings remain your property.

**6. Prohibited Use** — Do not use DrawingIQ for illegal purposes.

**Contact:** support@drawingiq.com
        """)
    with tc2:
        st.markdown("### Privacy Policy")
        st.markdown("""
**What we collect:** Email, company name, uploaded drawings, analysis results, usage statistics.

**How we use it:** To provide the DrawingIQ service and improve AI accuracy.

**What we never do:** Sell your data, share drawings with other users, store credit card numbers, use your data for advertising.

**Your rights:** Delete your account and all data at any time. Export your history at any time.

**Security:** All data encrypted at rest and in transit. Hosted on Supabase (SOC 2 compliant).

**Contact:** support@drawingiq.com
        """)
    st.markdown("---")
    st.caption("© 2026 DrawingIQ. All rights reserved.")