import io
import uuid
import json
from typing import List
from datetime import datetime
from html import escape
from app.schemas.event import EventResponse

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.colors import HexColor
# pyrefly: ignore [missing-import]
from stix2 import Incident, Bundle


def generate_pdf(events: List[EventResponse]) -> bytes:
    """Generate a simple PDF intelligence brief from a list of events."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = styles['Heading1']
    event_title_style = styles['Heading3']

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        textColor=HexColor('#555555'),
        fontSize=9,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        spaceAfter=20,
        leading=14
    )

    story = []

    # Header
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph("ThreatAtlas Intelligence Export", title_style))
    story.append(Paragraph(f"Generated: {now_str} | Total Events: {len(events)}", meta_style))
    story.append(Spacer(1, 20))

    for event in events:
        # Event Title
        story.append(Paragraph(escape(event.title), event_title_style))

        # Meta info
        meta_parts = [
            f"Date: {event.event_timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Level: {escape(event.threat_level)} ({event.threat_score:.1f})",
            f"Credibility: {event.credibility_score:.1f}",
            f"Type: {escape(event.event_type or 'Unknown')}",
        ]
        if event.location_name:
            meta_parts.append(f"Location: {escape(event.location_name)}")
        if event.country_code:
            meta_parts.append(f"Country: {escape(event.country_code.upper())}")

        story.append(Paragraph(" | ".join(meta_parts), meta_style))

        # Summary
        summary = escape(event.summary or "No summary available.")
        story.append(Paragraph(summary, body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_stix_bundle(events: List[EventResponse]) -> bytes:
    """Generate a STIX 2.1 Bundle containing an Incident SDO for each event."""
    stix_objects = []

    for event in events:
        # Generate deterministic UUIDv5 from the MongoDB ObjectId string
        event_uuid = uuid.uuid5(uuid.NAMESPACE_OID, str(event.id))
        stix_id = f"incident--{event_uuid}"

        # Build custom properties dictionary safely
        custom_props = {
            "x_threatatlas_score": event.threat_score,
            "x_threatatlas_credibility": event.credibility_score,
            "x_threatatlas_level": event.threat_level,
        }

        if event.country_code:
            custom_props["x_threatatlas_country"] = event.country_code

        if event.location and event.location.coordinates and len(event.location.coordinates) >= 2:
            custom_props["x_threatatlas_location"] = {
                "lon": float(event.location.coordinates[0]),
                "lat": float(event.location.coordinates[1])
            }

        if event.event_type:
            custom_props["x_threatatlas_type"] = event.event_type

        # Create the Incident object
        incident = Incident(
            id=stix_id,
            name=event.title,
            description=event.summary or "No summary provided.",
            created=event.created_at,
            modified=event.updated_at,
            allow_custom=True,  # Required by stix2 to allow x_ properties
            **custom_props
        )
        stix_objects.append(incident)

    bundle = Bundle(objects=stix_objects, allow_custom=True)
    return bundle.serialize().encode("utf-8")
