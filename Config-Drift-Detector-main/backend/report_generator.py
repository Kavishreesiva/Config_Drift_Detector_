import io
import json
import datetime
import html
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def escape_xml(text) -> str:
    """Escapes special HTML/XML characters for ReportLab Paragraph elements."""
    if text is None:
        return ""
    return html.escape(str(text))

def generate_markdown_report(data: dict) -> str:
    """
    Generates a structured Markdown report.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    intended_file = data.get("intended_file", "intended_config")
    actual_file = data.get("actual_file", "actual_config")
    drifts = data.get("drifts", [])
    
    # Calculate stats
    total = len(drifts)
    breaking = sum(1 for d in drifts if d.get("severity") == "Breaking")
    functional = sum(1 for d in drifts if d.get("severity") == "Functional")
    cosmetic = sum(1 for d in drifts if d.get("severity") == "Cosmetic")
    risk_score = data.get("risk_score", 0)
    
    md = f"""# AI Config Drift Detector - Analysis Report

**Date of Analysis:** {now}
**Intended File:** `{intended_file}`
**Actual/Live File:** `{actual_file}`

---

## Summary Statistics

| Metric | Value |
| :--- | :--- |
| **Total Drifts Detected** | {total} |
| **Breaking Drifts (Critical/High Risk)** | {breaking} |
| **Functional Drifts (Medium Risk)** | {functional} |
| **Cosmetic Drifts (Low Risk)** | {cosmetic} |
| **Overall Risk Score** | **{risk_score}/100** |

---

## Drift Analysis Details
"""

    if not drifts:
        md += "\n*No configuration drifts detected. Actual matches the intended configuration perfectly.*\n"
        return md

    for i, d in enumerate(drifts, 1):
        md += f"""
### {i}. `{d.get('key')}`
* **Type of Change:** {d.get('type')}
* **Severity:** **{d.get('severity')}**
* **Risk Level:** {d.get('risk_level', 'Medium')}

| Parameter | Value |
| :--- | :--- |
| **Intended (Old) Value** | `{d.get('old_value') if d.get('old_value') is not None else 'None (Added)'}` |
| **Actual (New) Value** | `{d.get('new_value') if d.get('new_value') is not None else 'None (Removed)'}` |

#### AI Impact Assessment:
> **Explanation:** {d.get('explanation')}
>
> **Operational/Security Impact:** {d.get('impact')}
>
> **Recommended Fix:** {d.get('recommendation')}

