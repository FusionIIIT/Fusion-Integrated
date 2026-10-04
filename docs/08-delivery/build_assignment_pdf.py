from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, HRFlowable,
)

NAVY = colors.HexColor("#1B2A4A")
TEXT = colors.HexColor("#1F1F1F")
MUTED = colors.HexColor("#5B5B5B")
RULE = colors.HexColor("#D0D0D0")
PAGE_W = 17 * cm

title_style = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, spaceAfter=6)
subtitle_style = ParagraphStyle("Subtitle", fontName="Helvetica-Oblique", fontSize=10.5, textColor=MUTED, spaceAfter=14)
h1_style = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=13.5, textColor=NAVY, spaceBefore=16, spaceAfter=8)
body_style = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.3, leading=15, textColor=TEXT, alignment=TA_JUSTIFY, spaceAfter=8)
bullet_style = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=10.3, leading=14.5, textColor=TEXT)
check_style = ParagraphStyle("Check", fontName="Helvetica", fontSize=10.1, leading=14.5, textColor=TEXT)
code_style = ParagraphStyle("Code", fontName="Courier", fontSize=9.3, textColor=NAVY)
cell_style = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9.8, leading=13, textColor=TEXT)
cell_head_style = ParagraphStyle("CellHead", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white)


def para(text, style=body_style):
    return Paragraph(text, style)


def bullets(items, style=bullet_style):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=6) for t in items],
        bulletType="bullet", leftIndent=16, bulletFontSize=8,
    )


def numbered(items, style=bullet_style):
    flows = []
    for i, t in enumerate(items, start=1):
        row = Table([[Paragraph(f"{i}.", code_style), Paragraph(t, style)]],
                    colWidths=[0.7 * cm, PAGE_W - 0.7 * cm])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        flows.append(row)
    return flows


def checklist(items):
    rows = []
    for t in items:
        row = Table([[Paragraph("[ ]", check_style), Paragraph(t, check_style)]],
                    colWidths=[0.8 * cm, PAGE_W - 0.8 * cm])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        rows.append(row)
    return rows


def hr():
    return HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=4, spaceAfter=10)


def step_heading(n, title):
    return para(f"Step {n} — {title}", h1_style)


doc = SimpleDocTemplate(
    "/Users/vikrant/Documents/Fusion/Fusion-Integrated/docs/08-delivery/student-assignment-guide.pdf",
    pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    title="New Module Assignment — Student Guide",
)

story = []
story.append(para("New Module Assignment", title_style))
story.append(para("Student Guide — Fusion-Integrated", subtitle_style))
story.append(para(
    "How a student picks up a new-module assignment and runs <font name='Courier'>new-module-prompt.md</font> "
    "end to end. This is the wrapper around that prompt, not a replacement for it — read both.",
    body_style))
story.append(hr())

story.append(para(
    "<b>This is real work on a real platform.</b> The module you are assigned will go into "
    "production if it clears review. There is no simplified version of the standard for a "
    "student assignment — <font name='Courier'>definition-of-done.md</font> and §8 of the "
    "prompt apply exactly as written.", body_style))
story.append(para(
    "You have to follow these steps in order. Do not skip ahead to Step 5 because you already "
    "know what the prompt says — Steps 1 through 4 are what make the prompt work for your "
    "specific module, and every one of them is something you do, not something that happens "
    "for you.", body_style))

story.append(step_heading(1, "Find out your assignment"))
story.append(para("You have to ask your mentor for these before you open anything else:", body_style))
story.extend(numbered([
    "<b>Module name</b> — what you are building.",
    "<b>Spec folder path</b> — where the BR (business rules), UC (use cases), and workflow "
    "documents for your module live. If this does not exist yet, you have to say so now — "
    "writing a module against a spec you wrote yourself is not this exercise.",
    "<b>Module code</b> — a short, lowercase, singular-ish slug for it (no underscores). "
    "You have to agree this with your mentor — do not invent it on your own.",
]))
story.append(para(
    "Do not guess any of these. Getting one wrong — especially the environment value in "
    "Step 4 — sends you reading for files that do not exist on your machine.", body_style))

story.append(step_heading(2, "Read your own module's requirement specification documents"))
story.append(para(
    "<font name='Courier'>modules/placement</font> and <font name='Courier'>modules/leave</font> "
    "are reference modules the <b>prompt</b> already tells the AI to read, as part of its own "
    "Phase 0 (Step 1.2) — that reading is the AI's job, not yours, and you do not need to open "
    "that code yourself.", body_style))
