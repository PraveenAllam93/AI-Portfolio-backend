"""
Template: HeroImage

Features:
- Large hero section
- Optional profile image
- Fade animations
- Premium layout
- Modern aesthetic

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

<div class="container hero-grid">


<div class="hero-text">

<h1>{v["name"]}</h1>

<p class="headline">{v["headline"]}</p>

<p class="location">{v["location"]}</p>


<div class="links">

{links_html}
{email_link}

</div>

</div>


<div class="hero-image-wrapper">

{image_html}

</div>


</div>


</header>



<main class="container">


<div class="section-grid">

<section>

<h2>About</h2>

<p class="bio">{v["bio"]}</p>

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

--primary:#6366f1;

--text:#1f2937;

--muted:#6b7280;

--bg:#ffffff;

--bg-alt:#f9fafb;

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

line-height:1.7;

}



/* Layout */

.container{

max-width:1150px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

background:linear-gradient(135deg,#6366f1,#4f46e5);

color:white;

padding:6rem 0;

}



.hero-grid{

display:grid;

grid-template-columns:1fr 320px;

gap:60px;

align-items:center;

}



.hero-text h1{

font-size:clamp(3rem,6vw,4.5rem);

margin-bottom:10px;

animation:fadeUp .8s ease;

}



.headline{

font-size:1.3rem;

margin-bottom:10px;

opacity:.9;

animation:fadeUp .9s ease;

}



.location{

opacity:.7;

margin-bottom:20px;

animation:fadeUp 1s ease;

}



.links{

display:flex;

gap:10px;

flex-wrap:wrap;

animation:fadeUp 1.1s ease;

}



.links a{

border:1px solid rgba(255,255,255,.4);

padding:8px 16px;

border-radius:6px;

text-decoration:none;

color:white;

}



/* Image */

.hero-image-wrapper{

display:flex;

justify-content:center;

}



.hero-image{

width:280px;

height:280px;

object-fit:cover;

border-radius:20px;

box-shadow:0 20px 60px rgba(0,0,0,.25);

animation:fadeUp 1.2s ease;

}



/* Main */

main{

padding:5rem 0;

}



section{

margin-bottom:4rem;

}



h2{

margin-bottom:1.5rem;

font-size:1.4rem;

border-bottom:2px solid var(--primary);

padding-bottom:6px;

}



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

padding:6px 12px;

border-radius:20px;

border:1px solid var(--border);

}



/* Cards */

.experience-item,
.education-item{

background:var(--bg-alt);

padding:1.5rem;

border-radius:10px;

margin-bottom:1rem;

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

@media(max-width:900px){

.hero-grid{

grid-template-columns:1fr;

text-align:center;

}

.hero-image{

width:200px;
height:200px;

margin-top:20px;

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
