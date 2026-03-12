from enrichrag.core.relation_extractor import BioRelation


def test_relation_normalization_maps_unknown_labels():
    rel1 = BioRelation(
        source="ATM",
        source_type="gene",
        target="BRCA1",
        target_type="gene",
        relation="impact",
        evidence="ATM impacts BRCA1 signaling.",
    )
    rel2 = BioRelation(
        source="PARP1",
        source_type="gene",
        target="DNA repair",
        target_type="pathway",
        relation="target",
        evidence="PARP1 is a target in DNA repair.",
    )

    assert rel1.relation == "associate"
    assert rel2.relation == "associate"
