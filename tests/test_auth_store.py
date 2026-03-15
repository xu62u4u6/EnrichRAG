from enrichrag import auth_store
from enrichrag.settings import settings


def test_auth_and_history_roundtrip(tmp_path):
    original_db = settings.auth_db_path
    original_user = settings.auth_default_email
    original_password = settings.auth_default_password
    try:
        settings.auth_db_path = str(tmp_path / "auth.db")
        settings.auth_default_email = "lab@enrichrag.local"
        settings.auth_default_password = "secret-demo"

        auth_store.init_storage()
        user = auth_store.authenticate_user("lab@enrichrag.local", "secret-demo")
        assert user is not None

        token = auth_store.create_session(user["id"])
        session_user = auth_store.get_user_by_session(token)
        assert session_user["email"] == "lab@enrichrag.local"

        analysis_id = auth_store.save_analysis_run(
            user["id"],
            {
                "disease_context": "cancer",
                "input_genes": ["BRCA1", "BRCA2"],
                "enrichment_results": {},
            },
        )
        history = auth_store.list_analysis_runs(user["id"])
        assert history[0]["id"] == analysis_id
        assert history[0]["gene_count"] == 2

        item = auth_store.get_analysis_run(user["id"], analysis_id)
        assert item["disease_context"] == "cancer"
        assert item["input_genes"] == ["BRCA1", "BRCA2"]
    finally:
        settings.auth_db_path = original_db
        settings.auth_default_email = original_user
        settings.auth_default_password = original_password
