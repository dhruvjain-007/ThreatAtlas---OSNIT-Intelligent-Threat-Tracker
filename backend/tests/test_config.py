from app.core.config import Settings


def test_mongodb_config_defaults():
    settings = Settings()
    assert settings.MONGO_URI is not None
    assert settings.MONGO_DB_NAME == "threat_atlas"
    assert "mongodb://" in settings.MONGO_URI


def test_mongodb_config_custom_values(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://test_host:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "test_db")

    custom_settings = Settings()
    assert custom_settings.MONGO_URI == "mongodb://test_host:27017"
    assert custom_settings.MONGO_DB_NAME == "test_db"


def test_production_mongodb_and_cors_env(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb+srv://user:pass@cluster.mongodb.net/test?retryWrites=true")
    monkeypatch.setenv("DATABASE_NAME", "prod_threat_atlas")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://threatatlas.vercel.app, https://custom-domain.com")

    settings = Settings()
    assert settings.MONGO_URI == "mongodb+srv://user:pass@cluster.mongodb.net/test?retryWrites=true"
    assert settings.MONGODB_URL == "mongodb+srv://user:pass@cluster.mongodb.net/test?retryWrites=true"
    assert settings.MONGO_DB_NAME == "prod_threat_atlas"
    assert settings.DATABASE_NAME == "prod_threat_atlas"
    assert "https://threatatlas.vercel.app" in settings.ALLOWED_ORIGINS
    assert "https://custom-domain.com" in settings.ALLOWED_ORIGINS


def test_mask_mongodb_uri():
    """Verify MongoDB URI passwords are masked for logging."""
    from app.db.session import mask_mongodb_uri

    uri_with_password = "mongodb+srv://admin:MySecretPassword123@cluster.mongodb.net/threat_atlas?retryWrites=true"
    masked = mask_mongodb_uri(uri_with_password)
    assert "MySecretPassword123" not in masked
    assert "admin:****@cluster.mongodb.net" in masked

    uri_without_password = "mongodb://localhost:27017/threat_atlas"
    assert mask_mongodb_uri(uri_without_password) == uri_without_password
    assert mask_mongodb_uri("") == ""


def test_semantic_embeddings_setting():
    """Verify ENABLE_SEMANTIC_EMBEDDINGS defaults to False."""
    from app.intelligence.config import ENABLE_SEMANTIC_EMBEDDINGS
    from app.core.config import Settings

    settings = Settings()
    assert settings.ENABLE_SEMANTIC_EMBEDDINGS is False
    assert ENABLE_SEMANTIC_EMBEDDINGS is False


