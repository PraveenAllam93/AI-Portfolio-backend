"""
Template: Designer

Visual designer-focused portfolio.

Features:
- Large hero typography
- Optional profile image
- Grid-based experience cards
- Bold skill highlights
- Smooth animations
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    image_html = (
        f'<img class="profile-img" src="{v["profile_image"]}">'
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

<div class="hero-text">

<h1>{v["name"]}</h1>

<p class="headline">

{v["headline"]}

</p>


<div class="links">

{links_html}
{email_link}

</div>

</div>

{image_html}

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

<h2>Experience</h2>

<div class="grid">

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

--primary:#111827;

--accent:#2563eb;

--bg:#ffffff;

--card:#f9fafb;

--text:#111827;

--muted:#6b7280;

--border:#e5e7eb;

}



*{
margin:0;
padding:0;
box-sizing:border-box;
}



body{

font-family:'Inter';

background:var(--bg);

color:var(--text);

line-height:1.6;

}



/* Layout */

.container{

max-width:1100px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

padding:6rem 0;

}



.hero-inner{

display:flex;

align-items:center;

justify-content:space-between;

gap:40px;

flex-wrap:wrap;

}



.hero-text{

flex:1;

min-width:250px;

}



.hero h1{

font-size:4rem;

line-height:1.1;

margin-bottom:15px;

}



.headline{

font-size:1.2rem;

color:var(--muted);

margin-bottom:25px;

}



/* Profile image */

.profile-img{

width:260px;

height:260px;

object-fit:cover;

border-radius:20px;

box-shadow:0 10px 30px rgba(0,0,0,.15);

}



/* Links */

.links{

display:flex;

gap:10px;

flex-wrap:wrap;

}



.links a{

border:1px solid var(--border);

padding:10px 18px;

border-radius:8px;

text-decoration:none;

color:var(--text);

transition:.2s;

}



.links a:hover{

background:var(--accent);

color:white;

border-color:var(--accent);

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

font-size:1.6rem;

}



/* Bio */

.bio{

max-width:700px;

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

background:var(--card);

border:1px solid var(--border);

padding:8px 16px;

border-radius:30px;

transition:.2s;

}



.skill:hover{

background:var(--accent);

color:white;

}



/* Grid cards */

.grid{

display:grid;

grid-template-columns:repeat(auto-fit,minmax(280px,1fr));

gap:20px;

}



.card{

background:var(--card);

padding:20px;

border-radius:12px;

border:1px solid var(--border);

transition:.2s;

}



.card:hover{

transform:translateY(-4px);

box-shadow:0 10px 25px rgba(0,0,0,.1);

}



.card-title{

font-weight:600;

margin-bottom:5px;

}



.card-meta{

font-size:14px;

color:var(--muted);

margin-bottom:10px;

}



.card-body{

color:var(--muted);

font-size:15px;

}



.card-list{

margin-top:10px;

padding-left:18px;

}



footer{

border-top:1px solid var(--border);

padding:2rem 0;

text-align:center;

color:var(--muted);

}



/* Mobile */

@media(max-width:700px){

.hero h1{

font-size:2.4rem;

}


.profile-img{

width:200px;

height:200px;

}

}



@media(min-width:900px){

.section-grid{

display:grid;

grid-template-columns:3fr 2fr;

gap:3rem;

align-items:start;

}

.bio{

max-width:none;

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
            f'<div class="card">'
            f'<div class="card-title">{exp["title"]}</div>'
            f'<div class="card-meta">{exp["company"]} · {exp["duration"]}</div>'
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
            f'<div class="card-title">{edu["degree"]}</div>'
            f'<div class="card-meta">{edu["institution"]} · {edu["year"]}</div>'
            f"</div>"
        )

    return out
