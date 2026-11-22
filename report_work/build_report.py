from pathlib import Path
import zipfile

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(r"C:\Users\M S I\Desktop\internet-security-project")
WORK = ROOT / "report_work"
REFERENCE = Path(r"C:\Users\M S I\Downloads\CT-8415_Project Report.docx")
OUTPUT = ROOT / "CT-8415_Honeypot_Project_Report.docx"
NAVY = "17365D"
PALE_BLUE = "EAF1F8"
LIGHT_GRAY = "F2F2F2"
BORDER = "D9D9D9"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), BORDER)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_run_font(run, size=11, bold=False, italic=False, color="000000"):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), "Times New Roman")
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def clear_document_body(doc):
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def configure_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(6)

    for name, size in (("Title", 16), ("Heading 1", 13), ("Heading 2", 12), ("Heading 3", 11)):
        try:
            style = doc.styles[name]
        except KeyError:
            style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(6)
        p_pr = style._element.get_or_add_pPr()
        num_pr = p_pr.find(qn("w:numPr"))
        if num_pr is not None:
            p_pr.remove(num_pr)


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Update field in Microsoft Word"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def add_page_number(section):
    footer = section.footer
    p = footer.paragraphs[0]
    for child in list(p._p):
        if child.tag != qn("w:pPr"):
            p._p.remove(child)
    for extra in list(footer.paragraphs[1:]):
        footer._element.remove(extra._p)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(p, "PAGE")


def add_paragraph(doc, text="", bold_lead=None, align=None, first_line=True, italic=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if first_line and align is None:
        p.paragraph_format.first_line_indent = Inches(0.3)
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        set_run_font(r, bold=True)
        r2 = p.add_run(text[len(bold_lead):])
        set_run_font(r2, italic=italic)
    else:
        r = p.add_run(text)
        set_run_font(r, italic=italic)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        set_run_font(p.add_run(item))


def add_numbered(doc, items):
    for number, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        set_run_font(p.add_run(f"{number}. {item}"))


def add_heading(doc, text, level=2):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), size=13 if level == 1 else 12, bold=True)
    return p


def add_chapter(doc, number, title):
    if len(doc.paragraphs) > 0:
        doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(3)
    set_run_font(p.add_run(f"CHAPTER {number}"), size=12, bold=True)
    p2 = doc.add_paragraph(style="Heading 1")
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(14)
    set_run_font(p2.add_run(title.upper()), size=13, bold=True)


def add_table(doc, headers, rows, widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_shading(cell, NAVY)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(str(h)), size=font_size, bold=True, color="FFFFFF")
        if widths:
            cell.width = Inches(widths[i])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if ridx % 2:
                set_cell_shading(cell, PALE_BLUE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if len(str(value)) < 25 else WD_ALIGN_PARAGRAPH.LEFT
            set_run_font(p.add_run(str(value)), size=font_size)
            if widths:
                cell.width = Inches(widths[i])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = False
    p.paragraph_format.space_after = Pt(9)
    set_run_font(p.add_run(text), size=10, italic=True)


def box(draw, xy, text, fill, outline="#17365D", font=None):
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline=outline, width=3)
    x1, y1, x2, y2 = xy
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] > (x2 - x1 - 24) and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    line_h = 24
    y = (y1 + y2 - len(lines) * line_h) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) / 2, y), line, fill="#111111", font=font)
        y += line_h


def arrow(draw, start, end, color="#17365D"):
    draw.line([start, end], fill=color, width=4)
    x, y = end
    if abs(end[0] - start[0]) > abs(end[1] - start[1]):
        points = [(x, y), (x - 14 if x > start[0] else x + 14, y - 8), (x - 14 if x > start[0] else x + 14, y + 8)]
    else:
        points = [(x, y), (x - 8, y - 14 if y > start[1] else y + 14), (x + 8, y - 14 if y > start[1] else y + 14)]
    draw.polygon(points, fill=color)


def create_diagrams():
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        small = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        small = font

    img = Image.new("RGB", (1500, 900), "white")
    d = ImageDraw.Draw(img)
    box(d, (60, 80, 360, 220), "User or Attacker Browser", "#EAF1F8", font=font)
    box(d, (500, 60, 940, 230), "Windows Host Real Library localhost 3000 Python Backend and Frontend", "#E2F0D9", font=font)
    box(d, (1080, 80, 1420, 220), "SQLite library.db", "#FFF2CC", font=font)
    box(d, (500, 330, 940, 500), "Fake Admin Honeypot localhost 4000 webadmin", "#FCE4D6", font=font)
    box(d, (60, 620, 400, 790), "JSONL Security Log wazuh honeypot alerts", "#EDEDED", font=font)
    box(d, (550, 620, 900, 790), "Windows Wazuh Agent", "#DDEBF7", font=font)
    box(d, (1050, 590, 1430, 820), "Docker Wazuh Manager Indexer Dashboard", "#D9EAD3", font=font)
    arrow(d, (360, 150), (500, 150))
    arrow(d, (940, 150), (1080, 150))
    arrow(d, (720, 230), (720, 330))
    arrow(d, (500, 415), (400, 690))
    arrow(d, (400, 705), (550, 705))
    arrow(d, (900, 705), (1050, 705))
    d.text((372, 110), "HTTP", fill="#333333", font=small)
    d.text((955, 110), "SQL", fill="#333333", font=small)
    d.text((730, 265), "forged admin JWT", fill="#333333", font=small)
    img.save(WORK / "architecture.png")

    flow = Image.new("RGB", (1500, 650), "white")
    d = ImageDraw.Draw(flow)
    labels = [
        "Normal login obtains library JWT",
        "Attacker discovers weak HS256 secret",
        "Role claim changed from user to admin",
        "Request to localhost 3000 webadmin",
        "Redirect to decoy admin on port 4000",
        "Bait download creates alert and ban action",
    ]
    xs = [30, 270, 510, 750, 990, 1230]
    for x, label in zip(xs, labels):
        box(d, (x, 190, x + 210, 440), label, "#EAF1F8" if x < 750 else "#FCE4D6", font=small)
    for x in xs[:-1]:
        arrow(d, (x + 210, 315), (x + 240, 315))
    flow.save(WORK / "attack_flow.png")

    pipe = Image.new("RGB", (1500, 620), "white")
    d = ImageDraw.Draw(pipe)
    labels = [
        "Python detects application event",
        "Append one JSON object to JSONL",
        "Wazuh Agent reads local file",
        "TCP sends event to Manager",
        "Custom rule 100500 to 100507 matches",
        "Indexer stores and Dashboard displays",
    ]
    xs = [30, 275, 520, 765, 1010, 1255]
    fills = ["#E2F0D9", "#EDEDED", "#DDEBF7", "#DDEBF7", "#FFF2CC", "#D9EAD3"]
    for x, label, fill in zip(xs, labels, fills):
        box(d, (x, 180, x + 205, 420), label, fill, font=small)
    for x in xs[:-1]:
        arrow(d, (x + 205, 300), (x + 245, 300))
    pipe.save(WORK / "wazuh_pipeline.png")


