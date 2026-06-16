# Your steps — Veritas (H0) — written for zero assumptions

I (Claude) have built and tested everything that runs on your machine: the
database design, the data loader, the whole website, and the background worker.
What's left is the stuff only **you** can do because it needs **your accounts and
your face/voice**: turning on the cloud, putting the site online, and recording
the video.

Pattern for the whole list: **you click; then paste me one thing; I do the rest.**
Anything in `code font` is a value to copy. When a step says "→ tell Claude," come
back to this chat and paste what it asks for.

Time estimate: ~2–3 focused hours, most of it waiting for AWS to create things.

---

## What is already done (you don't need to touch any of this)
- ✅ Database schema (`db/schema.sql`) — built, applied, tested.
- ✅ Data loader (`ingest/ingest.py`) — loads your real cases; counts verified.
- ✅ The website (`web/`) — 6 screens, builds clean, tested against real data.
- ✅ Background worker (`ingest/worker.py`) — the "queue a new run" feature, tested.
- ✅ Architecture diagram, submission text, demo script — in `docs/`.

You are wiring this proven thing to the cloud. Nothing here is risky.

---

## Step 1 — Redeem your two credit codes (10 min)

**Why:** these pay for the database (AWS) and the design tool (v0). Both are free
to you.

1. **AWS $100:** create a normal AWS account at https://aws.amazon.com (you'll
   need a card; the $100 credit covers this hackathon). Then go to
   https://aws.amazon.com/awscredits/ and paste your code `PC3OFBUUZX9MF55`.
   - ⚠️ Apply it to your **main billing account**, not a trial.
2. **v0 $30:** sign up at https://vercel.com/signup, then open v0 at
   https://v0.app → Settings → Billing → paste `DEVPOSTV030`.

→ Nothing to tell me yet. Just confirm both codes show as redeemed.

---

## Step 2 — Put the code on GitHub (10 min)

**Why:** Vercel deploys websites *from* GitHub, and the hackathon needs a public
repo.

1. Go to https://github.com/new. Repository name: `veritas` (or anything).
   Visibility: **Public**. Do **not** add a README/license (we have them). Create.
2. GitHub shows you a URL like `https://github.com/3sk1nt4n/veritas.git`.

→ **Tell me that URL.** I'll push all the code to it for you (one command on my
side; I won't push anything public without your go-ahead).

---

## Step 3 — Create the Aurora database (30 min, mostly waiting)

**Why:** this is the AWS database the whole project is judged on.

1. Sign in to AWS, search for **RDS**, open it. Top-right: set your **Region**
   (pick one near you, e.g. `us-east-1`). Remember which one.
2. Click **Create database**.
3. Choose:
   - **Standard create**
   - Engine: **Amazon Aurora**
   - Edition: **Aurora PostgreSQL-Compatible Edition**
   - Version: leave the default (any 15.x/16.x).
4. Templates: **Dev/Test**.
5. **Cluster identifier:** `veritas-db`.
6. **Credentials:** Master username `postgres`. Choose **Self managed** password,
   set one you'll keep (e.g. a long random string). **Write it down.**
7. **Cluster storage / capacity:** choose **Serverless v2**. Min capacity: `0.5`
   ACU, Max: `2` ACU (cheap; plenty for the demo).
8. **Connectivity:**
   - **Public access: Yes** (so Vercel and your machine can reach it — simplest
     path for a hackathon).
   - VPC security group: **Create new**, name it `veritas-sg`.
9. Leave the rest as defaults. Click **Create database**. Wait ~10–15 min until
   status is **Available**.
10. **Open the firewall:** RDS → your `veritas-db` → Connectivity & security →
    click the **VPC security group** → **Inbound rules** → **Edit** → **Add rule**
    → Type **PostgreSQL** (port 5432), Source **Anywhere-IPv4 (0.0.0.0/0)** →
    Save. (Fine for a demo; we can tighten later.)
11. On the `veritas-db` page, copy the **Endpoint** of the *writer* instance — it
    looks like `veritas-db.cluster-xxxx.us-east-1.rds.amazonaws.com`.

→ **Tell me:** the **endpoint**, the **master password**, and the **region**.
I'll build your connection string, load the schema, and ingest all the cases into
Aurora for you, and confirm the row counts. (You can also paste them as one line:
`endpoint=… password=… region=…`.)

> Security note: a DB password is a secret. It's okay to paste here so I can wire
> it up; just don't post it anywhere public, and you can rotate it after the
> hackathon in the RDS console.

