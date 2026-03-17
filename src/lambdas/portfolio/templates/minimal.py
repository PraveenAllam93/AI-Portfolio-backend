"""
Template: Minimal (v2 Premium Clean)

Upgrades:
- Wider layout
- Premium spacing
- Professional experience layout
- Strong minimal typography
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

<h1>{v["name"]}</h1>

<p class="headline">
{v["headline"]}
</p>


<div class="meta">

<span>{v["location"]}</span>

<div class="links">

{links_html}

{email_link}

</div>

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

Generated with AI Portfolio Builder

</div>

</footer>


</body>
</html>
"""


def css() -> str:

    return """

:root{

--ink:#111827;
--muted:#6b7280;

--border:#e5e7eb;

--bg:#ffffff;

}


*{

margin:0;
padding:0;
box-sizing:border-box;

}



body{

font-family:'Inter',sans-serif;

background:var(--bg);

color:var(--ink);

line-height:1.7;

}



/* Container Upgrade */

.container{

max-width:1100px;

margin:auto;

padding:0 2rem;

}



/* Hero */

.hero{

padding:5rem 0 4rem;

border-bottom:3px solid black;

}



.hero h1{

font-size:clamp(2.8rem,5vw,3.8rem);

margin-bottom:.6rem;

letter-spacing:-.03em;

}



.headline{

font-size:1.2rem;

color:var(--muted);

margin-bottom:1.5rem;

max-width:700px;

}



.meta{

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

text-decoration:none;

color:black;

border-bottom:1px solid var(--border);

padding-bottom:2px;

}



/* Main */

main{

padding:5rem 0;

}



section{

margin-bottom:4rem;

}



h2{

font-size:.75rem;

letter-spacing:.15em;

text-transform:uppercase;

color:var(--muted);

margin-bottom:1.5rem;

display:flex;

gap:12px;

align-items:center;

}



h2::after{

content:"";

flex:1;

height:1px;

background:var(--border);

}



/* Bio */

.bio{

max-width:700px;

line-height:1.9;

color:#374151;

}



/* Skills */

.skills-container{

display:flex;

flex-wrap:wrap;

gap:8px;

}



.skill-tag{

border:1px solid var(--border);

padding:6px 12px;

font-size:.85rem;

}



/* Experience Premium */

.experience-item{

margin-bottom:2.5rem;

padding-bottom:2rem;

border-bottom:1px solid var(--border);

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

color:var(--muted);

font-size:.9rem;

}



.exp-duration{

font-size:.8rem;

color:var(--muted);

}



.experience-item p{

margin-top:8px;

color:#374151;

}



.experience-item ul{

margin-top:10px;

padding-left:18px;

}



.education-item{

margin-bottom:1.5rem;

}



/* Footer */

footer{

border-top:1px solid var(--border);

padding:2rem 0;

text-align:center;

color:var(--muted);

}



/* Mobile */

@media(max-width:800px){

.hero{

padding:3rem 0;

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
