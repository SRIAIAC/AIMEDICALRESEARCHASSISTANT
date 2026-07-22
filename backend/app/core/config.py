from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Medical Research Assistant"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    # LLM / embeddings
    llm_provider: str = "ollama"  # ollama | anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    embedding_provider: str = "ollama"  # hash | ollama | sentence_transformers
    embedding_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    ollama_embedding_model: str = "nomic-embed-text"

    # Vector database
    vector_store_provider: str = "chroma"  # chroma | faiss | pinecone
    chroma_persist_dir: str = "./data/chroma"
    pinecone_api_key: str | None = None
    pinecone_environment: str | None = None

    # Relational database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/medresearch"

    # External data source APIs
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_api_key: str | None = None
    ncbi_email: str | None = None
    clinicaltrials_base_url: str = "https://clinicaltrials.gov/api/v2"
    openfda_base_url: str = "https://api.fda.gov"
    rxnav_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    drugbank_api_key: str | None = None
    chembl_base_url: str = "https://www.ebi.ac.uk/chembl/api/data"
    wikipedia_base_url: str = "https://en.wikipedia.org"
    duckduckgo_base_url: str = "https://api.duckduckgo.com"

    # Auth
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS: browsers treat localhost and 127.0.0.1 as distinct origins, so
    # both are listed to cover either way the dev frontend gets opened. Set
    # CORS_ORIGINS to a comma-separated string in production (e.g.
    # "https://example.com"). Kept as a plain str field (not list[str]) —
    # pydantic-settings tries to JSON-decode list-typed env vars before any
    # validator runs, which breaks on a plain comma-separated value.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
