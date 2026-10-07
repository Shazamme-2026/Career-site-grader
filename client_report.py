"""
Client-facing "Website Opportunity Report".

Turns a stored grade into a short, plain-English, marketing-led document a
non-technical client can read in two minutes: where they stand, what has
changed in the world, their biggest opportunities, and what amazing looks like
with Shazamme. No check names, no jargon, no code.

build_html(report, logo_src=None) -> str      print-ready A4 HTML
render_pdf(html) -> bytes                     Chromium PDF via Playwright
"""

import html as _html
import os
import sys
from datetime import date

BRAND_SITE = os.environ.get('BRAND_SITE', 'https://www.shazamme.com')
BRAND_EMAIL = os.environ.get('BRAND_EMAIL', 'hello@shazamme.com')
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL',
                                 'https://career-site-grader-production.up.railway.app')


def _e(v) -> str:
    return _html.escape(str(v if v is not None else ''), quote=True)


def _clip(text, n=230) -> str:
    text = (text or '').strip()
    return text if len(text) <= n else text[:n - 1].rstrip() + '…'


# --- Plain-English translation of the grader's pillars -----------------------

PILLAR_LABELS = {
    'SEO & Discoverability': ('Being found on Google',
                              'Do employers and candidates find you when they search?'),
    'GEO & AI Visibility': ('Being found by AI assistants',
                            'Do ChatGPT, Perplexity and Google AI recommend you?'),
    'Candidate Experience': ('Candidate experience',
                             'Can a candidate find and apply for a job in two minutes on a phone?'),
    'Employer Brand & Content': ('Your story and employer brand',
                                 'Does the site show who you are and why people should work with you?'),
    'Technical Performance': ('Speed and reliability',
                              'Does the site load fast enough to keep visitors?'),
    'Conversion & Engagement': ('Turning visitors into candidates and clients',
                                'Are visitors given a clear next step, and captured if they are not ready?'),
    'Security & Trust': ('Trust and security', 'Does the site look and behave like a safe, credible business?'),
    'User Experience': ('Ease of use', 'Can visitors find what they came for without effort?'),
    'Content Quality': ('Content that convinces', 'Does the content answer real questions and build confidence?'),
}


# --- Plain-English translation of the grader's checks ------------------------
# check name -> (title, why it matters to the business, what great looks like)

_SECTOR = ('Pages for every sector you recruit in',
           "Employers search for 'IT recruitment agency'. Candidates search for 'IT jobs'. "
           'Without a page for each sector, on both sides, you are invisible to both.',
           'A page per sector for employers and one for jobseekers, each with live jobs, '
           'your consultants and answers to the questions people actually ask.')
_SPEED = ('A faster website',
          'Every extra second of loading loses visitors, and Google ranks slow sites lower. '
          'Most candidates are on a phone, often on mobile data.',
          'Pages that load in under two seconds on a phone, every time.')
_ACCESS = ('A site everyone can use',
           'Around one in five people lives with a disability. An accessible site reaches more '
           'candidates and reduces legal risk.',
           'Readable text, labelled forms and images, and a site that works with a keyboard '
           'or screen reader.')
_FIND = ('Making sure Google can find every page',
         'If Google cannot find or index a page, nobody can. Simple housekeeping decides '
         'whether your best pages ever appear.',
         'Every important page listed, indexable and pointing to one clean address.')
_HEADINGS = ('Clear, specific page structure',
             'Google and AI assistants read your headings first to understand each page. '
             'Vague or repeated headings leave them guessing.',
             'One clear headline per page, each unique and specific to that page.')
_JOBS_OWN = ('Jobs on your own website',
             'Jobs hosted on another domain, or inside an embedded widget, earn search traffic '
             'for someone else, not you.',
             'Every job published as its own page on your own domain, with its own address.')
_APPLY = ('Finding and applying for jobs fast',
          'Candidates expect to find a job and apply in under two minutes from their phone. '
          'Friction here is where applications are lost.',
          'Instant search with filters and a one-tap apply that works from mobile.')
_CAPTURE = ('Capturing candidates who are not ready yet',
            'Most visitors do not apply on their first visit. Without job alerts or a simple '
            'sign-up, they leave and never come back.',
            'Job alerts and a one-field sign-up so you stay in touch with passive candidates.')
_FAQ = ('Answers to the questions people ask',
        "Google and AI assistants favour sites that answer real questions, like "
        "'How do I register?' or 'What do you charge?'",
        'Short FAQ sections on key pages, written so Google and AI can quote them.')
