"""
Unit tests for utils.file_utils — filename sanitization and ZIP name generation.

Run:
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    pytest tests/test_file_utils.py -v
"""

from uuid import UUID

from utils.file_utils import (
    deduplicate_filename,
    extract_name_parts,
    generate_zip_filename,
    sanitize_filename,
)

# ============================================================================
# sanitize_filename
# ============================================================================


def test_sanitize_ascii_passthrough():
    assert sanitize_filename("hello-world") == "hello-world"


def test_sanitize_accented_chars():
    assert sanitize_filename("François") == "Francois"


def test_sanitize_apostrophe():
    assert sanitize_filename("O'Brien") == "O-Brien"


def test_sanitize_empty_string():
    assert sanitize_filename("") == ""


def test_sanitize_only_special_chars():
    assert sanitize_filename("@#$%^&*") == ""


def test_sanitize_consecutive_special_chars():
    # Multiple special chars collapse to a single hyphen, then stripped at edges
    assert sanitize_filename("a@@@@b") == "a-b"


def test_sanitize_preserves_dots():
    assert sanitize_filename("file.name.pdf") == "file.name.pdf"


def test_sanitize_strips_hyphens_around_dot_segments():
    # "-seg-" around dots should be stripped per segment
    assert sanitize_filename("-hello-.world-") == "hello.world"


def test_sanitize_mixed_unicode():
    # é, ü, ñ all transliterate cleanly via NFKD
    assert sanitize_filename("café-über-niño") == "cafe-uber-nino"


# ============================================================================
# extract_name_parts
# ============================================================================


def test_extract_name_parts_camel_case():
    assert extract_name_parts({"firstName": "Jane", "lastName": "Doe"}) == ("Jane", "Doe")


def test_extract_name_parts_snake_case():
    assert extract_name_parts({"first_name": "Jane", "last_name": "Doe"}) == ("Jane", "Doe")


def test_extract_name_parts_camel_case_priority_over_snake():
    form_data = {
        "firstName": "Camel",
        "lastName": "Case",
        "first_name": "Snake",
        "last_name": "Case",
    }
    assert extract_name_parts(form_data) == ("Camel", "Case")


def test_extract_name_parts_full_name_two_tokens():
    assert extract_name_parts({"fullName": "Jane Doe"}) == ("Jane", "Doe")


def test_extract_name_parts_full_name_single_token():
    assert extract_name_parts({"fullName": "Madonna"}) == ("Madonna", "")


def test_extract_name_parts_full_name_multi_token():
    # First token = first name, last token = last name
    assert extract_name_parts({"fullName": "Mary Jane Watson"}) == ("Mary", "Watson")


def test_extract_name_parts_snake_full_name():
    assert extract_name_parts({"full_name": "John Smith"}) == ("John", "Smith")


def test_extract_name_parts_empty_form_data():
    assert extract_name_parts({}) == ("", "")


def test_extract_name_parts_missing_name_fields():
    assert extract_name_parts({"email": "a@b.com", "age": 25}) == ("", "")


def test_extract_name_parts_only_first_name_camel():
    # lastName missing — still returns what's available
    assert extract_name_parts({"firstName": "Solo"}) == ("Solo", "")


def test_extract_name_parts_only_last_name_camel():
    assert extract_name_parts({"lastName": "Solo"}) == ("", "Solo")


# ============================================================================
# generate_zip_filename
# ============================================================================

FIXED_ID = UUID("12345678-1234-1234-1234-123456789abc")


def test_generate_zip_filename_normal():
    result = generate_zip_filename(
        field_name="resume",
        form_data={"firstName": "Jane", "lastName": "Doe"},
        original_filename="my_resume.pdf",
        registration_id=FIXED_ID,
    )
    assert result == "doe-jane-resume.pdf"


def test_generate_zip_filename_no_name_falls_back_to_id():
    result = generate_zip_filename(
        field_name="resume",
        form_data={},
        original_filename="document.pdf",
        registration_id=FIXED_ID,
    )
    assert result == f"{FIXED_ID}-resume.pdf"


def test_generate_zip_filename_extracts_extension():
    result = generate_zip_filename(
        field_name="cover",
        form_data={"fullName": "Alice Smith"},
        original_filename="cover_letter.docx",
        registration_id=FIXED_ID,
    )
    assert result.endswith(".docx")


def test_generate_zip_filename_no_extension():
    result = generate_zip_filename(
        field_name="data",
        form_data={"firstName": "Bob", "lastName": "Lee"},
        original_filename="noext",
        registration_id=FIXED_ID,
    )
    assert result == "lee-bob-data"


def test_generate_zip_filename_dotted_original():
    # Extension is the part after the LAST dot
    result = generate_zip_filename(
        field_name="report",
        form_data={"firstName": "X", "lastName": "Y"},
        original_filename="my.report.file.pdf",
        registration_id=FIXED_ID,
    )
    assert result == "y-x-report.pdf"


def test_generate_zip_filename_sanitizes_field_name():
    result = generate_zip_filename(
        field_name="Cover Letter",
        form_data={"firstName": "A", "lastName": "B"},
        original_filename="x.pdf",
        registration_id=FIXED_ID,
    )
    assert result == "b-a-cover-letter.pdf"


def test_generate_zip_filename_sanitizes_name_parts():
    result = generate_zip_filename(
        field_name="resume",
        form_data={"firstName": "François", "lastName": "O'Brien"},
        original_filename="r.pdf",
        registration_id=FIXED_ID,
    )
    assert result == "o-brien-francois-resume.pdf"


# ============================================================================
# deduplicate_filename
# ============================================================================


def test_deduplicate_no_collision():
    assert deduplicate_filename("file.pdf", set()) == "file.pdf"


def test_deduplicate_first_collision():
    used = {"file.pdf"}
    assert deduplicate_filename("file.pdf", used) == "file-2.pdf"


def test_deduplicate_chained_collisions():
    used = {"file.pdf", "file-2.pdf", "file-3.pdf"}
    assert deduplicate_filename("file.pdf", used) == "file-4.pdf"


def test_deduplicate_no_extension():
    used = {"readme"}
    assert deduplicate_filename("readme", used) == "readme-2"


def test_deduplicate_no_extension_chained():
    used = {"readme", "readme-2"}
    assert deduplicate_filename("readme", used) == "readme-3"