def add_figure(doc, path, width, label):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    caption(doc, label)


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    create_diagrams()
    doc = Document(str(REFERENCE))
    clear_document_body(doc)
    configure_styles(doc)
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    add_page_number(section)

    logo = WORK / "uit_logo.png"
    with zipfile.ZipFile(REFERENCE) as zf:
        logo.write_bytes(zf.read("word/media/image1.png"))

    # Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    set_run_font(p.add_run("University of Information Technology"), size=14, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(logo), width=Inches(1.35))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(20)
    set_run_font(p.add_run("PROJECT REPORT"), size=14, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(28)
    set_run_font(p.add_run("Design and Implementation of a Web Based Honeypot System for Detecting Unauthorized JWT Role Manipulation and Attacker Activities"), size=16, bold=True)
    for line in (
        "Network and Internet Security CT 8415",
        "Student Name  [Enter Name]",
        "Student ID  [Enter ID]",
        "Supervisor  [Enter Supervisor Name]",
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(p.add_run(line), size=11, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(40)
    set_run_font(p.add_run("September 2026"), size=11, bold=True)

    # Abstract
    doc.add_page_break()
    add_heading(doc, "ABSTRACT", 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_paragraph(doc,
        "This project develops a web based library honeypot that combines an ordinary borrowing service with a controlled decoy administration area. The real application runs on localhost port 3000 and supports book browsing, registration, login, borrowing, return processing, overdue fines, and personal loan records. Authentication uses a signed JSON Web Token stored in the library_jwt cookie. For the purpose of the security exercise, the HS256 signing secret is intentionally weak, while unsecured tokens using the none algorithm are rejected. A user who recovers the secret and changes the token role from user to admin is diverted to a fake administration page on port 4000. The page contains believable borrower credential, loan, and fine files. Access to these files produces structured JSON security events. A Windows Wazuh agent monitors the JSONL event file and sends new records to a Docker based Wazuh manager, where custom rules classify eight types of suspicious activity. The highest severity rule can call an active response script that bans the attacking account and revokes its stored credentials. The completed prototype demonstrates how a deliberate vulnerability can be contained inside a local teaching environment and connected to monitoring, investigation, and response. It also shows the limits of this design: the weak key and decoy credentials are suitable only for an isolated laboratory and must never be carried into a production system.")
    p = doc.add_paragraph()
    set_run_font(p.add_run("Keywords  "), bold=True)
    set_run_font(p.add_run("honeypot, JSON Web Token, Wazuh, SIEM, active response, web security, deception technology"))

    # Acknowledgement
    doc.add_page_break()
    add_heading(doc, "ACKNOWLEDGEMENT", 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_paragraph(doc,
        "I would like to thank my teachers and classmates for the guidance and feedback they provided during this project. Their suggestions helped me move from a simple library website to a working security laboratory with event monitoring and an automated response. I am also grateful for the practical exercises in Network and Internet Security, which gave me the background needed to connect web application behavior, log analysis, and Wazuh rules. Any remaining errors in the design or report are my own.")

    # TOC
    doc.add_page_break()
    add_heading(doc, "TABLE OF CONTENTS", 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    add_field(p, 'TOC \\o "1-3" \\h \\z \\u')

    # Chapter 1
    add_chapter(doc, 1, "Introduction")
    add_heading(doc, "1.1 Background and Motivation")
    add_paragraph(doc,
        "Web applications often make authorization decisions from session data carried between the browser and the server. JSON Web Token, or JWT, is a compact format for carrying claims such as a user identifier and role [1]. A signed token can protect those claims from modification, but that protection depends on correct algorithm validation and a signing key with enough entropy. RFC 8725 specifically warns that weak symmetric keys can be recovered through offline dictionary or brute force attacks after an attacker obtains a token [2].")
    add_paragraph(doc,
        "This weakness is useful in a controlled security exercise because it creates a clear path from an ordinary user account to attempted privilege escalation. The project deliberately uses the short key book for HS256 signing. It still rejects the none algorithm, so the exercise distinguishes an implementation that performs signature verification from one that uses an unsafe key. Once an altered role claim is accepted, the application does not expose real administrative data. Instead, it moves the suspicious session into a decoy service where later actions can be observed.")
    add_paragraph(doc,
        "Honeypots are systems or resources designed to attract activity that has little or no legitimate reason to occur. Their value comes from the high signal of an interaction and the opportunity to record attacker behavior [3], [4]. In this project the decoy is application specific. It looks like a library administration page and offers files that an attacker may consider valuable, while the files contain synthetic records. Wazuh then provides centralized rule matching, alert storage, dashboard investigation, and active response.")

    add_heading(doc, "1.2 Problem Statement")
    add_paragraph(doc,
        "A normal library application can record failed logins, but a basic log entry does not show how several suspicious actions relate to one session. The project therefore addresses three connected problems. First, it needs a believable application in which normal users can perform real work. Second, it needs a contained attack path that demonstrates JWT role manipulation without exposing genuine administrator information. Third, it needs a monitoring pipeline that turns application events into searchable alerts and can respond automatically to a high confidence deception event.")
    add_paragraph(doc,
        "The design must also control false positives. A forgotten password should not automatically ban a member, and a scanner signature by itself may not prove compromise. For that reason, most custom rules are review only. Automatic account banning is reserved for the stronger signal produced when a forged administrator session downloads a bait file.")

    add_heading(doc, "1.3 Project Objectives")
    add_paragraph(doc, "The main objective is to design and implement a local web honeypot that detects JWT role manipulation and records subsequent attacker activity. The specific objectives are:", first_line=False)
    add_bullets(doc, [
        "Build a usable library website with public book browsing, registration, login, borrowing, returns, due dates, and overdue fine calculation.",
        "Use an HS256 JWT cookie for authentication and deliberately configure a weak signing key for an authorized laboratory exercise.",
        "Reject unsecured JWTs using the none algorithm while allowing the weak secret to demonstrate a different JWT failure mode.",
        "Redirect forged administrator sessions from the real website on port 3000 to a fake administration page on port 4000.",
        "Generate structured security events for bait downloads, login brute force, decoy login, IDOR probes, SQL injection probes, scanner user agents, and path enumeration.",
        "Integrate the application with a Windows Wazuh agent and Docker based Wazuh server components.",
        "Use a custom active response for the high confidence bait download event while leaving lower confidence events for analyst review.",
    ])

    add_heading(doc, "1.4 Project Scope")
    add_paragraph(doc,
        "The project is a single host laboratory deployment. The real and decoy web services run on Windows, while the Wazuh manager, indexer, and dashboard run in Docker containers on the same machine. SQLite stores application data locally. Testing is limited to accounts, traffic, and files created for this project. The system is not exposed to the public Internet and does not collect data from unrelated users.")
    add_paragraph(doc,
        "The scope includes detection and response demonstrations rather than enterprise hardening. It does not include TLS termination, multi factor authentication, a production password recovery process, distributed deployment, long term alert retention planning, or high availability. The weak JWT secret and webadmin decoy credentials are intentional vulnerabilities, not recommended settings.")

    add_heading(doc, "1.5 Expected Contributions")
    add_paragraph(doc,
        "The principal contribution is a working example that connects application logic to security operations. It demonstrates that a honeypot is more useful when it records specific context, such as the username, attempted path, selected bait file, token role, source address, and recommended response. It also provides a compact custom ruleset and a reproducible event flow that can be demonstrated in a classroom without requiring external infrastructure.")

    # Chapter 2
    add_chapter(doc, 2, "Literature Review")
    add_heading(doc, "2.1 Honeypot Concepts")
    add_paragraph(doc,
        "Honeypots are commonly classified by purpose and interaction level. A production honeypot supports operational detection, while a research honeypot is designed to collect information about techniques and behavior. Low interaction systems emulate a narrow set of services and reduce risk, whereas high interaction systems provide a fuller environment at the cost of greater containment and maintenance requirements [3], [4]. The present project is a low to medium interaction application honeypot. It offers real HTTP behavior and stateful sessions but does not provide an attacker with an operating system shell.")
    add_paragraph(doc,
        "Deception changes the meaning of an event. A failed login may come from an ordinary mistake, but opening a hidden decoy administration page or downloading fabricated borrower credentials has no normal business purpose. This makes bait interaction suitable as a high confidence detection signal. NIST guidance treats honeypots as a complementary detection technology rather than a replacement for ordinary controls [5]. The project follows that principle by combining the decoy with authentication checks, parameterized database queries, application logging, and Wazuh monitoring.")

    add_heading(doc, "2.2 JSON Web Token Security")
    add_paragraph(doc,
        "RFC 7519 defines JWT as a compact representation of claims that may be signed or encrypted [1]. In this project the token contains a subject identifier, username, role, issue time, and expiration time. HS256 calculates a message authentication code over the encoded header and payload. If the key remains secret and has adequate entropy, a modified payload will fail verification.")
    add_paragraph(doc,
        "Two JWT weaknesses are relevant to the design. The first is acceptance of the none algorithm, which removes signature protection. The backend explicitly requires HS256, so this attack is rejected. The second is a weak HMAC key. RFC 8725 and the OWASP JWT guidance both state that human memorable or short secrets are vulnerable to offline guessing and recommend cryptographically generated keys of sufficient length [2], [6]. The project intentionally violates the key strength recommendation to create the learning scenario, while preserving algorithm verification so that students can observe the difference.")

    add_heading(doc, "2.3 Web Application Threats")
    add_paragraph(doc,
        "The rule set reflects common web testing activities. OWASP identifies broken access control as a major risk because it can allow a user to act outside intended permissions [7]. IDOR is one form of this problem: an attacker changes an object identifier and tries to access another user's record [8]. SQL injection occurs when untrusted input changes the structure of a database query [9]. Automated password attacks and weak or default credentials are also recognized authentication failures [10].")
    add_paragraph(doc,
        "The application does not deliberately make its SQLite statements injectable. It uses parameterized queries, then separately inspects login and API values for recognizable SQL injection probes. This separation is important. A detection exercise should observe malicious input without needing to let that input execute against the database.")

    add_heading(doc, "2.4 Security Monitoring and Active Response")
    add_paragraph(doc,
        "Wazuh collects endpoint and application events through agents. Its localfile configuration can read a single line JSON log and forward each record for decoding and rule evaluation [11]. Custom rules allow local fields and event types to be assigned project specific rule identifiers and severity levels [12]. The indexer stores resulting alerts, and the dashboard provides search and visualization.")
    add_paragraph(doc,
        "Active response links a rule to a command that runs on a manager or agent [13]. Automation reduces response time, but it can also amplify a false positive. The project therefore associates the banning command only with rule 100500. Other detections remain visible to the analyst without changing the user's account.")

    add_heading(doc, "2.5 Comparison of Approaches")
    add_table(doc,
        ["Approach", "Strength", "Limitation", "Use in this project"],
        [
            ["Ordinary application logging", "Simple and low cost", "Events may lack security context", "Used for internal security_events records"],
            ["Network scanner or IDS", "Observes traffic patterns", "May not know user or application state", "Represented by scanner and path probe detections"],
            ["Application honeypot", "High signal from decoy interaction", "Can be recognized if the decoy is unrealistic", "Fake library administration page and CSV bait"],
            ["SIEM with custom rules", "Central search and severity classification", "Requires agent and rule configuration", "Wazuh rules 100500 through 100507"],
            ["Automated response", "Fast containment", "False positives can disrupt valid users", "Restricted to forged admin bait downloads"],
        ], [1.25, 1.55, 1.75, 1.95])
    caption(doc, "Table 2.1 Comparison of security monitoring approaches")

    add_heading(doc, "2.6 Relevant Standards and Guidance")
    add_paragraph(doc,
        "The security design draws on several established sources. RFC 7519 and RFC 8725 define JWT behavior and secure implementation practices [1], [2]. The OWASP Top 10 and Web Security Testing Guide provide categories and testing methods for access control, authentication, injection, and object references [7]-[10]. NIST SP 800-115 supports planned technical security testing and emphasizes documenting methods, findings, and mitigation [14]. Wazuh documentation supplies the operational requirements for log collection, custom rules, and active response [11]-[13].")

    add_heading(doc, "2.7 Research Gap")
    add_paragraph(doc,
        "Many honeypot examples focus on network services such as SSH or on generic web decoys. Many JWT demonstrations stop after showing that a role claim can be forged. This project joins those topics into one traceable workflow: a realistic member account is compromised at the token level, the suspicious session is redirected rather than granted genuine administration access, bait interaction is converted into a structured SIEM alert, and a selected event can trigger an account response. The result is small enough for a student laboratory but broad enough to demonstrate detection engineering decisions.")

    # Chapter 3
    add_chapter(doc, 3, "Requirement Analysis")
    add_heading(doc, "3.1 Functional Requirements")
    req_rows = [
        ["FR 01", "The public catalog shall display books and book details without requiring login."],
        ["FR 02", "A visitor shall be able to register and log in as a library member."],
        ["FR 03", "An authenticated member shall be able to borrow an available book."],
        ["FR 04", "The system shall calculate a 14 day due date and a fine of 500 MMK per overdue day."],
        ["FR 05", "A member shall be able to return a non overdue book and restore its available copy count."],
        ["FR 06", "The real service shall run on port 3000 and the fake administration service on port 4000 at webadmin."],
        ["FR 07", "The backend shall reject JWTs that do not use HS256 or have an invalid signature."],
        ["FR 08", "A valid token carrying an administrator role for a normal database user shall be redirected to the decoy service."],
        ["FR 09", "The decoy page shall provide synthetic credential, borrowed book, and fine files."],
        ["FR 10", "The application shall write one line JSON events for defined suspicious behaviors."],
        ["FR 11", "Wazuh shall classify the events with custom rules 100500 through 100507."],
        ["FR 12", "Rule 100500 shall support automatic account banning and credential revocation."],
    ]
    add_table(doc, ["ID", "Requirement"], req_rows, [0.8, 5.7], 9)
    caption(doc, "Table 3.1 Functional requirements")

    add_heading(doc, "3.2 Non Functional Requirements")
    add_table(doc,
        ["Quality", "Requirement"],
        [
            ["Usability", "Normal library tasks must remain understandable and must not display the JWT value in the interface."],
            ["Reliability", "Borrow and return transactions must keep loan status and available book counts consistent."],
            ["Maintainability", "Detection thresholds and rule mappings must be easy to locate and change."],
            ["Auditability", "Each security event must include a timestamp, event type, source information, and useful context."],
            ["Separation", "The decoy administration service must run separately from the normal website."],
            ["Safety", "All testing must remain inside the authorized local environment and use synthetic bait data."],
            ["Recoverability", "Application records and bans must survive a normal process restart through SQLite storage."],
        ], [1.3, 5.2], 9)
    caption(doc, "Table 3.2 Non functional requirements")

    add_heading(doc, "3.3 Asset Identification")
    add_table(doc,
        ["Asset", "Classification", "Reason for protection"],
        [
            ["Member accounts and password hashes", "Critical", "Compromise permits impersonation and unauthorized borrowing."],
            ["JWT signing secret", "Critical", "Knowledge of the key permits forged role claims in this laboratory design."],
            ["Library database", "High", "Contains users, books, loans, bans, tickets, and security records."],
            ["Wazuh alerts and rules", "High", "Support investigation and determine whether automated action occurs."],
            ["Book availability and loan records", "Medium", "Incorrect updates affect library operation and user records."],
            ["Synthetic bait files", "Low", "The content is fake, but access to it is an important detection signal."],
            ["Docker configuration and volumes", "High", "Control availability and persistence of Wazuh services."],
        ], [2.0, 1.0, 3.5], 9)
    caption(doc, "Table 3.3 Asset classification")

    add_heading(doc, "3.4 Threat and Vulnerability Identification")
    add_paragraph(doc,
        "The central intentional vulnerability is the weak JWT secret. The token algorithm is fixed to HS256, but the word book has very little entropy and can be recovered offline. The webadmin account also uses deliberately obvious credentials to act as a decoy. These settings are isolated to the laboratory. Other threat scenarios are detected as probes rather than implemented as exploitable flaws.")
    add_table(doc,
        ["Threat", "Relevant weakness or signal", "Target"],
        [
            ["JWT role manipulation", "Weak HS256 signing secret", "Authorization and user identity"],
            ["Credential brute force", "Repeated failed logins from one source IP", "Member accounts"],
            ["Path enumeration", "Three unrelated paths in 60 seconds", "Hidden administration routes"],
            ["SQL injection probing", "Quotes, backslashes, tautologies, comments, or SQL keywords in input", "Login and API fields"],
            ["IDOR probing", "Request for an object owned by another user", "Loan and account objects"],
            ["Automated scanning", "Known scanner name in User Agent", "Web application"],
            ["Bait file access", "Download from the decoy admin session", "Synthetic records and attacker account"],
        ], [1.55, 3.05, 1.9], 9)
    caption(doc, "Table 3.4 Threats and observed indicators")

    add_heading(doc, "3.5 Risk Assessment")
    add_paragraph(doc,
        "Risk was scored as likelihood multiplied by impact on a five point scale. Scores from 1 to 4 are Low, 5 to 9 are Medium, 10 to 16 are High, and 17 to 25 are Critical. The assessment describes the deliberately vulnerable laboratory if it were operated without the decoy and monitoring controls.")
    add_table(doc,
        ["Risk", "Likelihood", "Impact", "Score", "Level", "Treatment"],
        [
            ["Forged JWT grants administrator role", 5, 5, 25, "Critical", "Redirect to isolated decoy; never expose real admin functions"],
            ["Attacker downloads sensitive looking files", 4, 4, 16, "High", "Use synthetic data; alert and ban forged account"],
            ["Credential brute force", 4, 3, 12, "High", "Alert after 10 failures in 60 seconds; analyst review"],
            ["SQL injection attempt", 3, 4, 12, "High", "Parameterized queries and probe alert"],
            ["IDOR attempt", 3, 4, 12, "High", "Ownership checks and probe alert"],
            ["False positive automated ban", 2, 4, 8, "Medium", "Bind active response only to rule 100500"],
            ["Wazuh unavailable", 2, 3, 6, "Medium", "Keep local JSONL and SQLite records; verify service health"],
        ], [1.45, 0.65, 0.6, 0.55, 0.65, 2.35], 8)
    caption(doc, "Table 3.5 Risk assessment matrix")

    add_heading(doc, "3.6 Selected Security Controls")
    add_bullets(doc, [
        "Algorithm allow listing. JWT verification accepts HS256 only and rejects none or unexpected algorithms.",
        "Database authorization checks. Return operations verify both loan identifier and current user ownership.",
        "Parameterized SQL. User supplied identifiers are passed as query parameters instead of being concatenated into statements.",
        "Service separation. Real member functions and the fake administration service use separate ports and request handlers.",
        "Short lived handoff ticket. A ten minute ticket connects the suspicious real site session to the decoy without displaying it in the final webadmin URL.",
        "Structured audit events. The backend writes JSON with stable field names that Wazuh can decode.",
        "Selective response. Only a high confidence bait download from a forged personal account is configured for automatic banning.",
        "Synthetic data. The downloadable files contain decoy records rather than real member credentials or financial information.",
    ])

    # Chapter 4
    add_chapter(doc, 4, "System Architecture and Implementation")
    add_heading(doc, "4.1 Overall Architecture")
    add_figure(doc, WORK / "architecture.png", 6.5, "Figure 4.1 Overall system architecture")
    add_paragraph(doc,
        "The browser first communicates with the real library service on port 3000. The Python backend serves the static HTML, CSS, and JavaScript files and exposes JSON API routes. It reads and updates the SQLite database in the same process. If a verified token contains an administrator role while the associated database account remains an ordinary user, the request is treated as a role manipulation signal and is redirected to the decoy service on port 4000.")
    add_paragraph(doc,
        "Security events are written to logs/wazuh-honeypot-alerts.jsonl. The Windows Wazuh agent monitors this file and sends new entries over TCP to the Wazuh manager container. The manager decodes the JSON and evaluates local rules. Matching alerts are stored by the indexer and displayed in the dashboard. For rule 100500, the manager can instruct the reporting Windows agent to run the ban script.")

    add_heading(doc, "4.2 Attack and Deception Flow")
    add_figure(doc, WORK / "attack_flow.png", 6.5, "Figure 4.2 Intended JWT manipulation and honeypot flow")
    add_paragraph(doc,
        "The intended exercise begins with a valid member login. Because JWT payloads are encoded rather than encrypted, the role claim can be inspected. The attacker performs an offline dictionary search against the HS256 signature and discovers the deliberately weak key. After changing the role to admin and re-signing the token, the attacker replaces the library_jwt cookie. A request to the real site webadmin path is then redirected to the fake administration page. The decoy looks useful but does not expose a real administrator function.")

    add_heading(doc, "4.3 Application Data Flow")
    add_paragraph(doc,
        "Registration inserts a user record with a generated identifier, the user role, and a derived password hash. Login compares the submitted value with the stored hash and issues a signed cookie after success. Borrowing creates a loan record, reduces copies_available, and calculates a due date fourteen days after the transaction. A normal return closes the loan and increases book availability. If the due date has passed, the interface displays 500 MMK for each overdue day and the return action is refused until the fine condition is addressed.")
    add_paragraph(doc,
        "The backend keeps operational and security data separate. Users, books, loans, tickets, bans, failed login attempts, and path probes are stored in SQLite. Events intended for Wazuh are appended to a JSONL file so the agent can consume them incrementally. SQLite is suitable for this local prototype because it is an in process, serverless database stored in a single file and requires no separate database service [15].")

    add_heading(doc, "4.4 Database Design")
    add_table(doc,
        ["Table", "Purpose", "Important fields"],
        [
            ["users", "Member identity and local role", "id, username, full_name, role, password_hash"],
            ["books", "Catalog and stock", "title, category, copies_total, copies_available, ISBN"],
            ["loans", "Borrow and return lifecycle", "user_id, book_id, status, due_at, fine_mmk"],
            ["security_events", "Local application audit history", "type, IP, method, path, details"],
            ["honeypot_tickets", "Short lived handoff to decoy", "username, token_role, expires_at"],
            ["banned_accounts", "Persistent account response", "username, reason, source_event, banned_at"],
            ["login_attempts", "Rolling login threshold data", "created_at, IP, username, password, User Agent"],
            ["path_probe_attempts", "Rolling path threshold data", "created_at, IP, method, path, User Agent"],
        ], [1.35, 2.25, 2.9], 9)
    caption(doc, "Table 4.1 SQLite tables")

    add_heading(doc, "4.5 Tools and Technologies")
    add_table(doc,
        ["Technology", "Role", "Reason for selection"],
        [
            ["HTML CSS JavaScript", "Browser interface", "No frontend framework is required for this compact application."],
            ["Python standard library", "HTTP servers, JWT logic, CSV output, logging", "Keeps the backend transparent for study."],
            ["SQLite", "Persistent application database", "Single file, transactional, and zero configuration [15]."],
            ["Wazuh Agent", "Reads the application JSONL log", "Connects a Windows hosted application to centralized analysis."],
            ["Wazuh Manager", "Decoding, custom rules, active response", "Provides rule based SIEM functions [11]-[13]."],
            ["Wazuh Indexer and Dashboard", "Alert storage and investigation", "Supports filtering by rule ID and event fields."],
            ["Docker Compose", "Runs Wazuh server components", "Provides repeatable multi container startup and separation [16]."],
            ["npm script", "Convenient project launcher", "Maps npm start to python backend/run_servers.py; Node is not the server."],
        ], [1.45, 2.0, 3.05], 9)
    caption(doc, "Table 4.2 Tools and technologies")

    add_heading(doc, "4.6 Wazuh Event Pipeline")
    add_figure(doc, WORK / "wazuh_pipeline.png", 6.5, "Figure 4.3 Application event processing in Wazuh")
    add_paragraph(doc,
        "Each alert record contains honeypot_program with the value northstar-library-honeypot and an event_type value that identifies the behavior. The agent localfile entry uses JSON log format and points to the project JSONL path. Wazuh's JSON decoder extracts the fields, and local_rules.xml checks the program and event type after parent rule 86600. Wazuh recommends custom identifiers in the 100000 to 120000 range to avoid conflicts with built in rules [12].")

    add_heading(doc, "4.7 Custom Rule Design")
    add_table(doc,
        ["Rule", "Event type", "Level", "Response", "Meaning"],
        [
            ["100500", "honeypot_file_download", "12", "Auto ban", "Forged personal account downloaded bait"],
            ["100501", "login_bruteforce_detected", "8", "Review", "10 failed logins from one IP in 60 seconds"],
            ["100502", "webadmin_decoy_login", "10", "Review", "Decoy webadmin credentials used"],
            ["100503", "webadmin_file_download", "10", "Review", "Decoy account downloaded bait"],
            ["100504", "idor_probe_detected", "8", "Review", "Possible access to another user's object"],
            ["100505", "sql_injection_probe", "8", "Review", "Recognized SQL injection input pattern"],
            ["100506", "scanner_user_agent", "7", "Review", "Known scanner name in User Agent"],
            ["100507", "path_bruteforce", "8", "Review", "Three unrelated paths from one IP in 60 seconds"],
        ], [0.7, 1.55, 0.55, 0.8, 2.9], 8)
    caption(doc, "Table 4.3 Custom Wazuh rules")
    add_paragraph(doc,
        "The two rolling thresholds are implemented in the Python backend, not in Wazuh. The application writes login_bruteforce_detected only when the tenth failed login from the same source IP enters the previous sixty second window. It writes path_bruteforce when the third unknown route from the same IP enters its sixty second window. Wazuh then classifies the resulting event. This design keeps request context close to the application and keeps the XML rules simple.")

    add_heading(doc, "4.8 Active Response and Account Revocation")
    add_paragraph(doc,
        "The active response configuration associates rule 100500 with ban-library-account.cmd at the local location, which means the command runs on the Windows agent that reported the event. The command passes the alert to backend/ban_account.py. The script extracts account_to_ban, inserts or updates the banned_accounts record, replaces the stored password hash with a revoked value, and removes the decoy password. Future login and token checks reject the account. Wazuh supports this model by allowing rules_id to select the alert that activates a command [13].")
    add_paragraph(doc,
        "The webadmin decoy account is deliberately excluded from automatic banning. Its purpose is to let an analyst observe use of the planted credentials. A download by that account creates rule 100503 for review. This distinction prevents the shared decoy identity from being destroyed during every demonstration.")

    add_heading(doc, "4.9 Environment Setup")
    add_numbered(doc, [
        "Start the Docker Desktop service and run docker-compose up -d in the Wazuh single-node folder. The manager, indexer, and dashboard containers should become healthy.",
        "Configure the Windows Wazuh agent to connect to the manager through the mapped TCP port and add the JSON localfile entry for wazuh-honeypot-alerts.jsonl.",
        "Copy local_rules.xml to /var/ossec/etc/rules/local_rules.xml inside the manager, validate the configuration, and restart the manager container.",
        "Copy ban-library-account.cmd to the Windows agent active-response bin folder and add the command and active-response blocks to the manager configuration.",
        "Start WazuhSvc on Windows. Confirm that the agent appears active in the dashboard.",
        "Run npm start in the project folder. This executes python backend/run_servers.py and starts ports 3000 and 4000.",
        "Open the real library at http://localhost:3000 and the Wazuh dashboard at https://localhost. Use dashboard filters such as rule.id:100500 for testing.",
    ])

    add_heading(doc, "4.10 Implementation Summary")
    add_paragraph(doc,
        "The completed implementation separates ordinary library work from the decoy service, records both operational and security state, and sends stable JSON events into Wazuh. The design keeps the deliberate weakness narrow: a short JWT secret and known decoy credentials. It does not depend on SQL injection, IDOR, or algorithm none being exploitable. Those behaviors are observed and reported while ordinary authorization and parameterized SQL remain in place.")

    # Chapter 5
    add_chapter(doc, 5, "Testing and Evaluation")
    add_heading(doc, "5.1 Test Plan")
    add_paragraph(doc,
        "Testing was performed inside the local Windows and Docker laboratory. Functional tests checked member workflows and stock updates. Security tests generated one behavior at a time and used the application log and Wazuh dashboard to confirm the expected event type and rule identifier. The tests did not target external systems. NIST SP 800-115 recommends defining the purpose, scope, procedures, and handling of results before technical testing [14]; this project follows that approach on a small scale.")

    add_heading(doc, "5.2 Functional Test Cases")
    add_table(doc,
        ["ID", "Test", "Expected result", "Observed result", "Status"],
        [
            ["FT 01", "Open book catalog without login", "Books and filters are available", "Catalog loads and remains public", "Pass"],
            ["FT 02", "Register and log in", "User record and JWT cookie created", "Member session is created", "Pass"],
            ["FT 03", "Borrow available book", "Loan created and availability decreases", "Both database values update", "Pass"],
            ["FT 04", "Return non overdue book", "Loan closes and availability increases", "Book leaves My Books and stock returns", "Pass"],
            ["FT 05", "View overdue loan", "Fine equals days overdue times 500 MMK", "Fine is displayed and return is blocked", "Pass"],
            ["FT 06", "Logout from decoy", "Cookies cleared and browser returns to port 3000", "Session returns to real site", "Pass"],
        ], [0.6, 1.45, 2.0, 1.9, 0.55], 8)
    caption(doc, "Table 5.1 Functional test results")

    add_heading(doc, "5.3 Security Test Cases")
    add_table(doc,
        ["ID", "Security test", "Expected evidence", "Rule", "Status"],
        [
            ["ST 01", "Submit a JWT with alg none", "Request rejected; no admin access", "Not applicable", "Pass"],
            ["ST 02", "Forge HS256 role with key book", "Redirect to port 4000 webadmin", "Application event", "Pass"],
            ["ST 03", "Download bait as forged account", "Alert and banned account record", "100500", "Pass"],
            ["ST 04", "Fail login 10 times in 60 seconds", "Attempted credentials shown for review", "100501", "Pass"],
            ["ST 05", "Use webadmin credentials", "Decoy login alert without ban", "100502", "Pass"],
            ["ST 06", "Download bait as webadmin", "Review alert without ban", "100503", "Pass"],
            ["ST 07", "Request another user's loan ID", "Ownership failure and IDOR alert", "100504", "Pass"],
            ["ST 08", "Place quote or 1=1 in login input", "SQL injection probe alert", "100505", "Pass"],
            ["ST 09", "Send sqlmap or ffuf User Agent", "Scanner alert containing User Agent", "100506", "Pass"],
            ["ST 10", "Request three unrelated paths in 60 seconds", "Attempted path list in alert", "100507", "Pass"],
        ], [0.55, 1.75, 2.5, 0.75, 0.55], 8)
    caption(doc, "Table 5.2 Security test results")

    add_heading(doc, "5.4 Evaluation of Detection Logic")
    add_paragraph(doc,
        "The bait download event is the strongest signal because a normal member has no route to the decoy file list. For that reason it receives level 12 and is connected to the account response. The webadmin account uses a similar page but a different event type, allowing the analyst to observe use of planted credentials without repeatedly disabling the shared decoy account.")
    add_paragraph(doc,
        "The login threshold was increased from five to ten failures in sixty seconds to reduce noise from ordinary password mistakes. The threshold is based on source IP rather than username. This is easy to explain and demonstrate, but it can combine several users behind one network address. Path brute force uses a lower threshold of three unknown paths in sixty seconds because normal navigation should remain inside the known route set. Scanner User Agent detection has lower confidence because headers can be changed or spoofed.")
    add_paragraph(doc,
        "SQL injection detection looks for quotes, backslashes, tautologies, comments, SQL keywords, union select patterns, delay functions, and schema names. These patterns provide visible evidence during a demonstration but are not a complete web application firewall. IDOR detection is more contextual because it compares the requested loan object with the authenticated user and records the actual owner when access is denied.")

    add_heading(doc, "5.5 Results and Discussion")
    add_paragraph(doc,
        "The project achieved its main objective. A forged role does not reveal a genuine administrator dashboard; it leads to an instrumented decoy. The monitoring path preserves useful context from the application through the JSONL record and into Wazuh. Rule IDs make each demonstration easy to isolate in the dashboard, and the high confidence event can produce a visible change in SQLite through the banned_accounts table.")
    add_paragraph(doc,
        "The design also exposes an important operational lesson. Detection and response are different decisions. A suspicious User Agent, unknown path, or failed password sequence should alert an analyst, but these signals are not always reliable enough for automatic punishment. Bait download is narrower and therefore supports stronger automation. This distinction reduces the chance that a normal member is banned because of a typo or unusual browser behavior.")

    add_heading(doc, "5.6 Challenges Encountered")
    add_bullets(doc, [
        "The real application and honeypot share the localhost name, so cookie scope and redirect behavior had to be designed carefully to avoid redirect loops.",
        "A query parameter used during early handoff testing made the decoy URL look suspicious. The final flow stores the short lived ticket in a cookie and leaves the visible URL at webadmin.",
        "Windows port reservations prevented Docker from binding the default Wazuh ports. Host ports were remapped while the manager retained its internal service ports.",
        "Custom rules initially matched only the parent JSON rule. Copying the updated local_rules.xml into the manager and validating the configuration corrected the issue.",
        "Active response required coordination between manager configuration and a script located on the Windows agent. Testing the script separately helped separate application, agent, and manager problems.",
        "Frequent Windows audit events made demonstrations noisy. Dashboard filters by custom rule range, rule group, or honeypot_program were used instead of deleting useful endpoint logs.",
    ])

    add_heading(doc, "5.7 Lessons Learned")
    add_paragraph(doc,
        "The project showed that security monitoring works best when the application supplies meaningful context. A generic 404 or failed login count says less than an event that includes the attempted route, credentials, account, token role, and recommended action. It also showed that a deliberate vulnerability must be documented and contained. The weak signing key is useful only because the system is local, the admin data is fake, and the response path is visible.")
    add_paragraph(doc,
        "A second lesson is that configuration belongs to the system design. The Python code alone cannot produce a Wazuh dashboard alert. The agent localfile entry, TCP connection, manager rule file, indexer, dashboard, and active response configuration all have to agree. Testing each stage independently made troubleshooting more reliable.")

    # Chapter 6
    add_chapter(doc, 6, "Conclusion")
    add_heading(doc, "6.1 Project Summary")
    add_paragraph(doc,
        "This project implemented a library management website and an application specific honeypot on one Windows host. Normal members use port 3000 to browse, borrow, return, and review books. A deliberately weak JWT signing secret supports an authorized role manipulation exercise. Suspicious administrator sessions are redirected to a decoy page on port 4000, where fake borrower files create high value detection events. A Windows Wazuh agent forwards those events to Docker based Wazuh services for rule matching, storage, investigation, and selected response.")

    add_heading(doc, "6.2 Key Contributions")
    add_bullets(doc, [
        "A complete normal user workflow that makes the decoy part of a believable application rather than an isolated page.",
        "A contained JWT attack path that rejects algorithm none but demonstrates the risk of a weak symmetric signing key.",
        "A separate fake administration service with synthetic credential, loan, and fine files.",
        "Eight project specific Wazuh rules covering deception, authentication, access control, injection, scanning, and enumeration events.",
        "A selective active response that bans a forged personal account and revokes its stored credentials after bait interaction.",
        "A reproducible local architecture suitable for classroom demonstration and security analysis.",
    ])

    add_heading(doc, "6.3 Project Limitations")
    add_paragraph(doc,
        "The prototype is intentionally not production ready. It uses HTTP on localhost, a weak JWT secret, known decoy credentials, and a simple password derivation scheme. Event thresholds are stored and calculated by a single Python process and are grouped mainly by source IP. The decoy may be recognized by a skilled attacker, especially if they compare service fingerprints or inspect the local environment. The system has not been load tested, independently penetration tested, or evaluated against public Internet traffic. Automatic banning changes an application account rather than blocking a network source.")

    add_heading(doc, "6.4 Future Enhancements")
    add_bullets(doc, [
        "Move secrets and secure deployment values into environment configuration, and use a cryptographically random key outside the training mode.",
        "Replace the demonstration password derivation with a standard adaptive password hashing library such as Argon2id or bcrypt.",
        "Add TLS through a local reverse proxy and test secure, HttpOnly, and SameSite cookie behavior.",
        "Introduce correlation rules that combine scanner, path, login, and decoy events over a longer period without storing attempted passwords in clear text.",
        "Add a controlled fine payment workflow so overdue loans can be resolved without manual database changes.",
        "Use container volumes or deployment automation so custom Wazuh rules persist whenever manager containers are recreated.",
        "Evaluate decoy realism, false positives, detection latency, and resource use with a documented repeatable test set.",
        "Deploy the application and Wazuh manager on separate virtual machines to study network boundaries and remote agent communication.",
    ])

    # References
    doc.add_page_break()
    add_heading(doc, "REFERENCES", 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
    references = [
        "[1] M. Jones, J. Bradley, and N. Sakimura, JSON Web Token JWT, RFC 7519, May 2015. Available: https://datatracker.ietf.org/doc/html/rfc7519",
        "[2] Y. Sheffer, D. Hardt, and M. Jones, JSON Web Token Best Current Practices, RFC 8725, February 2020. Available: https://datatracker.ietf.org/doc/html/rfc8725",
        "[3] L. Spitzner, Honeypots Tracking Hackers. Boston, MA: Addison Wesley, 2002.",
        "[4] N. Provos and T. Holz, Virtual Honeypots From Botnet Tracking to Intrusion Detection. Boston, MA: Addison Wesley, 2007.",
        "[5] K. Scarfone and P. Mell, Guide to Intrusion Detection and Prevention Systems IDPS, NIST SP 800-94, February 2007. Available: https://doi.org/10.6028/NIST.SP.800-94",
        "[6] OWASP Foundation, JSON Web Token Cheat Sheet for Java, Cheat Sheet Series. Available: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html, accessed September 18 2026.",
        "[7] OWASP Foundation, A01 2021 Broken Access Control, OWASP Top 10. Available: https://top10.owasp.org/2021/A01_2021-Broken_Access_Control/, accessed September 18 2026.",
        "[8] OWASP Foundation, Testing for Insecure Direct Object References, Web Security Testing Guide. Available: https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/05-Authorization/04-Insecure_Direct_Object_References/, accessed September 18 2026.",
        "[9] OWASP Foundation, Testing for SQL Injection, Web Security Testing Guide version 4.2. Available: https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection/, accessed September 18 2026.",
        "[10] OWASP Foundation, A07 2021 Identification and Authentication Failures, OWASP Top 10. Available: https://top10.owasp.org/2021/A07_2021-Identification_and_Authentication_Failures/, accessed September 18 2026.",
        "[11] Wazuh, localfile Local configuration ossec conf. Available: https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html, accessed September 18 2026.",
        "[12] Wazuh, Custom rules. Available: https://documentation.wazuh.com/current/user-manual/ruleset/rules/custom.html, accessed September 18 2026.",
        "[13] Wazuh, Active response Local configuration ossec conf. Available: https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/active-response.html, accessed September 18 2026.",
        "[14] K. Scarfone, M. Souppaya, A. Cody, and A. Orebaugh, Technical Guide to Information Security Testing and Assessment, NIST SP 800-115, September 2008. Available: https://doi.org/10.6028/NIST.SP.800-115",
        "[15] SQLite Consortium, About SQLite. Available: https://www.sqlite.org/about.html, accessed September 18 2026.",
        "[16] Docker Inc., Docker overview. Available: https://docs.docker.com/get-started/docker-overview/, accessed September 18 2026.",
        "[17] M. Nawrocki, M. Wahlisch, T. C. Schmidt, C. Keil, and J. Schonfelder, A Survey on Honeypot Software and Data Analysis, arXiv:1608.06249, 2016. Available: https://arxiv.org/abs/1608.06249",
    ]
    for ref in references:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        set_run_font(p.add_run(ref), size=10)

    # Ensure Word updates TOC and page fields when opened.
    settings = doc.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")
    doc.core_properties.title = "Design and Implementation of a Web Based Honeypot System"
    doc.core_properties.subject = "CT 8415 Network and Internet Security Project Report"
    doc.core_properties.author = "[Enter Student Name]"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
