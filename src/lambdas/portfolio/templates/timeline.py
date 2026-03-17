"""
Template: Timeline

Animated career timeline portfolio.

Features:
- Vertical timeline layout
- Smooth fade animations
- Optional profile image
- Elegant layout
- Story-driven design
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    image_html = (
        f'<img class="avatar" src="{v["profile_image"]}">'
        if v.get("profile_image")
        else ""
    )

    return f"""<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width">

<meta http-equiv="Content-Security-Policy" content="{CSP}">

<title>{v["name"]} Portfolio</title>

<link rel="stylesheet" href="styles.css">

<link href="{FONTS_URL}" rel="stylesheet">

</head>


<body>



<header class="hero">

<div class="container hero-inner">

{image_html}

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

<section>

<h2>About</h2>

<p class="bio">

{v["bio"]}

</p>

</section>



<section>

<h2>Skills</h2>

<div class="skills">

{skills_html}

</div>

</section>

</div>



<section>

<h2>Career Journey</h2>

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

Built with AI Portfolio Builder

</div>

</footer>



</body>

</html>
"""


def css() -> str:

    return """

:root{

--primary:#2563eb;

--bg:#ffffff;

--text:#111827;

--muted:#6b7280;

--border:#e5e7eb;

--timeline:#dbeafe;

}



/* Reset */

*{
margin:0;
padding:0;
box-sizing:border-box;
}



/* Body */

body{

font-family:'Inter';

background:var(--bg);

color:var(--text);

line-height:1.6;

}



.container{

max-width:850px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

padding:5rem 0;

text-align:center;

}



.avatar{

width:130px;

height:130px;

border-radius:50%;

object-fit:cover;

margin-bottom:20px;

}



.hero h1{

font-size:3rem;

margin-bottom:10px;

}



.headline{

color:var(--muted);

margin-bottom:5px;

}



.location{

color:var(--muted);

margin-bottom:20px;

}



/* Links */

.links{

display:flex;

justify-content:center;

gap:10px;

flex-wrap:wrap;

}



.links a{

padding:8px 18px;

border-radius:8px;

border:1px solid var(--border);

text-decoration:none;

color:var(--text);

transition:.2s;

}



.links a:hover{

background:var(--primary);

color:white;

}



/* Sections */

main{

padding:2rem 0 4rem;

}



section{

margin-bottom:4rem;

}



h2{

margin-bottom:1.5rem;

font-size:1.4rem;

}



/* Bio */

.bio{

color:var(--muted);

line-height:1.8;

}



/* Skills */

.skills{

display:flex;

flex-wrap:wrap;

gap:10px;

}



.skill{

padding:8px 16px;

border-radius:20px;

border:1px solid var(--border);

}



.skill:hover{

background:var(--primary);

color:white;

}



/* TIMELINE */

.timeline{

position:relative;

padding-left:40px;

}



/* Vertical line */

.timeline:before{

content:"";

position:absolute;

left:15px;

top:0;

bottom:0;

width:2px;

background:var(--timeline);

}



/* Timeline item */

.timeline-item{

position:relative;

margin-bottom:30px;

animation:fadeUp .7s ease;

}



/* Timeline dot */

.timeline-item:before{

content:"";

position:absolute;

left:-26px;

top:6px;

width:14px;

height:14px;

border-radius:50%;

background:var(--primary);

}



/* Card */

.card{

background:#f9fafb;

border-radius:10px;

padding:18px;

border:1px solid var(--border);

transition:.2s;

}



.card:hover{

transform:translateY(-3px);

box-shadow:0 8px 20px rgba(0,0,0,.08);

}



.card-title{

font-weight:600;

margin-bottom:4px;

}



.card-meta{

font-size:14px;

color:var(--muted);

margin-bottom:8px;

}



.card-body{

color:var(--muted);

font-size:15px;

}



.card-list{

margin-top:10px;

padding-left:18px;

}



/* Education cards */

.education{

margin-bottom:15px;

}



/* Footer */

footer{

border-top:1px solid var(--border);

padding:2rem 0;

text-align:center;

color:var(--muted);

}



/* Animation */

@keyframes fadeUp{

from{

opacity:0;

transform:translateY(20px);

}

to{

opacity:1;

transform:translateY(0);

}

}



/* Mobile */

@media(max-width:640px){

.hero h1{

font-size:2rem;

}


.timeline{

padding-left:25px;

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

    return "".join(f'<span class="skill">{s}</span>' for s in skills[:24])


def _experience(items: list) -> str:

    out = ""

    for exp in items:
        highlights = "".join(f"<li>{h}</li>" for h in exp["highlights"])

        out += (
            f'<div class="timeline-item">'
            f'<div class="card">'
            f'<div class="card-title">{exp["title"]}</div>'
            f'<div class="card-meta">{exp["company"]} · {exp["duration"]}</div>'
            f'<div class="card-body">{exp["description"]}</div>'
            f'<ul class="card-list">{highlights}</ul>'
            f"</div>"
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="card education">'
            f'<div class="card-title">{edu["degree"]}</div>'
            f'<div class="card-meta">{edu["institution"]} · {edu["year"]}</div>'
            f"</div>"
        )

    return out
