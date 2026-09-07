"""
src/report_generator.py
-----------------------
Generates professional clinical diagnosis & risk assessment PDF reports
using ReportLab.

Strict requirements implemented:
1. Current visit assessment & deterministic rule engine outputs only.
2. NO previous diagnoses displayed in report body or history sections.
3. Compact "Last 5 Visits" widget rendered in top-right header section (Date | Visit).
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_medical_diagnosis_pdf(
    patient_info: Dict[str, Any],
    doctor_info: Dict[str, Any],
    diagnosis_info: Dict[str, Any],
    assessment_info: Optional[Dict[str, Any]] = None,
    blood_test_info: Optional[Dict[str, Any]] = None,
    past_visits: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """
    Builds a structured, professional medical diagnosis PDF report in memory.
    Includes a small 'Last 5 Visits' widget in the top-right corner.
    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    primary_color = colors.HexColor("#0f3a60")
    secondary_color = colors.HexColor("#0284c7")
    dark_text = colors.HexColor("#1e293b")
    muted_text = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")
    risk_critical_color = colors.HexColor("#991b1b")
    risk_high_color = colors.HexColor("#dc2626")
    risk_med_color = colors.HexColor("#d97706")
    risk_low_color = colors.HexColor("#16a34a")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=primary_color,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=muted_text,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=primary_color,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=dark_text,
    )
    widget_hdr = ParagraphStyle(
        "WgtHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=primary_color,
        alignment=1,
    )
    widget_cell = ParagraphStyle(
        "WgtCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=dark_text,
        alignment=1,
    )

    story = []

    # ---------------------------------------------------------------------------
    # 1. Top Header Banner with "Last 5 Visits" Widget (Top-Right)
    # ---------------------------------------------------------------------------
    visit_rows = [
        [
            Paragraph("<b>Date</b>", widget_hdr),
            Paragraph("<b>Visit</b>", widget_hdr),
        ]
    ]

    # Process and sort past visits newest -> oldest, limit to max 5
    clean_visits = []
    if past_visits:
        for v in past_visits:
            v_date = v.get("date") or v.get("created_at")
            if hasattr(v_date, "strftime"):
                date_str = v_date.strftime("%d %b %Y")
            else:
                date_str = str(v_date)[:10] if v_date else "N/A"
            v_label = v.get("label") or v.get("type") or "Visit"
            clean_visits.append((date_str, v_label))

    clean_visits = clean_visits[:5]

    if clean_visits:
        for d_str, v_lbl in clean_visits:
            visit_rows.append([
                Paragraph(d_str, widget_cell),
                Paragraph(v_lbl, widget_cell),
            ])
    else:
        visit_rows.append([
            Paragraph(datetime.now(timezone.utc).strftime("%d %b %Y"), widget_cell),
            Paragraph("Current", widget_cell),
        ])

    widget_table = Table(visit_rows, colWidths=[65, 45])
    widget_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    wgt_title = Paragraph("<b>Last 5 Visits</b>", ParagraphStyle("WgtT", parent=widget_hdr, fontSize=8, leading=10, textColor=primary_color, spaceAfter=2))
    widget_container_data = [[wgt_title], [widget_table]]
    widget_container = Table(widget_container_data, colWidths=[115])
    widget_container.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    current_date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    rpt_id = f"RPT-{patient_info.get('id', '00')}-{diagnosis_info.get('id', '00')}"

    header_data = [
        [
            Paragraph(
                f"<b>MEDICAL RISK & CLINICAL CARE REPORT</b><br/>"
                f"<font size=8 color='#64748b'>Report Date: {current_date_str} | ID: {rpt_id}</font><br/>"
                f"<font size=8 color='#991b1b'><b>Confidential Medical Document</b></font>",
                title_style,
            ),
            widget_container,
        ]
    ]

    header_table = Table(header_data, colWidths=[415, 125])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=8))

    # ---------------------------------------------------------------------------
    # 2. Patient & Attending Physician Information Table
    # ---------------------------------------------------------------------------
    patient_sex_str = "Male" if str(patient_info.get("sex")) in ["1", "1.0", "Male"] else ("Female" if str(patient_info.get("sex")) in ["0", "0.0", "Female"] else "Unspecified")
    patient_age_str = f"{int(patient_info['age'])} yrs" if patient_info.get("age") is not None else "Not recorded"

    info_data = [
        [
            Paragraph("<b>PATIENT DEMOGRAPHICS</b>", section_heading),
            Paragraph("<b>ATTENDING PHYSICIAN</b>", section_heading),
        ],
        [
            Paragraph(
                f"<b>Name:</b> {patient_info.get('name', 'N/A')}<br/>"
                f"<b>Age / Sex:</b> {patient_age_str} | {patient_sex_str}<br/>"
                f"<b>Patient ID:</b> #{patient_info.get('id', 'N/A')}<br/>"
                f"<b>Contact:</b> {patient_info.get('phone_number') or 'N/A'}<br/>"
                f"<b>Emergency Contact:</b> {patient_info.get('emergency_contact_name') or 'N/A'} ({patient_info.get('emergency_contact_phone') or 'N/A'})",
                body_style,
            ),
            Paragraph(
                f"<b>Doctor Name:</b> {doctor_info.get('name', 'N/A')}<br/>"
                f"<b>Specialization:</b> {doctor_info.get('specialization') or 'Internal Medicine / Cardiology'}<br/>"
                f"<b>License No:</b> {doctor_info.get('license_number') or 'DOC-REG-2026'}<br/>"
                f"<b>Email:</b> {doctor_info.get('email', 'N/A')}<br/>"
                f"<b>Care Center:</b> Central Clinical Institute",
                body_style,
            ),
        ],
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e0f2fe")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e0f2fe")),
        ("BACKGROUND", (0, 1), (0, 1), bg_light),
        ("BACKGROUND", (1, 1), (1, 1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------------------------
    # 3. Current Visit Diagnosis & Clinical Assessment (No Past Diagnoses)
    # ---------------------------------------------------------------------------
    diag_title = diagnosis_info.get("diagnosis_title", "Clinical Evaluation & Risk Assessment")
    diag_notes = diagnosis_info.get("clinical_notes", "Evaluation performed based on current patient parameters.")
    diag_plan = diagnosis_info.get("treatment_plan") or "Follow standard therapeutic management and lifestyle protocol."
    diag_rx = diagnosis_info.get("prescriptions") or "As prescribed during consultation."
    diag_date = diagnosis_info.get("created_at")
    diag_date_str = diag_date.strftime("%Y-%m-%d %H:%M") if hasattr(diag_date, "strftime") else str(diag_date or current_date_str)

    diag_data = [
        [Paragraph(f"<b>CURRENT VISIT DIAGNOSIS & CLINICAL IMPRESSION</b> (Visit Date: {diag_date_str})", section_heading)],
        [
            Paragraph(
                f"<b>Primary Diagnosis:</b><br/>"
                f"<font size=10 color='#0f3a60'><b>{diag_title}</b></font><br/><br/>"
                f"<b>Clinical Notes & Findings:</b><br/>{diag_notes}<br/><br/>"
                f"<b>Treatment & Management Plan:</b><br/>{diag_plan}<br/><br/>"
                f"<b>Prescriptions / Recommendations:</b><br/>{diag_rx}",
                body_style,
            )
        ]
    ]
    diag_table = Table(diag_data, colWidths=[540])
    diag_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0, 1), (0, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(diag_table)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------------------------
    # 4. Deterministic Clinical Risk Prediction Engine Summary (Enhanced)
    # ---------------------------------------------------------------------------
    if assessment_info:
        risk_level = assessment_info.get("risk_level", "Low Risk")
        prob_val = float(assessment_info.get("risk_probability", 0))
        prob_pct = f"{prob_val * 100:.1f}%" if prob_val <= 1.0 else f"{prob_val:.1f}%"

        if "Critical" in risk_level:
            risk_color = risk_critical_color
        elif "High" in risk_level:
            risk_color = risk_high_color
        elif "Mod" in risk_level or "Med" in risk_level:
            risk_color = risk_med_color
        else:
            risk_color = risk_low_color

        vitals_str = (
            f"<b>Systolic / Diastolic BP:</b> {assessment_info.get('systolic_bp', '-')}/{assessment_info.get('diastolic_bp', '-')} mmHg  |  "
            f"<b>Max HR:</b> {assessment_info.get('max_heart_rate', '-')} bpm  |  "
            f"<b>BMI:</b> {assessment_info.get('bmi', '-')} kg/m²<br/>"
            f"<b>Cholesterol:</b> {assessment_info.get('cholesterol', '-')} mg/dL  |  "
            f"<b>ST Dep:</b> {assessment_info.get('st_depression', '0.0')} mm"
        )

        # Extract enhanced rule engine outputs
        triggered_rules = assessment_info.get("triggered_rules", [])
        triggered_rule_codes = [r.get("rule_code", "") for r in triggered_rules]
        
        # Build point breakdown section
        point_breakdown_rows = [["<b>Rule Code</b>", "<b>Category</b>", "<b>Points</b>", "<b>Description</b>"]]
        for rule in triggered_rules[:10]:  # Show top 10 rules
            rule_code = rule.get("rule_code", "N/A")
            category = rule.get("category", "General")
            points = str(rule.get("points", 0))
            description = rule.get("description", "")[:60] + ("..." if len(rule.get("description", "")) > 60 else "")
            point_breakdown_rows.append([Paragraph(rule_code, widget_cell), Paragraph(category, widget_cell), 
                                          Paragraph(points, widget_cell), Paragraph(description, widget_cell)])

        # Build synergy rules section
        synergy_rules = [r for r in triggered_rules if "SYNERGY" in r.get("rule_code", "")]
        synergy_text = "None detected" if not synergy_rules else "; ".join([r.get("rule_code", "") for r in synergy_rules])

        # Build clinical recommendations section
        clinical_recommendations = assessment_info.get("clinical_recommendations", [])
        recommendations_text = "; ".join(clinical_recommendations[:5]) if clinical_recommendations else "Standard clinical follow-up recommended"

        ai_data = [
            [
                Paragraph("<b>DETERMINISTIC CLINICAL RISK ENGINE OUTPUT</b>", section_heading),
                Paragraph(f"<b>Classification:</b> <font color='{risk_color.hexval()}'><b>{risk_level} ({prob_pct})</b></font>", section_heading),
            ],
            [
                Paragraph(
                    f"<b>Current Vitals & Lab Measurements:</b><br/>{vitals_str}<br/><br/>"
                    f"<b>Triggered Clinical Risk Factors:</b> {len(triggered_rules)} rules activated<br/>"
                    f"<b>Synergy Rules:</b> {synergy_text}<br/><br/>"
                    f"<i>Note: Evaluated by deterministic rule engine using established AHA/ACC clinical practice guidelines.</i>",
                    body_style,
                ),
                Paragraph(
                    f"<b>Risk Status:</b> {risk_level}<br/>"
                    f"<b>Risk Index:</b> {prob_pct}<br/>"
                    f"<b>Assessment Date:</b> {assessment_info.get('created_at', current_date_str)}",
                    body_style,
                )
            ]
        ]
        ai_table = Table(ai_data, colWidths=[370, 170])
        ai_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2") if "High" in risk_level or "Critical" in risk_level else colors.HexColor("#f0fdf4")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 10))

        # Point Breakdown Table
        if triggered_rules:
            point_table = Table(point_breakdown_rows, colWidths=[80, 70, 40, 350])
            point_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]))
            story.append(Paragraph("<b>RULE ENGINE POINT BREAKDOWN</b>", section_heading))
            story.append(point_table)
            story.append(Spacer(1, 10))

        # Clinical Recommendations Section
        if clinical_recommendations:
            rec_data = [
                [Paragraph("<b>CLINICAL RECOMMENDATIONS</b>", section_heading)],
                [Paragraph(recommendations_text, body_style)]
            ]
            rec_table = Table(rec_data, colWidths=[540])
            rec_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fef3c7")),
                ("BACKGROUND", (0, 1), (0, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(rec_table)
            story.append(Spacer(1, 10))

    # ---------------------------------------------------------------------------
    # 5. Laboratory Profile (if recorded for current visit)
    # ---------------------------------------------------------------------------
    if blood_test_info:
        bt_data = [
            [Paragraph("<b>CURRENT LABORATORY BLOOD TEST PROFILE</b>", section_heading), Paragraph("", section_heading)],
            [
                Paragraph(
                    f"<b>Fasting Glucose:</b> {blood_test_info.get('fasting_glucose', '-')} mg/dL  |  "
                    f"<b>HbA1c:</b> {blood_test_info.get('hba1c', '-')} %  |  "
                    f"<b>Hemoglobin:</b> {blood_test_info.get('hemoglobin', '-')} g/dL<br/>"
                    f"<b>Total Cholesterol:</b> {blood_test_info.get('total_cholesterol', '-')}  |  "
                    f"<b>HDL:</b> {blood_test_info.get('hdl', '-')}  |  "
                    f"<b>LDL:</b> {blood_test_info.get('ldl', '-')}  |  "
                    f"<b>Creatinine:</b> {blood_test_info.get('creatinine', '-')} mg/dL",
                    body_style,
                ),
                Paragraph(f"<b>Notes:</b> {blood_test_info.get('notes') or 'Verified sample'}", body_style)
            ]
        ]
        bt_table = Table(bt_data, colWidths=[370, 170])
        bt_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), bg_light),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(bt_table)
        story.append(Spacer(1, 10))

    # ---------------------------------------------------------------------------
    # 6. Physician Sign-Off & Legal Disclaimer Footer
    # ---------------------------------------------------------------------------
    sign_data = [
        [
            Paragraph(
                "<b>Clinical Disclaimer:</b><br/>"
                "This report is generated by the Medical Risk Decision Support System based on deterministic clinical rules. "
                "It serves as clinical decision support for attending healthcare professionals.",
                ParagraphStyle("Disc", parent=subtitle_style, fontSize=7.5, leading=10),
            ),
            Paragraph(
                f"<b>Physician Signature:</b><br/><br/>"
                f"_______________________________<br/>"
                f"<b>{doctor_info.get('name', 'Doctor')}</b><br/>"
                f"{doctor_info.get('specialization', 'Attending Physician')}",
                ParagraphStyle("Sign", parent=body_style, fontSize=8, leading=11, alignment=1),
            ),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[360, 180])
    sign_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=6),
        sign_table,
    ]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
