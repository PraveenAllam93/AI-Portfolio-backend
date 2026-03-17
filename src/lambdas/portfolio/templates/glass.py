"""
Template: Glass

Premium glassmorphism template.

Features:
- Frosted glass cards
- Soft gradient background
- Floating blur shapes
- Optional profile image
- Smooth fade animations
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
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width">

<meta http-equiv="Content-Security-Policy" content="{CSP}">

<title>{v["name"]} Portfolio</title>

<link rel="stylesheet" href="styles.css">

<link href="{FONTS_URL}" rel="stylesheet">

</head>



<body>


<div class="bg1"></div>
<div class="bg2"></div>



<header class="hero">

<div class="glass container">

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

<section class="glass">

<h2>About</h2>

<p class="bio">

{v["bio"]}

</p>

</section>




<section class="glass">

<h2>Skills</h2>

<div class="skills">

{skills_html}

</div>

</section>

</div>




<section class="glass">

<h2>Experience</h2>

{experience_html}

</section>




<section class="glass">

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

--glass:rgba(255,255,255,.15);

--border:rgba(255,255,255,.3);

--text:#ffffff;

--muted:rgba(255,255,255,.75);

}



*{
margin:0;
padding:0;
box-sizing:border-box;
}



body{

font-family:'Inter';

color:var(--text);

background:linear-gradient(
135deg,
#6366f1,
#8b5cf6,
#ec4899
);

min-height:100vh;

}



/* Background shapes */

.bg1{

position:fixed;

width:500px;

height:500px;

background:#22c55e;

border-radius:50%;

filter:blur(120px);

top:-100px;

left:-100px;

opacity:.4;

}



.bg2{

position:fixed;

width:500px;

height:500px;

background:#3b82f6;

border-radius:50%;

filter:blur(120px);

bottom:-100px;

right:-100px;

opacity:.4;

}



/* Layout */

.container{

max-width:950px;

margin:auto;

padding:0 2rem;

}



/* Glass cards */

.glass{

background:var(--glass);

border:1px solid var(--border);

border-radius:20px;

padding:2rem;

margin-bottom:2rem;

backdrop-filter:blur(20px);

-webkit-backdrop-filter:blur(20px);

animation:fadeUp .9s ease;

}



/* Hero */

.hero{

padding:5rem 0 3rem;

text-align:center;

}



/* Avatar */

.avatar{

width:140px;

height:140px;

border-radius:50%;

object-fit:cover;

margin-bottom:20px;

}



/* Name */

.hero h1{

font-size:3rem;

margin-bottom:10px;

}



.headline{

opacity:.9;

margin-bottom:5px;

}



.location{

opacity:.7;

margin-bottom:15px;

}



/* Links */

.links{

display:flex;

justify-content:center;

gap:10px;

flex-wrap:wrap;

}



.links a{

border:1px solid rgba(255,255,255,.5);

padding:8px 16px;

border-radius:20px;

color:white;

text-decoration:none;

transition:.2s;

}



.links a:hover{

background:rgba(255,255,255,.2);

}



/* Titles */

h2{

margin-bottom:1rem;

}



/* Skills */

.skills{

display:flex;

flex-wrap:wrap;

gap:8px;

}



.skill{

border:1px solid rgba(255,255,255,.5);

padding:6px 14px;

border-radius:20px;

}



.skill:hover{

background:rgba(255,255,255,.2);

}



/* Cards */

.experience,
.education{

margin-bottom:1rem;

}



.job{

margin-bottom:10px;

}



footer{

padding:3rem 0;

text-align:center;

color:white;

opacity:.7;

}



@keyframes fadeUp{

from{
opacity:0;
transform:translateY(30px);
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


.avatar{

width:100px;
height:100px;

}

}



@media(min-width:900px){

.section-grid{

display:grid;

grid-template-columns:1fr 1fr;

gap:2rem;

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

    return "".join(f'<span class="skill">{s}</span>' for s in skills[:20])


def _experience(items: list) -> str:

    out = ""

    for exp in items:
        highlights = "".join(f"<li>{h}</li>" for h in exp["highlights"])

        out += (
            f'<div class="experience">'
            f"<b>{exp['title']}</b><br>"
            f"{exp['company']}<br>"
            f"{exp['duration']}"
            f"<p>{exp['description']}</p>"
            f"<ul>{highlights}</ul>"
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="education">'
            f"{edu['degree']} {edu['field']}<br>"
            f"{edu['institution']} {edu['year']}"
            f"</div>"
        )

    return out
