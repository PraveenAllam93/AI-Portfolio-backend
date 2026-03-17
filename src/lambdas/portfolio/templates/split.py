"""
Template: Split

Premium split-screen portfolio template.

Features:
- Split hero layout
- Optional profile image
- Strong typography hierarchy
- Premium layout
- Clean modern style
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    image_html = (
        f'<div class="hero-image"><img src="{v["profile_image"]}"></div>'
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

<div class="container hero-grid">


<div class="hero-left">

<h1>

{v["name"]}

</h1>


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

{experience_html}

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

--accent:#4f46e5;

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



/* HERO */

.hero{

padding:6rem 0;

}



.hero-grid{

display:grid;

grid-template-columns:1fr 420px;

align-items:center;

gap:60px;

}



.hero-left{

max-width:520px;

}



/* Name */

.hero h1{

font-size:3.8rem;

line-height:1.1;

margin-bottom:20px;

}



/* Headline */

.headline{

font-size:1.3rem;

color:var(--muted);

margin-bottom:20px;

}



/* Location */

.location{

color:var(--muted);

margin-bottom:25px;

}



/* Image */

.hero-image img{

width:100%;

border-radius:16px;

object-fit:cover;

box-shadow:0 20px 60px rgba(0,0,0,.15);

}



/* Links */

.links{

display:flex;

gap:12px;

flex-wrap:wrap;

}



.links a{

padding:10px 20px;

border-radius:8px;

border:1px solid var(--border);

text-decoration:none;

color:var(--text);

transition:.2s;

}



.links a:hover{

background:var(--accent);

color:white;

border-color:var(--accent);

}



/* Content */

main{

padding:2rem 0 4rem;

}



section{

margin-bottom:4rem;

}



h2{

margin-bottom:1.5rem;

font-size:1.5rem;

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

padding:8px 16px;

border-radius:30px;

border:1px solid var(--border);

background:var(--card);

}



.skill:hover{

background:var(--accent);

color:white;

}



/* Cards */

.card{

background:var(--card);

padding:20px;

border-radius:12px;

border:1px solid var(--border);

margin-bottom:20px;

transition:.2s;

}



.card:hover{

transform:translateY(-4px);

box-shadow:0 10px 25px rgba(0,0,0,.08);

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



/* MOBILE */

@media(max-width:900px){

.hero-grid{

grid-template-columns:1fr;

}


.hero h1{

font-size:2.4rem;

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
