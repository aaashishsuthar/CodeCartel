"""
Agent Kautilya — Data Validator, Cleaner & Local Government Directory (LGD) Matcher
Implements official LGD state & district code resolution (Source S10 from websites_needed_to_get_data.docx),
fuzzy district name matching, currency and text sanitization, and data quality scoring.
"""

import re
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy.orm import Session

from ..models.project import ProjectModel
from ..models.allocation import MPAllocation

# Official Local Government Directory (LGD) State Codes
LGD_STATE_CODES: Dict[str, int] = {
    "andaman and nicobar islands": 35,
    "andhra pradesh": 28,
    "arunachal pradesh": 12,
    "assam": 18,
    "bihar": 10,
    "chandigarh": 4,
    "chhattisgarh": 22,
    "dadra and nagar haveli and daman and diu": 26,
    "delhi": 7,
    "goa": 30,
    "gujarat": 24,
    "haryana": 6,
    "himachal pradesh": 2,
    "jammu and kashmir": 1,
    "jharkhand": 20,
    "karnataka": 29,
    "kerala": 32,
    "ladakh": 37,
    "lakshadweep": 31,
    "madhya pradesh": 23,
    "maharashtra": 27,
    "manipur": 14,
    "meghalaya": 17,
    "mizoram": 15,
    "nagaland": 13,
    "odisha": 21,
    "puducherry": 34,
    "punjab": 3,
    "rajasthan": 8,
    "sikkim": 11,
    "tamil nadu": 33,
    "telangana": 36,
    "tripura": 16,
    "uttar pradesh": 9,
    "uttarakhand": 5,
    "west bengal": 19,
}

# Key LGD District Codes (Official Codes crosswalk)
LGD_DISTRICT_CODES: Dict[str, Tuple[int, int]] = {
    # District Name (normalized) -> (LGD_District_Code, LGD_State_Code)
    "gautam buddha nagar": (140, 9),
    "varanasi": (178, 9),
    "lucknow": (157, 9),
    "agra": (124, 9),
    "kanpur nagar": (154, 9),
    "prayagraj": (125, 9),
    "allahabad": (125, 9),
    "ayodhya": (137, 9),
    "faizabad": (137, 9),
    "gorakhpur": (141, 9),
    "mathura": (160, 9),
    "meerut": (161, 9),
    "ghaziabad": (139, 9),
    "aligarh": (126, 9),
    "bareilly": (132, 9),
    "hathras": (159, 9),
    "aonla": (132, 9),

    "mumbai": (485, 27),
    "mumbai city": (485, 27),
    "mumbai suburban": (486, 27),
    "pune": (492, 27),
    "nagpur": (489, 27),
    "thane": (497, 27),
    "nashik": (490, 27),
    "aurangabad": (473, 27),
    "chhatrapati sambhajinagar": (473, 27),

    "east khasi hills": (274, 17),
    "shillong": (274, 17),
    "west khasi hills": (276, 17),
    "ri bhoi": (275, 17),
    "west garo hills": (277, 17),

    "bengaluru urban": (528, 29),
    "bangalore urban": (528, 29),
    "bengaluru rural": (527, 29),
    "mysuru": (545, 29),
    "mysore": (545, 29),

    "chennai": (565, 33),
    "coimbatore": (566, 33),
    "madurai": (573, 33),

    "hyderabad": (674, 36),
    "rangareddy": (684, 36),
    "medchal malkajgiri": (680, 36),

    "ahmedabad": (442, 24),
    "surat": (460, 24),
    "vadodara": (462, 24),
    "gandhinagar": (448, 24),

    "patna": (214, 10),
    "gaya": (210, 10),
    "muzaffarpur": (213, 10),

    "kolkata": (316, 19),
    "howrah": (314, 19),
    "north 24 parganas": (321, 19),
    "south 24 parganas": (325, 19),

    "jaipur": (95, 8),
    "jodhpur": (97, 8),
    "udaipur": (114, 8),
    "kota": (99, 8),

    "bhopal": (392, 23),
    "indore": (406, 23),
    "gwalior": (403, 23),
    "jabalpur": (407, 23),

    "kamrup metropolitan": (292, 18),
    "guwahati": (292, 18),
    "cuttack": (353, 21),
    "khordha": (363, 21),
    "bhubaneswar": (363, 21),

    "new delhi": (87, 7),
    "south delhi": (85, 7),
    "north delhi": (83, 7),
    "east delhi": (80, 7),
    "west delhi": (86, 7),
}

