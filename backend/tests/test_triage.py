from app import triage


class _Q:
    def __init__(self, question, row_index=0):
        self.question = question
        self.row_index = row_index


def _qs(texts):
    return [_Q(t, i) for i, t in enumerate(texts)]


def test_detects_caiq_from_filename():
    assert triage.detect_framework("Vendor_CAIQ_v4.xlsx", _qs(["Do you encrypt data?"])) == "CAIQ"


def test_detects_caiq_lite_by_size():
    qs = _qs([f"Control {i}?" for i in range(50)])
    assert triage.detect_framework("caiq-lite.xlsx", qs) == "CAIQ Lite"


def test_detects_caiq_from_control_ids():
    qs = _qs(["AIS-01 Do you...", "IAM-02 Are roles...", "DCS-05 Is the facility..."])
    assert triage.detect_framework("questions.xlsx", qs) == "CAIQ"


def test_detects_sig_and_vsaq():
    assert triage.detect_framework("SIG_Lite_2025.xlsx", _qs(["Q?"])) == "SIG Lite"
    assert triage.detect_framework("google-vsaq.csv", _qs(["Q?"])) == "VSAQ"


def test_unknown_is_custom():
    assert triage.detect_framework("vendor_questions.xlsx", _qs(["Do you have MFA?"])) == "Custom"


def test_out_of_scope_needs_cloud_only_signal():
    # No documents -> we can't infer cloud-only -> no suggestions.
    assert triage.out_of_scope_suggestions(-1, _qs(["Describe your data centre access controls."])) == {}
