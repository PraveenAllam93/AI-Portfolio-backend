"""
Template: Aurora (v2 Premium Desktop)

Upgrades:
- Wider layout (1150px)
- Premium spacing
- Skills + Education grid
- Professional experience layout
- Better hero alignment
"""

from .base import CSP

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Syne:wght@400;600;700;800"
    "&family=DM+Sans:wght@300;400;500&display=swap"
)


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    location_html = (
        f'<p class="hero-location">{v["location"]}</p>' if v["location"] else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="{CSP}">

<title>{v["name"]} Portfolio</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{_FONTS}" rel="stylesheet">

<link rel="stylesheet" href="styles.css">

</head>

<body>


<div class="bubble b1"></div>
<div class="bubble b2"></div>
<div class="bubble b3"></div>
<div class="bubble b4"></div>


<header class="hero">

<div class="container">

<div class="hero-tag">Open to Work</div>

<h1 class="hero-name">{v["name"]}</h1>

<p class="hero-headline">
{v["headline"]}
</p>

{location_html}

<div class="hero-links">

{links_html}

{email_link}

</div>

</div>

</header>


<div class="wave-sep">

<svg viewBox="0 0 1440 60" preserveAspectRatio="none">

<path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z"
fill="rgba(15,23,42,0.9)"/>

</svg>

</div>



<main class="container">


<div class="content-grid">

<section class="section">

<h2>About</h2>

<div class="glass-panel">

<p class="bio">

{v["bio"]}

</p>

</div>

</section>


<section class="section">

<h2>Skills</h2>

<div class="skills-grid">

{skills_html}

</div>

</section>

</div>



<section class="section">

<h2>Experience</h2>

{experience_html}

</section>


<section class="section">

<h2>Education</h2>

{education_html}

</section>


</main>



<footer>

<div class="container">

<p class="footer-text">

Built with AI Portfolio Builder

</p>

</div>

</footer>



</body>
</html>
"""


def css() -> str:

    return """

:root{

--em:#4ade80;
--cy:#22d3ee;
--text:#f0f9ff;
--muted:rgba(226,232,240,0.7);
--glass:rgba(255,255,255,0.06);
--glass-b:rgba(255,255,255,0.14);
--dark-bg:#0f172a;

}


*{margin:0;padding:0;box-sizing:border-box;}


/* Background */

body{

font-family:'DM Sans',sans-serif;

background:linear-gradient(-45deg,
#0d1b2a,
#0a4a4a,
#1a0a3e,
#0d2d5e,
#063b2f,
#1e1040);

background-size:400% 400%;

color:var(--text);

animation:aurora 14s infinite;

}


@keyframes aurora{

0%{background-position:0% 50%;}
50%{background-position:100% 50%;}
100%{background-position:0% 50%;}

}



/* Container Upgrade */

.container{

max-width:1150px;

margin:auto;

padding:0 2rem;

position:relative;

z-index:1;

}



/* Hero */

.hero{

padding:7rem 0 5rem;

text-align:center;

}



.hero-name{

font-family:'Syne';

font-size:clamp(3rem,8vw,5.5rem);

font-weight:800;

letter-spacing:-0.03em;

text-shadow:
0 0 40px rgba(74,222,128,0.4),
0 0 80px rgba(34,211,238,0.2),
0 0 140px rgba(74,222,128,0.15);

margin-bottom:1rem;

}


.hero-headline{

max-width:700px;

margin:auto;

font-size:1.2rem;

color:var(--muted);

margin-bottom:2rem;

}


.hero-links{

display:flex;

justify-content:center;

gap:10px;

flex-wrap:wrap;

}


.hero-links a{

padding:10px 18px;

border-radius:10px;

border:1px solid var(--glass-b);

text-decoration:none;

color:white;

background:var(--glass);

backdrop-filter:blur(14px);

}



/* Grid Layout */

.content-grid{

display:grid;

grid-template-columns:1fr 1fr;

gap:40px;

}



.section{

margin-bottom:5rem;

}


h2{

font-family:'Syne';

font-size:1.6rem;

margin-bottom:1.5rem;

background:linear-gradient(135deg,var(--em),var(--cy));

-webkit-background-clip:text;

-webkit-text-fill-color:transparent;

}



/* Glass Panels */

.glass-panel{

background:var(--glass);

border:1px solid var(--glass-b);

border-radius:16px;

padding:2rem;

backdrop-filter:blur(20px);

}



.bio{

font-size:1.05rem;

color:var(--muted);

line-height:1.9;

}



/* Skills */

.skills-grid{

display:flex;

flex-wrap:wrap;

gap:8px;

}


.skill-tag{

padding:6px 14px;

border-radius:20px;

border:1px solid rgba(255,255,255,0.1);

background:rgba(255,255,255,0.04);

font-size:.8rem;

}



/* Cards */

.card{

background:var(--glass);

border:1px solid var(--glass-b);

border-radius:14px;

padding:1.6rem;

margin-bottom:1rem;

backdrop-filter:blur(20px);

}



/* Premium Experience Layout */

.card-header{

display:flex;

justify-content:space-between;

flex-wrap:wrap;

margin-bottom:8px;

}


.card-role{

font-family:'Syne';

font-weight:700;

font-size:1.1rem;

}


.card-company{

opacity:.6;

}


.card-duration{

font-size:.85rem;

color:var(--em);

}



.card-body{

margin-top:8px;

color:var(--muted);

}


.card-list{

margin-top:10px;

padding-left:16px;

}



footer{

padding:3rem 0;

text-align:center;

opacity:.5;

}



/* Mobile */

@media(max-width:900px){

.content-grid{

grid-template-columns:1fr;

}

.hero{

padding:4rem 0 3rem;

}

}
"""


def _links(v: dict) -> str:

    out = ""

    if v["linkedin_url"]:
        out += f'<a href="{v["linkedin_url"]}">LinkedIn</a>'

    if v["github_url"]:
        out += f'<a href="{v["github_url"]}">GitHub</a>'

    return out


def _email_link(email: str) -> str:

    return f'<a href="mailto:{email}">Contact</a>' if email else ""


def _skills(skills: list) -> str:

    return "".join(f'<span class="skill-tag">{s}</span>' for s in skills[:24])


def _experience(items: list) -> str:

    out = ""

    for exp in items:
        highlights = "".join(f"<li>{h}</li>" for h in exp["highlights"])

        out += (
            f'<div class="card">'
            f'<div class="card-header">'
            f"<div>"
            f'<div class="card-role">{exp["title"]}</div>'
            f'<div class="card-company">{exp["company"]}</div>'
            f"</div>"
            f'<div class="card-duration">{exp["duration"]}</div>'
            f"</div>"
            f'<div class="card-body">{exp["description"]}</div>'
            f'<ul class="card-list">{highlights}</ul>'
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="card">'
            f'<div class="card-role">{edu["degree"]}</div>'
            f'<div class="card-meta">'
            f"{edu['institution']} · {edu['year']}"
            f"</div>"
            f"</div>"
        )

    return out
