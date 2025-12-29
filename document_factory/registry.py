"""Document Types Registry - Defines all supported legal document types."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocumentCategory(Enum):
    """Categories of legal documents."""
    CORRESPONDENCE = "correspondence"
    PLEADING = "pleading"
    MOTION = "motion"
    DISCOVERY = "discovery"
    BRIEF = "brief"
    COURT_ORDER = "court_order"


class CitationStyle(Enum):
    """Citation formatting styles."""
    BLUEBOOK = "bluebook"
    INLINE_PARENTHETICAL = "inline_parenthetical"
    FOOTNOTE = "footnote"


class Tone(Enum):
    """Document tone options."""
    PROFESSIONAL = "professional"
    FORMAL = "formal"
    ASSERTIVE = "assertive"
    AGGRESSIVE = "aggressive"
    CONCILIATORY = "conciliatory"
    PERSUASIVE = "persuasive"


@dataclass
class DocumentTemplate:
    """Template definition for a document type."""
    name: str
    category: DocumentCategory
    description: str
    sections: list[str]
    tone: list[Tone]
    citation_style: CitationStyle
    has_caption: bool = False
    has_signature_block: bool = True
    has_certificate_of_service: bool = False


# =============================================================================
# DOCUMENT TYPES REGISTRY
# =============================================================================

DOCUMENT_TYPES: dict[str, DocumentTemplate] = {

    # -------------------------------------------------------------------------
    # CLIENT COMMUNICATIONS
    # -------------------------------------------------------------------------

    "client_letter": DocumentTemplate(
        name="Client Advisory Letter",
        category=DocumentCategory.CORRESPONDENCE,
        description="Professional letter to client analyzing legal issues and providing recommendations",
        sections=[
            "letterhead_and_date",
            "client_address",
            "re_line",
            "salutation",
            "introduction",
            "analysis_sections",  # Multiple sections based on issues
            "recommendations",
            "next_steps",
            "closing",
            "signature"
        ],
        tone=[Tone.PROFESSIONAL, Tone.CONCILIATORY],
        citation_style=CitationStyle.INLINE_PARENTHETICAL,
        has_signature_block=True
    ),

    "engagement_letter": DocumentTemplate(
        name="Engagement Letter",
        category=DocumentCategory.CORRESPONDENCE,
        description="Letter establishing attorney-client relationship and scope of representation",
        sections=[
            "letterhead_and_date",
            "client_address",
            "re_line",
            "salutation",
            "scope_of_representation",
            "fee_arrangement",
            "client_responsibilities",
            "termination_provisions",
            "acknowledgment",
            "signature_block_with_acceptance"
        ],
        tone=[Tone.PROFESSIONAL, Tone.FORMAL],
        citation_style=CitationStyle.INLINE_PARENTHETICAL,
        has_signature_block=True
    ),

    # -------------------------------------------------------------------------
    # OPPOSING COUNSEL COMMUNICATIONS
    # -------------------------------------------------------------------------

    "demand_letter": DocumentTemplate(
        name="Demand Letter",
        category=DocumentCategory.CORRESPONDENCE,
        description="Formal demand to opposing party or counsel",
        sections=[
            "letterhead_and_date",
            "recipient_address",
            "re_line",
            "salutation",
            "demand_statement",
            "factual_background",
            "legal_basis",
            "damages_or_relief_sought",
            "deadline_and_consequences",
            "closing",
            "signature"
        ],
        tone=[Tone.ASSERTIVE, Tone.PROFESSIONAL],
        citation_style=CitationStyle.INLINE_PARENTHETICAL,
        has_signature_block=True
    ),

    "settlement_offer": DocumentTemplate(
        name="Settlement Offer Letter",
        category=DocumentCategory.CORRESPONDENCE,
        description="Formal settlement proposal to opposing counsel",
        sections=[
            "letterhead_and_date",
            "recipient_address",
            "re_line_with_rule_408_notice",
            "salutation",
            "settlement_proposal",
            "terms_and_conditions",
            "rationale",
            "response_deadline",
            "closing",
            "signature"
        ],
        tone=[Tone.PROFESSIONAL, Tone.CONCILIATORY],
        citation_style=CitationStyle.INLINE_PARENTHETICAL,
        has_signature_block=True
    ),

    "meet_and_confer_letter": DocumentTemplate(
        name="Meet and Confer Letter",
        category=DocumentCategory.CORRESPONDENCE,
        description="Letter attempting to resolve discovery or other disputes before court intervention",
        sections=[
            "letterhead_and_date",
            "recipient_address",
            "re_line",
            "salutation",
            "dispute_identification",
            "our_position",
            "proposed_resolution",
            "request_for_response",
            "closing",
            "signature"
        ],
        tone=[Tone.PROFESSIONAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.INLINE_PARENTHETICAL,
        has_signature_block=True
    ),

    # -------------------------------------------------------------------------
    # PLEADINGS
    # -------------------------------------------------------------------------

    "complaint": DocumentTemplate(
        name="Complaint",
        category=DocumentCategory.PLEADING,
        description="Initial pleading setting forth claims against defendant",
        sections=[
            "caption",
            "introduction",
            "parties",
            "jurisdiction_and_venue",
            "factual_allegations",
            "claims_for_relief",  # Multiple counts
            "prayer_for_relief",
            "jury_demand",
            "signature_block",
            "verification"  # If required
        ],
        tone=[Tone.FORMAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "answer": DocumentTemplate(
        name="Answer",
        category=DocumentCategory.PLEADING,
        description="Responsive pleading to complaint with admissions, denials, and affirmative defenses",
        sections=[
            "caption",
            "introduction",
            "responses_to_allegations",  # Paragraph-by-paragraph
            "affirmative_defenses",
            "prayer_for_relief",
            "signature_block"
        ],
        tone=[Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "counterclaim": DocumentTemplate(
        name="Counterclaim",
        category=DocumentCategory.PLEADING,
        description="Claims by defendant against plaintiff",
        sections=[
            "caption",
            "introduction",
            "parties",
            "factual_allegations",
            "claims_for_relief",
            "prayer_for_relief",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "amended_complaint": DocumentTemplate(
        name="Amended Complaint",
        category=DocumentCategory.PLEADING,
        description="Modified version of original complaint",
        sections=[
            "caption",
            "introduction_noting_amendment",
            "parties",
            "jurisdiction_and_venue",
            "factual_allegations",
            "claims_for_relief",
            "prayer_for_relief",
            "jury_demand",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    # -------------------------------------------------------------------------
    # MOTIONS
    # -------------------------------------------------------------------------

    "motion_sanctions": DocumentTemplate(
        name="Motion for Sanctions",
        category=DocumentCategory.MOTION,
        description="Motion seeking sanctions for misconduct (spoliation, discovery abuse, Rule 11, etc.)",
        sections=[
            "caption",
            "introduction",
            "statement_of_facts",
            "legal_standard",
            "argument",
            "requested_relief",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "motion_to_dismiss": DocumentTemplate(
        name="Motion to Dismiss",
        category=DocumentCategory.MOTION,
        description="Motion seeking dismissal of claims",
        sections=[
            "caption",
            "introduction",
            "statement_of_facts",
            "legal_standard",
            "argument",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "motion_summary_judgment": DocumentTemplate(
        name="Motion for Summary Judgment",
        category=DocumentCategory.MOTION,
        description="Motion seeking judgment without trial on undisputed facts",
        sections=[
            "caption",
            "introduction",
            "statement_of_undisputed_facts",
            "legal_standard",
            "argument",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "motion_to_compel": DocumentTemplate(
        name="Motion to Compel Discovery",
        category=DocumentCategory.MOTION,
        description="Motion seeking court order to compel discovery responses",
        sections=[
            "caption",
            "introduction",
            "procedural_background",
            "discovery_at_issue",
            "meet_and_confer_efforts",
            "legal_standard",
            "argument",
            "requested_relief",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.ASSERTIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "motion_in_limine": DocumentTemplate(
        name="Motion in Limine",
        category=DocumentCategory.MOTION,
        description="Pre-trial motion to exclude or admit evidence",
        sections=[
            "caption",
            "introduction",
            "factual_background",
            "evidence_at_issue",
            "legal_standard",
            "argument",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "opposition_brief": DocumentTemplate(
        name="Opposition Brief",
        category=DocumentCategory.MOTION,
        description="Brief opposing a motion filed by opposing party",
        sections=[
            "caption",
            "introduction",
            "statement_of_facts",
            "legal_standard",
            "argument",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "reply_brief": DocumentTemplate(
        name="Reply Brief",
        category=DocumentCategory.MOTION,
        description="Reply to opposition brief",
        sections=[
            "caption",
            "introduction",
            "argument",  # Responding to opposition points
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    # -------------------------------------------------------------------------
    # DISCOVERY
    # -------------------------------------------------------------------------

    "interrogatories": DocumentTemplate(
        name="Interrogatories",
        category=DocumentCategory.DISCOVERY,
        description="Written questions to be answered under oath",
        sections=[
            "caption",
            "propounding_party_info",
            "definitions",
            "instructions",
            "interrogatories",  # Numbered questions
            "signature_block"
        ],
        tone=[Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "requests_production": DocumentTemplate(
        name="Requests for Production of Documents",
        category=DocumentCategory.DISCOVERY,
        description="Requests for documents and tangible items",
        sections=[
            "caption",
            "propounding_party_info",
            "definitions",
            "instructions",
            "requests",  # Numbered requests
            "signature_block"
        ],
        tone=[Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "requests_admission": DocumentTemplate(
        name="Requests for Admission",
        category=DocumentCategory.DISCOVERY,
        description="Requests for admission of facts or genuineness of documents",
        sections=[
            "caption",
            "propounding_party_info",
            "definitions",
            "instructions",
            "requests",  # Numbered requests
            "signature_block"
        ],
        tone=[Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "deposition_notice": DocumentTemplate(
        name="Notice of Deposition",
        category=DocumentCategory.DISCOVERY,
        description="Notice of intent to take deposition",
        sections=[
            "caption",
            "notice_statement",
            "deponent_information",
            "date_time_location",
            "documents_requested",  # If duces tecum
            "signature_block"
        ],
        tone=[Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    # -------------------------------------------------------------------------
    # BRIEFS AND MEMORANDA
    # -------------------------------------------------------------------------

    "legal_memorandum": DocumentTemplate(
        name="Legal Memorandum",
        category=DocumentCategory.BRIEF,
        description="Internal legal analysis memorandum",
        sections=[
            "header",  # To, From, Date, Re
            "question_presented",
            "brief_answer",
            "statement_of_facts",
            "discussion",
            "conclusion"
        ],
        tone=[Tone.PROFESSIONAL, Tone.FORMAL],
        citation_style=CitationStyle.BLUEBOOK,
        has_signature_block=False
    ),

    "trial_brief": DocumentTemplate(
        name="Trial Brief",
        category=DocumentCategory.BRIEF,
        description="Brief submitted for trial",
        sections=[
            "caption",
            "introduction",
            "statement_of_facts",
            "issues",
            "argument",
            "conclusion",
            "signature_block"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),

    "appellate_brief": DocumentTemplate(
        name="Appellate Brief",
        category=DocumentCategory.BRIEF,
        description="Brief for appeal",
        sections=[
            "cover_page",
            "table_of_contents",
            "table_of_authorities",
            "statement_of_jurisdiction",
            "statement_of_issues",
            "statement_of_case",
            "statement_of_facts",
            "summary_of_argument",
            "argument",
            "conclusion",
            "certificate_of_compliance",
            "certificate_of_service"
        ],
        tone=[Tone.FORMAL, Tone.PERSUASIVE],
        citation_style=CitationStyle.BLUEBOOK,
        has_caption=True,
        has_signature_block=True,
        has_certificate_of_service=True
    ),
}


def get_document_template(document_type: str) -> DocumentTemplate:
    """Get template for a document type.

    Args:
        document_type: The document type identifier

    Returns:
        The DocumentTemplate for that type

    Raises:
        ValueError: If document type is not found
    """
    if document_type not in DOCUMENT_TYPES:
        available = ", ".join(sorted(DOCUMENT_TYPES.keys()))
        raise ValueError(
            f"Unknown document type: '{document_type}'. "
            f"Available types: {available}"
        )
    return DOCUMENT_TYPES[document_type]


def list_document_types() -> dict[str, list[str]]:
    """List all document types grouped by category.

    Returns:
        Dict mapping category names to lists of document types
    """
    by_category: dict[str, list[str]] = {}
    for doc_type, template in DOCUMENT_TYPES.items():
        category = template.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(doc_type)
    return by_category
