import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GROQ_API_KEY")

email_text = """Dear Santhosh A.P,

You are now officially registered for Datathon 2026, presented by Karnataka State Police, powered by Hack2skill, with Zoho as the Technology Partner.

We are excited to welcome you to a nationwide innovation challenge where developers, data enthusiasts, analysts, and problem-solvers come together to build impactful solutions for real-world public safety and policing challenges.

What’s Next?

Form Your Team
Participants can compete individually or form teams of 2 to 5 members. If you haven’t formed your team yet, now is the perfect time to collaborate with like-minded innovators and start building your idea.
Explore the Platform
The Catalyst by Zoho module and platform access will go live on 28 May. We encourage you and your team to explore the platform capabilities and get familiar with the tools available.
Start Preparing Your Prototype
Prototype submissions will officially open on 28 May. Begin brainstorming ideas, identifying the problem statement you want to solve, and preparing your solution approach.
Stay Connected
Keep an eye on your inbox and the official event page for important announcements, workshops, mentorship sessions, timelines, and submission updates.
Gear Up for Demo Day
Shortlisted teams will get an opportunity to showcase their solutions during the in-person Demo Day before industry experts, mentors, and stakeholders.
If you have any questions or need assistance at any stage of the hackathon, feel free to reach out to the organizing team.

Thank you for being a part of Datathon 2026. We look forward to seeing your innovation come to life.

Best Regards,
Team Hack2skill"""

prompt = f"""You are an expert AI Data Extraction & Enrichment Agent.
Extract hackathon details from the following email text:

EMAIL TEXT:
\"\"\"{email_text}\"\"\"

Target fields: name, organizer, theme, registration_deadline, submission_deadline, prize_pool, eligibility, team_size, mode, official_website.

Respond in JSON format:
{{
  "extracted_fields": {{
     "name": "extracted name string or null",
     "organizer": "extracted organizer string or null",
     "theme": "extracted theme string or null",
     "registration_deadline": "extracted date string or null",
     "submission_deadline": "extracted date string or null",
     "prize_pool": "extracted prize string or null",
     "eligibility": "extracted string or null",
     "team_size": "extracted string or null",
     "mode": "extracted string or null",
     "official_website": "extracted URL string or null"
  }}
}}
"""

client = httpx.Client(timeout=15.0)
for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]:
    resp = client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
    )
    print(f"Model: {model} | Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Output:")
        print(json.dumps(resp.json()["choices"][0]["message"]["content"], indent=2))
        break