_SOCIAL = ('Looking great when shared',
           'Jobs and pages shared on LinkedIn or WhatsApp show a preview. A blank or broken '
           'preview gets ignored.',
           'A proper image, title and summary on every page when it is shared.')
_SECURE = ('A secure, trusted site',
           'Browsers warn visitors about sites that are not fully secure, and candidates '
           'will not hand their CV to a site they do not trust.',
           'Fully secure connections and modern security settings across the whole site.')
_STORY = ('Real people and real stories',
          'Candidates and clients trust faces and stories over marketing copy. Culture and '
          'team content is what makes someone choose you.',
          'Consultant profiles, team stories and testimonials on the pages that matter.')
_SITEMAP = _FIND

CHECKS = {
    'Recruitment Content Streams': _SECTOR,
    'Industry & Sector Pages': _SECTOR,
    'Local / Location Schema': (
        'Showing up in local searches',
        "Searches like 'recruitment agency near me' go to sites that tell Google exactly "
        'where they operate. Most agencies never set this up.',
        'Your locations clearly marked so Google and Maps surface you for local searches.'),
    'Content Structure': (
        'Content that AI assistants can read',
        "ChatGPT, Perplexity and Google's AI answers pull from pages with clear headings and "
        'direct answers. Long, unstructured text gets skipped.',
        'Clear headings, short sections and direct answers, so AI assistants quote you.'),
    'AEO / Answer-Engine Readiness': (
        'Being the answer AI gives',
        'More and more candidates and employers ask an AI assistant instead of searching. '
        'Sites that answer questions directly become the recommendation.',
        'Each key page answers one clear question in its first paragraph.'),
    'AI Crawler Access': (
        'Letting AI assistants in',
        'If AI crawlers are blocked, ChatGPT and Perplexity cannot read your site, so they '
        'can never recommend you.',
        'AI crawlers explicitly welcomed, so you appear in AI answers.'),
    'llms.txt File': (
        'A guide for AI assistants',
        'AI tools look for a simple file that explains who you are and what you do. Almost '
        'no agencies have one yet, which makes it an easy win.',
        'A short, plain-English summary file that AI assistants read first.'),
    'llm-info File': (
        'A guide for AI assistants',
        'AI tools look for a simple file that explains who you are and what you do. Almost '
        'no agencies have one yet, which makes it an easy win.',
        'A short, plain-English summary file that AI assistants read first.'),
    'FAQ & Q&A Schema': _FAQ,
    'FAQ Content': _FAQ,
    'Entity & Authority': (
        'Being recognised as a trusted brand',
        'Google and AI tools rank organisations they recognise: consistent details, reviews, '
        'profiles and mentions elsewhere on the web.',
        'Consistent company details, reviews and social profiles all connected to your site.'),
    'Crawlable Content (JS-render)': (
        'Jobs that search engines can actually see',
        'If your jobs only appear after scripts run, Google and AI tools may never see them.',
        'Jobs published as real pages that any search engine or AI can read.'),
    'Job Board: Crawlable Listings': _JOBS_OWN,
    'Job Board: Indexable Embed': _JOBS_OWN,
    'Job Board: Same-Domain Hosting': _JOBS_OWN,
    'Job URL & Metadata': (
        'Every job as its own page',
        'A job with its own address and title can be found on Google, shared and tracked. '
        'Jobs buried in a list cannot.',
        'Each job on its own page with a clear title, location and salary.'),
    'Schema / Structured Data': (
        'Rich job listings in Google',
        'Google shows jobs with salary, location and logo directly in results, but only for '
        'sites that provide the detail. Those listings get up to three times more clicks.',
        'Every job and page marked up automatically so Google shows the rich version.'),
    'Structured Data Validity': (
        'Rich job listings in Google',
        'Job detail with errors is ignored by Google, so you lose the rich listings you '
        'think you have.',
        'Clean, valid job detail on every listing, checked automatically.'),
    'Video Content': (
        'Video that shows who you are',
        'Candidates and clients trust faces over text. Video lifts application intent by '
        'around a third.',
        'A short team or culture video on your homepage and key pages.'),
    'Call-to-Action Strength': (
        'A clear next step on every page',
        "Visitors who are not told what to do next leave. Every page needs an obvious "
        "'search jobs', 'apply' or 'talk to us'.",
        'One prominent action for candidates and one for employers on every page.'),
    'Job Alerts & Lead Capture': _CAPTURE,
    'Lead Capture / Newsletter': _CAPTURE,
    'Live Chat & Chatbot': (
        'Answering candidate questions instantly',
        'Candidates have questions at 9pm. If nobody answers, they move on. Chat cuts '
        'drop-off by up to 40%.',
        'An AI assistant that answers questions, suggests jobs and books calls 24/7.'),
    'Social Sharing & Referrals': (
        'Making jobs easy to share',
        'Referrals are your cheapest, best-quality hires. Jobs that cannot be shared in a '
        'tap do not travel.',
        'One-tap sharing on every job to LinkedIn, WhatsApp and email.'),
    'Social Links & Sharing': _SOCIAL,
    'Open Graph / Social Tags': _SOCIAL,
    'og:image': _SOCIAL,
    'Social Presence': (
        'Connected to your social channels',
        'Candidates check LinkedIn before they apply. A site with no visible social presence '
        'feels smaller than it is.',
        'Live social links and recent activity visible on the site.'),
    'Social Proof & Reviews': (
        'Proof that clients and candidates rate you',
        'Reviews and testimonials are the first thing a new client or candidate looks for. '
        'Without them, you are asking people to take your word for it.',
        'Google reviews, client logos and candidate testimonials on the pages that sell.'),
    'Heading Hierarchy': _HEADINGS,
    'Heading Structure': _HEADINGS,
    'H1 Heading': _HEADINGS,
    'Duplicate Headings': (
        'Pages competing with each other',
        'When several pages use the same headings, Google cannot tell which one to rank, '
        'so none of them rank well.',
        'Every page with its own specific headline.'),
    'Title Tag': (
        'Better headlines in Google results',
        'Your page title and description are your advert in Google. Weak ones get skipped '
        'even when you rank.',
        'Compelling, specific titles and descriptions on every page.'),
    'Meta Description': (
        'Better headlines in Google results',
        'Your page title and description are your advert in Google. Weak ones get skipped '
        'even when you rank.',
        'Compelling, specific titles and descriptions on every page.'),
    'Lighthouse Performance': _SPEED,
    'Core Web Vitals': _SPEED,
    'Page Speed (TTFB)': _SPEED,
    'Server Response (TTFB)': _SPEED,
    'Render-Blocking Scripts': _SPEED,
    'Image Optimization': _SPEED,
    'Image Dimensions': _SPEED,
    'Caching Strategy': _SPEED,
    'Content Compression': _SPEED,
    'Font Loading': _SPEED,
    'Resource Hints': _SPEED,
    'HTTP/2+': _SPEED,
    'Mobile Readiness': (
        'A great experience on a phone',
        'Most candidates browse jobs on their phone, often in the evening. A site that is '
        'fiddly on mobile loses them.',
        'Designed for the phone first: big touch targets, fast pages, simple apply.'),
    'Apply Flow & Job Search': _APPLY,
    'Job Search & Filters': _APPLY,
    'Search Functionality': _APPLY,
    'Form Usability': (
        'Forms people actually finish',
        'Long or confusing forms are where applications and enquiries die.',
        'Short forms with clear labels, and apply with a CV upload or LinkedIn in one step.'),
    'Image Alt Text': _ACCESS,
    'Accessibility (WCAG)': _ACCESS,
    'Semantic HTML & ARIA': _ACCESS,
    'Navigation & Structure': (
        'Easy to find your way around',
        'Visitors give a site a few seconds. If the menu does not make the next step '
        'obvious, they leave.',
        'A simple menu split for candidates and employers, with jobs one tap away.'),
    'Navigation': (
        'Easy to find your way around',
        'Visitors give a site a few seconds. If the menu does not make the next step '
        'obvious, they leave.',
        'A simple menu split for candidates and employers, with jobs one tap away.'),
    'Internal Linking': (
        'Pages that lead to each other',
        'Good sites guide visitors from a sector page to its jobs to the consultant. Dead '
        'ends lose people and weaken your Google ranking.',
        'Every sector, job and consultant page linked together.'),
    'EVP & Pay Transparency': (
        'Telling candidates why they should choose you',
        'Candidates want to know what they get: pay, flexibility, progression. Sites that '
        'say it clearly win the application.',
        'A clear statement of what you offer, with salary ranges shown on jobs.'),
    'Culture & Team Content': _STORY,
    'Employee Stories & Testimonials': _STORY,
    'DE&I Commitment': (
        'Showing your commitment to inclusion',
        'A visible commitment to inclusion widens your candidate pool and matters to the '
        'employers you want to win.',
        'A short, genuine statement with evidence, not a slogan.'),
    'Visual Brand Assets': (
        'A consistent, professional look',
        'First impressions are formed in a second. An inconsistent look makes a good '
        'agency seem smaller than it is.',
        'A consistent logo, colours and imagery across every page.'),
    'Analytics & Tracking': (
        'Knowing what is working',
        'Without measurement you cannot tell which jobs, pages or campaigns bring '
        'candidates and clients.',
        'Simple analytics that show where applications and enquiries come from.'),
    'HTTPS / SSL': _SECURE,
    'HTTPS Trust Signal': _SECURE,
    'Mixed Content': _SECURE,
    'Strict-Transport-Security': _SECURE,
    'Content-Security-Policy': _SECURE,
    'X-Frame-Options': _SECURE,
    'X-Content-Type-Options': _SECURE,
    'Referrer-Policy': _SECURE,
    'Permissions-Policy': _SECURE,
    'XML Sitemap': _SITEMAP,
    'Sitemap.xml': _SITEMAP,
    'robots.txt Health': _SITEMAP,
    'Indexability': _SITEMAP,
    'Canonical URL': _SITEMAP,
    'Privacy & Cookie Policy': (
        'Privacy done properly',
        'Candidates hand you personal data. A clear privacy policy is expected, and in many '
        'places required.',
        'A clear privacy and cookie policy, linked from every page.'),
    'WordPress Core Currency': (
        'An up-to-date, secure platform',
        'Out-of-date software is the most common way sites get hacked, and a hacked site '
        'can disappear from Google overnight.',
        'A platform that is updated and secured for you, automatically.'),
    'WordPress Plugin Currency': (
        'An up-to-date, secure platform',
        'Out-of-date software is the most common way sites get hacked, and a hacked site '
        'can disappear from Google overnight.',
        'A platform that is updated and secured for you, automatically.'),
    'Content Depth': (
        'Content that convinces',
        'Thin pages do not rank and do not persuade. Employers and candidates want enough '
        'detail to trust you.',
        'Sector and service pages with real substance: who, what, where, and proof.'),
    'Content Quality': (
        'Content that convinces',
        'Thin pages do not rank and do not persuade. Employers and candidates want enough '
        'detail to trust you.',
        'Sector and service pages with real substance: who, what, where, and proof.'),
    'Structured Content': (
        'Content that AI assistants can read',
        "ChatGPT, Perplexity and Google's AI answers pull from pages with clear headings and "
        'direct answers. Long, unstructured text gets skipped.',
        'Clear headings, short sections and direct answers, so AI assistants quote you.'),
    'ATS Platform Detection': (
        'Jobs connected to your recruitment system',
        'When jobs flow automatically from your recruitment system to your site, they are '
        'always current and consultants never re-key them.',
        'Jobs published and removed automatically from your recruitment system.'),
}