story.append(para(
    "Your job here is different: you have to read every BR (business rule), UC (use case), and "
    "workflow document in your <font name='Courier'>SPEC_FOLDER_PATH</font> yourself, before you "
    "ever open the prompt. You need to actually understand what you are asking the AI to build, "
    "because:", body_style))
story.append(bullets([
    "Phase 1 (Step 2.1–2.8 of the prompt) asks <b>you</b> real questions — you have to "
    "answer them from knowledge of your own spec, not guess at what sounds right.",
    "Phase 2's blueprint needs <b>your</b> approval before any code gets written — "
    "approving something you have not read defeats the entire point of that gate.",
    "If the AI derives a role in Step 2.4 because nobody handed it a role list, you are the one "
    "who has to catch it if that derived role is wrong — you cannot catch a wrong reading "
    "of your spec if you never read the spec yourself.",
]))

story.append(step_heading(3, "Set up your environment"))
story.append(para(
    "You get the <b>module-only</b> environment — <font name='Courier'>Fusion_System_Administrator</font> "
    "and <font name='Courier'>Fusion-Integrated</font> checked out, <font name='Courier'>fusionlab</font> "
    "restored from the public <font name='Courier'>fusion-dev.dump</font> (Fusion-README). You will "
    "not be given <font name='Courier'>Fusion</font> or <font name='Courier'>Fusion-client</font> "
    "checkouts, and you do not need them — the prompt's §1 tells you exactly what to read "
    "instead.", body_style))
story.append(para("You have to confirm all of this before you go further:", body_style))
story.extend(checklist([
    "<font name='Courier'>docker compose up</font> brings up postgres, redis, the IAM and the platform, all healthy",
    "<font name='Courier'>cd client &amp;&amp; npm run dev</font> runs standalone — this is where you will demo your module",
    "You can log in with a test account and see <font name='Courier'>modules/placement</font> and <font name='Courier'>modules/leave</font> working, so you know the fixture is actually loaded",
]))

story.append(step_heading(4, "Fill in the prompt's five blanks, before you paste anything"))
story.append(para(
    "Open <font name='Courier'>new-module-prompt.md</font> but do not paste it yet. You have to "
    "write down the five values that go in its §0 first, using what you got in Step 1:", body_style))
