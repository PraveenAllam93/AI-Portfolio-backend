"""
Template: GradientHero

Very aesthetic premium template.

Features:
- Large gradient hero
- Animated gradient background
- Huge gradient name text
- Optional profile image
- Fade animations
- Premium layout

Image hides automatically if empty.
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:

    links_html = _links(v)
    email_link = _email_link(v["email"])
    skills_html = _skills(v["skills"])
    experience_html = _experience(v["experience"])
    education_html = _education(v["education"])

    image_html = (
        f'<img class="hero-image" src="{v["profile_image"]}">'
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

<div class="skills-container">

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

--text:#111827;

--muted:#6b7280;

--border:#e5e7eb;

--bg:#ffffff;

--bg-alt:#f9fafb;

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

line-height:1.7;

}



/* Layout */

.container{

max-width:950px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

padding:8rem 0 6rem;

text-align:center;

color:white;

background:linear-gradient(
270deg,
#6366f1,
#8b5cf6,
#ec4899,
#6366f1
);

background-size:600% 600%;

animation:gradientMove 18s ease infinite;

}



@keyframes gradientMove{

0%{background-position:0% 50%}

50%{background-position:100% 50%}

100%{background-position:0% 50%}

}



/* Name */

.hero h1{

font-size:clamp(3.5rem,8vw,6rem);

font-weight:700;

letter-spacing:-2px;

margin-bottom:10px;


background:linear-gradient(
90deg,
white,
#e0e7ff
);

-webkit-background-clip:text;

-webkit-text-fill-color:transparent;

animation:fadeUp .8s ease;

}



/* Image */

.hero-image{

width:180px;

height:180px;

border-radius:50%;

object-fit:cover;

margin-bottom:25px;

box-shadow:0 20px 60px rgba(0,0,0,.35);

animation:fadeUp .9s ease;

}



/* Headline */

.headline{

font-size:1.3rem;

opacity:.95;

margin-bottom:10px;

animation:fadeUp 1s ease;

}



.location{

opacity:.75;

margin-bottom:20px;

animation:fadeUp 1.1s ease;

}



/* Links */

.links{

display:flex;

justify-content:center;

gap:10px;

flex-wrap:wrap;

animation:fadeUp 1.2s ease;

}



.links a{

border:1px solid rgba(255,255,255,.4);

padding:8px 16px;

border-radius:6px;

color:white;

text-decoration:none;

transition:.2s;

}



.links a:hover{

background:rgba(255,255,255,.2);

}



/* Main */

main{

padding:5rem 0;

}



section{

margin-bottom:4rem;

}



/* Titles */

h2{

margin-bottom:1.5rem;

font-size:1.4rem;

border-bottom:2px solid #6366f1;

padding-bottom:6px;

}



/* About */

.bio{

max-width:700px;

color:#374151;

}



/* Skills */

.skills-container{

display:flex;

flex-wrap:wrap;

gap:8px;

}



.skill-tag{

background:var(--bg-alt);

padding:6px 14px;

border-radius:20px;

border:1px solid var(--border);

transition:.2s;

}



.skill-tag:hover{

border-color:#6366f1;

}



/* Cards */

.experience-item,
.education-item{

background:var(--bg-alt);

padding:1.5rem;

border-radius:12px;

margin-bottom:1rem;

transition:.2s;

}



.experience-item:hover,
.education-item:hover{

transform:translateY(-3px);

box-shadow:0 10px 30px rgba(0,0,0,.08);

}



/* Footer */

footer{

padding:3rem 0;

text-align:center;

color:var(--muted);

}



/* Animations */

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

.hero{

padding:5rem 0 4rem;

}


.hero h1{

font-size:2.5rem;

}


.hero-image{

width:130px;
height:130px;

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

    return "".join(f'<span class="skill-tag">{s}</span>' for s in skills[:24])


def _experience(items: list) -> str:

    out = ""

    for exp in items:
        highlights = "".join(f"<li>{h}</li>" for h in exp["highlights"])

        out += (
            f'<div class="experience-item">'
            f"<b>{exp['title']}</b><br>"
            f"{exp['company']}<br>"
            f"<small>{exp['duration']}</small>"
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
            f"{edu['degree']} {edu['field']}<br>"
            f"{edu['institution']} {edu['year']}"
            f"</div>"
        )

    return out
