"""
Template: Apple

Premium Apple-style portfolio.

Features:
- Extremely clean layout
- Huge typography
- Soft gray backgrounds
- Large whitespace
- Smooth fade animations
- Premium feel
- Recruiter friendly
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

<meta name="viewport" content="width=device-width">

<meta http-equiv="Content-Security-Policy" content="{CSP}">

<title>{v["name"]} Portfolio</title>

<link rel="stylesheet" href="styles.css">

<link href="{FONTS_URL}" rel="stylesheet">

</head>



<body>



<header class="hero">

<div class="container">

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




<main>



<div class="section-grid container">

<section class="intro">

<p>

{v["bio"]}

</p>

</section>


<section class="section">

<h2>Skills</h2>

<div class="skills">

{skills_html}

</div>

</section>

</div>




<section class="section container">

<h2>Experience</h2>

{experience_html}

</section>




<section class="section container">

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

--text:#111;

--muted:#6e6e73;

--bg:#ffffff;

--bg-alt:#f5f5f7;

--border:#e5e5e5;

}



*{
margin:0;
padding:0;
box-sizing:border-box;
}



body{

font-family:-apple-system,
BlinkMacSystemFont,
'Inter',
sans-serif;

background:var(--bg);

color:var(--text);

line-height:1.7;

}



/* Layout */

.container{

max-width:900px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

padding:7rem 0 5rem;

text-align:center;

border-bottom:1px solid var(--border);

animation:fade .8s ease;

}



.hero h1{

font-size:clamp(3rem,6vw,4.5rem);

font-weight:600;

letter-spacing:-1px;

margin-bottom:12px;

}



.headline{

font-size:1.4rem;

color:var(--muted);

margin-bottom:8px;

}



.location{

color:var(--muted);

margin-bottom:22px;

}



/* Links */

.links{

display:flex;

justify-content:center;

gap:14px;

flex-wrap:wrap;

}



.links a{

color:#0066cc;

text-decoration:none;

font-weight:500;

font-size:0.95rem;

}



.links a:hover{

text-decoration:underline;

}



/* Intro */

.intro{

padding:5rem 0;

font-size:1.3rem;

color:#1d1d1f;

max-width:720px;

text-align:center;

animation:fadeUp 1s ease;

}



/* Sections */

.section{

padding:4rem 0;

border-top:1px solid var(--border);

animation:fadeUp 1s ease;

}



.section h2{

font-size:1.8rem;

margin-bottom:2rem;

font-weight:600;

}



/* Skills */

.skills{

display:flex;

flex-wrap:wrap;

gap:10px;

}



.skill{

background:var(--bg-alt);

padding:8px 16px;

border-radius:20px;

font-size:.9rem;

}



.skill:hover{

background:#e8e8ed;

}



/* Experience */

.experience{

margin-bottom:2.5rem;

}



.job-title{

font-weight:600;

font-size:1.1rem;

margin-bottom:3px;

}



.job-company{

color:var(--muted);

margin-bottom:4px;

}



.job-duration{

color:var(--muted);

font-size:.85rem;

margin-bottom:10px;

}



.job-description{

color:#1d1d1f;

}



.job-list{

margin-top:8px;

padding-left:18px;

}



.job-list li{

margin-bottom:4px;

color:var(--muted);

}



/* Education */

.edu{

margin-bottom:2rem;

}



.edu-title{

font-weight:600;

}



.edu-meta{

color:var(--muted);

}



/* Footer */

footer{

padding:3rem 0;

text-align:center;

color:var(--muted);

background:var(--bg-alt);

}



/* Animations */

@keyframes fade{

from{opacity:0}
to{opacity:1}

}



@keyframes fadeUp{

from{
opacity:0;
transform:translateY(25px);
}

to{
opacity:1;
transform:translateY(0);
}

}



/* Mobile */

@media(max-width:640px){

.hero{

padding:4rem 0 3rem;

}


.hero h1{

font-size:2.2rem;

}


.intro{

font-size:1.1rem;

padding:3rem 0;

}

}



@media(min-width:900px){

.section-grid{

display:grid;

grid-template-columns:3fr 2fr;

gap:3rem;

align-items:start;

padding-top:3rem;

padding-bottom:2rem;

}

.section-grid .intro{

text-align:left;

max-width:none;

padding:0;

}

.section-grid .section{

padding:0;

border-top:none;

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
            f'<div class="job-title">{exp["title"]}</div>'
            f'<div class="job-company">{exp["company"]}</div>'
            f'<div class="job-duration">{exp["duration"]}</div>'
            f'<div class="job-description">{exp["description"]}</div>'
            f'<ul class="job-list">{highlights}</ul>'
            f"</div>"
        )

    return out


def _education(items: list) -> str:

    out = ""

    for edu in items:
        out += (
            f'<div class="edu">'
            f'<div class="edu-title">'
            f"{edu['degree']} {edu['field']}"
            f"</div>"
            f'<div class="edu-meta">'
            f"{edu['institution']} {edu['year']}"
            f"</div>"
            f"</div>"
        )

    return out