# --- Plain-English translation of the "Shazamme advantage" items -------------
# feature name -> (the gap in the client's words, what you get, plain description)

STAT_OVERRIDES = {
    'Auto Schema Engine': 'Up to 3× more clicks from Google',
    'GEO-Ready Out of the Box': 'Shows up in AI answers about jobs and agencies',
}

ADVANTAGE = {
    'Auto Schema Engine': (
        'Plain job listings in Google',
        'Rich Google job listings, automatically',
        'Every job and page carries the detail Google needs to show salary, location and your '
        'logo right in the results. Nothing for you to set up or maintain.'),
    'Streamlined Career Application Flow': (
        'Applications lost to friction',
        'Apply in under two minutes, from any phone',
        'A short, mobile-first application that connects straight to your recruitment system '
        'and keeps candidates moving to the finish.'),
    'AI-Powered Job Search & One-Click Apply': (
        'Hard to find and apply for jobs',
        'Instant job search and one-tap apply',
        'Candidates find the right job in seconds and apply with a CV or LinkedIn in one step, '
        'straight into your recruitment system.'),
    'Intelligent Job Alert Engine': (
        'Visitors leave and never come back',
        'Job alerts that bring candidates back',
        'Candidates subscribe in one step and hear the moment a matching job is posted, so a '
        'visit that did not convert today still becomes a placement.'),
    'AI Recruitment Chatbot': (
        'Nobody answering at 9pm',
        'An AI assistant on every page',
        'Answers candidate and client questions, suggests jobs and books calls around the '
        'clock, without your consultants lifting a finger.'),
    'GEO-Ready Out of the Box': (
        'Invisible to AI assistants',
        'Recommended by ChatGPT and Google AI',
        'Every Shazamme site is built so AI assistants can read, trust and recommend it. When '
        'someone asks who to work with, your agency is the answer.'),
    'Mobile-First Architecture': (
        'A fiddly experience on a phone',
        'Designed for the phone first',
        'Fast pages, big touch targets and a simple apply, built for the way candidates '
        'actually look for jobs.'),
    'Employer Brand Content Studio': (
        'No story, no faces, no video',
        'Your story, told properly',
        'Team video, consultant profiles and culture content that make candidates and '
        'clients choose you over the agency next door.'),
    'EVP & Transparency Framework': (
        'Candidates cannot see what they get',
        'A clear reason to choose you',
        'What you offer, stated plainly, with salary ranges on jobs. Candidates apply with '
        'confidence and fewer drop out.'),
    'Sector Page Generator': (
        'No pages for the sectors you recruit in',
        'A page for every sector, for employers and candidates',
        'Sector pages with live jobs, your consultants and the answers people search for, '
        'generated and kept current for you.'),
    'Global Edge CDN': (
        'A slow website',
        'Pages that load in under two seconds',
        'Your site is served from locations close to every visitor, so it is fast on any '
        'phone, anywhere, and Google rewards it.'),
}

_PRIORITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


def opportunities(report: dict, limit: int = 5) -> list:
    """Top recommendations translated to plain English, one per theme."""
    recs = sorted(report.get('recommendations') or [],
                  key=lambda r: _PRIORITY_ORDER.get(r.get('priority'), 9))
    out, seen = [], set()
    for r in recs:
        mapped = CHECKS.get(r.get('check', ''))
        if mapped:
            title, why, great = mapped
        else:
            title = r.get('check', 'Opportunity')
            why = r.get('impact') or r.get('detail') or ''
            great = r.get('how_to_fix') or r.get('detail') or ''
        if title in seen:
            continue
        seen.add(title)
        pillar = PILLAR_LABELS.get(r.get('pillar', ''), (r.get('pillar', ''), ''))[0]
        out.append({'title': title, 'why': why, 'great': great,
                    'pillar': pillar, 'priority': r.get('priority', '')})
        if len(out) >= limit:
            break
    return out


def advantages(report: dict, limit: int = 4) -> list:
    """Shazamme advantage items in the client's language, grader text as fallback."""
    out = []
    for a in (report.get('shazamme_advantage') or [])[:limit]:
        mapped = ADVANTAGE.get(a.get('feature', ''))
        if mapped:
            gap, title, desc = mapped
        else:
            gap, title, desc = a.get('gap', ''), a.get('feature', ''), a.get('description', '')
        stat = STAT_OVERRIDES.get(a.get('feature', ''), a.get('stat', ''))
        out.append({'gap': gap, 'title': title, 'desc': desc, 'stat': stat})
    return out


