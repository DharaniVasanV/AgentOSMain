import os
import json
import asyncio
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

MOCK_DEMO_QUESTIONS = [
    {"field_id": "q1_fullname",  "question_text": "What is your full name?",                          "field_type": "short_text", "is_required": True,  "options": []},
    {"field_id": "q2_email",     "question_text": "Email Address",                                    "field_type": "short_text", "is_required": True,  "options": []},
    {"field_id": "q3_phone",     "question_text": "Phone Number",                                     "field_type": "short_text", "is_required": False, "options": []},
    {"field_id": "q4_role",      "question_text": "Preferred Job Role / Title",                       "field_type": "dropdown",   "is_required": True,  "options": ["Software Engineer", "Product Manager", "Data Scientist", "UI/UX Designer", "DevOps Engineer"]},
    {"field_id": "q5_experience","question_text": "Years of Professional Experience",                 "field_type": "radio",      "is_required": True,  "options": ["0-1 Years", "2-4 Years", "5-8 Years", "9+ Years"]},
    {"field_id": "q6_skills",    "question_text": "Technical Skills (Select all that apply)",         "field_type": "checkbox",   "is_required": False, "options": ["Python", "JavaScript / HTML / CSS", "Docker / Kubernetes", "SQL & Databases", "Cloud Platforms (AWS/GCP)"]},
    {"field_id": "q7_bio",       "question_text": "Briefly describe your career goals and background","field_type": "paragraph",  "is_required": False, "options": []},
    {"field_id": "q8_location",  "question_text": "City / Current Location",                          "field_type": "short_text", "is_required": True,  "options": []},
    {"field_id": "q9_resume",    "question_text": "Upload Resume / CV (PDF or DOCX)",                 "field_type": "file",       "is_required": False, "options": []},
]


def _clean_url(form_url: str) -> str:
    url = form_url.strip()
    if "/edit" in url:
        url = url.split("/edit")[0] + "/viewform"
    # Strip usp param — causes forced login even on public forms
    if "?" in url:
        base, params = url.split("?", 1)
        kept = "&".join(p for p in params.split("&") if not p.startswith("usp="))
        url = f"{base}?{kept}" if kept else base
    return url


async def parse_google_form(form_url: str, user_email: str = "default"):
    clean = _clean_url(form_url)
    logger.info(f"Parsing form URL: {clean}")

    if clean.lower() in ["demo", "test", "example"]:
        return {"title": "Job Application & Developer Survey 2026", "description": "", "questions": MOCK_DEMO_QUESTIONS}

    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(pool, lambda: asyncio.run(_playwright_parse(clean, user_email)))
    except Exception as err:
        logger.error(f"Form parse error: {err}")
        return {"error": str(err), "title": "Extraction Failed", "questions": []}