---

## Step 4 — I load Aurora (you do nothing)

Once you give me Step 3's values, I will:
- apply `db/schema.sql` to Aurora,
- ingest the 3 real cases,
- run the trust-layer queries to confirm everything matches,
- give you the exact `DATABASE_URL` to paste into Vercel next.

---

## Step 5 — Deploy the website to Vercel (15 min)

**Why:** this is the public app + the "front end on Vercel" the rules require.

1. Go to https://vercel.com → **Add New… → Project** → **Import** your `veritas`
   GitHub repo.
2. **Important — Root Directory:** click **Edit** and set it to **`web`** (our
   Next.js app lives in the `web/` folder).
3. **Environment Variables** (I'll give you the exact values in Step 4):
   - `DATABASE_URL` = `postgresql://postgres:YOURPASS@YOUR-ENDPOINT:5432/postgres`
   - `PGSSL` = `require`
4. Click **Deploy**. Wait ~2 min. You get a public URL like
   `https://veritas-xxxx.vercel.app`.
5. **Find your Vercel Team ID** (needed for submission): Vercel → your avatar →
   **Settings** → **General** → **Team ID** (copy it).

→ **Tell me the live URL** so I can sanity-check every page loads against Aurora.

---

## Step 6 — (Optional, "go big") the live "new run" worker

The website's **New run** feature works the moment the worker process is running.
For the demo you can run the worker on your own machine (it talks to Aurora):

```bash
cd /home/sansforensics/veritas-h0
DATABASE_URL="<the Aurora URL from Step 4>" .venv/bin/python ingest/worker.py --loop
```

Leave it running while you record; queue a run in the UI and the 16-step bar
moves. (Real evidence-from-S3 upload is a production extra; the demo uses the
seeded captures. Skip this entire step if you're short on time — the read app is
the star.)

---

## Step 7 — Record the demo video (45 min) — **this is the big one**

**Why:** the most heavily weighted submission artifact. Under 3 minutes, YouTube.

- Open `docs/DEMO-SCRIPT.md` — it's a word-for-word, timed script (2:45).
- Record your screen + voice (Loom, OBS, or even your phone over the screen).
- Must show: the live Vercel URL, the "AI overruled" moment, the proof chain, the
  cross-case pivot, one live SQL query, and **the AWS Aurora console**.
- Upload to YouTube as **Public** or **Unlisted** (not Private).

→ Tell me the YouTube link; I'll help slot it into the submission.

---

## Step 8 — The AWS proof screenshot (2 min)

In the AWS RDS console, screenshot the `veritas-db` page showing it's an **Aurora
PostgreSQL Serverless v2** cluster, status Available. Save it — the rules require
a screenshot proving AWS database usage.

---

## Step 9 — Submit on Devpost (15 min)

Go to the H0 project page → Submit. You'll paste:
- [ ] **Text description** — I'll hand you the final version (`docs/SUBMISSION.md`).
- [ ] **Demo video** link (Step 7).
- [ ] **Published Vercel URL** + **Vercel Team ID** (Step 5).
- [ ] **Architecture diagram** — `docs/architecture.png` (done).
- [ ] **AWS screenshot** (Step 8).
- [ ] **Public GitHub repo** link (Step 2).
- [ ] (Bonus) a short blog/LinkedIn post with **#H0Hackathon** — I can draft it.

**Deadline: 2026-06-29, 5:00 PM PT. Submit a day early.**

---

## Separate track — Qwen hackathon (not part of H0)

Whenever Jade sends your DashScope key:
```bash
cd /home/sansforensics/Sentinel-Ensemble-Qwen
export SIFT_LLM_PROVIDER=qwen DASHSCOPE_API_KEY=sk-... SIFT_DEFAULT_MODEL=qwen-max
python3 scripts/qwen_smoke.py        # should print a Qwen reply
```
And when you make that repo public on GitHub, tell me the URL and I'll push it.
(Qwen deadline is 2026-07-09 — after H0. Do H0 first.)

---

### The shortest version
1. Redeem 2 codes. 2. Make a public GitHub repo → **tell me the URL**.
3. Create Aurora Serverless v2, open port 5432 → **tell me endpoint+password+region**.
4. I load the data + give you `DATABASE_URL`. 5. Import repo on Vercel (root =
`web`), paste the 2 env vars → **tell me the live URL**. 6. Record the video from
the script. 7. Screenshot the AWS console. 8. Submit on Devpost.