# Aliases and alternate spellings
DISTRICT_ALIASES: Dict[str, str] = {
    "noida": "gautam buddha nagar",
    "gautambudhnagar": "gautam buddha nagar",
    "kashi": "varanasi",
    "banaras": "varanasi",
    "benares": "varanasi",
    "shilong": "shillong",
    "gurgaon": "gurugram",
    "bangalore": "bengaluru urban",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "baroda": "vadodara",
    "trivandrum": "thiruvananthapuram",
    "cochin": "ernakulam",
}


class LGDDirectoryMatcher:
    """
    Local Government Directory (LGD) Matcher and Geo-Coding Engine.
    Resolves free-text constituency/district names to official LGD codes.
    """

    @classmethod
    def normalize_name(cls, name: Optional[str]) -> str:
        if not name:
            return ""
        cleaned = name.strip().lower()
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def match_district(cls, district_name: Optional[str], state_name: Optional[str] = None) -> Tuple[Optional[int], Optional[int], str]:
        """
        Matches a district or constituency name to official LGD (district_code, state_code, canonical_name).
        Employs:
          1. Exact match against canonical LGD districts.
          2. Alias dictionary lookup.
          3. State-bounded fuzzy matching (difflib close match >= 0.75).
          4. State code lookup.
        """
        if not district_name:
            state_code = cls.get_state_code(state_name)
            return None, state_code, "Unknown"

        norm = cls.normalize_name(district_name)

        # 1. Direct match
        if norm in LGD_DISTRICT_CODES:
            d_code, s_code = LGD_DISTRICT_CODES[norm]
            return d_code, s_code, norm.title()

        # 2. Alias match
        if norm in DISTRICT_ALIASES:
            canonical = DISTRICT_ALIASES[norm]
            if canonical in LGD_DISTRICT_CODES:
                d_code, s_code = LGD_DISTRICT_CODES[canonical]
                return d_code, s_code, canonical.title()

        # 3. Fuzzy match against known districts
        candidates = list(LGD_DISTRICT_CODES.keys())
        matches = difflib.get_close_matches(norm, candidates, n=1, cutoff=0.75)
        if matches:
            best_match = matches[0]
            d_code, s_code = LGD_DISTRICT_CODES[best_match]
            return d_code, s_code, best_match.title()

        # 4. Fallback: match state code only
        state_code = cls.get_state_code(state_name)
        return None, state_code, norm.title()

    @classmethod
    def get_state_code(cls, state_name: Optional[str]) -> Optional[int]:
        if not state_name:
            return None
        norm_state = cls.normalize_name(state_name)
        return LGD_STATE_CODES.get(norm_state)


