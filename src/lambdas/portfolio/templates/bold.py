"""
Template: Bold (v2 Premium)

Upgrades:
- Wider layout
- Premium spacing
- Professional experience layout
- Stronger hero
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

<div class="hero-badge">Portfolio</div>

<h1>{v["name"]}</h1>

<p class="headline">
{v["headline"]}
</p>

<p class="location">
{v["location"]}
</p>

<div class="links">

{links_html}

{email_link}

</div>

</div>

</header>



<main class="container">


<div class="section-grid">

<section class="about">

<h2><span class="h2-accent">//</span> About</h2>

<p>{v["bio"]}</p>

</section>



<section class="skills">

<h2><span class="h2-accent">//</span> Skills</h2>

<div class="skills-container">

{skills_html}

</div>

</section>

</div>



<section class="experience">

<h2><span class="h2-accent">//</span> Experience</h2>

{experience_html}

</section>



<section class="education">

<h2><span class="h2-accent">//</span> Education</h2>

{education_html}

</section>



</main>



<footer>

<div class="container">

<p>Generated with AI Portfolio Builder</p>

</div>

</footer>


</body>
</html>
"""


def css() -> str:

    return """

:root{

--accent:#f97316;
--accent-glow:rgba(249,115,22,0.35);

--bg:#0f172a;
--bg-card:#1e293b;
--bg-card-hover:#263348;

--text:#f1f5f9;
--muted:#94a3b8;

--border:#334155;

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

line-height:1.6;

}



/* Container Upgrade */

.container{

max-width:1150px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

background:linear-gradient(160deg,#0f172a,#1e293b);

padding:6rem 0 5rem;

border-bottom:2px solid var(--accent);

}


.hero-badge{

font-size:.7rem;

letter-spacing:.2em;

text-transform:uppercase;

color:var(--accent);

border:1px solid var(--accent);

padding:4px 10px;

display:inline-block;

margin-bottom:1.5rem;

}



.hero h1{

font-size:clamp(3rem,7vw,4.5rem);

font-weight:700;

letter-spacing:-.03em;

margin-bottom:.8rem;

}



.headline{

max-width:700px;

font-size:1.2rem;

color:var(--muted);

margin-bottom:.6rem;

}



.location{

color:var(--muted);

margin-bottom:2rem;

}



.links{

display:flex;

gap:10px;

flex-wrap:wrap;

}



.links a{

padding:8px 16px;

border:1px solid var(--border);

border-radius:6px;

text-decoration:none;

color:white;

transition:.2s;

}



.links a:hover{

border-color:var(--accent);

color:var(--accent);

box-shadow:0 0 16px var(--accent-glow);

transform:translateY(-1px);

}



/* Main */

main{

padding:5rem 0;

}


section{

margin-bottom:5rem;

}



h2{

font-size:1.4rem;

margin-bottom:2rem;

display:flex;

gap:10px;

align-items:center;

}


h2::after{

content:"";

flex:1;

height:1px;

background:var(--border);

}


.h2-accent{

color:var(--accent);

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

border:1px solid var(--accent);

padding:6px 14px;

border-radius:4px;

color:var(--accent);

font-size:.85rem;

transition:.2s;

}


.skill-tag:hover{

background:var(--accent);

color:var(--bg);

box-shadow:0 0 14px var(--accent-glow);

}



/* Premium Experience Layout */

.experience-item,
.education-item{

background:var(--bg-card);

border-radius:10px;

padding:1.7rem;

margin-bottom:1.3rem;

border-left:3px solid var(--border);

transition:.2s;

}



.experience-item:hover,
.education-item:hover{

border-left-color:var(--accent);

background:var(--bg-card-hover);

transform:translateX(4px);

}



.exp-header{

display:flex;

justify-content:space-between;

flex-wrap:wrap;

margin-bottom:8px;

}



.exp-role{

font-weight:600;

font-size:1.1rem;

}



.exp-company{

opacity:.6;

font-size:.95rem;

}



.exp-duration{

font-size:.8rem;

color:var(--accent);

}



.experience-item p{

color:var(--muted);

margin-top:6px;

}



.experience-item ul{

margin-top:10px;

padding-left:18px;

}



.experience-item li{

color:var(--muted);

margin-bottom:4px;

}



/* Footer */

footer{

border-top:1px solid var(--border);

padding:3rem 0;

text-align:center;

color:var(--muted);

}



/* Mobile */

@media(max-width:900px){

.hero h1{

font-size:2.3rem;

}

}



@media(min-width:900px){

.section-grid{

display:grid;

grid-template-columns:3fr 2fr;

gap:3rem;

align-items:start;

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