---
"""
    return md

def generate_pdf_report(data: dict) -> bytes:
    """
    Generates a high-quality PDF report using ReportLab and returns the binary stream.
    """
    buffer = io.BytesIO()
    
    # Page Setup
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, 
        leftMargin=40,
        topMargin=40, 
        bottomMargin=45
    )
    
    # Styling
    styles = getSampleStyleSheet()
    
    # Palette definition
    primary_color = colors.HexColor("#6366F1")    # Indigo
    dark_text = colors.HexColor("#1F2937")        # Dark slate
    light_bg = colors.HexColor("#F3F4F6")         # Light grey
    accent_breaking = colors.HexColor("#EF4444")  # Red
    accent_functional = colors.HexColor("#F59E0B")# Orange
    accent_cosmetic = colors.HexColor("#10B981")  # Green
    border_color = colors.HexColor("#E5E7EB")
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=20
    )
    
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor("#111827"),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    normal_bold = ParagraphStyle(
        'NormalBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=dark_text
    )
    
    normal_text = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=dark_text,
        leading=14
    )
    
    code_text = ParagraphStyle(
        'CodeText',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=9,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#E2E8F0"),
        borderWidth=0.5,
        borderPadding=4,
        spaceAfter=4
    )
    
    ai_box_title = ParagraphStyle(
        'AiBoxTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=primary_color,
        spaceAfter=2
    )

    story = []
    
    # 1. Header Block
    story.append(Paragraph("Configuration Drift Analysis Report", title_style))
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"AI Config Drift Detector • Generated on {now_str}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Summary Metadata Table
    intended_file = data.get("intended_file", "intended_config")
    actual_file = data.get("actual_file", "actual_config")
    drifts = data.get("drifts", [])
    
    total = len(drifts)
    breaking = sum(1 for d in drifts if d.get("severity") == "Breaking")
    functional = sum(1 for d in drifts if d.get("severity") == "Functional")
    cosmetic = sum(1 for d in drifts if d.get("severity") == "Cosmetic")
    risk_score = data.get("risk_score", 0)
    
    meta_data = [
        [Paragraph("<b>Intended Config File:</b>", normal_text), Paragraph(intended_file, normal_text),
         Paragraph("<b>Total Drifts:</b>", normal_text), Paragraph(str(total), normal_bold)],
        [Paragraph("<b>Actual/Live Config File:</b>", normal_text), Paragraph(actual_file, normal_text),
         Paragraph("<b>Breaking Drifts:</b>", normal_text), Paragraph(f"<font color='#EF4444'><b>{breaking}</b></font>", normal_text)],
        [Paragraph("<b>Analysis Date:</b>", normal_text), Paragraph(now_str, normal_text),
         Paragraph("<b>Functional Drifts:</b>", normal_text), Paragraph(f"<font color='#F59E0B'><b>{functional}</b></font>", normal_text)],
        [Paragraph("<b>Overall Risk Score:</b>", normal_text), Paragraph(f"<b>{risk_score}/100</b>", normal_bold),
         Paragraph("<b>Cosmetic Drifts:</b>", normal_text), Paragraph(f"<font color='#10B981'><b>{cosmetic}</b></font>", normal_text)]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.8*inch, 2.5*inch, 1.5*inch, 1.2*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9FAFB")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
    ]))
    
    story.append(meta_table)
    story.append(Spacer(1, 20))
    
    # 3. Detailed Drift List
    story.append(Paragraph("Detailed Drift Logs", h2_style))
    
    if not drifts:
        story.append(Paragraph("No configuration drifts detected. The files are identical.", normal_text))
    else:
        for idx, d in enumerate(drifts, 1):
            severity = d.get("severity", "Cosmetic")
            if severity == "Breaking":
                sev_color = "#EF4444"
                sev_bg = "#FEE2E2"
            elif severity == "Functional":
                sev_color = "#F59E0B"
                sev_bg = "#FEF3C7"
            else:
                sev_color = "#10B981"
                sev_bg = "#D1FAE5"
                
            # Key Title with Severity Badge
            badge_html = f"<font color='{sev_color}'><b>[{severity.upper()}]</b></font>"
            header_text = f"<b>{idx}. {escape_xml(d.get('key'))}</b> {badge_html}"
            
            # Values Table
            old_val = d.get('old_value')
            if old_val is None:
                old_val_str = "None (Added)"
            else:
                old_val_str = json.dumps(old_val) if isinstance(old_val, (dict, list)) else str(old_val)
                
            new_val = d.get('new_value')
            if new_val is None:
                new_val_str = "None (Removed)"
            else:
                new_val_str = json.dumps(new_val) if isinstance(new_val, (dict, list)) else str(new_val)
                
            val_data = [
                [Paragraph("<b>Intended Value</b>", normal_bold), Paragraph("<b>Actual Value</b>", normal_bold)],
                [Paragraph(escape_xml(old_val_str), code_text), Paragraph(escape_xml(new_val_str), code_text)]
            ]
            val_table = Table(val_data, colWidths=[3.5*inch, 3.5*inch])
            val_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,0), 2),
                ('TOPPADDING', (0,1), (-1,1), 4),
            ]))
            
            # AI impact assessment styled box
            ai_data = [
                [Paragraph("🤖 AI Impact Analysis", ai_box_title)],
                [Paragraph(f"<b>Explanation:</b> {escape_xml(d.get('explanation'))}", normal_text)],
                [Paragraph(f"<b>Operational/Security Impact:</b> {escape_xml(d.get('impact'))}", normal_text)],
                [Paragraph(f"<b>Recommended Action:</b> <i>{escape_xml(d.get('recommendation'))}</i>", normal_text)]
            ]
            ai_table = Table(ai_data, colWidths=[7.0*inch])
            ai_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F3FF")), # Lavender background
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#DDD6FE")),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,0), 4),
            ]))
            
            # Keep each drift block together to avoid page breaks mid-card
            drift_block = []
            drift_block.append(Paragraph(header_text, ParagraphStyle('DriftHead', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=11, spaceBefore=10, spaceAfter=4)))
            drift_block.append(val_table)
            drift_block.append(Spacer(1, 4))
            drift_block.append(ai_table)
            drift_block.append(Spacer(1, 15))
            
            story.append(KeepTogether(drift_block))
            
    # Build Document
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        page_num = canvas.getPageNumber()
        canvas.drawRightString(letter[0] - 40, 20, f"Page {page_num}")
        canvas.drawString(40, 20, "Confidential - Configuration Drift Report")
        
        # Add footer line
        canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
        canvas.setLineWidth(0.5)
        canvas.line(40, 32, letter[0] - 40, 32)
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