class DataSanitizer:
    """
    Sanitizes raw external strings, currency amounts, and dates from government scrapes.
    """

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        # Remove embedded newlines, carriage returns, and control characters
        cleaned = re.sub(r"[\r\n\t]+", " ", str(text))
        # Remove multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Remove trailing strange characters
        cleaned = cleaned.strip(";:- ")
        return cleaned

    @staticmethod
    def clean_currency(val: Any) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return max(0.0, float(val))

        s = str(val).strip()
        # Remove currency symbols (₹, Rs., INR) and commas, preserve decimal point
        s = re.sub(r"[₹\s]|rs\.?|inr", "", s, flags=re.IGNORECASE)
        s = s.replace(",", "")
        try:
            return max(0.0, float(s))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def clean_date(val: Any) -> Optional[datetime]:
        if not val:
            return None
        if isinstance(val, datetime):
            return val

        s = str(val).strip()
        # Try standard formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d"
        ]:
            try:
                return datetime.strptime(s[:19] if "T" in s else s[:10], fmt[:len(s)])
            except Exception:
                continue

        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def clean_agency_name(raw_name: Optional[str]) -> str:
        if not raw_name:
            return "District Authority"
        cleaned = DataSanitizer.clean_text(raw_name)
        # Remove leading "Office of the", "Office of", etc.
        cleaned = re.sub(r"^(office of the|office of|the)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned[:90] if cleaned else "District Authority"


class DataCleanerEngine:
    """
    Master Ingestion Cleaning and LGD Enrichment Engine.
    """

    def __init__(self):
        self.sanitizer = DataSanitizer()
        self.lgd_matcher = LGDDirectoryMatcher()

    def resolve_lgd_codes(self, district: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolves district and state names to official LGD codes and canonical designations.
        """
        d_code, s_code, canonical = self.lgd_matcher.match_district(district, state)
        status = "EXACT_OR_ALIAS" if d_code is not None else ("STATE_ONLY" if s_code is not None else "UNMATCHED")
        return {
            "query_district": district,
            "query_state": state,
            "canonical_name": canonical,
            "lgd_district_code": d_code,
            "lgd_state_code": s_code,
            "match_status": status
        }

    def clean_and_enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes record fields and enriches with official LGD codes.
        """
        cleaned = dict(record)
        # Clean text
        if "description" in cleaned:
            cleaned["description"] = self.sanitizer.clean_text(cleaned["description"])
        if "work_type" in cleaned:
            cleaned["work_type"] = self.sanitizer.clean_text(cleaned["work_type"])
        if "vendor" in cleaned:
            cleaned["vendor"] = self.sanitizer.clean_agency_name(cleaned["vendor"])

        # Clean amounts
        for amt_col in ["sanctioned_amount", "bill_amount", "uc_amount", "expenditure"]:
            if amt_col in cleaned:
                cleaned[amt_col] = self.sanitizer.clean_currency(cleaned[amt_col])

        # LGD District & State Matching
        district = cleaned.get("district") or cleaned.get("constituency")
        state = cleaned.get("state")
        d_code, s_code, canonical = self.lgd_matcher.match_district(district, state)
        cleaned["lgd_district_code"] = d_code
        cleaned["lgd_state_code"] = s_code
        if canonical and canonical != "Unknown":
            cleaned["canonical_district"] = canonical

        return cleaned

    def clean_and_enrich_database(self, db: Session, batch_size: int = 500) -> Dict[str, Any]:
        """
        Scans all projects and allocations in the database:
          1. Sanitizes free text and numbers.
          2. Enriches with LGD district and state codes.
          3. Calculates overall data quality score (0 - 100%).
        """
        total_projects = db.query(ProjectModel).count()
        matched_lgd = 0
        sanitized_count = 0

        # Query all projects in chunks
        offset = 0
        while offset < total_projects:
            projects = db.query(ProjectModel).offset(offset).limit(batch_size).all()
            if not projects:
                break

            for p in projects:
                # Sanitize text
                clean_desc = self.sanitizer.clean_text(p.description)
                clean_vendor = self.sanitizer.clean_agency_name(p.vendor)
                if clean_desc != p.description or clean_vendor != p.vendor:
                    p.description = clean_desc
                    p.vendor = clean_vendor
                    sanitized_count += 1

                # Match LGD codes
                dist_lookup = p.district or p.constituency
                d_code, s_code, canonical = self.lgd_matcher.match_district(dist_lookup, p.state)
                p.lgd_district_code = d_code
                p.lgd_state_code = s_code

                if d_code is not None:
                    matched_lgd += 1

            db.commit()
            offset += batch_size

        match_rate = round((matched_lgd / total_projects * 100), 2) if total_projects > 0 else 0.0
        quality_score = min(100.0, round(70.0 + (match_rate * 0.3), 1))

        return {
            "total_projects_processed": total_projects,
            "lgd_district_matched": matched_lgd,
            "lgd_match_rate_pct": match_rate,
            "sanitized_records_count": sanitized_count,
            "data_quality_score": quality_score,
            "timestamp": datetime.utcnow().isoformat()
        }