def pillar_rows(report: dict) -> list:
    rows = []
    for p in (report.get('pillars') or {}).values():
        label, meaning = PILLAR_LABELS.get(p.get('name', ''), (p.get('name', ''), ''))
        rows.append({'label': label, 'meaning': meaning, 'score': int(p.get('score') or 0)})
    return sorted(rows, key=lambda r: r['score'])


def _band(score: int):
    if score >= 85:
        return ('#059669', 'Your website is already a strong performer. The opportunities '
                           'below are about staying ahead as search and candidate behaviour '
                           'keep changing.')
    if score >= 70:
        return ('#0891b2', 'Your website has good foundations. A handful of focused changes '
                           'would move it into the top tier.')
    if score >= 55:
        return ('#d97706', 'Your website is working, but it is leaving candidates and clients '
                           'on the table. The gaps are clear, and every one of them is fixable.')
    return ('#e11d48', 'Your website is costing you candidates and clients every week. The '
                       'good news: everything in this report is fixable, and most of it quickly.')


def _bar_colour(score: int) -> str:
    return _band(score)[0]


def _benchmark_line(report: dict) -> str:
    b = report.get('benchmark') or {}
    if not b.get('ready') or b.get('average') is None:
        return ''
    avg = int(b['average'])
    score = int(report.get('overall_score') or 0)
    if score >= avg:
        return (f'You are already ahead of the average recruitment website we have graded '
                f'({avg}/100). The top performers score 85 and above.')
    return (f'The average recruitment website we have graded scores {avg}/100, and the top '
            f'performers score 85 and above. That gap is your opportunity.')


# --- HTML ---------------------------------------------------------------------

_CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #fff; }
body { font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a;
       line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 210mm; height: 297mm; padding: 18mm 18mm 16mm; position: relative;
        page-break-after: always; overflow: hidden; }
