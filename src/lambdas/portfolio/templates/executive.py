"""
Template: Executive (v2 Premium Corporate)

Upgrades:
- Wider layout (1150px)
- Executive hero
- About + Skills grid
- Premium timeline layout
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    return f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<meta http-equiv="Content-Security-Policy" content="{CSP}">

<title>{v["name"]} Portfolio</title>

<link rel="stylesheet" href="styles.css">
<link href="{FONTS_URL}" rel="stylesheet">

</head>


<body>



<header class="hero">

<div class="container">

<p class="hero-label">
Professional Portfolio
</p>

<h1>
{v["name"]}
</h1>

<p class="headline">
{v["headline"]}
</p>


<div class="hero-meta">

<span>
{v["location"]}
</span>

<div class="links">

{links_html}

{email_link}

</div>

</div>

</div>

</header>



<main class="container">



<div class="grid">


<section class="about">

<h2>About</h2>

<p>
{v["bio"]}
</p>

</section>



<section class="skills">

<h2>Core Competencies</h2>

<div class="skills-container">

{skills_html}

</div>

</section>



</div>



<section>

<h2>Professional Experience</h2>

<div class="timeline">

{experience_html}

</div>

</section>



<section>

<h2>Education</h2>

{education_html}

</section>



</main>



<footer>

<div class="container">

Generated with AI Portfolio Builder

</div>

</footer>


</body>
</html>
"""


def css() -> str:

    return """

:root{

--green:#166534;
--green-dark:#14532d;

--gold:#b45309;

--text:#1c1917;
--muted:#57534e;

--bg:#fafaf9;
--bg-alt:#f5f5f4;

--border:#d6d3d1;

}



*{
margin:0;
padding:0;
box-sizing:border-box;
}



body{

font-family:'Inter',sans-serif;

background:var(--bg);

color:var(--text);

line-height:1.65;

}



/* Container */

.container{

max-width:1150px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

background:linear-gradient(140deg,var(--green-dark),var(--green));

color:white;

padding:6rem 0 5rem;

}



.hero-label{

letter-spacing:.2em;

font-size:.7rem;

opacity:.7;

margin-bottom:1rem;

}



.hero h1{

font-size:clamp(3rem,6vw,4rem);

margin-bottom:.5rem;

}



.headline{

font-size:1.2rem;

opacity:.85;

margin-bottom:2rem;

max-width:700px;

}



.hero-meta{

display:flex;

gap:20px;

flex-wrap:wrap;

align-items:center;

}



.links{

display:flex;

gap:10px;

flex-wrap:wrap;

}



.links a{

border:1px solid rgba(255,255,255,.3);

padding:6px 14px;

border-radius:4px;

text-decoration:none;

color:white;

}



/* Grid */

.grid{

display:grid;

grid-template-columns:1fr 1fr;

gap:50px;

margin:5rem 0;

}



/* Sections */

section{

margin-bottom:4rem;

}



h2{

font-size:1.35rem;

color:var(--gold);

margin-bottom:1.5rem;

}



h2::after{

content:"";

display:block;

height:2px;

background:var(--gold);

width:60px;

margin-top:6px;

}



/* About */

.about p{

font-size:1.05rem;

color:var(--muted);

line-height:1.9;

}



/* Skills */

.skills-container{

display:flex;

flex-wrap:wrap;

gap:8px;

}



.skill-tag{

background:var(--bg-alt);

padding:6px 12px;

border-radius:4px;

border:1px solid var(--border);

font-size:.85rem;

}



/* Timeline */

.timeline{

position:relative;

padding-left:30px;

}



.timeline::before{

content:"";

position:absolute;

left:0;

top:0;

bottom:0;

width:2px;

background:var(--border);

}



.experience-item{

position:relative;

margin-bottom:2.5rem;

}



.experience-item::before{

content:"";

position:absolute;

left:-34px;

top:6px;

width:12px;

height:12px;

border-radius:50%;

background:var(--gold);

}



.exp-header{

display:flex;

justify-content:space-between;

flex-wrap:wrap;

margin-bottom:6px;

}



.exp-role{

font-weight:600;

font-size:1.05rem;

}



.exp-company{

opacity:.7;

font-size:.9rem;

}



.exp-duration{

font-size:.8rem;

color:var(--gold);

}



.experience-item p{

margin-top:6px;

color:var(--muted);

}



.experience-item ul{

margin-top:10px;

padding-left:18px;

}



.education-item{

background:var(--bg-alt);

padding:1.5rem;

border-radius:6px;

margin-bottom:1rem;

border-left:3px solid var(--gold);

}



/* Footer */

footer{

background:var(--bg-alt);

padding:2rem 0;

text-align:center;

margin-top:4rem;

}



/* Mobile */

@media(max-width:900px){

.grid{
grid-template-columns:1fr;
gap:30px;
}

.hero{
padding:4rem 0;
}

}
"""


# -----------------------
# Helpers
# -----------------------


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

    return "".join(f'<span class="skill-tag">{s}</span>' for s in skills[:20])


def _experience(items: list) -> str:

    out = ""

    for exp in items:
        highlights = "".join(f"<li>{h}</li>" for h in exp["highlights"])

        out += (
            f'<div class="experience-item">'
            f'<div class="exp-header">'
            f"<div>"
            f'<div class="exp-role">{exp["title"]}</div>'
            f'<div class="exp-company">{exp["company"]}</div>'
            f"</div>"
            f'<div class="exp-duration">{exp["duration"]}</div>'
            f"</div>"
            f"<p>{exp['description']}</p>"
            f"<ul>{highlights}</ul>"
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="education-item">'
            f'<div class="exp-role">{edu["degree"]}</div>'
            f'<div class="exp-duration">'
            f"{edu['institution']} · {edu['year']}"
            f"</div>"
            f"</div>"
        )

    return out
