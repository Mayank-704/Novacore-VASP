from backend.attribution import attribute_labeled_address


def test_unverified_label_returns_medium_candidate_and_evidence():
    result = attribute_labeled_address(
        "bc1qexample",
        {
            "bc1qexample": {
                "entity": "Demo Exchange",
                "type": "deposit",
                "source": "Synthetic fixture",
                "verified": False,
            }
        },
    )

    assert result is not None
    candidate, evidence = result
    assert candidate.entity_name == "Demo Exchange"
    assert candidate.confidence == "Medium"
    assert candidate.status == "candidate"
    assert evidence.evidence_type == "direct_label"
    assert evidence.evidence_id in candidate.evidence_ids


def test_verified_label_returns_high_candidate_with_evidence():
    result = attribute_labeled_address(
        "bc1qverified",
        {
            "bc1qverified": {
                "entity": "Verified Exchange",
                "type": "hot-wallet",
                "source": "Verified source",
                "verified": True,
            }
        },
    )

    assert result is not None
    candidate, evidence = result
    assert candidate.confidence == "High"
    assert candidate.status == "corroborated"
    assert evidence.evidence_id in candidate.evidence_ids


def test_unknown_or_malformed_label_returns_none():
    assert attribute_labeled_address("bc1qunknown", {}) is None
    assert attribute_labeled_address(
        "bc1qbad",
        {"bc1qbad": {"entity": "", "type": "deposit", "source": "test"}},
    ) is None


def test_candidate_ids_are_stable_for_same_input():
    labels = {
        "bc1qexample": {
            "entity": "Demo Exchange",
            "type": "deposit",
            "source": "Fixture",
            "verified": False,
        }
    }
    first = attribute_labeled_address("bc1qexample", labels)
    second = attribute_labeled_address("bc1qexample", labels)

    assert first is not None and second is not None
    assert first[0].candidate_id == second[0].candidate_id
    assert first[1].evidence_id == second[1].evidence_id