.page:last-child { page-break-after: auto; }
.kicker { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
          color: #6d28d9; margin-bottom: 8px; }
h1 { font-size: 36px; font-weight: 800; line-height: 1.1; letter-spacing: -.02em; }
h2 { font-size: 24px; font-weight: 800; letter-spacing: -.02em; margin-bottom: 14px; }
h3 { font-size: 14px; font-weight: 700; }
p { font-size: 12.5px; color: #334155; }
.muted { color: #64748b; }
.brand { font-weight: 900; font-size: 15px; letter-spacing: -.02em;
         background: linear-gradient(120deg, #6d28d9, #ec2baf 55%, #0891b2);
         -webkit-background-clip: text; background-clip: text; color: transparent; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 26px;
          font-size: 11px; color: #64748b; }
.footer { position: absolute; left: 18mm; right: 18mm; bottom: 9mm; display: flex;
          justify-content: space-between; font-size: 10px; color: #94a3b8; }
.cover-logo { height: 44px; max-width: 200px; object-fit: contain; margin-bottom: 36px; }
.cover-domain { font-size: 15px; font-weight: 600; color: #475569; margin: 10px 0 40px; }
.score-card { display: flex; align-items: center; gap: 28px; padding: 26px 28px; border-radius: 20px;
              background: linear-gradient(135deg, #f5f3ff, #fdf2f8 60%, #ecfeff); border: 1px solid rgba(15,23,42,.08);
              margin-bottom: 30px; }
.score-big { font-size: 84px; font-weight: 900; line-height: 1; letter-spacing: -.04em; white-space: nowrap; }
.score-big small { font-size: 22px; font-weight: 700; color: #64748b; letter-spacing: 0; }
.score-label { font-size: 20px; font-weight: 800; margin-bottom: 6px; }
.verdict { font-size: 15px; color: #0f172a; line-height: 1.55; max-width: 150mm; }
.callout { border-left: 4px solid #ec2baf; padding: 10px 16px; background: #fdf2f8; border-radius: 0 12px 12px 0;
           font-size: 13px; color: #0f172a; margin-top: 20px; }
.pillars { display: grid; grid-template-columns: 1fr; gap: 9px; margin: 6px 0 24px; }
.pillar { display: grid; grid-template-columns: 62mm 1fr 14mm; align-items: center; gap: 12px; }
.pillar .l { font-size: 12.5px; font-weight: 700; }
.pillar .m { font-size: 10.5px; color: #64748b; font-weight: 400; display: block; }
.track { height: 10px; background: #f1f5f9; border-radius: 999px; overflow: hidden; }
.fill { height: 100%; border-radius: 999px; }
.pillar .s { font-size: 14px; font-weight: 800; text-align: right; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.box { border: 1px solid rgba(15,23,42,.1); border-radius: 16px; padding: 16px 18px; }
.box h3 { margin-bottom: 8px; }
.box ul { padding-left: 16px; font-size: 12.5px; color: #334155; }
.box li { margin-bottom: 4px; }
.stat { font-size: 30px; font-weight: 900; letter-spacing: -.03em; line-height: 1.1; }
.stat small { font-size: 11px; font-weight: 600; color: #64748b; display: block; letter-spacing: 0; }
.tiles { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 26px; }
.tile { padding: 16px 18px; border-radius: 16px; background: #f8fafc; border: 1px solid rgba(15,23,42,.06); }
.shifts { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 6px 0 18px; }
.shift { padding: 11px 12px; border-radius: 14px; background: #f8fafc; border: 1px solid rgba(15,23,42,.06); }
.shift .n { font-size: 11px; font-weight: 800; color: #6d28d9; margin-bottom: 6px; }
.shift h3 { font-size: 13px; margin-bottom: 4px; }
.shift p { font-size: 11px; line-height: 1.4; }
.opp { display: grid; grid-template-columns: 11mm 1fr; gap: 10px; padding: 8px 0; border-top: 1px solid rgba(15,23,42,.08); }
.opp .num { width: 30px; height: 30px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
            font-weight: 900; font-size: 14px; color: #fff; background: linear-gradient(135deg, #7c3aed, #ec2baf); }
.opp h3 { font-size: 14px; margin-bottom: 2px; }
.opp .pill { font-size: 10px; font-weight: 700; color: #6d28d9; text-transform: uppercase; letter-spacing: .08em; }
.opp p { font-size: 11px; margin-top: 2px; line-height: 1.4; }
.opp p b { color: #0f172a; }
.adv { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.adv .box { padding: 14px 16px; }
.adv .gap { font-size: 10.5px; color: #e11d48; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
.adv h3 { font-size: 13.5px; margin: 4px 0; }
.adv p { font-size: 11.5px; }
.adv .st { font-size: 12px; font-weight: 800; color: #059669; margin-top: 6px; }
.steps { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 8px 0 22px; }
.step { padding: 14px; border-radius: 14px; background: #f5f3ff; }
.step .n { font-size: 22px; font-weight: 900; color: #7c3aed; line-height: 1; margin-bottom: 6px; }
.step h3 { font-size: 13px; margin-bottom: 3px; }
.step p { font-size: 11.5px; }
.cta { border-radius: 18px; padding: 22px 26px; color: #fff;
       background: linear-gradient(120deg, #6d28d9 0%, #ec2baf 60%, #0891b2 120%); }
.cta h2 { color: #fff; margin-bottom: 6px; }
.cta p { color: rgba(255,255,255,.92); font-size: 13px; }
.cta .links { margin-top: 12px; font-size: 13px; font-weight: 700; }
"""

_SHIFTS = [
    ('AI answers before Google does',
     'Candidates and employers now ask ChatGPT, Perplexity and Google AI who to work with. '
     'Those tools recommend the sites they can read and trust. Most agency websites were '
     'built before this existed.'),
    ('Candidates decide on their phone',
     'Most job searches happen on a phone, often in the evening. If a candidate cannot find '
     'a job and apply in two minutes, they apply with someone else.'),
    ('Clients judge you by your website',
     'Before an employer returns your call they look at your site. Sector pages, '
     'consultants, proof and speed decide whether you look like the specialist you are.'),
]


def _header(domain: str, page: int, total: int) -> str:
    return (f'<div class="topbar"><span class="brand">shazamme</span>'
            f'<span>Website Opportunity Report · {_e(domain)}</span></div>')


def _footer(report_link: str, page: int) -> str:
    return (f'<div class="footer"><span>Prepared by Shazamme · {date.today().strftime("%-d %B %Y")}</span>'
            f'<span>Full technical report: {_e(report_link)}</span><span>{page} / 4</span></div>')


def build_html(report: dict, logo_src: str = None) -> str:
    score = int(report.get('overall_score') or 0)
    domain = report.get('domain') or report.get('url') or ''
    label = report.get('grade_label') or ''
    colour, verdict = _band(score)
    report_id = report.get('report_id') or ''
    report_link = f'{PUBLIC_BASE_URL}/r/{report_id}' if report_id else PUBLIC_BASE_URL
    es = report.get('executive_summary') or {}
    strengths = [PILLAR_LABELS.get(s, (s, ''))[0] for s in (es.get('strengths') or [])]
    rows = pillar_rows(report)
    opps = opportunities(report)
    bench = _benchmark_line(report)
    critical = sum(1 for r in (report.get('recommendations') or []) if r.get('priority') == 'critical')

    logo_html = f'<img class="cover-logo" src="{_e(logo_src)}" alt="">' if logo_src else ''

    pillar_html = ''.join(
        f'<div class="pillar"><div class="l">{_e(r["label"])}<span class="m">{_e(r["meaning"])}</span></div>'
        f'<div class="track"><div class="fill" style="width:{r["score"]}%;background:{_bar_colour(r["score"])}"></div></div>'
        f'<div class="s" style="color:{_bar_colour(r["score"])}">{r["score"]}</div></div>'
        for r in rows)

    strengths_html = ''.join(f'<li>{_e(s)}</li>' for s in strengths) or \
        '<li>The basics are in place: the site loads, is secure and can be found.</li>'
    weakest_html = ''.join(f'<li>{_e(r["label"])}</li>' for r in rows[:2])

    shifts_html = ''.join(
        f'<div class="shift"><div class="n">0{i + 1}</div><h3>{_e(t)}</h3><p>{_e(b)}</p></div>'
        for i, (t, b) in enumerate(_SHIFTS))

    opps_html = ''.join(
        f'<div class="opp"><div class="num">{i + 1}</div><div>'
        f'<div class="pill">{_e(o["pillar"])}</div><h3>{_e(o["title"])}</h3>'
        f'<p><b>Why it matters.</b> {_e(_clip(o["why"], 185))}</p>'
        f'<p><b>What great looks like.</b> {_e(_clip(o["great"]))}</p></div></div>'
        for i, o in enumerate(opps)) or '<p class="muted">No significant gaps found.</p>'

    adv_html = ''.join(
        f'<div class="box"><div class="gap">{_e(a["gap"])}</div><h3>{_e(a["title"])}</h3>'
        f'<p>{_e(_clip(a["desc"], 190))}</p><div class="st">{_e(a["stat"])}</div></div>'
        for a in advantages(report)) or (
        '<div class="box"><h3>Built for recruitment, ready for AI</h3><p>Sector pages, live jobs from '
        'your recruitment system, rich Google listings, AI chat and job alerts are all included and '
        'switched on from day one.</p></div>')

    bench_html = f'<div class="callout">{_e(bench)}</div>' if bench else ''

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Website Opportunity Report · {_e(domain)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>{_CSS}</style></head>
<body>

<section class="page">
  {_header(domain, 1, 4)}
  {logo_html}
  <div class="kicker">Website Opportunity Report</div>
  <h1>Your website could be<br>working much harder for you.</h1>
  <div class="cover-domain">{_e(domain)}</div>
  <div class="score-card">
    <div class="score-big" style="color:{colour}">{score}<small> / 100</small></div>
    <div>
      <div class="score-label" style="color:{colour}">{_e(label)}</div>
      <div class="verdict">{_e(verdict)}</div>
    </div>
  </div>
  <p>We looked at {_e(domain)} the way a candidate, an employer, Google and an AI assistant would
  see it today, and scored it across six areas that decide whether a recruitment website wins work.
  This report keeps it simple: where you stand, what has changed, and the handful of changes that
  would make the biggest difference.</p>
  {bench_html}
  <div class="tiles">
    <div class="tile"><div class="stat">{critical}<small>critical gaps found</small></div></div>
    <div class="tile"><div class="stat">{len(opps)}<small>opportunities in this report</small></div></div>
    <div class="tile"><div class="stat">{len(strengths)}<small>area{'' if len(strengths) == 1 else 's'} already strong</small></div></div>
  </div>
  {_footer(report_link, 1)}
</section>

<section class="page">
  {_header(domain, 2, 4)}
  <div class="kicker">Where you stand today</div>
  <h2>Six things that decide whether a recruitment website wins work</h2>
  <div class="pillars">{pillar_html}</div>
  <div class="two">
    <div class="box"><h3>What is already working</h3><ul>{strengths_html}</ul></div>
    <div class="box"><h3>Where the biggest upside is</h3><ul>{weakest_html}</ul></div>
  </div>
  {_footer(report_link, 2)}
</section>

<section class="page">
  {_header(domain, 3, 4)}
  <div class="kicker">The world has changed</div>
  <h2>Three shifts that most agency websites were never built for</h2>
  <div class="shifts">{shifts_html}</div>
  <div class="kicker">Your biggest opportunities</div>
  {opps_html}
  {_footer(report_link, 3)}
</section>

<section class="page">
  {_header(domain, 4, 4)}
  <div class="kicker">What amazing looks like</div>
  <h2>With Shazamme, these gaps are closed on day one</h2>
  <div class="adv">{adv_html}</div>
  <div class="kicker">What happens next</div>
  <div class="steps">
    <div class="step"><div class="n">1</div><h3>A 30-minute walkthrough</h3><p>We take you through this report and show you a live example of what your site could look like.</p></div>
    <div class="step"><div class="n">2</div><h3>We build it</h3><p>Design, content, jobs connected to your recruitment system, and everything above switched on.</p></div>
    <div class="step"><div class="n">3</div><h3>Launch and keep improving</h3><p>Your site goes live and we re-score it every month, so you can see the result.</p></div>
  </div>
  <div class="cta">
    <h2>Let's make it amazing.</h2>
    <p>Shazamme builds recruitment and career websites that Google ranks, AI recommends and candidates love. Book a walkthrough and see your site re-imagined.</p>
    <div class="links">{_e(BRAND_SITE.replace('https://', ''))} · {_e(BRAND_EMAIL)}</div>
  </div>
  {_footer(report_link, 4)}
</section>

</body></html>"""


# --- PDF ----------------------------------------------------------------------

def _log(msg):
    print(f'[client_report] {msg}', file=sys.stderr, flush=True)


def render_pdf(html: str, timeout_ms: int = 30000) -> bytes:
    """Render print-ready HTML to A4 PDF bytes with Chromium. Raises on failure."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
        try:
            page = browser.new_page()
            page.set_content(html, wait_until='networkidle', timeout=timeout_ms)
            page.emulate_media(media='print')
            pdf = page.pdf(format='A4', print_background=True,
                           margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
            _log(f'rendered {len(pdf)} bytes')
            return pdf
        finally:
            browser.close()