async def _playwright_parse(clean_url: str, user_email: str = "default"):
    from playwright.async_api import async_playwright
    from services.google_auth import is_google_login_page, google_authenticate

    user_data_dir = os.path.abspath(f"user_data_{user_email}")
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900}
            )
            page = context.pages[0] if context.pages else await context.new_page()

            response = await page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            page_title = await page.title()

            # 404 check
            if (response and response.status == 404) or "Page not found" in page_title:
                return {"error": "Google Form not found (404). Please check the URL.", "title": "Not Found", "questions": []}

            # Auth check
            if await is_google_login_page(page, page_title):
                authenticated, auth_error = await google_authenticate(page)
                if not authenticated:
                    return {"error": auth_error or "Form requires Google login but authentication failed.", "title": "Auth Required", "questions": []}
                # After auth, Google redirects automatically — just wait, don't goto again
                await page.wait_for_timeout(4000)
                try:
                    await page.wait_for_url(lambda url: "accounts.google.com" not in url, timeout=15000)
                except Exception:
                    pass
                await page.wait_for_timeout(2000)
                page_title = await page.title()

            # Wait for form content
            try:
                await page.wait_for_selector(
                    '[jsmodel], div[data-params], div.freebirdFormviewerViewItemsItemItem, div[role="listitem"]',
                    timeout=15000
                )
            except Exception:
                pass

            form_title = page_title
            try:
                t = await page.query_selector('div[role="heading"], h1, div.freebirdFormviewerViewHeaderHeader')
                if t:
                    txt = (await t.inner_text()).strip()
                    if txt:
                        form_title = txt
            except Exception:
                pass

            questions = await _extract_questions(page)

            if questions:
                return {"title": form_title or "Google Form", "description": "Extracted via Playwright.", "questions": questions}
            else:
                # Save HTML for debugging
                try:
                    html = await page.evaluate("document.body.innerHTML")
                    with open("debug_form_dump.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.warning("No questions found — HTML saved to debug_form_dump.html")
                except Exception:
                    pass
                return {"error": "Failed to fetch form questions from the URL. Please make sure the Google Form is valid and publicly accessible.", "title": "Extraction Failed", "questions": []}

        except Exception as err:
            logger.error(f"Playwright parse error: {err}")
            return {"error": f"Failed to fetch form from URL: {err}", "title": "Extraction Failed", "questions": []}
        finally:
            await context.close()


async def _extract_questions(page) -> list:
    """Try multiple selector strategies to extract questions from Google Forms."""
    questions = []

    # Strategy 1: Find all blocks that have data-params or match standard question item classes
    blocks = await page.query_selector_all('div[data-params], div.geS5ne, div[jsmodel][data-params]')
    if not blocks:
        # Strategy 2: Classic selectors
        blocks = await page.query_selector_all(
            'div.freebirdFormviewerViewItemsItemItem, '
            'div.freebirdFormviewerViewItemsItemItemContainer, '
            'div[role="listitem"], '
            'div.QrShb'
        )
    if not blocks:
        # Strategy 3: Any block containing a heading + input
        blocks = await page.query_selector_all('div[jscontroller]')

    logger.info(f"Found {len(blocks)} question blocks")

    idx = 1
    seen_texts = set()

    for block in blocks:
        try:
            # Try to extract details from data-params first (highly reliable for modern Google Forms)
            data_params_str = await block.get_attribute("data-params")
            parsed_from_params = False
            question_text = ""
            field_type = "short_text"
            options = []

            if data_params_str:
                try:
                    clean_str = data_params_str.strip()
                    if clean_str.startswith("%.@."):
                        clean_str = clean_str[5:]
                    data = json.loads(clean_str)
                    
                    if len(data) >= 4:
                        raw_q_text = str(data[1] or "")
                        question_text = raw_q_text.replace("*", "").split("\n")[0].strip().rstrip(":")
                        
                        type_id = data[3]
                        type_mapping = {
                            0: "short_text",
                            1: "paragraph",
                            2: "radio",
                            3: "dropdown",
                            4: "checkbox",
                            9: "file",
                            10: "date",
                            11: "time"
                        }
                        field_type = type_mapping.get(type_id, "short_text")
                        
                        # Extract choices/options for multiple choice, dropdowns, checkboxes
                        if type_id in (2, 3, 4) and len(data) > 4 and data[4]:
                            options_data = data[4][0][1]
                            for opt_item in options_data:
                                if opt_item and len(opt_item) > 0 and opt_item[0] is not None:
                                    options.append(str(opt_item[0]).strip())
                        
                        parsed_from_params = True
                except Exception as pe:
                    logger.warning(f"Failed to parse data-params JSON: {pe}")

            # Fallback to DOM selectors if data-params extraction failed
            if not question_text:
                heading = await block.query_selector(
                    'span.M7eMe, '
                    'div[role="heading"], '
                    'div.freebirdFormviewerViewItemsItemItemTitle, '
                    'div.freebirdFormviewerComponentsQuestionBaseTitle'
                )
                if not heading:
                    continue

                raw = (await heading.inner_text()).strip()
                if not raw or len(raw) < 2:
                    continue

                question_text = raw.replace("*", "").split("\n")[0].strip().rstrip(":")

            if not question_text or question_text in seen_texts:
                continue
            seen_texts.add(question_text)

            # Required check
            req_elem = await block.query_selector('span.vnumgf, span[aria-label*="required" i], span[aria-label*="Required"]')
            is_required = req_elem is not None

            if not parsed_from_params:
                field_type, options = await _detect_field_type(block, page, question_text)

            questions.append({
                "field_id": f"q_{idx}",
                "question_text": question_text,
                "field_type": field_type,
                "is_required": is_required,
                "options": options
            })
            idx += 1

        except Exception as e:
            logger.warning(f"Block parse error: {e}")

    return questions


async def _detect_field_type(block, page, question_text: str) -> tuple:
    q_lower = question_text.lower()
    options = []

    # Date
    if any(k in q_lower for k in ["date of birth", "dob", "birth date", "expiry date", "start date", "end date", "date"]):
        return "date", []
    date_inp = await block.query_selector('input[type="date"], [aria-label*="date" i]')
    if date_inp:
        return "date", []

    # Time
    if "time" in q_lower:
        return "time", []
    time_inp = await block.query_selector('input[type="time"], [aria-label*="time" i]')
    if time_inp:
        return "time", []

    # File upload
    if any(k in q_lower for k in ["upload", "resume", "cv", "attach"]):
        return "file", []
    file_inp = await block.query_selector('input[type="file"], [aria-label*="Add file" i]')
    if file_inp:
        return "file", []

    # Radio
    radios = await block.query_selector_all('div[role="radio"], label input[type="radio"]')
    if radios:
        for r in radios:
            lbl = await r.evaluate('el => el.getAttribute("aria-label") || el.closest("label")?.innerText || el.innerText || ""')
            if lbl and lbl.strip():
                options.append(lbl.strip())
        return "radio", options

    # Checkbox
    checkboxes = await block.query_selector_all('div[role="checkbox"], label input[type="checkbox"]')
    if checkboxes:
        for c in checkboxes:
            lbl = await c.evaluate('el => el.getAttribute("aria-label") || el.closest("label")?.innerText || el.innerText || ""')
            if lbl and lbl.strip():
                options.append(lbl.strip())
        return "checkbox", options

    # Dropdown
    listbox = await block.query_selector('div[role="listbox"], select')
    if listbox:
        opts = await block.query_selector_all('div[role="option"], option')
        for o in opts:
            t = (await o.inner_text()).strip()
            if t and t not in ("Choose", "Select"):
                options.append(t)
        return "dropdown", options

    # Paragraph / long text
    textarea = await block.query_selector('textarea')
    if textarea:
        return "paragraph", []

    # Short text (default)
    return "short_text", []
