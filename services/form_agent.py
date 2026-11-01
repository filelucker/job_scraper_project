import os
import re
import json
import random
import time
import requests
from typing import Dict, Any, List, Optional

class FormAgent:
    """
    Autonomous form inspector and AI responder that analyzes dynamic application fields
    (inputs, textareas, selects, radios, checkboxes, file uploads) and generates
    context-aware answers matching the candidate's profile.
    """

    def __init__(self, gemini_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    def inspect_form(self, page) -> List[Dict[str, Any]]:
        """
        Executes JavaScript on the page to extract all visible, actionable form controls.
        """
        js_inspector = """
        () => {
            const controls = [];
            const isVisible = (elem) => {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                const rect = elem.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && rect.width > 0 && rect.height > 0;
            };

            const getLabel = (elem) => {
                if (elem.getAttribute('aria-label')) return elem.getAttribute('aria-label');
                if (elem.id) {
                    const l = document.querySelector(`label[for="${elem.id}"]`);
                    if (l) return l.innerText.trim();
                }
                const parentLabel = elem.closest('label');
                if (parentLabel) return parentLabel.innerText.trim();
                const container = elem.closest('div, fieldset, .form-group, .field, tr, p');
                if (container) {
                    const labelElem = container.querySelector('label, .label, legend, span.title, h3, h4');
                    if (labelElem && labelElem !== elem) return labelElem.innerText.trim();
                }
                return elem.getAttribute('placeholder') || elem.getAttribute('name') || elem.getAttribute('data-ui') || '';
            };

            const makeSelector = (el, fallbackTag, idx) => {
                if (el.id) return `#${el.id}`;
                if (el.name) return `[name="${el.name}"]`;
                if (el.getAttribute('data-ui')) return `[data-ui="${el.getAttribute('data-ui')}"]`;
                if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
                if (el.getAttribute('placeholder')) return `${fallbackTag}[placeholder="${el.getAttribute('placeholder')}"]`;
                return `${fallbackTag}:nth-of-type(${idx + 1})`;
            };

            // 1. Text, Email, Tel, Number Inputs & Textareas
            document.querySelectorAll('input, textarea').forEach((el, idx) => {
                const type = (el.getAttribute('type') || 'text').toLowerCase();
                if (['hidden', 'submit', 'button', 'reset', 'image'].includes(type)) return;
                if (!isVisible(el) && type !== 'file') return;

                if (['text', 'email', 'tel', 'url', 'number', 'password'].includes(type) || el.tagName.toLowerCase() === 'textarea') {
                    controls.push({
                        kind: 'text',
                        tag: el.tagName.toLowerCase(),
                        type: type,
                        id: el.id || '',
                        name: el.name || '',
                        label: getLabel(el),
                        placeholder: el.placeholder || '',
                        value: el.value || '',
                        required: el.required || el.getAttribute('aria-required') === 'true',
                        selector: makeSelector(el, el.tagName.toLowerCase(), idx),
                        index: idx
                    });
                } else if (type === 'file') {
                    controls.push({
                        kind: 'file',
                        type: 'file',
                        id: el.id || '',
                        name: el.name || '',
                        label: getLabel(el),
                        accept: el.accept || '',
                        required: el.required || false,
                        selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : 'input[type="file"]'),
                        index: idx
                    });
                } else if (type === 'checkbox') {
                    controls.push({
                        kind: 'checkbox',
                        id: el.id || '',
                        name: el.name || '',
                        label: getLabel(el),
                        checked: el.checked,
                        required: el.required || el.getAttribute('aria-required') === 'true',
                        selector: makeSelector(el, 'input[type="checkbox"]', idx),
                        index: idx
                    });
                } else if (type === 'radio') {
                    const rVal = el.value || '';
                    controls.push({
                        kind: 'radio',
                        type: 'radio',
                        id: el.id || '',
                        name: el.name || '',
                        value: rVal,
                        label: getLabel(el),
                        checked: el.checked,
                        required: el.required || el.getAttribute('aria-required') === 'true',
                        selector: el.id ? `#${el.id}` : (el.name ? `input[type="radio"][name="${el.name}"][value="${rVal}"]` : makeSelector(el, 'input[type="radio"]', idx)),
                        index: idx
                    });
                }
            });

            // 2. Select Elements (Dropdowns)
            document.querySelectorAll('select').forEach((sel, idx) => {
                if (!isVisible(sel)) return;
                const options = Array.from(sel.options).map(o => ({
                    value: o.value,
                    text: (o.text || '').trim()
                })).filter(o => o.text.length > 0 && o.value !== '');

                controls.push({
                    kind: 'select',
                    id: sel.id || '',
                    name: sel.name || '',
                    label: getLabel(sel),
                    options: options,
                    required: sel.required || sel.getAttribute('aria-required') === 'true',
                    selector: makeSelector(sel, 'select', idx),
                    index: idx
                });
            });

            return controls;
        }
        """
        try:
            raw_controls = page.evaluate(js_inspector)
            return raw_controls or []
        except Exception as e:
            print(f"[FormAgent] Error inspecting page controls: {e}")
            return []

    def answer_fields(self, controls: List[Dict[str, Any]], candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps extracted form fields to high-confidence candidate answers.
        Uses rule-based heuristics first; delegates ambiguous questions to Gemini/OpenAI.
        """
        answers = {}
        unresolved = []

        for idx, ctrl in enumerate(controls):
            kind = ctrl.get("kind")
            label = (ctrl.get("label") or ctrl.get("placeholder") or ctrl.get("name") or "").lower()
            key = ctrl.get("selector") or f"{kind}_{idx}"
            val = str(ctrl.get("value") or "").lower()
            is_req = ctrl.get("required", False)

            # 1. Experience & Salary
            if any(term in label for term in ["years of experience", "experience in years", "how many years", "total experience"]):
                yoe = str(candidate.get("years_of_experience", 7))
                if kind == "select":
                    answers[key] = self._match_select_option(ctrl.get("options", []), [yoe, "5+", "6+", "7+", "senior"])
                else:
                    answers[key] = yoe
            elif any(term in label for term in ["salary", "compensation", "expected rate", "remuneration", "expected salary"]):
                answers[key] = "Negotiable / Competitive"
            elif any(term in label for term in ["notice period", "start date", "availability", "available from"]):
                answers[key] = candidate.get("work_authorization", {}).get("notice_period", "Immediate / 2 weeks")

            # 2. Standard Identity & Contact Fields
            elif any(term in label for term in ["first name", "given name", "first_name", "firstname"]) or label.strip() == "first":
                answers[key] = candidate.get("first_name", "Md")
            elif any(term in label for term in ["last name", "family name", "surname", "last_name", "lastname"]) or label.strip() == "last":
                answers[key] = candidate.get("last_name", "Moniruzzaman")
            elif any(term in label for term in ["full name", "your name"]) or (label.strip() == "name"):
                answers[key] = candidate.get("full_name", "Md Moniruzzaman")
            elif "email" in label:
                answers[key] = candidate.get("email", "contact@moniruz.dev")
            elif (
                ctrl.get("type") == "tel"
                or any(term in label for term in ["phone", "telephone", "mobile phone", "cell number", "contact number"])
                or label.strip() in ["mobile", "mobile no", "mobile number", "phone number"]
            ):
                answers[key] = candidate.get("phone", "+8801721915013")
            elif "linkedin" in label:
                answers[key] = candidate.get("urls", {}).get("linkedin", "")
            elif "github" in label:
                answers[key] = candidate.get("urls", {}).get("github", "")
            elif any(term in label for term in ["portfolio", "website", "personal site", "public profile"]):
                answers[key] = candidate.get("urls", {}).get("portfolio", "https://moniruz.dev/")
            elif any(term in label for term in ["city", "current city"]):
                answers[key] = candidate.get("city", "Dhaka")
            elif any(term in label for term in ["address", "current location", "residence", "country", "location"]) and "sponsorship" not in label:
                answers[key] = candidate.get("location", "Dhaka, Bangladesh")

            # 3. Work Authorization & Sponsorship
            elif any(term in label for term in ["sponsor", "visa"]):
                requires_sponsor = candidate.get("work_authorization", {}).get("requires_sponsorship", True)
                if kind == "select":
                    answers[key] = self._match_select_option(ctrl.get("options", []), ["yes", "require", "true"])
                elif kind == "checkbox":
                    answers[key] = True if requires_sponsor else False
                elif kind == "radio":
                    is_yes_opt = any(y in val for y in ["yes", "1", "require", "true"])
                    is_no_opt = any(n in val for n in ["no", "0", "false"])
                    if is_yes_opt:
                        answers[key] = requires_sponsor
                    elif is_no_opt:
                        answers[key] = not requires_sponsor
                    else:
                        answers[key] = requires_sponsor
                else:
                    answers[key] = "Yes, will require visa sponsorship."

            elif any(term in label for term in ["authorization", "authorized", "eligible to work", "legally"]):
                auth_us = candidate.get("work_authorization", {}).get("authorized_in_us", False)
                if kind == "select":
                    answers[key] = self._match_select_option(ctrl.get("options", []), ["yes" if auth_us else "no"])
                elif kind == "checkbox":
                    answers[key] = auth_us
                elif kind == "radio":
                    is_yes_opt = any(y in val for y in ["yes", "1", "authorized", "true"])
                    is_no_opt = any(n in val for n in ["no", "0", "false"])
                    if is_yes_opt:
                        answers[key] = auth_us
                    elif is_no_opt:
                        answers[key] = not auth_us
                    else:
                        answers[key] = auth_us
                else:
                    answers[key] = "No" if not auth_us else "Yes"

            # 4. Consent / Terms Checkboxes
            elif kind == "checkbox":
                if is_req or any(term in label for term in ["agree", "consent", "privacy", "terms", "policy", "acknowledge", "certify", "confirm", "gdpr", "accurat"]):
                    answers[key] = True
                else:
                    answers[key] = False

            # 5. Radio buttons (EEO, Demographics, and Fallbacks)
            elif kind == "radio":
                if any(term in label for term in ["gender", "sex"]):
                    answers[key] = True if any(g in val or g in label for g in ["male", "man", "decline"]) else False
                elif any(term in label for term in ["veteran", "military"]):
                    answers[key] = True if any(v in val or v in label for v in ["not", "no", "decline"]) else False
                elif any(term in label for term in ["disability", "handicap"]):
                    answers[key] = True if any(d in val or d in label for d in ["not", "no", "decline"]) else False
                elif is_req:
                    answers[key] = True if ("yes" in val or "agree" in val or idx == 0) else False

            elif is_req and kind == "text":
                answers[key] = "N/A"

            else:
                unresolved.append({"key": key, "control": ctrl})

        # If there are unresolved custom screening questions, query AI
        if unresolved and (self.gemini_api_key or self.openai_api_key):
            ai_answers = self._resolve_with_ai(unresolved, candidate)
            answers.update(ai_answers)

        return answers

    def _match_select_option(self, options: List[Dict[str, str]], target_terms: List[str]) -> Optional[str]:
        """Finds the best matching option value in a <select> element."""
        for opt in options:
            text = opt.get("text", "").lower()
            val = opt.get("value", "").lower()
            for term in target_terms:
                if term in text or term == val:
                    return opt.get("value")
        return options[0].get("value") if options else None

    def _resolve_with_ai(self, unresolved: List[Dict[str, Any]], candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Queries LLM to answer complex/bespoke company questions."""
        questions = []
        for item in unresolved:
            c = item["control"]
            questions.append({
                "key": item["key"],
                "label": c.get("label"),
                "kind": c.get("kind"),
                "options": [o.get("text") for o in c.get("options", [])] if c.get("options") else None
            })

        prompt = f"""You are an autonomous job application agent answering screening questions on behalf of candidate:
Candidate Profile:
{json.dumps(candidate, indent=2)}

Questions to answer:
{json.dumps(questions, indent=2)}

Instructions:
- For text/textarea inputs: provide a concise, highly professional response (1 sentence max unless requested).
- For select dropdowns: choose the exact text matching one of the provided options.
- Return a JSON object where keys are the 'key' strings and values are the chosen answers.
Only return valid JSON."""

        try:
            if self.gemini_api_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                resp = requests.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"}
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)

            elif self.openai_api_key:
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(text)
        except Exception as e:
            print(f"[FormAgent] AI field resolution failed: {e}")

        return {}

    def fill_and_submit(self, page, controls: List[Dict[str, Any]], answers: Dict[str, Any], pdf_path: str, auto_submit: bool = False, candidate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fills the form on the page using human-like typing and option selections.
        Attaches the PDF resume. Handles multi-step form progression and submits.
        """
        filled_count = 0
        resume_attached = False
        submitted = False
        action_type = "none"

        button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button[data-ui="application-form-submit"]',
            'button[data-ui*="submit"]',
            'button[data-qa*="submit"]',
            'button[data-test*="submit"]',
            'button[data-testid*="submit"]',
            'button:has-text("Submit Application")',
            'button:has-text("Submit application")',
            'button:has-text("Submit")',
            'button:has-text("Send Application")',
            'button:has-text("Send application")',
            'button:has-text("Send")',
            'button:has-text("Apply now")',
            'button:has-text("Apply Now")',
            'button:has-text("Apply")',
            'a[role="button"]:has-text("Submit")',
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Save and continue")',
            'button:has-text("Proceed")'
        ]

        step_count = 0
        max_steps = 5
        active_controls = controls
        active_answers = answers

        while step_count < max_steps:
            step_count += 1

            for ctrl in active_controls:
                selector = ctrl.get("selector")
                kind = ctrl.get("kind")
                if not selector:
                    continue

                try:
                    elem = page.query_selector(selector)
                    if not elem:
                        continue

                    if kind == "file":
                        if pdf_path and os.path.exists(pdf_path):
                            abs_pdf = os.path.abspath(pdf_path)
                            elem.set_input_files(abs_pdf)
                            resume_attached = True
                            filled_count += 1
                            time.sleep(0.5)

                    elif kind == "text":
                        answer = active_answers.get(selector)
                        if answer is not None and str(answer).strip():
                            elem.scroll_into_view_if_needed()
                            elem.click()
                            elem.fill("")
                            elem.type(str(answer), delay=random.randint(10, 30))
                            filled_count += 1
                            time.sleep(random.uniform(0.05, 0.2))

                    elif kind == "select":
                        answer = active_answers.get(selector)
                        if answer:
                            elem.scroll_into_view_if_needed()
                            elem.select_option(value=str(answer))
                            filled_count += 1

                    elif kind == "checkbox":
                        should_check = active_answers.get(selector)
                        if should_check:
                            elem.scroll_into_view_if_needed()
                            if not elem.is_checked():
                                elem.check()
                                filled_count += 1

                    elif kind == "radio":
                        should_check = active_answers.get(selector)
                        if should_check:
                            elem.scroll_into_view_if_needed()
                            if not elem.is_checked():
                                elem.check()
                                filled_count += 1

                except Exception:
                    pass

            # Search for submit or next-step button
            submit_btn = None
            action_type = "none"

            for b_sel in button_selectors:
                try:
                    candidate_btn = page.query_selector(b_sel)
                    if candidate_btn and candidate_btn.is_visible():
                        btn_text = (candidate_btn.inner_text() or "").lower()
                        if any(t in btn_text for t in ["next", "continue", "proceed", "save and continue"]):
                            action_type = "next_step"
                        else:
                            action_type = "submit"
                        submit_btn = candidate_btn
                        break
                except Exception:
                    pass

            if not submit_btn:
                break

            if action_type == "next_step":
                print(f"[FormAgent] Multi-step form step {step_count}: advancing...")
                try:
                    submit_btn.scroll_into_view_if_needed()
                    submit_btn.click()
                    time.sleep(2)
                    # Re-inspect controls for next step
                    active_controls = self.inspect_form(page)
                    if candidate:
                        active_answers = self.answer_fields(active_controls, candidate)
                    continue
                except Exception as e:
                    print(f"[FormAgent] Multi-step advance error: {e}")
                    break

            elif action_type == "submit":
                if auto_submit:
                    print(f"[FormAgent] Clicking submit application button...")
                    try:
                        submit_btn.scroll_into_view_if_needed()
                        submit_btn.click(timeout=6000)
                    except Exception:
                        page.evaluate("btn => btn.click()", submit_btn)

                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass
                    time.sleep(2)
                    submitted = True
                break

        return {
            "filled_fields_count": filled_count,
            "resume_attached": resume_attached,
            "action_type": action_type,
            "submitted": submitted
        }
