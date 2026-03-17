"""
Template: Luxury (v2 Ultra Premium)

Upgrades:
- Wider layout
- Editorial grid
- Premium spacing
- Desktop optimized
"""

from .base import CSP

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600"
    "&family=Raleway:wght@300;400;500&display=swap"
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


<div class="dot-grid"></div>



<header class="hero">

<div class="container">

<div class="hero-inner">

<p class="hero-greeting">

Hello, I am

</p>

<h1 class="hero-name">

{v["name"]}

</h1>


<p class="hero-headline">

{v["headline"]}

</p>


<div class="hero-rule"></div>


{location_html}


<div class="hero-links">

{links_html}

{email_link}

</div>

</div>

</div>

</header>



<main class="container">


<div class="grid">


<section>

<h2>About</h2>

<p class="bio">

{v["bio"]}

</p>

</section>


<section>

<h2>Expertise</h2>

<div class="skills-grid">

{skills_html}

</div>

</section>


</div>



<section>

<h2>Experience</h2>

<div class="timeline">

{experience_html}

</div>

</section>



<section>

<h2>Education</h2>

<div class="edu-grid">

{education_html}

</div>

</section>



</main>



<footer>

<div class="container">

<div class="footer-rule"></div>

<p class="footer-sig">

{v["name"]}

</p>

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

--gold:#c9a84c;
--bg:#060c18;

--text:#f0e8d8;
--muted:rgba(220,210,190,0.6);

--border:rgba(201,168,76,0.2);

}



/* Reset */

*{

margin:0;
padding:0;
box-sizing:border-box;

}



body{

font-family:'Raleway',sans-serif;

background:var(--bg);

color:var(--text);

line-height:1.7;

}



/* Container Upgrade */

.container{

max-width:1150px;

margin:auto;

padding:0 2rem;

}



/* Dot Background */

.dot-grid{

position:fixed;

inset:0;

background-image:radial-gradient(rgba(201,168,76,.06) 1px,transparent 1px);

background-size:28px 28px;

}



/* Hero */

.hero{

padding:7rem 0 6rem;

text-align:center;

border-bottom:1px solid var(--border);

}



.hero-inner{

max-width:700px;

margin:auto;

}



.hero-greeting{

font-family:'Cormorant Garamond';

font-style:italic;

color:var(--gold);

margin-bottom:6px;

}



.hero-name{

font-family:'Cormorant Garamond';

font-size:clamp(3rem,8vw,6rem);

margin-bottom:10px;

color:var(--gold);

}



.hero-headline{

font-family:'Cormorant Garamond';

font-style:italic;

opacity:.8;

margin-bottom:20px;

}



.hero-rule{

width:80px;

height:1px;

background:var(--gold);

margin:20px auto;

}



.hero-links{

display:flex;

justify-content:center;

gap:10px;

flex-wrap:wrap;

}



.hero-links a{

border:1px solid var(--border);

padding:8px 16px;

text-decoration:none;

color:var(--gold);

}



/* Editorial Grid */

.grid{

display:grid;

grid-template-columns:1fr 1fr;

gap:80px;

margin:5rem 0;

}



/* Sections */

section{

margin-bottom:4rem;

}



h2{

font-family:'Cormorant Garamond';

margin-bottom:1.5rem;

color:var(--gold);

}



.bio{

max-width:650px;

line-height:1.9;

}



/* Skills */

.skills-grid{

display:flex;

flex-wrap:wrap;

gap:8px;

}



.skill-tag{

border:1px solid var(--border);

padding:6px 12px;

font-size:.8rem;

}



/* Timeline */

.timeline{

padding-left:30px;

border-left:1px solid var(--gold);

}



.t-item{

margin-bottom:2rem;

}



.t-title{

font-family:'Cormorant Garamond';

margin-bottom:4px;

}



.t-company{

color:var(--gold);

margin-bottom:6px;

}



.t-desc{

color:var(--muted);

}



.t-list{

margin-top:8px;

padding-left:18px;

}



/* Education */

.edu-card{

border:1px solid var(--border);

padding:1.5rem;

margin-bottom:1rem;

}



.footer-rule{

width:120px;

height:1px;

background:var(--gold);

margin:auto auto 1rem;

}



footer{

padding:4rem 0;

text-align:center;

}



/* Mobile */

@media(max-width:900px){

.grid{

grid-template-columns:1fr;

gap:40px;

}

.hero{

padding:4rem 0;

}

}

"""


# Helpers


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
            f'<div class="t-item">'
            f'<p class="t-title">{exp["title"]}</p>'
            f'<p class="t-company">{exp["company"]}</p>'
            f'<p class="t-desc">{exp["description"]}</p>'
            f'<ul class="t-list">{highlights}</ul>'
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="edu-card">'
            f"{edu['degree']} in {edu['field']}<br>"
            f"{edu['institution']} · {edu['year']}"
            f"</div>"
        )

    return out
