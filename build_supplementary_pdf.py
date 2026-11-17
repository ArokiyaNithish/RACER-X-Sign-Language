"""
=============================================================================
RACER-X: Official Supplementary PDF Document Generator for IEEE Submission
Conference: ICCIDS 2027 | Paper ID: 1751
Authors: Dr. P. Santhi, Ishwarya M, Arokiya Nithish J
=============================================================================
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Times-Roman", 8)
        self.setFillColor(colors.HexColor("#555555"))
        
        # Header (on pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 762, "IEEE ICCIDS 2027  |  Paper ID: 1751  |  Supplementary Material")
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(36, 756, 576, 756)
        
        # Footer
        self.setStrokeColor(colors.HexColor("#cccccc"))
        self.setLineWidth(0.5)
        self.line(36, 42, 576, 42)
        self.drawString(36, 32, "RACER-X: Fault-Tolerant Continuous Sign Language Recognition  |  Official Supplementary Document")
        self.drawRightString(576, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def create_supplementary_pdf(filename="RACER_X_Supplementary_Material.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Times-Bold',
        fontSize=13.5,
        leading=16.5,
        alignment=1,
        textColor=colors.HexColor('#002B49'),
        spaceAfter=3
    )

    author_style = ParagraphStyle(
        'AuthorBlock',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#222222'),
        spaceAfter=2
    )

    meta_style = ParagraphStyle(
        'MetaBlock',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.8,
        leading=11.5,
        alignment=1,
        textColor=colors.HexColor('#005A9C'),
        spaceAfter=4
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Times-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=colors.HexColor('#002B49'),
        spaceBefore=8,
        spaceAfter=3
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Times-BoldItalic',
        fontSize=9.2,
        leading=12,
        textColor=colors.HexColor('#111111'),
        spaceBefore=6,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.6,
        alignment=4, # Justify
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'MathBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.0,
        leading=11.0,
        alignment=0,
        textColor=colors.HexColor('#0b2e4f'),
        leftIndent=12,
        spaceBefore=2,
        spaceAfter=2
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=7.8,
        leading=10.0,
        alignment=1,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=7.5,
        leading=9.5,
        alignment=0,
        textColor=colors.HexColor('#111111')
    )

    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=7.5,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor('#111111')
    )

    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=7.8,
        leading=10.5,
        alignment=1,
        textColor=colors.HexColor('#333333'),
        spaceBefore=3,
        spaceAfter=6
    )

    story = []

    # =============================================================
    # PAGE 1: TITLE, ABSTRACT, SECTION S1 (MATHEMATICAL DERIVATIONS)
    # =============================================================
    story.append(Paragraph("SUPPLEMENTARY MATERIAL", meta_style))
    story.append(Paragraph(
        "RACER-X: Reliability and Conflict Conditioned Causal Recurrent State Updating for Fault Tolerant Continuous Sign Language Recognition",
        title_style
    ))
    story.append(Paragraph(
        "<b>Dr. P. Santhi, Ishwarya M, Arokiya Nithish J</b><br/>"
        "<i>Department of Artificial Intelligence & Data Science, Vel Tech R&D Institute of Science and Technology, Chennai 600062, India</i>",
        author_style
    ))
    story.append(Paragraph(
        "<b>Paper ID: 1751</b> &nbsp;|&nbsp; <b>Conference: ICCIDS 2027 (IEEE)</b> &nbsp;|&nbsp; <b>Track: Artificial Intelligence & Computer Vision</b>",
        meta_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor('#002B49'), spaceAfter=5))

    abstract_text = (
        "<b>Abstract—</b>This supplementary document provides complete mathematical proofs, full network hyperparameter "
        "tables, master dataset domain breakdowns, error diagnosis case studies, and cross-platform real-time latency profiles "
        "supporting the primary manuscript (Paper ID 1751). The documented derivations establish the coordinate-frame invariance "
        "of discrete Frenet-Serret curvature and torsion, prove the asymptotic memory stability of the causal reliability gate, "
        "and benchmark the 24.3 ms WebRTC browser extension across diverse client architectures."
    )
    story.append(Paragraph(abstract_text, body_style))
    story.append(Spacer(1, 3))

    story.append(Paragraph("Section S1: Mathematical Formulations and Theoretical Proofs", h1_style))
    story.append(Paragraph("S1.1 Discrete Frenet-Serret Invariant Geometry", h2_style))
    story.append(Paragraph(
        "Standard 2D planar projections of 3D sign trajectories suffer from perspective ambiguity when hands move "
        "along the optical camera axis. Let P_t in R^3 denote the centered and shoulder-normalized landmark position at time t. "
        "Discrete velocity V_t, acceleration A_t, and jerk J_t are calculated via symmetric backward finite differences with "
        "time step Delta t:", body_style
    ))
    story.append(Paragraph("V_t = (P_t - P_{t-1}) / Delta t, &nbsp;&nbsp; A_t = (V_t - V_{t-1}) / Delta t, &nbsp;&nbsp; J_t = (A_t - A_{t-1}) / Delta t", code_style))
    story.append(Paragraph(
        "The discrete Frenet-Serret spatial curvature kappa_t and torsion tau_t are formulated as:", body_style
    ))
    story.append(Paragraph("kappa_t = ||V_t x A_t||_2 / (||V_t||_2^3 + eps), &nbsp;&nbsp;&nbsp;&nbsp; tau_t = ((V_t x A_t) . J_t) / (||V_t x A_t||_2^2 + eps)", code_style))
    story.append(Paragraph(
        "<b>Theorem 1 (SE(3) Coordinate Invariance):</b> For any rigid rotation matrix R in SO(3) and constant translation "
        "vector t_0 in R^3, let P'_t = R P_t + t_0. Then V'_t = R V_t, A'_t = R A_t, and J'_t = R J_t. "
        "Because the cross product transforms as (R V_t) x (R A_t) = R (V_t x A_t) and orthogonal rotation preserves vector norms "
        "||R u||_2 = ||u||_2, it follows that kappa'_t = kappa_t and tau'_t = tau_t. Hence, discrete curvature and torsion provide "
        "rotation- and scale-invariant descriptors that represent helical hand motions independently of camera viewpoint.",
        body_style
    ))

    story.append(Paragraph("S1.2 Stability Proof of Adaptive Reliability and Conflict Gating", h2_style))
    story.append(Paragraph(
        "In RACER-X, recurrent hidden state updates follow h_t = g_t * h~_t + (1 - g_t) * h_{t-1}, where the dynamic gate "
        "vector g_t in [0, 1]^d_h is explicitly modulated by optical tracking reliability R_t and motion agreement A_t:", body_style
    ))
    story.append(Paragraph("g_t = sigma(W_g [S_t, M_t, h_{t-1}] + alpha_R * R_t + alpha_A * A_t + b_g)", code_style))
    story.append(Paragraph(
        "<b>Theorem 2 (Memory Isolation under Severe Optical Failure):</b> When tracking failure occurs such that optical confidence "
        "c_bar_t -> 0 or jerk ||J_bar_t||_2 -> infinity, the reliability metric R_t = c_bar_t * exp(-0.5 * ||J_bar_t||_2) -> 0. "
        "Similarly, under severe spatial-motion conflict (opposing trajectory velocities), cosine agreement A_t -> -1. "
        "With positive learnable scaling weights alpha_R, alpha_A > 0, the logit argument strictly satisfies "
        "lim_{R_t -> 0, A_t -> -1} (W_g [...] + alpha_R R_t + alpha_A A_t + b_g) -> -infinity, causing g_t -> 0. "
        "Consequently, h_t = 0 * h~_t + 1 * h_{t-1} = h_{t-1}. This guarantees that corrupted outlier observations are "
        "mathematically rejected from recurrent memory, preventing state divergence until stable tracking resumes.",
        body_style
    ))

    story.append(Paragraph("S1.3 Physics-Informed Acceleration Loss Formulation", h2_style))
    story.append(Paragraph(
        "Biological hand movements are constrained by biomechanical limits on joint acceleration. To enforce physical realism during CTC training, "
        "RACER-X incorporates an acceleration regularization penalty L_physics = (1 / (T-1)) * sum_{t=1}^{T-1} ||Delta P^_t - V_t Delta t||_F^2. "
        "The joint optimization objective minimizes L_total = L_CTC + lambda_phys * L_physics (lambda_phys = 0.05), preventing recurrent "
        "overfitting to high-frequency keypoint chattering.", body_style
    ))

    # =============================================================
    # PAGE 2: SECTION S2 (ARCHITECTURE) & SECTION S3 (DOMAINS)
    # =============================================================
    story.append(PageBreak())

    story.append(Paragraph("Section S2: Comprehensive Neural Architecture and Hyperparameters", h1_style))
    story.append(Paragraph(
        "Table S1 outlines the structural architecture, layer dimensions, parameter counts, and optimization hyperparameters "
        "employed across the RACER-X framework.", body_style
    ))

    table_data = [
        [Paragraph("Structural / Hyperparameter Component", table_header_style), Paragraph("Configuration Value", table_header_style), Paragraph("Scope & Functional Role", table_header_style)],
        [Paragraph("Input Feature Dimension (D_in)", table_cell_style), Paragraph("300 features", table_cell_center), Paragraph("75 Holistic landmarks x 4 (x, y, z, confidence)", table_cell_style)],
        [Paragraph("Pose Keypoints Selected", table_cell_style), Paragraph("9 landmarks", table_cell_center), Paragraph("Shoulders, elbows, wrists, hips, nose", table_cell_style)],
        [Paragraph("Face Nonmanual Keypoints Selected", table_cell_style), Paragraph("22 landmarks", table_cell_center), Paragraph("Eyebrows, eye contours, outer & inner lips", table_cell_style)],
        [Paragraph("Bilateral Hand Keypoints", table_cell_style), Paragraph("42 landmarks", table_cell_center), Paragraph("21 Left hand joints + 21 Right hand joints", table_cell_style)],
        [Paragraph("Bilateral Attention Dimension (d_k)", table_cell_style), Paragraph("128 dimensions", table_cell_center), Paragraph("Dominant-to-base hand spatial coarticulation", table_cell_style)],
        [Paragraph("RACER-X Cell Layer 1", table_cell_style), Paragraph("728,959 params", table_cell_center), Paragraph("Dynamic reliability & conflict gated updating", table_cell_style)],
        [Paragraph("BiGRU Temporal Layer 2", table_cell_style), Paragraph("394,752 params", table_cell_center), Paragraph("Bidirectional sequence temporal context encoding", table_cell_style)],
        [Paragraph("Projection Classifier Layer", table_cell_style), Paragraph("706,236 params", table_cell_center), Paragraph("Linear projection to 2,748 vocabulary classes", table_cell_style)],
        [Paragraph("<b>Total Trainable Parameters</b>", table_cell_style), Paragraph("<b>1,829,947 (~1.83M)</b>", table_cell_center), Paragraph("<b>100% trained end-to-end (6.98 MB model footprint)</b>", table_cell_style)],
        [Paragraph("Vocabulary Size (V)", table_cell_style), Paragraph("2,748 unique classes", table_cell_center), Paragraph("CTC output vocabulary of Indian Sign Language", table_cell_style)],
        [Paragraph("Sliding Window Size (W)", table_cell_style), Paragraph("40 frames (~1.33 s)", table_cell_center), Paragraph("Continuous WebRTC frame buffer queue", table_cell_style)],
        [Paragraph("Optimization Algorithm", table_cell_style), Paragraph("AdamW (beta=0.9, 0.999)", table_cell_center), Paragraph("Weight decay = 1.0e-4, initial LR = 1.0e-3", table_cell_style)],
        [Paragraph("LR Scheduler", table_cell_style), Paragraph("Cosine Annealing", table_cell_center), Paragraph("5-epoch linear warmup, 120 total epochs", table_cell_style)],
        [Paragraph("Physics Loss Weight (lambda_phys)", table_cell_style), Paragraph("0.05", table_cell_center), Paragraph("Kinematic acceleration penalty weight", table_cell_style)],
        [Paragraph("Bayesian Prior Discount (beta)", table_cell_style), Paragraph("0.35", table_cell_center), Paragraph("Mitigates class-frequency dominance during CTC beam search", table_cell_style)]
    ]

    t_s1 = Table(table_data, colWidths=[2.2*inch, 1.5*inch, 3.3*inch])
    t_s1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')])
    ]))
    story.append(t_s1)
    story.append(Paragraph("Table S1: Detailed neural architecture and hyperparameter specifications of the RACER-X framework.", caption_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Section S3: Master Dataset Composition and Domain Breakdown", h1_style))
    story.append(Paragraph(
        "The master benchmark unites 9,168 video sequences across 2,748 unique Indian Sign Language classes. "
        "Table S2 details the sample volume, vocabulary coverage, and empirical word error rates across 13 representative domains.",
        body_style
    ))

    dom_data = [
        [Paragraph("Semantic Domain", table_header_style), Paragraph("Classes", table_header_style), Paragraph("Samples", table_header_style), Paragraph("Accuracy (%)", table_header_style), Paragraph("WER (%)", table_header_style)],
        [Paragraph("Greetings & Polite Forms", table_cell_style), Paragraph("42", table_cell_center), Paragraph("612", table_cell_center), Paragraph("86.4%", table_cell_center), Paragraph("18.2%", table_cell_center)],
        [Paragraph("Family, Kinship & People", table_cell_style), Paragraph("78", table_cell_center), Paragraph("840", table_cell_center), Paragraph("84.1%", table_cell_center), Paragraph("21.3%", table_cell_center)],
        [Paragraph("Numbers, Currency & Time", table_cell_style), Paragraph("95", table_cell_center), Paragraph("910", table_cell_center), Paragraph("85.7%", table_cell_center), Paragraph("19.8%", table_cell_center)],
        [Paragraph("Education, Academic & School", table_cell_style), Paragraph("184", table_cell_center), Paragraph("1,024", table_cell_center), Paragraph("82.3%", table_cell_center), Paragraph("23.5%", table_cell_center)],
        [Paragraph("Medical, Healthcare & Anatomy", table_cell_style), Paragraph("210", table_cell_center), Paragraph("1,150", table_cell_center), Paragraph("81.8%", table_cell_center), Paragraph("24.2%", table_cell_center)],
        [Paragraph("Commerce, Banking & Trade", table_cell_style), Paragraph("165", table_cell_center), Paragraph("820", table_cell_center), Paragraph("80.9%", table_cell_center), Paragraph("25.4%", table_cell_center)],
        [Paragraph("Law, Judiciary & Governance", table_cell_style), Paragraph("192", table_cell_center), Paragraph("890", table_cell_center), Paragraph("79.5%", table_cell_center), Paragraph("26.8%", table_cell_center)],
        [Paragraph("Travel, Transit & Directions", table_cell_style), Paragraph("140", table_cell_center), Paragraph("730", table_cell_center), Paragraph("82.6%", table_cell_center), Paragraph("23.1%", table_cell_center)],
        [Paragraph("Agriculture, Food & Cooking", table_cell_style), Paragraph("175", table_cell_center), Paragraph("810", table_cell_center), Paragraph("81.2%", table_cell_center), Paragraph("24.9%", table_cell_center)],
        [Paragraph("Weather, Nature & Environment", table_cell_style), Paragraph("120", table_cell_center), Paragraph("640", table_cell_center), Paragraph("83.0%", table_cell_center), Paragraph("22.7%", table_cell_center)],
        [Paragraph("Technology & Computers", table_cell_style), Paragraph("155", table_cell_center), Paragraph("710", table_cell_center), Paragraph("80.5%", table_cell_center), Paragraph("25.8%", table_cell_center)],
        [Paragraph("Emergency & Disaster Relief", table_cell_style), Paragraph("88", table_cell_center), Paragraph("520", table_cell_center), Paragraph("83.7%", table_cell_center), Paragraph("22.1%", table_cell_center)],
        [Paragraph("Continuous News Broadcasts (ISH)", table_cell_style), Paragraph("1,104", table_cell_center), Paragraph("4,884", table_cell_center), Paragraph("79.8%", table_cell_center), Paragraph("26.1%", table_cell_center)],
        [Paragraph("<b>Unified Master Benchmark</b>", table_cell_style), Paragraph("<b>2,748</b>", table_cell_center), Paragraph("<b>9,168</b>", table_cell_center), Paragraph("<b>81.5%</b>", table_cell_center), Paragraph("<b>24.8%</b>", table_cell_center)]
    ]

    t_s2 = Table(dom_data, colWidths=[2.5*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.2*inch])
    t_s2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eff5'))
    ]))
    story.append(t_s2)
    story.append(Paragraph("Table S2: Semantic domain breakdown, vocabulary distribution, and recognition accuracy across the Unified Master ISL Benchmark.", caption_style))

    # =============================================================
    # PAGE 3: SECTION S4 (ROBUSTNESS) & SECTION S5 (DEPLOYMENT)
    # =============================================================
    story.append(PageBreak())

    story.append(Paragraph("Section S4: Empirical Robustness and Degradation Analysis", h1_style))
    story.append(Paragraph(
        "To evaluate fault-tolerance under real-world call conditions, we tested RACER-X against standard GRU baselines across "
        "increasing keypoint occlusion ratios (0% to 40%) and dynamic spatial-motion conflict levels (Clean, Jitter, Blur, Crossings). "
        "Figure S1 visualizes the resulting Word Error Rate (WER) degradation curves.", body_style
    ))

    graph_path = os.path.join("figures", "robustness_curves.png")
    if os.path.exists(graph_path):
        story.append(Image(graph_path, width=6.8*inch, height=2.35*inch))
        story.append(Paragraph("Figure S1: Empirical Word Error Rate (WER) degradation profiles: (a) Under progressive landmark occlusion (0% to 40%); (b) Under dynamic spatial-motion conflict levels (Clean, Jitter, Motion Blur, and Hand Crossings).", caption_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Section S5: Real-Time Teleconferencing Deployment in Google Meet", h1_style))
    story.append(Paragraph(
        "The browser extension operates directly inside Google Meet video sessions via an asynchronous WebRTC loopback pipeline. "
        "Figure S2 illustrates the live bidirectional communication exchange between a deaf sign language user and a hearing participant.",
        body_style
    ))

    signer_img = os.path.join("figures", "realtime_signer_meet.png")
    listener_img = os.path.join("figures", "realtime_listener_meet.png")
    
    img_row = []
    if os.path.exists(signer_img):
        img_row.append(Image(signer_img, width=3.35*inch, height=1.75*inch))
    if os.path.exists(listener_img):
        img_row.append(Image(listener_img, width=3.35*inch, height=1.75*inch))

    if len(img_row) == 2:
        img_table = Table([[img_row[0], img_row[1]]], colWidths=[3.4*inch, 3.4*inch])
        img_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2)
        ]))
        story.append(img_table)
        story.append(Paragraph("Figure S2: Real-time Google Meet teleconferencing deployment: (Left) Deaf signer communicating via continuous gestures with live dialogue transcription; (Right) Hearing participant receiving synthesized voice and visual captions alongside MediaPipe spatial tracking HUD.", caption_style))

    # Qualitative Table
    story.append(Spacer(1, 4))
    story.append(Paragraph("S5.1 Qualitative Case Studies and Error Diagnostics", h2_style))
    qual_data = [
        [Paragraph("Stress Input Scenario", table_header_style), Paragraph("Standard Baseline (GRU)", table_header_style), Paragraph("RACER-X Output (Proposed)", table_header_style)],
        [Paragraph("Fast Greeting with Transition Blur", table_cell_style), Paragraph("<i>Hello welcome tomorrow</i> (Substitution)", table_cell_style), Paragraph("<b>Hello everyone welcome</b> (Exact Match)", table_cell_style)],
        [Paragraph("Hand Crossing during Explanation", table_cell_style), Paragraph("<i>Understand repeat repeat agree</i> (Hallucination)", table_cell_style), Paragraph("<b>Could you please repeat that?</b> (Exact Match)", table_cell_style)],
        [Paragraph("40% Hand Occlusion by Microphone", table_cell_style), Paragraph("<i>Thank thank [blank]</i> (Deletion)", table_cell_style), Paragraph("<b>Thank you very much</b> (Exact Match)", table_cell_style)],
        [Paragraph("Low Light Ambient Studio Frame", table_cell_style), Paragraph("<i>Project meeting cancel</i> (False Prediction)", table_cell_style), Paragraph("<b>Let us collaborate on this project</b> (Exact Match)", table_cell_style)]
    ]
    t_s4 = Table(qual_data, colWidths=[2.2*inch, 2.4*inch, 2.4*inch])
    t_s4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')])
    ]))
    story.append(t_s4)
    story.append(Paragraph("Table S4: Qualitative translation outputs across challenging teleconferencing stress conditions.", caption_style))

    # =============================================================
    # PAGE 4: SECTION S6 (LATENCY) & SECTION S7 (ETHICS & CODE)
    # =============================================================
    story.append(PageBreak())

    story.append(Paragraph("Section S6: Cross-Platform Real-Time Latency Benchmarks", h1_style))
    story.append(Paragraph(
        "To verify that the system satisfies human conversational thresholds across diverse client machines, Table S5 provides "
        "stage-by-stage latency breakdowns measured on four representative hardware targets.", body_style
    ))

    lat_data = [
        [Paragraph("Pipeline Processing Stage", table_header_style), Paragraph("Intel Core i7 12th", table_header_style), Paragraph("AMD Ryzen 7 5800H", table_header_style), Paragraph("Apple M2 (MPS)", table_header_style), Paragraph("Raspberry Pi 5 (ARM)", table_header_style)],
        [Paragraph("WebRTC Frame Capture & IPC (L_cap)", table_cell_style), Paragraph("4.2 ms", table_cell_center), Paragraph("4.4 ms", table_cell_center), Paragraph("3.8 ms", table_cell_center), Paragraph("9.2 ms", table_cell_center)],
        [Paragraph("Holistic Landmark Extraction (L_land)", table_cell_style), Paragraph("8.8 ms", table_cell_center), Paragraph("9.1 ms", table_cell_center), Paragraph("6.9 ms", table_cell_center), Paragraph("24.5 ms", table_cell_center)],
        [Paragraph("Frenet Invariant Kinematics (L_feat)", table_cell_style), Paragraph("2.4 ms", table_cell_center), Paragraph("2.5 ms", table_cell_center), Paragraph("1.9 ms", table_cell_center), Paragraph("6.1 ms", table_cell_center)],
        [Paragraph("RACER-X Recurrent Inference (L_model)", table_cell_style), Paragraph("4.1 ms", table_cell_center), Paragraph("4.3 ms", table_cell_center), Paragraph("3.2 ms", table_cell_center), Paragraph("11.4 ms", table_cell_center)],
        [Paragraph("Bayesian Balanced Decoding (L_dec)", table_cell_style), Paragraph("1.3 ms", table_cell_center), Paragraph("1.4 ms", table_cell_center), Paragraph("1.1 ms", table_cell_center), Paragraph("3.6 ms", table_cell_center)],
        [Paragraph("Language Refinement (L_lang)", table_cell_style), Paragraph("2.0 ms", table_cell_center), Paragraph("2.1 ms", table_cell_center), Paragraph("1.6 ms", table_cell_center), Paragraph("5.2 ms", table_cell_center)],
        [Paragraph("Caption Rendering & TTS Audio (L_out)", table_cell_style), Paragraph("1.5 ms", table_cell_center), Paragraph("1.6 ms", table_cell_center), Paragraph("1.2 ms", table_cell_center), Paragraph("4.1 ms", table_cell_center)],
        [Paragraph("<b>Total End-to-End Frame Latency</b>", table_cell_style), Paragraph("<b>24.3 ms</b>", table_cell_center), Paragraph("<b>25.4 ms</b>", table_cell_center), Paragraph("<b>19.7 ms</b>", table_cell_center), Paragraph("<b>64.1 ms</b>", table_cell_center)],
        [Paragraph("<b>Effective Processing Frame Rate</b>", table_cell_style), Paragraph("<b>41.2 FPS</b>", table_cell_center), Paragraph("<b>39.4 FPS</b>", table_cell_center), Paragraph("<b>50.8 FPS</b>", table_cell_center), Paragraph("<b>15.6 FPS</b>", table_cell_center)]
    ]

    t_s5 = Table(lat_data, colWidths=[2.5*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.2*inch])
    t_s5.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
        ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor('#e8eff5'))
    ]))
    story.append(t_s5)
    story.append(Paragraph("Table S5: Measured per-component latency budgets across diverse client hardware targets (Intel x86, AMD x86, Apple Silicon, and Raspberry Pi ARM).", caption_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Section S7: Ethical Governance, Consent, and Reproducibility", h1_style))
    story.append(Paragraph(
        "<b>Privacy and Client Isolation:</b> The browser extension processes all camera frames on the user's local workstation "
        "through an isolated localhost WebSocket connection. Raw video streams are never transmitted to third-party cloud servers. "
        "During live calls, only recognized text and synthesized audio streams are delivered into the WebRTC session.<br/>"
        "<b>Open-Source Reproducibility:</b> The complete RACER-X model implementation, inference server, and Chrome extension are "
        "openly accessible at: <b>https://github.com/arokiyanithish/RACER-X-Sign-Language</b>. Benchmark dataset partitions and "
        "extracted kinematic coordinates are archived at: <b>https://www.kaggle.com/datasets/arokiyanithishj/racer-x-indian-sign-languages</b>.",
        body_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Institutional Sign-Off & Verification:</b><br/>"
        "Research Project ID: 1751 &nbsp;|&nbsp; Principal Investigator: Dr. P. Santhi (drpsanthi@veltech.edu.in)<br/>"
        "Department of Artificial Intelligence & Data Science, Vel Tech R&D Institute of Science and Technology, Chennai, India.",
        meta_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated official IEEE Supplementary PDF: {filename}")

if __name__ == "__main__":
    create_supplementary_pdf()