table_data = [
    [Paragraph("Blank", cell_head_style), Paragraph("Your value", cell_head_style), Paragraph("How you get it", cell_head_style)],
    [Paragraph("MODULE_NAME", code_style), Paragraph("you fill this in", cell_style), Paragraph("you asked your mentor in Step 1", cell_style)],
    [Paragraph("SPEC_FOLDER_PATH", code_style), Paragraph("you fill this in", cell_style), Paragraph("you asked your mentor in Step 1", cell_style)],
    [Paragraph("ID_PREFIX", code_style), Paragraph("you fill this in", cell_style), Paragraph("you read it off the spec documents yourself, once you have the folder", cell_style)],
    [Paragraph("module_code", code_style), Paragraph("you fill this in", cell_style), Paragraph("you agreed it with your mentor in Step 1", cell_style)],
    [Paragraph("ENVIRONMENT", code_style), Paragraph("module-only", cell_style), Paragraph("fixed — this is the value for every student assignment", cell_style)],
]
tbl = Table(table_data, colWidths=[3.6 * cm, 2.9 * cm, PAGE_W - 6.5 * cm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("GRID", (0, 0), (-1, -1), 0.5, RULE),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(tbl)
story.append(Spacer(1, 0.3 * cm))
story.append(para(
    "You have to fill these into the prompt text itself before you paste it. Do not paste the "
    "prompt with the bracketed placeholders still in it and fill them in afterward — the "
    "AI session needs the real values from the first line.", body_style))

story.append(step_heading(5, "Paste the prompt into a fresh AI session"))
story.append(para(
    "You have to copy everything between <font name='Courier'>--- PROMPT BEGINS ---</font> and "
    "<font name='Courier'>--- PROMPT ENDS ---</font>, with your five blanks already filled in, "
    "into a <b>brand-new</b> AI coding session — not one that already has other context in "
    "it. Do not summarise the prompt, do not trim it, do not paraphrase a section you think you "
    "already understand. The length is deliberate.", body_style))

story.append(step_heading(6, "Work through the prompt's own steps"))
story.append(para(
    "From here the prompt drives itself — it is itself written as an explicit numbered "
    "sequence (Step 0.1 through Step 7.6, covering read → questions → blueprint → "
    "backend → tests → frontend → ops). At each one, you have to <b>answer what it "
    "asks and get approval where it asks for approval</b> — you do not get to skip ahead "
    "because a later step looks easy.", body_style))
story.append(para(
    "Two stops matter more than the rest, because they are where a student assignment most "
    "often goes wrong:", body_style))
story.append(bullets([
    "<b>You must not write any application code before your mentor approves the Step "
    "3.1–3.8 blueprint.</b> You have to post the blueprint "
    "(<font name='Courier'>docs/[NN]-[module_code]/[module_code]-blueprint.md</font>) and wait "
    "for a yes. The blueprint is the review, not a formality before the real work.",
    "<b>You have to stop and report, not guess, when</b>: a spec file is missing, two spec "
    "documents contradict each other, the spec conflicts with the platform's architecture, or "
    "you would otherwise have to invent the intended behaviour — including a role nobody "
    "gave you and no BR/UC/workflow document names (Step 2.4 of the prompt). Report the "
    "specific gap. An assignment where you report three honest open questions is worth more "
    "than one where you guessed and built on it.",
]))
story.append(para(
    "The one thing you resolve yourself, no exception: if matching the spec or the reference "
    "modules would weaken security or cross a data-isolation boundary, you refuse it and say "
    "why — you do not escalate this one, you just refuse it.", body_style))

story.append(step_heading(7, "Create your own branch"))
story.append(para(
    "You have to fork <font name='Courier'>Fusion-Integrated</font> if you have not already, "
    "then create <b>your own branch</b> off <font name='Courier'>main</font> — you do not "
    "share a branch with another student, and you do not commit to "
    "<font name='Courier'>main</font> directly. Name it for your module: "
    "<font name='Courier'>module/&lt;module_code&gt;</font>.", body_style))

story.append(step_heading(8, "Commit correctly"))
story.append(bullets([
    "You have to commit under <b>your own GitHub identity</b>. No AI attribution anywhere "
    "— not in code, comments, commit messages, or the PR body. This is §8 item 8 of "
    "the prompt, and it is not negotiable.",
    "You have to keep production data out of every commit, PR body, and doc — no real "
    "roll numbers, names, or person ids. Use the synthetic "
    "<font name='Courier'>fusion-dev.dump</font> accounts for every example instead.",
    "You must not commit, push, or open the PR until your mentor tells you the module is ready "
    "for it. An earlier “go ahead” does not carry forward to the next phase — you "
    "have to ask again.",
]))

story.append(step_heading(9, "Open your pull request"))
story.append(para(
    "You have to open the PR <b>from your branch to <font name='Courier'>main</font></b> on "
    "<font name='Courier'>FusionIIIT/Fusion-Integrated</font> — not to any other base "
    "branch, and not to your fork's own <font name='Courier'>main</font>. Link the blueprint "
    "and the spec folder it implements in the description.", body_style))

story.append(step_heading(10, "Self-check against the definition of done, before requesting review"))
story.append(para(
    "You have to pull the full checklist from the prompt's §8 and "
    "<font name='Courier'>definition-of-done.md</font>'s “A pull request” and “A "
    "module” sections, and run it on yourself before you ask anyone to review. The short "
    "version:", body_style))
story.extend(checklist([
    "<font name='Courier'>make check</font> and <font name='Courier'>make check-client</font> both green — tsc finished, not just npm test",
    "Every live spec id is implemented and cited at its enforcement point, or listed as a known gap with a reason; no retired id cited anywhere",
    "Fresh database → migrate → seed → grant → first user action succeeds — you have to prove this by doing it once, not by reasoning about it",
    "The adversarial pass (Step 5.11 of the prompt) was actually run, not skipped",
    "Every scheduled task was run manually once",
    "No comment longer than one line anywhere in the diff",
    "No credential anywhere in a tracked file",
    "The plain user — the one with no interesting roles — was tested, not only the interesting accounts",
    "Every role in your permission list traces back to Step 1's assignment or to a cited BR/UC/workflow id from Step 2.4 of the prompt — none of them invented",
]))
story.append(para(
    "If you cannot check every box, you have to say which ones are open in the PR description. "
    "A PR that lists its own gaps honestly is reviewable; one that claims a green checklist it "
    "did not actually run is not.", body_style))

story.append(para("If you get stuck", h1_style))
story.append(para(
    "You have to re-read §0's stop conditions in the prompt before asking. If what you "
    "have is genuinely one of them — a missing file, a contradiction, an architecture "
    "conflict, or a guess you'd otherwise have to make — bring the specific thing, not a "
    "general “I'm stuck.” If it is not one of those, it is probably answered already "
    "in the prompt's Step 1.1 through Step 3.8; re-read the relevant step yourself before "
    "escalating.", body_style))

doc.build(story)
print("Wrote student-assignment-guide.pdf")
