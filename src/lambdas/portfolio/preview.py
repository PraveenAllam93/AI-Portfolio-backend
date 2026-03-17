import http.server
import socketserver
import importlib
import os

# Templates list
TEMPLATES = [
    "apple",
    "modern",
    "minimal",
    "bold",
    "creative",
    "executive",
    "luxury",
    "nebula",
    "aurora",
    "designer",
    "glass",
    "split",
    "timeline",
    "gradient_hero",
    "hero_image",
]


# Dummy Resume Data
dummy_data = {
    "name": "Alex Johnson",
    "title": "Senior Software Engineer",
    "headline": "Building scalable cloud platforms",
    "bio": "Senior engineer with 8+ years building distributed systems and modern cloud infrastructure.",
    "email": "alex@example.com",
    "location": "San Francisco",
    "skills": [
        "Python",
        "AWS",
        "React",
        "Docker",
        "Kubernetes",
        "PostgreSQL",
        "Terraform",
        "NodeJS",
    ],
    "linkedin_url": "https://linkedin.com",
    "github_url": "https://github.com",
    "profile_image": "https://picsum.photos/400",
    "experience": [
        {
            "title": "Senior Engineer",
            "company": "Google",
            "duration": "2022 — Present",
            "description": "Building infrastructure platforms",
            "highlights": [
                "Scaled API to 5M users",
                "Reduced cost 30%",
                "Led platform team",
            ],
        },
        {
            "title": "Engineer",
            "company": "Amazon",
            "duration": "2019 — 2022",
            "description": "Worked on distributed systems",
            "highlights": ["Built microservices", "Improved latency", "Led migration"],
        },
    ],
    "education": [
        {
            "degree": "B.Tech",
            "field": "Computer Science",
            "institution": "MIT",
            "year": "2018",
        }
    ],
}


def generate():

    os.makedirs("output", exist_ok=True)

    for t in TEMPLATES:
        mod = importlib.import_module(f"templates.{t}")

        html = mod.html(dummy_data)
        css = mod.css()

        folder = f"output/{t}"

        os.makedirs(folder, exist_ok=True)

        open(f"{folder}/index.html", "w").write(html)
        open(f"{folder}/styles.css", "w").write(css)


generate()


# Simple server


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):

        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = "<h1>Template Preview</h1>"

            for t in TEMPLATES:
                html += f'<p><a href="/output/{t}/index.html">{t}</a></p>'

            self.wfile.write(html.encode())

        else:
            super().do_GET()


PORT = 8000

socketserver.TCPServer(("", PORT), Handler).serve_forever()
