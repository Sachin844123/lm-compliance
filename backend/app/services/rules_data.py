"""
Reference data encoding the mandatory declarations required under the
Legal Metrology (Packaged Commodities) Rules, 2011 (India).

NOTE: This is a representative, simplified digitisation of the rules for the
purpose of an automated screening prototype. Rule text, thresholds and
schedules should be verified against the current gazette notification /
amendments by a Legal Metrology domain expert before any enforcement use.
"""

# Each entry describes one mandatory declaration under Rule 6 (principal
# display panel declarations) and related rules. `patterns` are regexes
# (case-insensitive) run against OCR text to detect the declaration.
MANDATORY_DECLARATIONS = [
    {
        "key": "manufacturer_details",
        "label": "Name & address of manufacturer/packer/importer",
        "rule_ref": "Rule 6(1)(a)",
        "patterns": [
            r"(manufactured|mfd|marketed|packed|packer|imported)\s*(by|for)?[^\n]{0,80}",
            r"\bmfg\.?\s*by\b",
        ],
        "anchor_keywords": ["MANUFACTURED BY", "MFD BY", "MARKETED BY", "PACKED BY", "PACKER"],
        "requires_font_check": False,
    },
    {
        "key": "common_name",
        "label": "Common / generic name of the commodity",
        "rule_ref": "Rule 6(1)(b)",
        "patterns": [r"[a-zA-Z]{3,}"],
        "requires_font_check": False,
        "fallback_note": "Verify manually - free text, not reliably regex-detectable.",
    },
    {
        "key": "net_quantity",
        "label": "Net quantity (weight/volume/number/measure)",
        "rule_ref": "Rule 6(1)(c) & Rule 8",
        "patterns": [
            r"net\s*(wt|weight|qty|quantity|vol|volume|contents)?\.?\s*[:\-]?\s*\d+(\.\d+)?\s*(kg|g|gm|gms|mg|l|ltr|litre|liter|ml|cl|pcs|pieces|n|u|units?)\b",
            r"\b\d+(\.\d+)?\s*(kg|g|gm|gms|ml|l|ltr|litre)\b",
        ],
        "anchor_keywords": ["NET WEIGHT", "NET WT", "NET QTY", "NET QUANTITY", "NET VOLUME", "NET CONTENTS"],
        "requires_font_check": True,
    },
    {
        "key": "mfg_date",
        "label": "Month & year of manufacture/packing/import",
        "rule_ref": "Rule 6(1)(d) & Rule 18",
        "patterns": [
            r"(mfg|manufactured|packed|pkd|packing|mfd|import(ed)?)\.?\s*(date|on|dt)?\.?\s*[:\-]?\s*(\d{1,2}[\/\-. ])?\d{2,4}",
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*[\-/]?\s*\d{2,4}",
        ],
        "anchor_keywords": ["MFG DATE", "MFD DATE", "MANUFACTURING DATE", "PACKED ON", "PACKAGING DATE", "DATE OF MANUFACTURE"],
        "requires_font_check": False,
    },
    {
        "key": "mrp",
        "label": "Maximum Retail Price (inclusive of all taxes)",
        "rule_ref": "Rule 6(1)(e) & Rule 18",
        "patterns": [
            r"(mrp|m\.r\.p\.?|maximum\s*retail\s*price)[^\d]{0,25}(rs\.?|inr|₹)?\s?\d+([.,]\d{1,2})?",
            r"(₹|rs\.?)\s?\d+([.,]\d{1,2})?[^\n]{0,40}(incl(usive)?\s*of\s*(all\s*)?tax)",
        ],
        "anchor_keywords": ["MRP", "M.R.P", "MAXIMUM RETAIL PRICE", "INCLUSIVE OF ALL TAXES"],
        "requires_font_check": True,
    },
    {
        "key": "consumer_care",
        "label": "Consumer/customer care name, address & contact",
        "rule_ref": "Rule 6(1)(f)",
        "patterns": [
            r"(consumer|customer)\s*care",
            r"(toll[\s-]*free|helpline|for\s*(complaints|feedback|queries))",
            r"\b\d{6}\b",
            r"[\w.+-]+@[\w-]+\.[a-z]{2,}",
        ],
        "anchor_keywords": ["CUSTOMER CARE", "CONSUMER CARE", "TOLL FREE", "HELPLINE", "FOR COMPLAINTS"],
        "requires_font_check": False,
    },
    {
        "key": "country_of_origin",
        "label": "Country of origin (imported goods)",
        "rule_ref": "Rule 6(8) / Legal Metrology (PC) Amendment, 2017",
        "patterns": [r"country\s*of\s*origin", r"made\s*in\s*[a-z]+"],
        "anchor_keywords": ["COUNTRY OF ORIGIN", "MADE IN"],
        "requires_font_check": False,
        "optional": True,
    },
    {
        "key": "unit_sale_price",
        "label": "Unit sale price (Rs. per kg / litre / unit)",
        "rule_ref": "Rule 6(1)(e), Explanation",
        "patterns": [r"(unit\s*sale\s*price|price\s*per\s*(kg|g|l|ml|unit))"],
        "anchor_keywords": ["UNIT SALE PRICE", "PRICE PER KG", "PRICE PER LITRE"],
        "requires_font_check": False,
        "optional": True,
    },
]

# Second Schedule (Rule 6/7): minimum height of numerals/letters used for the
# net quantity declaration, based on the area of the principal display panel.
# Format: (max_area_cm2_inclusive_or_None_for_unbounded, min_height_mm)
NET_QUANTITY_FONT_TABLE = [
    (100, 1.0),
    (500, 2.0),
    (2500, 4.0),
    (None, 6.0),
]

# MRP declaration is required to use numerals at least 1mm tall per Rule 6;
# in practice enforcement expects it to be at least as prominent as net
# quantity, so we reuse a flat baseline minimum here for the demo checker.
MRP_MIN_HEIGHT_MM = 1.0


def min_required_mm_for_net_quantity(pdp_area_cm2: float | None) -> float:
    if pdp_area_cm2 is None:
        # Without a known panel area we cannot size-check against the
        # schedule; fall back to the smallest statutory minimum.
        return NET_QUANTITY_FONT_TABLE[0][1]
    for max_area, min_mm in NET_QUANTITY_FONT_TABLE:
        if max_area is None or pdp_area_cm2 <= max_area:
            return min_mm
    return NET_QUANTITY_FONT_TABLE[-1][1]
